from obsidian_core import Vault


def test_vault_can_create_and_read_note(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("Test.md")

    assert not note.exists

    note.write("# Test\n\nHello world.")

    assert note.exists
    assert note.read() == "# Test\n\nHello world."


def test_nested_note(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("40 - Knowledge/Test.md")

    note.write("# Test")

    assert note.exists
    assert note.read() == "# Test"


def test_vault_rejects_path_escape(tmp_path):
    vault = Vault(tmp_path)

    try:
        vault.note("../outside.md")
    except Exception:
        pass
    else:
        raise AssertionError("Vault allowed a path to escape its root")