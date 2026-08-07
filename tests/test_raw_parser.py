from datetime import datetime, timezone
from obsidian_core import RawParser, RawRecord, RawStore, Vault
import pytest

def test_parser_recovers_record(tmp_path):
    vault = Vault(tmp_path)
    store = RawStore(vault)

    original = RawRecord(
        timestamp=datetime(
            2026,
            8,
            7,
            18,
            42,
            31,
            123000,
            tzinfo=timezone.utc,
        ),
        source="esp32-sniffer",
        event_type="wifi_observation",
        identifiers={
            "mac": "AA:BB:CC:DD:EE:FF",
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

    path = store.append(original)

    content = path.read_text()

    records = RawParser.parse(content)

    assert len(records) == 1

    record = records[0]

    assert record.timestamp == original.timestamp
    assert record.source == original.source
    assert record.event_type == original.event_type
    assert record.identifiers == original.identifiers
    assert record.metadata == original.metadata
    assert record.payload == original.payload
