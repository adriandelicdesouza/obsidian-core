from datetime import UTC, datetime

import pytest

from obsidian_core import GeneratedParser, GeneratedRecord, GeneratedStore, Vault


def make_record(**kwargs):
    values = {
        "timestamp": datetime(
            2026,
            8,
            7,
            19,
            30,
            tzinfo=UTC,
        ),
        "generator": "daily-summary",
        "generator_version": "1",
        "content": "Generated summary",
        "source_ids": [
            "20260807T184231.123000Z-esp32-sniffer-wifi_observation",
        ],
        "metadata": {
            "status": "generated",
            "confidence": 0.95,
        },
    }

    values.update(kwargs)

    return GeneratedRecord(**values)


def render_record(tmp_path, record=None):
    vault = Vault(tmp_path)
    store = GeneratedStore(vault)

    record = record or make_record()

    path = store.append(record)

    return path, path.read_text()


def test_generated_parser_round_trip(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    records = GeneratedParser.parse(content)

    assert len(records) == 1

    parsed = records[0]

    assert parsed.timestamp == record.timestamp
    assert parsed.generator == record.generator
    assert parsed.generator_version == record.generator_version
    assert parsed.content == record.content
    assert parsed.source_ids == record.source_ids
    assert parsed.metadata == record.metadata
    assert parsed.generated_id == record.generated_id


def test_generated_parser_rejects_modified_content(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "Generated summary",
        "Modified summary",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_modified_generator(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "## 2026-08-07T19:30:00+00:00 — daily-summary",
        "## 2026-08-07T19:30:00+00:00 — modified-generator",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_modified_generator_version(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "**Generator Version:** `1`",
        "**Generator Version:** `2`",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_modified_timestamp(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "## 2026-08-07T19:30:00+00:00 — daily-summary",
        "## 2026-08-07T19:31:00+00:00 — daily-summary",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_missing_generated_id(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        f"**Generated ID:** `{record.generated_id}`\n\n",
        "",
    )

    with pytest.raises(
        ValueError,
        match="Generated record field not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_metadata(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "- **status:** `generated`",
        "- malformed metadata",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_source_section(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "### Source Records",
        "### Invalid Source Records",
    )

    with pytest.raises(
        ValueError,
        match="Source records section not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_timestamp(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "## 2026-08-07T19:30:00+00:00 — daily-summary",
        "## not-a-timestamp — daily-summary",
    )

    with pytest.raises(
        ValueError,
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_header(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "## 2026-08-07T19:30:00+00:00 — daily-summary",
        "invalid header",
    )

    with pytest.raises(ValueError):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_missing_source_section(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "### Source Records",
        "### Invalid Source Records",
    )

    with pytest.raises(
        ValueError,
        match="Source records section not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_missing_metadata_section(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "### Metadata",
        "### Invalid Metadata",
    )

    with pytest.raises(
        ValueError,
        match="Metadata section not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_missing_content_section(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "### Content",
        "### Invalid Content",
    )

    with pytest.raises(
        ValueError,
        match="Content section not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_generated_id(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        f"**Generated ID:** `{record.generated_id}`",
        "**Generated ID:** `not-a-valid-generated-id`",
    )

    with pytest.raises(
        ValueError,
        match="integrity check failed",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_missing_generator_version(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        "**Generator Version:** `1`\n\n",
        "",
    )

    with pytest.raises(
        ValueError,
        match="Generated record field not found",
    ):
        GeneratedParser.parse(modified)


def test_generated_parser_rejects_malformed_source_records(tmp_path):
    record = make_record()

    path, content = render_record(tmp_path, record)

    modified = content.replace(
        f"- `{record.source_ids[0]}`",
        "- malformed source record",
    )

    with pytest.raises(
        ValueError,
        match="Malformed source records section",
    ):
        GeneratedParser.parse(modified)
