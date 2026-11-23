"""Relate archived Git activity to the Obsidian vault.

This is a presentation layer downstream of ingestion. It reads commit events
from the authoritative raw archive and writes one generated note per day.
Nothing here is stored in, or required by, the raw archive.

Relationship and wikilink rules
-------------------------------

A day's note lives at ``<root>/YYYY/MM/YYYY-MM-DD.md`` and links to:

* the daily note, ``[[YYYY-MM-DD]]`` (format configurable with
  ``daily_note_format``, a ``strftime`` pattern);
* the raw log the commits came from, ``[[Raw/git/YYYY/MM/DD|git raw log]]``;
* one note per repository, ``[[<repository_folder>/<repository>|<repository>]]``
  (set ``repository_folder=None`` to link ``[[<repository>]]``).

Each commit line names the raw event it was derived from by ``record_id``, so
the note can always be traced back to the archive.

Commits are grouped by the date of their committer timestamp, in the offset
recorded with the commit (the same date that selects the raw log file).

Idempotency
-----------

The note is a pure function of the archive: rendering the same day twice gives
the same text, commits are deduplicated by event key, and writing rewrites the
whole note instead of appending. Running it again therefore never adds
duplicate links. A note at the target path that this generator did not write
(no ``generator: obsidian-core.git-activity`` property) is never overwritten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

import yaml

from ..events import event_key
from ..frontmatter import Frontmatter
from ..links import create_wiki_link
from ..raw import RawRecord
from ..raw_store import RawStore
from ..relationships import Relationship, extract_relationships
from ..vault import Vault

GENERATOR = "obsidian-core.git-activity"
GENERATOR_VERSION = "1"

_UNSAFE_TARGET = re.compile(r"[\[\]|#^\\]")
_MARKDOWN_SPECIAL = re.compile(r"([\\\[\]#*_`<>|])")


class WriteStatus(Enum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    EMPTY = "empty"


@dataclass(frozen=True)
class WriteResult:
    status: WriteStatus
    path: Path


class ForeignNoteError(RuntimeError):
    """Raised instead of overwriting a note this generator did not create."""


def _escape(text: str) -> str:
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def _target(text: str) -> str:
    return _UNSAFE_TARGET.sub("-", text).strip() or "-"


class GitActivityNotes:
    """Generate daily Git activity notes linked into the vault."""

    def __init__(
        self,
        vault: Vault,
        store: RawStore,
        *,
        root: str | Path = "Git Activity",
        source: str = "git",
        daily_note_format: str = "%Y-%m-%d",
        repository_folder: str | None = "Repositories",
    ):
        self.vault = vault
        self.store = store
        self.root = Path(root)
        self.source = source
        self.daily_note_format = daily_note_format
        self.repository_folder = repository_folder

    def note_path(self, day: date) -> Path:
        return self.root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.isoformat()}.md"

    def commits(self, day: date) -> list[RawRecord]:
        """Commit events archived for a day, deduplicated and in time order."""
        try:
            records = self.store.read_day(self.source, day)
        except FileNotFoundError:
            return []

        unique: dict[str, RawRecord] = {}

        for record in records:
            if record.event_type == "commit":
                unique.setdefault(event_key(record), record)

        return sorted(
            unique.values(),
            key=lambda r: (r.timestamp, r.identifiers.get("repository", ""), r.identifiers.get("commit", "")),
        )

    def daily_link(self, day: date) -> str:
        return create_wiki_link(day.strftime(self.daily_note_format))

    def raw_log_link(self, day: date) -> str:
        target = self.store.day_path(self.source, day).with_suffix("").as_posix()
        return create_wiki_link(target, f"{self.source} raw log")

    def repository_link(self, repository: str) -> str:
        name = _target(repository)
        if self.repository_folder is None:
            return create_wiki_link(name)
        return create_wiki_link(f"{self.repository_folder}/{name}", name)

    def render(self, day: date) -> str | None:
        """Render a day's note, or ``None`` when no commits were archived."""
        commits = self.commits(day)

        if not commits:
            return None

        by_repo: dict[str, list[RawRecord]] = {}
        for record in commits:
            by_repo.setdefault(str(record.identifiers.get("repository", "unknown")), []).append(record)

        properties = {
            "type": "git-activity",
            "date": day.isoformat(),
            "generator": GENERATOR,
            "generator_version": GENERATOR_VERSION,
            "repositories": sorted(by_repo),
            "commits": len(commits),
            "source_records": [record.record_id for record in commits],
        }
        lines = [
            "---",
            yaml.safe_dump(properties, sort_keys=False, allow_unicode=True).rstrip("\n"),
            "---",
            "",
            f"# Git activity {day.isoformat()}",
            "",
            f"- Day: {self.daily_link(day)}",
            f"- Raw log: {self.raw_log_link(day)}",
        ]

        for repository in sorted(by_repo):
            lines += ["", f"## {self.repository_link(repository)}", ""]
            lines += [self._commit_line(record) for record in by_repo[repository]]

        return "\n".join(lines) + "\n"

    def relationships(self, day: date) -> list[Relationship]:
        """Relationships the day's note creates, one per distinct target."""
        content = self.render(day)

        if content is None:
            return []

        unique: dict[str, Relationship] = {}
        for relationship in extract_relationships(self.note_path(day).as_posix(), content):
            unique.setdefault(relationship.target, relationship)

        return list(unique.values())

    def write(self, day: date) -> WriteResult:
        """Write or refresh a day's note from the archive."""
        content = self.render(day)
        note = self.vault.note(self.note_path(day))

        if content is None:
            return WriteResult(WriteStatus.EMPTY, note.path)

        if not note.exists:
            note.write(content)
            return WriteResult(WriteStatus.CREATED, note.path)

        existing = note.read()

        if existing == content:
            return WriteResult(WriteStatus.UNCHANGED, note.path)

        try:
            generator = Frontmatter.parse(existing).get("generator")
        except ValueError:
            generator = None

        if generator != GENERATOR:
            raise ForeignNoteError(f"Refusing to overwrite a note not generated here: {note.path}")

        note.write(content)
        return WriteResult(WriteStatus.UPDATED, note.path)

    def write_days(self, days: list[date]) -> list[WriteResult]:
        return [self.write(day) for day in sorted(set(days))]

    @staticmethod
    def _commit_line(record: RawRecord) -> str:
        payload = record.payload if isinstance(record.payload, dict) else {}
        sha = str(record.identifiers.get("commit", ""))
        author = (payload.get("author") or {}).get("name", "")
        stats = (
            f"+{payload.get('insertions', 0)} −{payload.get('deletions', 0)}, "
            f"{payload.get('files_changed', 0)} files"
        )
        return (
            f"- {record.timestamp.strftime('%H:%M')} `{sha[:10]}` "
            f"{_escape(str(payload.get('subject', '')))} — {_escape(author)} "
            f"({stats}) · record `{record.record_id}`"
        )
