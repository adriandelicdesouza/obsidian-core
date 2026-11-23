import json
from datetime import UTC, datetime

import pytest

from obsidian_core import RawStore, Vault
from obsidian_core.checkpoints import (
    Checkpoint,
    CheckpointStatus,
    CheckpointStore,
    run_collector,
)
from obsidian_core.ingestion import Ingestor

from .collector_fakes import BASE, ListCollector, event

NOW = datetime(2026, 11, 23, 12, tzinfo=UTC)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "vault").mkdir()
    return Vault(tmp_path / "vault")


@pytest.fixture
def checkpoints(tmp_path):
    return CheckpointStore(tmp_path / "state")


def archived(vault):
    return RawStore(vault).read_day("sensor", BASE.date())


def run(collector, vault, checkpoints, **kwargs):
    return run_collector(collector, Ingestor(RawStore(vault)), checkpoints, **kwargs)


# Checkpoint store


def test_missing_checkpoint(checkpoints):
    assert checkpoints.load("sensor:a").status is CheckpointStatus.MISSING


def test_save_and_load_round_trip(checkpoints):
    saved = Checkpoint("sensor:a", "7", NOW, 7)
    path = checkpoints.save(saved)

    loaded = checkpoints.load("sensor:a")

    assert loaded.status is CheckpointStatus.VALID
    assert loaded.checkpoint == saved
    assert path.name == "sensor_a.json"
    assert [p.name for p in path.parent.iterdir()] == ["sensor_a.json"]  # no temp files left


def test_corrupt_checkpoint_is_moved_aside_not_deleted(checkpoints):
    path = checkpoints.path_for("sensor:a")
    path.parent.mkdir(parents=True)
    path.write_text("{not json")

    loaded = checkpoints.load("sensor:a")

    assert loaded.status is CheckpointStatus.CORRUPT
    assert not path.exists()
    [moved] = path.parent.glob("sensor_a.json.corrupt-*")
    assert moved.read_text() == "{not json"


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"format": 99, "collector": "sensor:a", "cursor": "1", "updated_at": NOW.isoformat()},
        {"format": 1, "collector": "other", "cursor": "1", "updated_at": NOW.isoformat()},
        {"format": 1, "collector": "sensor:a", "cursor": "", "updated_at": NOW.isoformat()},
        {"format": 1, "collector": "sensor:a", "cursor": "1", "updated_at": "yesterday"},
        {"format": 1, "collector": "sensor:a", "cursor": "1", "updated_at": "2026-11-23T12:00"},
        {
            "format": 1,
            "collector": "sensor:a",
            "cursor": "1",
            "updated_at": NOW.isoformat(),
            "events_seen": -1,
        },
    ],
)
def test_invalid_checkpoints_are_reported(checkpoints, data):
    path = checkpoints.path_for("sensor:a")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data))

    loaded = checkpoints.load("sensor:a")

    assert loaded.status is CheckpointStatus.INVALID
    assert loaded.checkpoint is None
    assert loaded.detail


# Runner


def test_first_run_collects_everything_and_checkpoints(vault, checkpoints):
    collector = ListCollector([event(n) for n in range(5)])

    report = run(collector, vault, checkpoints, collected_at=NOW)

    assert (report.new, report.known, report.conflicts) == (5, 0, [])
    assert report.checkpoint_status is CheckpointStatus.MISSING
    assert checkpoints.load("sensor:a").checkpoint.cursor == "4"
    assert checkpoints.load("sensor:a").checkpoint.events_seen == 5
    assert len(archived(vault)) == 5


def test_resume_from_checkpoint_only_collects_new_events(vault, checkpoints):
    events = [event(n) for n in range(5)]
    run(ListCollector(events[:3]), vault, checkpoints)

    collector = ListCollector(events)
    report = run(collector, vault, checkpoints)

    assert collector.calls == ["2"]
    assert (report.new, report.known) == (2, 0)
    assert len(archived(vault)) == 5


