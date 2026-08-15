from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from obsidian_core import RawRecord, RawStore, Vault


def make_record(**kwargs):
    values = {
        "timestamp": datetime(
            2026,
            8,
            7,
            18,
            42,
            31,
            tzinfo=UTC,
        ),
        "source": "esp32-sniffer",
        "event_type": "wifi_observation",
        "identifiers": {
            "mac": "AA:BB:CC:DD:EE:FF",
        },
        "metadata": {
            "rssi": -54,
        },
        "payload": {
            "frame_type": "probe_request",
        },
    }

    values.update(kwargs)

    return RawRecord(**values)


def test_append_creates_daily_file(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    record = make_record()

    path = store.append(record)

    assert path == (tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md")

    assert path.exists()


def test_append_creates_daily_frontmatter(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    store.append(make_record())

    content = (tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md").read_text()

    assert content.startswith("---\n")
    assert "type: raw-log" in content
    assert "source: esp32-sniffer" in content
    assert "date: 2026-08-07" in content


def test_append_preserves_previous_record(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    first = make_record(
        event_type="first_event",
    )

    second = make_record(
        event_type="second_event",
    )

    store.append(first)
    store.append(second)

    path = tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md"

    content = path.read_text()

    assert "first_event" in content
    assert "second_event" in content


def test_different_days_use_different_files(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    first = make_record(
        timestamp=datetime(
            2026,
            8,
            7,
            tzinfo=UTC,
        )
    )

    second = make_record(
        timestamp=datetime(
            2026,
            8,
            8,
            tzinfo=UTC,
        )
    )

    store.append(first)
    store.append(second)

    assert (tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md").exists()

    assert (tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "08.md").exists()


def test_payload_is_serialized_as_json(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    record = make_record(
        payload={
            "device": "test",
            "signal": -42,
        }
    )

    store.append(record)

    path = tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md"

    content = path.read_text()

    assert '"device": "test"' in content
    assert '"signal": -42' in content


def test_record_identifier_is_stored(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    record = make_record()

    store.append(record)

    path = tmp_path / "Raw" / "esp32-sniffer" / "2026" / "08" / "07.md"

    content = path.read_text()

    assert record.record_id in content


def test_append_many(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    records = [
        make_record(event_type="event_one"),
        make_record(event_type="event_two"),
        make_record(event_type="event_three"),
    ]

    paths = store.append_many(records)

    assert len(paths) == 3
    assert paths[0] == paths[1] == paths[2]

    content = paths[0].read_text()

    assert "event_one" in content
    assert "event_two" in content
    assert "event_three" in content


def test_append_is_append_only(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    first = make_record(event_type="first")
    second = make_record(event_type="second")

    path = store.append(first)

    original_content = path.read_text()

    store.append(second)

    updated_content = path.read_text()

    assert first.record_id in updated_content
    assert second.record_id in updated_content
    assert len(updated_content) > len(original_content)


def test_read_day_returns_parsed_records(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    record = make_record()

    store.append(record)

    records = store.read_day(
        source="esp32-sniffer",
        timestamp=date(2026, 8, 7),
    )

    assert isinstance(records, list)
    assert len(records) == 1
    assert isinstance(records[0], RawRecord)

    assert records[0].record_id == record.record_id
    assert records[0].timestamp == record.timestamp
    assert records[0].source == record.source
    assert records[0].event_type == record.event_type
    assert records[0].identifiers == record.identifiers
    assert records[0].metadata == record.metadata
    assert records[0].payload == record.payload


def test_read_day_round_trip_multiple_records(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    records = [
        make_record(event_type="event_one"),
        make_record(event_type="event_two"),
        make_record(event_type="event_three"),
    ]

    store.append_many(records)

    loaded = store.read_day(
        source="esp32-sniffer",
        timestamp=date(2026, 8, 7),
    )

    assert [record.record_id for record in loaded] == [record.record_id for record in records]


def test_read_day_rejects_modified_record(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    record = make_record()

    path = store.append(record)

    content = path.read_text()

    modified = content.replace(
        "**rssi:** `-54`",
        "**rssi:** `-20`",
    )

    path.write_text(modified)

    with pytest.raises(ValueError, match="integrity check failed"):
        store.read_day(
            source="esp32-sniffer",
            timestamp=date(2026, 8, 7),
        )


def test_read_missing_day(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    with pytest.raises(FileNotFoundError):
        store.read_day(
            source="esp32-sniffer",
            timestamp=date(2026, 8, 7),
        )


def test_day_path_uses_date(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    path = store.day_path(
        source="esp32-sniffer",
        timestamp=date(2026, 8, 7),
    )

    assert path == (Path("Raw") / "esp32-sniffer" / "2026" / "08" / "07.md")
