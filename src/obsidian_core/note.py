from pathlib import Path
from typing import TYPE_CHECKING

from .frontmatter import Frontmatter

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