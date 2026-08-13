from datetime import datetime
from pathlib import Path

from .raw_parser import RawParser
from .raw import RawRecord
from .vault import Vault


class RawStore:
    """Append-only storage for raw machine-generated records."""

    def __init__(self, vault: Vault, root: str | Path = "Raw"):
        self.vault = vault
        self.root = Path(root)

    def append(self, record: RawRecord) -> Path:
        """Append a raw record to its source's daily log."""
        relative_path = self._path_for(record)

        note = self.vault.note(str(relative_path))

        if note.exists:
            existing = note.read()
            separator = "\n" if existing.endswith("\n") else "\n\n"
            note.write(existing + separator + self._render(record))
        else:
            note.write(self._render_daily_file(record))

        return note.path

    def day_path(self, source: str, timestamp: datetime) -> Path:
        """Return the raw log path for a source and timestamp."""
        return (
            self.root
            / source
            / f"{timestamp.year:04d}"
            / f"{timestamp.month:02d}"
            / f"{timestamp.day:02d}.md"
        )

    def _path_for(self, record: RawRecord) -> Path:
        return self.day_path(record.source, record.timestamp)

    def _render_daily_file(self, record: RawRecord) -> str:
        return (
            "---\n"
            "type: raw-log\n"
            f"source: {record.source}\n"
            f"date: {record.timestamp.date()}\n"
            "---\n\n"
            + self._render(record)
        )

    def _render(self, record: RawRecord) -> str:
        return (
            f"## {record.timestamp.isoformat()} — "
            f"{record.event_type}\n\n"
            f"**Record ID:** `{record.record_id}`\n\n"
            "### Identifiers\n\n"
            f"{self._render_mapping(record.identifiers)}\n\n"
            "### Metadata\n\n"
            f"{self._render_mapping(record.metadata)}\n\n"
            "### Payload\n\n"
            "```json\n"
            f"{self._render_payload(record.payload)}\n"
            "```\n"
        )

    def append_many(self, records: list[RawRecord]) -> list[Path]:
        """Append multiple raw records."""
        paths = []

        for record in records:
            paths.append(self.append(record))

        return paths

    def read_day(
        self,
        source: str,
        year: int,
        month: int,
        day: int,
    ) -> list[RawRecord]:
        """Read and parse raw records for a specific day."""
        path = (
            self.root
            / source
            / f"{year:04d}"
            / f"{month:02d}"
            / f"{day:02d}.md"
        )

        note = self.vault.note(str(path))

        if not note.exists:
            raise FileNotFoundError(path)

        return RawParser.parse(note.read())

    def day_path(self, source: str, timestamp: datetime) -> Path:
        """Return the raw log path for a source and timestamp."""
        return (
            self.root
            / source
            / f"{timestamp.year:04d}"
            / f"{timestamp.month:02d}"
            / f"{timestamp.day:02d}.md"
        )


    @staticmethod
    def _render_mapping(mapping: dict) -> str:
        if not mapping:
            return "_None_"

        return "\n".join(
            f"- **{key}:** `{value}`"
            for key, value in mapping.items()
        )

    @staticmethod
    def _render_payload(payload) -> str:
        import json

        return json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
