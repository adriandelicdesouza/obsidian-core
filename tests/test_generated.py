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

def test_generated_record_requires_timezone_aware_timestamp():
    from datetime import datetime

    try:
        GeneratedRecord(
            timestamp=datetime(2026, 8, 7, 19, 30),
            generator="daily-summary",
            generator_version="1",
            content="Summary",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "GeneratedRecord allowed a timezone-naive timestamp"
        )

def test_generated_record_requires_generator():
    from datetime import datetime, timezone

    try:
        GeneratedRecord(
            timestamp=datetime.now(timezone.utc),
            generator="",
            generator_version="1",
            content="Summary",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "GeneratedRecord allowed an empty generator"
        )

def test_generated_record_requires_generator_version():
    from datetime import datetime, timezone

    try:
        GeneratedRecord(
            timestamp=datetime.now(timezone.utc),
            generator="daily-summary",
            generator_version="",
            content="Summary",
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "GeneratedRecord allowed an empty generator version"
        )

def test_generated_id_is_deterministic():
    from datetime import datetime, timezone

    timestamp = datetime(
        2026,
        8,
        7,
        19,
        30,
        tzinfo=timezone.utc,
    )

    first = GeneratedRecord(
        timestamp=timestamp,
        generator="daily-summary",
        generator_version="1",
        content="Summary A",
    )

    second = GeneratedRecord(
        timestamp=timestamp,
        generator="daily-summary",
        generator_version="1",
        content="Summary B",
    )

    assert first.generated_id == second.generated_id

def test_generated_id_changes_with_generator_version():
    from datetime import datetime, timezone

    timestamp = datetime(
        2026,
        8,
        7,
        19,
        30,
        tzinfo=timezone.utc,
    )

    version_one = GeneratedRecord(
        timestamp=timestamp,
        generator="daily-summary",
        generator_version="1",
        content="Summary",
    )

    version_two = GeneratedRecord(
        timestamp=timestamp,
        generator="daily-summary",
        generator_version="2",
        content="Summary",
    )

    assert version_one.generated_id != version_two.generated_id

def test_source_ids_are_preserved():
    from datetime import datetime, timezone

    source_ids = [
        "20260807T184231.123000Z-esp32-sniffer-wifi_observation",
        "20260807T184500.000000Z-esp32-sniffer-wifi_observation",
    ]

    record = GeneratedRecord(
        timestamp=datetime.now(timezone.utc),
        generator="daily-summary",
        generator_version="1",
        content="Summary",
        source_ids=source_ids,
    )

    assert record.source_ids == source_ids

def test_metadata_is_preserved():
    from datetime import datetime, timezone

    metadata = {
        "title": "Daily Summary",
        "status": "generated",
        "confidence": 0.95,
    }

    record = GeneratedRecord(
        timestamp=datetime.now(timezone.utc),
        generator="daily-summary",
        generator_version="1",
        content="Summary",
        metadata=metadata,
    )

    assert record.metadata == metadata

def test_generated_id_is_timezone_independent():
    from datetime import datetime, timedelta, timezone

    utc_record = GeneratedRecord(
        timestamp=datetime(
            2026,
            8,
            7,
            19,
            30,
            tzinfo=timezone.utc,
        ),
        generator="daily-summary",
        generator_version="1",
        content="Summary",
    )

    eastern_record = GeneratedRecord(
        timestamp=datetime(
            2026,
            8,
            7,
            15,
            30,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        generator="daily-summary",
        generator_version="1",
        content="Summary",
    )

    assert utc_record.generated_id == eastern_record.generated_id