from datetime import UTC, datetime, timedelta

import pytest

from obsidian_core import RawStore, Vault
from obsidian_core.checkpoints import Checkpoint, CheckpointStatus, CheckpointStore, run_collector
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


def ingestor(vault):
    return Ingestor(RawStore(vault))


def log_text(vault):
    path = vault.path / RawStore(vault).day_path("sensor", BASE.date())
    return path.read_text() if path.exists() else None


def reconcile(*args, **kwargs):
    from obsidian_core.reconciliation import reconcile as run

    return run(*args, collected_at=NOW, **kwargs)


def test_consistent_archive(vault, checkpoints):
    events = [event(n) for n in range(4)]
    run_collector(ListCollector(events), ingestor(vault), checkpoints)

    report = reconcile(ListCollector(events), ingestor(vault), checkpoints=checkpoints)

    assert report.consistent
    assert (report.examined, report.present, report.missing) == (4, 4, [])
    assert report.checkpoint_status is CheckpointStatus.VALID
    assert report.checkpoint_cursor_seen
    assert not report.checkpoint_ahead_of_archive


def test_gap_hidden_by_checkpoint_is_found_without_writing(vault, checkpoints):
    events = [event(n) for n in range(5)]
    run_collector(ListCollector(events[:2]), ingestor(vault), checkpoints)
    # Simulate a checkpoint saved ahead of the archive (e.g. archive restored from backup).
    checkpoints.save(Checkpoint("sensor:a", "3", NOW))

    # A normal run trusts the checkpoint and never sees events 2 and 3.
    assert run_collector(ListCollector(events), ingestor(vault), checkpoints).new == 1
    before = log_text(vault)

    report = reconcile(ListCollector(events), ingestor(vault), checkpoints=checkpoints)

    assert [r.identifiers["seq"] for r in report.missing] == [2, 3]
    assert report.checkpoint_ahead_of_archive
    assert report.repaired == 0
    assert not report.consistent
    assert log_text(vault) == before  # read-only without repair


def test_repair_appends_only_missing_events(vault, checkpoints):
    events = [event(n) for n in range(5)]
    for n in (0, 1, 4):
        ingestor(vault).ingest(events[n])
    before = log_text(vault)

    report = reconcile(ListCollector(events), ingestor(vault), repair=True)

    assert report.repaired == 2
    assert report.consistent
    assert log_text(vault).startswith(before)  # append-only: existing text untouched
    assert sorted(r.identifiers["seq"] for r in RawStore(vault).read_day("sensor", BASE.date())) == [
        0, 1, 2, 3, 4
    ]

    again = reconcile(ListCollector(events), ingestor(vault), repair=True)
    assert again.repaired == 0 and again.present == 5


def test_conflicts_are_reported_never_rewritten(vault):
    ingestor(vault).ingest(event(1))
    before = log_text(vault)

    report = reconcile(ListCollector([event(1, value=42)]), ingestor(vault), repair=True)

    assert len(report.conflicts) == 1
    assert report.repaired == 0
    assert log_text(vault) == before


def test_archive_only_events_from_this_collector(vault, checkpoints):
    events = [event(n) for n in range(3)]
    run_collector(ListCollector(events), ingestor(vault), checkpoints)
    # Another collector's records for the same source are not ours to judge.
    run_collector(
        ListCollector([event(9)], name="sensor:b"), ingestor(vault), CheckpointStore(vault.path)
    )
    later_day = event(1)
    later_day = type(later_day)(**{**later_day.__dict__, "timestamp": BASE + timedelta(days=3)})
    run_collector(ListCollector([later_day]), ingestor(vault), CheckpointStore(vault.path / "x"))

    # The source "forgot" event 1 and the whole later day.
    report = reconcile(ListCollector([events[0], events[2]]), ingestor(vault))

    assert sorted(r.timestamp for r in report.archive_only) == [
        events[1].timestamp,
        BASE + timedelta(days=3),
    ]
    assert not report.consistent


def test_partial_failure_is_reported_and_proves_no_absence(vault):
    events = [event(n) for n in range(6)]
    ingestor(vault).ingest(events[5])

    report = reconcile(ListCollector(events, fail_after=3), ingestor(vault), repair=True)

    assert not report.complete
    assert "source went away" in report.error
    assert report.repaired == 3  # safe: idempotent appends
    assert report.archive_only == []  # event 5 not reported, but nothing is concluded
    assert not report.consistent


def test_window_reconciliation_skips_archive_only(vault):
    events = [event(n) for n in range(4)]
    for e in events:
        ingestor(vault).ingest(e)

    report = reconcile(ListCollector(events), ingestor(vault), since="1")

    assert report.examined == 2
    assert report.archive_only == []
    assert report.consistent
