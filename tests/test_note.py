from pathlib import Path

from obsidian_core import Note, Vault


def make_note(tmp_path, name="test.md"):
    vault = Vault(tmp_path)
    path = tmp_path / name

    return Note(path, vault)


def test_append_preserves_existing_markdown(tmp_path):
    note = make_note(tmp_path)

    note.write("# Existing\n\nExisting content.")

    note.append("## New\n\nNew content.")

    content = note.read()

    assert "# Existing" in content
    assert "Existing content." in content
    assert "## New" in content
    assert "New content." in content


def test_append_preserves_frontmatter(tmp_path):
    note = make_note(tmp_path)

    note.write(
        "---\n"
        "title: Test\n"
        "type: note\n"
        "---\n\n"
        "# Existing\n"
    )

    note.append("## Appended")

    content = note.read()

    assert content.startswith(
        "---\n"
        "title: Test\n"
        "type: note\n"
        "---\n"
    )
    assert "# Existing" in content
    assert "## Appended" in content


def test_append_empty_file(tmp_path):
    note = make_note(tmp_path)

    note.write("")
    note.append("New content")

    assert note.read() == "New content"


def test_append_file_with_trailing_newline(tmp_path):
    note = make_note(tmp_path)

    note.write("Existing content\n")
    note.append("New content")

    assert note.read() == "Existing content\nNew content"


def test_append_file_without_trailing_newline(tmp_path):
    note = make_note(tmp_path)

    note.write("Existing content")
    note.append("New content")

    assert note.read() == "Existing content\n\nNew content"


def test_append_does_not_overwrite_existing_content(tmp_path):
    note = make_note(tmp_path)

    note.write("First record")
    note.append("Second record")

    content = note.read()

    assert "First record" in content
    assert "Second record" in content
    assert len(content) > len("First record")