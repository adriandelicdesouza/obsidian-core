from pathlib import Path

import pytest

from obsidian_core import Vault
from obsidian_core.exceptions import VaultError


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

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note("../outside.md")


def test_vault_rejects_absolute_path(tmp_path):
    vault = Vault(tmp_path)

    outside = tmp_path.parent / "outside.md"

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note(outside)


def test_vault_rejects_nested_path_escape(tmp_path):
    vault = Vault(tmp_path)

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note("foo/bar/../../../../outside.md")


def test_vault_allows_redundant_path_components(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("foo/../Test.md")

    note.write("# Test")

    assert note.exists
    assert note.read() == "# Test"


def test_vault_rejects_symlink_escape(tmp_path):
    vault = Vault(tmp_path)

    outside = tmp_path.parent / "outside"
    outside.mkdir()

    symlink = tmp_path / "link"
    symlink.symlink_to(outside, target_is_directory=True)

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note("link/outside.md")


def test_vault_rejects_symlinked_file_escape(tmp_path):
    vault = Vault(tmp_path)

    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside", encoding="utf-8")

    symlink = tmp_path / "link.md"
    symlink.symlink_to(outside)

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note("link.md")


@pytest.mark.parametrize(
    "path",
    [
        "/tmp/outside.md",
        "../outside.md",
        "foo/../../outside.md",
        "foo/bar/../../../outside.md",
    ],
)
def test_vault_rejects_traversal_variants(tmp_path, path):
    vault = Vault(tmp_path)

    with pytest.raises(VaultError, match="Path escapes the vault"):
        vault.note(path)


def test_vault_accepts_nested_safe_path(tmp_path):
    vault = Vault(tmp_path)

    path = Path("foo") / "bar" / "note.md"

    note = vault.note(path)

    note.write("# Test")

    assert note.exists
    assert note.read() == "# Test"