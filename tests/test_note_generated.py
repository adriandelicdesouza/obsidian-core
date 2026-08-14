from datetime import datetime, timezone

from obsidian_core import GeneratedRecord, Note, Vault


def make_note(tmp_path):
    vault = Vault(tmp_path)
    return Note(tmp_path / "test.md", vault)


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
        "source_ids": ["source-123"],
        "metadata": {"status": "generated"},
    }

    values.update(kwargs)

    return GeneratedRecord(**values)


def test_append_generated_preserves_human_content(tmp_path):
    note = make_note(tmp_path)

    note.write("# My Note\n\nHuman-written content.\n")

    note.append_generated(make_record())

    content = note.read()

    assert "# My Note" in content
    assert "Human-written content." in content
    assert "Generated summary" in content


def test_append_generated_identifies_generator(tmp_path):
    note = make_note(tmp_path)

    record = make_record()

    note.append_generated(record)

    content = note.read()

    assert "**Generator:** `daily-summary`" in content
    assert "**Generator Version:** `1`" in content


def test_append_generated_preserves_generated_history(tmp_path):
    note = make_note(tmp_path)

    first = make_record(
        generator_version="1",
        content="First generated result",
    )

    second = make_record(
        generator_version="2",
        content="Second generated result",
    )

    note.append_generated(first)
    note.append_generated(second)

    content = note.read()

    assert "First generated result" in content
    assert "Second generated result" in content
    assert "**Generator Version:** `1`" in content
    assert "**Generator Version:** `2`" in content


def test_append_generated_preserves_frontmatter(tmp_path):
    note = make_note(tmp_path)

    note.write(
        "---\n"
        "title: Test\n"
        "type: note\n"
        "---\n\n"
        "# Human Content\n"
    )

    note.append_generated(make_record())

    content = note.read()

    assert content.startswith(
        "---\n"
        "title: Test\n"
        "type: note\n"
        "---\n"
    )
    assert "# Human Content" in content
    assert "Generated summary" in content


def test_append_generated_has_identifiable_boundaries(tmp_path):
    note = make_note(tmp_path)

    note.append_generated(make_record())

    content = note.read()

    assert "<!-- obsidian-core:generated -->" in content
    assert "<!-- obsidian-core:generated-end -->" in content


def test_append_generated_round_trip_content(tmp_path):
    note = make_note(tmp_path)

    record = make_record()

    note.append_generated(record)

    content = note.read()

    assert record.generated_id in content
    assert record.generator in content
    assert record.generator_version in content
    assert record.content in content