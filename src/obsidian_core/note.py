from pathlib import Path
from typing import TYPE_CHECKING

from .frontmatter import Frontmatter
from .generated import GeneratedRecord

if TYPE_CHECKING:
    from .vault import Vault


class Note:
    """Representation of a Markdown note within an Obsidian vault."""

    def __init__(self, path: Path, vault: "Vault"):
        self.path = path
        self.vault = vault

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(self.vault.path)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def read(self) -> str:
        """Read the complete note contents."""
        return self.path.read_text(encoding="utf-8")

    def write(self, content: str) -> None:
        """Write complete note contents."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")

    def delete(self) -> None:
        """Safely delete this note from the vault."""
        vault_path = self.vault.path.resolve()
        note_path = self.path.resolve()

        try:
            note_path.relative_to(vault_path)
        except ValueError:
            raise ValueError("Cannot delete a note outside the vault")

        if not note_path.exists():
            raise FileNotFoundError(note_path)

        if not note_path.is_file():
            raise ValueError("Cannot delete a non-file path")

        note_path.unlink()

    def append(self, content: str) -> None:
        """Append content without overwriting existing note contents."""
        if not self.exists:
            self.write(content)
            return

        existing = self.read()

        if not existing:
            self.write(content)
            return

        if existing.endswith("\n"):
            self.write(existing + content)
        else:
            self.write(existing + "\n\n" + content)

    def append_generated(self, record: GeneratedRecord) -> None:
        """Append a generated record while preserving existing note content."""
        generated = (
            "<!-- obsidian-core:generated -->\n"
            f"## Generated: {record.generator}\n\n"
            f"**Generated ID:** `{record.generated_id}`\n\n"
            f"**Generator:** `{record.generator}`\n\n"
            f"**Generator Version:** `{record.generator_version}`\n\n"
            f"{record.content}\n"
            "<!-- obsidian-core:generated-end -->\n"
        )

        if not self.exists:
            self.write(generated)
            return

        existing = self.read()

        if not existing:
            self.write(generated)
            return

        separator = "\n" if existing.endswith("\n") else "\n\n"

        self.write(existing + separator + generated)

    @property
    def properties(self) -> Frontmatter:
        """Return the note's parsed properties."""
        return Frontmatter.parse(self.read())

    def set_property(self, key: str, value: object) -> None:
        """Set a property while preserving the note body."""
        content = self.read()
        frontmatter = Frontmatter.parse(content)

        frontmatter.set(key, value)

        self.write(_replace_frontmatter(content, frontmatter))

    def delete_property(self, key: str) -> None:
        """Delete a property while preserving the note body."""
        content = self.read()
        frontmatter = Frontmatter.parse(content)

        frontmatter.delete(key)

        self.write(_replace_frontmatter(content, frontmatter))


def _replace_frontmatter(content: str, frontmatter: Frontmatter) -> str:
    """Replace only the frontmatter portion of a Markdown document."""
    if not content.startswith("---"):
        return frontmatter.to_yaml() + content

    lines = content.splitlines(keepends=True)

    closing_index = None

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return frontmatter.to_yaml() + content

    body = "".join(lines[closing_index + 1:])

    return frontmatter.to_yaml() + body