from pathlib import Path

from .exceptions import VaultError
from .note import Note


class Vault:
    """Interface to an Obsidian vault stored on the filesystem."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()

        if not self.path.exists():
            raise VaultError(f"Vault does not exist: {self.path}")

        if not self.path.is_dir():
            raise VaultError(f"Vault path is not a directory: {self.path}")

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve a path and ensure it remains inside the vault."""
        target = (self.path / Path(path)).resolve()

        try:
            target.relative_to(self.path)
        except ValueError as exc:
            raise VaultError("Path escapes the vault") from exc

        return target

    def note(self, path: str | Path) -> Note:
        """Return a Note relative to the vault root."""
        return Note(self._resolve_path(path), self)

    def exists(self, path: str | Path) -> bool:
        """Return whether a path exists inside the vault."""
        return self._resolve_path(path).exists()
