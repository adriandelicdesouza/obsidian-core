from datetime import date
from pathlib import Path

from .generated import GeneratedRecord
from .generated_parser import GeneratedParser
from .vault import Vault


class GeneratedStore:
    """Storage for derived records generated from source data."""

    def __init__(
        self,
        vault: Vault,
        root: str | Path = "Generated",
    ):
        self.vault = vault
        self.root = Path(root)

    def append(self, record: GeneratedRecord) -> Path:
        """Append a generated record to its daily log."""

        relative_path = self.day_path(record.timestamp.date())

        note = self.vault.note(str(relative_path))

        if note.exists:
            existing = note.read()
            separator = "\n" if existing.endswith("\n") else "\n\n"
            note.write(existing + separator + self._render(record))
        else:
            note.write(self._render_daily_file(record))

        return note.path

    def day_path(self, timestamp: date) -> Path:
        """Return the generated log path for a date."""

        return (
            self.root
            / f"{timestamp.year:04d}"
            / f"{timestamp.month:02d}"
            / f"{timestamp.day:02d}.md"
        )

    def read_day(self, timestamp: date) -> list[GeneratedRecord]:
        """Read all generated records for a specific day."""

        path = self.day_path(timestamp)

        note = self.vault.note(str(path))

        if not note.exists:
            raise FileNotFoundError(path)

        return GeneratedParser.parse(note.read())

    def _render_daily_file(self, record: GeneratedRecord) -> str:
        return (
            "---\n"
            "type: generated-log\n"
            f"date: {record.timestamp.date()}\n"
            "---\n\n"
            + self._render(record)
        )

    @staticmethod
    def _render(record: GeneratedRecord) -> str:
        source_ids = "\n".join(
            f"- `{source_id}`"
            for source_id in record.source_ids
        )

        if not source_ids:
            source_ids = "_None_"

        metadata = "\n".join(
            f"- **{key}:** `{value}`"
            for key, value in record.metadata.items()
        )

        if not metadata:
            metadata = "_None_"

        return (
            f"## {record.timestamp.isoformat()} — "
            f"{record.generator}\n\n"
            f"**Generated ID:** `{record.generated_id}`\n\n"
            f"**Generator:** `{record.generator}`\n\n"
            f"**Generator Version:** `{record.generator_version}`\n\n"
            "### Source Records\n\n"
            f"{source_ids}\n\n"
            "### Metadata\n\n"
            f"{metadata}\n\n"
            "### Content\n\n"
            f"{record.content}\n"
        )