def test_interrupted_run_resumes_without_loss_or_duplicates(vault, checkpoints):
    events = [event(n) for n in range(10)]

    with pytest.raises(RuntimeError):
        run(ListCollector(events, fail_after=7), vault, checkpoints, checkpoint_every=3)

    # 7 ingested, checkpoint only covers the first 6 (saved every 3)
    assert checkpoints.load("sensor:a").checkpoint.cursor == "5"
    assert len(archived(vault)) == 7

    report = run(ListCollector(events), vault, checkpoints)

    assert (report.new, report.known) == (3, 1)  # event 6 replayed safely
    assert len(archived(vault)) == 10


@pytest.mark.parametrize("damage", ["corrupt", "lost"])
def test_damaged_or_lost_checkpoint_recovers_safely(vault, checkpoints, damage):
    events = [event(n) for n in range(4)]
    run(ListCollector(events), vault, checkpoints)

    if damage == "corrupt":
        checkpoints.path_for("sensor:a").write_text("garbage")
    else:
        checkpoints.clear("sensor:a")

    report = run(ListCollector(events), vault, checkpoints)

    assert report.started_from is None
    assert (report.new, report.known) == (0, 4)
    assert len(archived(vault)) == 4
    assert checkpoints.load("sensor:a").status is CheckpointStatus.VALID


def test_stale_checkpoint_behind_archive_is_safe(vault, checkpoints):
    events = [event(n) for n in range(6)]
    run(ListCollector(events), vault, checkpoints)
    checkpoints.save(Checkpoint("sensor:a", "1", NOW))  # older than the archive

    report = run(ListCollector(events), vault, checkpoints)

    assert (report.new, report.known) == (0, 4)
    assert len(archived(vault)) == 6


def test_cursor_rejected_by_collector_restarts_from_beginning(vault, checkpoints):
    events = [event(n) for n in range(3)]
    checkpoints.save(Checkpoint("sensor:a", "99", NOW, 50))
    collector = ListCollector(events)

    report = run(collector, vault, checkpoints)

    assert collector.calls == ["99", None]
    assert report.restarted_from_beginning
    assert "99" in report.detail
    assert report.new == 3
    assert checkpoints.load("sensor:a").checkpoint.cursor == "2"
    assert checkpoints.load("sensor:a").checkpoint.events_seen == 3


def test_rejected_cursor_with_empty_source_does_not_keep_bad_cursor(vault, checkpoints):
    checkpoints.save(Checkpoint("sensor:a", "99", NOW))
    run(ListCollector([]), vault, checkpoints)

    assert checkpoints.load("sensor:a").status is CheckpointStatus.MISSING


def test_checkpoint_is_not_history(vault, checkpoints):
    # A checkpoint far ahead of the archive must not make missing events "exist".
    events = [event(n) for n in range(3)]
    checkpoints.save(Checkpoint("sensor:a", "2", NOW))

    report = run(ListCollector(events), vault, checkpoints)

    assert report.new == 0
    with pytest.raises(FileNotFoundError):
        archived(vault)  # the gap is real; reconciliation finds it, the checkpoint does not


def test_conflicts_are_reported_and_archive_kept(vault, checkpoints):
    run(ListCollector([event(1)]), vault, checkpoints)
    checkpoints.clear("sensor:a")

    report = run(ListCollector([event(1, value=999)]), vault, checkpoints)

    assert len(report.conflicts) == 1
    assert [r.payload for r in archived(vault)] == [{"value": 1}]


def test_collector_yielding_wrong_source_is_rejected(vault, checkpoints):
    collector = ListCollector([event(1, source="other")])

    with pytest.raises(ValueError, match="expected 'sensor'"):
        run(collector, vault, checkpoints)


def test_checkpoint_every_must_be_positive(vault, checkpoints):
    with pytest.raises(ValueError):
        run(ListCollector([]), vault, checkpoints, checkpoint_every=0)
