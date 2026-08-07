from pathlib import Path
from typing import TYPE_CHECKING

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