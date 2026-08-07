from datetime import datetime, timezone

import pytest

from obsidian_core import RawRecord


def test_create_raw_record():
    timestamp = datetime(
        2026,
        8,
        7,
        18,
        42,
        31,
        123000,
        tzinfo=timezone.utc,
    )

    record = RawRecord(
        timestamp=timestamp,
        source="esp32-sniffer",
        event_type="wifi_observation",
        identifiers={
            "mac": "AA:BB:CC:DD:EE:FF",
            "node": "esp32-living-room",
        },
        metadata={
            "channel": 6,
            "rssi": -54,
        },
        payload={
            "frame_type": "probe_request",
            "ssid": "example",
        },
    )

    assert record.source == "esp32-sniffer"
    assert record.event_type == "wifi_observation"
    assert record.identifiers["mac"] == "AA:BB:CC:DD:EE:FF"
    assert record.metadata["rssi"] == -54
    assert record.payload["frame_type"] == "probe_request"


def test_raw_record_is_immutable():
    record = RawRecord(
        timestamp=datetime.now(timezone.utc),
        source="test",
        event_type="event",
    )

    with pytest.raises(AttributeError):
        record.source = "modified"


def test_source_cannot_be_empty():
    with pytest.raises(ValueError):
        RawRecord(
            timestamp=datetime.now(timezone.utc),
            source="",
            event_type="event",
        )


def test_event_type_cannot_be_empty():
    with pytest.raises(ValueError):
        RawRecord(
            timestamp=datetime.now(timezone.utc),
            source="test",
            event_type="",
        )


def test_record_id():
    timestamp = datetime(
        2026,
        8,
        7,
        18,
        42,
        31,
        123000,
        tzinfo=timezone.utc,
    )

    record = RawRecord(
        timestamp=timestamp,
        source="esp32-sniffer",
        event_type="wifi_observation",
    )

    assert record.record_id == (
        "20260807T184231.123000Z-"
        "esp32-sniffer-wifi_observation"
    )

def test_record_id_is_deterministic():
    timestamp = datetime(
        2026,
        8,
        7,
        18,
        42,
        31,
        123000,
        tzinfo=timezone.utc,
    )

    first = RawRecord(
        timestamp=timestamp,
        source="esp32",
        event_type="wifi",
        identifiers={"mac": "AA:BB:CC:DD:EE:FF"},
        metadata={"rssi": -50},
        payload={"ssid": "example"},
    )

    second = RawRecord(
        timestamp=timestamp,
        source="esp32",
        event_type="wifi",
        identifiers={"mac": "AA:BB:CC:DD:EE:FF"},
        metadata={"rssi": -50},
        payload={"ssid": "example"},
    )

    assert first.record_id == second.record_id