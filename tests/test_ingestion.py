from datetime import UTC, datetime, timedelta

import pytest

from obsidian_core import RawStore, Vault
from obsidian_core.events import EventSchemaError, with_envelope
from obsidian_core.ingestion import Ingestor, IngestStatus
from obsidian_core.raw import RawRecord

TS = datetime(2026, 11, 23, 14, 3, tzinfo=UTC)


def commit(sha="abc", subject="Fix", collected_at="t1", ts=TS):
    return with_envelope(
        RawRecord(
            timestamp=ts,
            source="git",
            event_type="commit",
            identifiers={"repository": "core", "commit": sha},
            payload={"subject": subject},
        ),
        {"collector": "git:core", "collected_at": collected_at},
    )


@pytest.fixture
def store(tmp_path):
    return RawStore(Vault(tmp_path))


DAY = TS.date()


def stored(store, day=DAY):
    return store.read_day("git", day)


def test_new_event_is_persisted(store):
    result = Ingestor(store).ingest(commit())

    assert result.status is IngestStatus.NEW
    assert result.written
    assert result.path.exists()
    assert stored(store) == [commit()]


def test_replayed_event_is_known_and_not_duplicated(store):
    ingestor = Ingestor(store)
    ingestor.ingest(commit())
    before = (store.vault.path / store.day_path("git", TS.date())).read_text()

    result = ingestor.ingest(commit(collected_at="t2"))

    assert result.status is IngestStatus.KNOWN
    assert not result.written
    assert result.existing_record_id == commit().record_id
    assert (store.vault.path / store.day_path("git", TS.date())).read_text() == before


def test_known_detection_reads_the_archive_not_process_memory(store):
    Ingestor(store).ingest(commit())

    result = Ingestor(store).ingest(commit(collected_at="later"))

    assert result.status is IngestStatus.KNOWN
    assert len(stored(store)) == 1


def test_changed_observation_under_same_identity_is_a_conflict(store):
    ingestor = Ingestor(store)
    ingestor.ingest(commit())

    result = ingestor.ingest(commit(subject="Rewritten"))

    assert result.status is IngestStatus.CONFLICT
    assert result.existing_record_id == commit().record_id
    assert stored(store) == [commit()]


def test_duplicates_within_one_batch(store):
    results = Ingestor(store).ingest_many([commit(), commit(collected_at="t2"), commit("def")])

    assert [r.status for r in results] == [IngestStatus.NEW, IngestStatus.KNOWN, IngestStatus.NEW]
    assert len(stored(store)) == 2


def test_classify_does_not_write(store):
    result = Ingestor(store).classify(commit())

    assert result.status is IngestStatus.NEW
    assert not result.path.exists()


def test_events_on_other_days_are_separate(store):
    ingestor = Ingestor(store)
    ingestor.ingest(commit())
    result = ingestor.ingest(commit(ts=TS + timedelta(days=1)))

    assert result.status is IngestStatus.NEW


def test_refresh_sees_writes_by_other_writers(store):
    ingestor = Ingestor(store)
    assert ingestor.classify(commit()).status is IngestStatus.NEW

    store.append(commit())  # another writer, bypassing this ingestor
    assert ingestor.classify(commit()).status is IngestStatus.NEW  # stale cache, documented

    ingestor.refresh()
    assert ingestor.classify(commit()).status is IngestStatus.KNOWN


def test_legacy_duplicates_in_archive_are_tolerated(store):
    store.append(commit())
    store.append(commit())  # pre-v0.4 archives may already hold duplicates

    assert Ingestor(store).ingest(commit()).status is IngestStatus.KNOWN
    assert len(stored(store)) == 2


def test_invalid_records_are_rejected_before_any_write(store):
    bad = RawRecord(timestamp=TS, source="git", event_type="commit", payload=(1, 2))

    with pytest.raises(EventSchemaError):
        Ingestor(store).ingest(bad)

    assert not (store.vault.path / store.day_path("git", TS.date())).exists()


def test_corrupt_archive_stops_ingestion(store):
    path = store.append(commit())
    path.write_text(path.read_text().replace('"Fix"', '"Tampered"'))

    with pytest.raises(ValueError, match="integrity"):
        Ingestor(store).ingest(commit("def"))
