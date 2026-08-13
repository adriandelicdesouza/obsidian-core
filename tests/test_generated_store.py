from datetime import datetime, timezone
from pathlib import Path

from obsidian_core import GeneratedRecord, GeneratedStore, Vault


def make_record(**kwargs):
    values = {
        "timestamp": datetime(
            2026,
            8,
            7,
            19,
            30,
            tzinfo=timezone.utc,
        ),
        "generator": "daily-summary",
        "generator_version": "1",
        "content": "Generated summary",
        "source_ids": [
            "20260807T184231.123000Z-esp32-sniffer-wifi_observation",
        ],
        "metadata": {
            "status": "generated",
        },
    }

    values.update(kwargs)

    return GeneratedRecord(**values)

def test_generated_store_append_many_same_day(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    records = [
        make_record(content="Summary one"),
        make_record(content="Summary two"),
        make_record(content="Summary three"),
    ]

    paths = store.append_many(records)

    assert len(paths) == 3
    assert paths[0] == paths[1] == paths[2]

    content = paths[0].read_text()

    assert "Summary one" in content
    assert "Summary two" in content
    assert "Summary three" in content

def test_generated_store_append_many_different_days(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    first = make_record(
        timestamp=datetime(
            2026,
            8,
            7,
            19,
            30,
            tzinfo=timezone.utc,
        )
    )

    second = make_record(
        timestamp=datetime(
            2026,
            8,
            8,
            19,
            30,
            tzinfo=timezone.utc,
        )
    )

    paths = store.append_many([first, second])

    assert len(paths) == 2
    assert paths[0] != paths[1]

    assert paths[0] == (
        tmp_path / "Generated" / "2026" / "08" / "07.md"
    )

    assert paths[1] == (
        tmp_path / "Generated" / "2026" / "08" / "08.md"
    )

def test_generated_store_writes_record(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    record = make_record()

    path = store.append(record)

    assert path.exists()
    assert path.suffix == ".md"


def test_generated_store_preserves_content(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    record = make_record()

    path = store.append(record)
    content = path.read_text()

    assert "Generated summary" in content
    assert "daily-summary" in content
    assert "20260807T184231.123000Z-esp32-sniffer-wifi_observation" in content


def test_generated_store_groups_by_day(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    record = make_record()

    path = store.append(record)

    assert path.relative_to(tmp_path) == Path("Generated/2026/08/07.md")


def test_generated_store_can_read_records(tmp_path):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    record = make_record()
    store.append(record)

    records = store.read_day(record.timestamp.date())

    assert len(records) == 1
    assert records[0].generator == record.generator
    assert records[0].generator_version == record.generator_version
    assert records[0].content == record.content
    assert records[0].source_ids == record.source_ids
