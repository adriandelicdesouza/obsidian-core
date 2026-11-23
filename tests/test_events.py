from datetime import UTC, datetime, timedelta, timezone

import pytest

from obsidian_core import RawParser, RawStore, Vault
from obsidian_core.events import (
    EVENT_KEY_VERSION,
    PROVENANCE_KEY,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    EventSchemaError,
    event_key,
    observation_digest,
    schema_version_of,
    validate_event,
    with_envelope,
)
from obsidian_core.raw import RawRecord

TS = datetime(2026, 11, 23, 14, 3, tzinfo=UTC)


def record(**overrides):
    values = {
        "timestamp": TS,
        "source": "git",
        "event_type": "commit",
        "identifiers": {"repository": "core", "commit": "abc"},
        "metadata": {},
        "payload": {"subject": "Fix"},
    }
    values.update(overrides)
    return RawRecord(**values)


def test_versions_are_explicit():
    assert SCHEMA_VERSION == 1
    assert EVENT_KEY_VERSION == 1


def test_event_key_is_full_sha256():
    key = event_key(record())
    assert len(key) == 64
    int(key, 16)


def test_event_key_ignores_collection_metadata():
    first = with_envelope(record(), {"collector": "git:core", "collected_at": "a"})
    second = with_envelope(record(), {"collector": "git:core", "collected_at": "b"})

    assert first.record_id != second.record_id
    assert event_key(first) == event_key(second)
    assert observation_digest(first) == observation_digest(second)


def test_event_key_uses_utc_instant():
    shifted = TS.astimezone(timezone(timedelta(hours=-5)))
    assert event_key(record()) == event_key(record(timestamp=shifted))


@pytest.mark.parametrize(
    "change",
    [
        {"source": "other"},
        {"event_type": "tag"},
        {"timestamp": TS + timedelta(seconds=1)},
        {"identifiers": {"repository": "core", "commit": "def"}},
    ],
)
def test_event_key_changes_with_identity_fields(change):
    assert event_key(record()) != event_key(record(**change))


def test_payload_is_not_identity_when_identifiers_exist():
    changed = record(payload={"subject": "Different"})
    assert event_key(record()) == event_key(changed)
    assert observation_digest(record()) != observation_digest(changed)


def test_payload_is_identity_when_identifiers_are_empty():
    first = record(identifiers={}, payload={"reading": 1})
    second = record(identifiers={}, payload={"reading": 2})
    assert event_key(first) != event_key(second)


def test_record_id_is_unchanged_by_this_module():
    # Same value as v0.3: identity work must not move the integrity hash.
    legacy = RawRecord(timestamp=TS, source="git", event_type="commit")
    assert len(legacy.record_id) == 16
    assert legacy.record_id == RawRecord(timestamp=TS, source="git", event_type="commit").record_id


def test_schema_version_defaults_to_zero_for_legacy_records():
    assert schema_version_of(record()) == 0
    assert schema_version_of(with_envelope(record())) == SCHEMA_VERSION


def test_with_envelope_sets_reserved_keys_without_mutating():
    original = record(metadata={"host": "srv"})
    stamped = with_envelope(original, {"collector": "x"})

    assert original.metadata == {"host": "srv"}
    assert stamped.metadata == {
        "host": "srv",
        SCHEMA_VERSION_KEY: SCHEMA_VERSION,
        PROVENANCE_KEY: {"collector": "x"},
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"payload": {"when": TS}},
        {"payload": (1, 2)},
        {"payload": float("nan")},
        {"identifiers": {1: "x"}},
        {"metadata": {"a:**b": 1}},
        {"metadata": {SCHEMA_VERSION_KEY: "1"}},
        {"metadata": {SCHEMA_VERSION_KEY: SCHEMA_VERSION + 1}},
        {"source": "a/b"},
        {"event_type": "a\nb"},
    ],
)
def test_validate_event_rejects_records_that_would_not_round_trip(bad):
    with pytest.raises(EventSchemaError):
        validate_event(record(**bad))


def test_valid_envelope_round_trips_through_the_raw_log(tmp_path):
    stamped = with_envelope(
        record(payload={"nested": [1, 2.5, None, True, "x"]}),
        {"collector": "git:core", "collected_at": TS.isoformat()},
    )
    validate_event(stamped)

    store = RawStore(Vault(tmp_path))
    path = store.append(stamped)
    [parsed] = RawParser.parse(path.read_text(encoding="utf-8"))

    assert parsed == stamped
    assert event_key(parsed) == event_key(stamped)
