from datetime import datetime, timezone

from obsidian_core import GeneratedRecord


def test_generated_record():
    record = GeneratedRecord(
        timestamp=datetime(
            2026,
            8,
            7,
            19,
            30,
            0,
            tzinfo=timezone.utc,
        ),
        generator="daily-summary",
        generator_version="1",
        content="Generated summary",
    )

    assert record.generator == "daily-summary"
    assert record.generator_version == "1"
    assert record.content == "Generated summary"
    assert record.source_ids == []
    assert record.metadata == {}


def test_generated_record_preserves_sources():
    record = GeneratedRecord(
        timestamp=datetime.now(timezone.utc),
        generator="daily-summary",
        generator_version="1",
        content="Summary",
        source_ids=[
            "20260807T184231.123000Z-esp32-sniffer-wifi_observation",
        ],
    )

    assert len(record.source_ids) == 1


def test_generated_record_id():
    timestamp = datetime(
        2026,
        8,
        7,
        19,
        30,
        0,
        tzinfo=timezone.utc,
    )

    record = GeneratedRecord(
        timestamp=timestamp,
        generator="daily-summary",
        generator_version="1",
        content="Summary",
    )

    assert record.generated_id == (
        "20260807T193000.000000+0000-"
        "daily-summary-1"
    )