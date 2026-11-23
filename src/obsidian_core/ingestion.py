"""Idempotent ingestion boundary between collectors and :class:`RawStore`.

``RawStore`` is append-only: appending the same record twice stores it twice.
Append-only is not idempotent. This module is the boundary that makes
ingestion idempotent, so collectors can replay observations safely after a
crash, a lost checkpoint or a reconciliation pass.

Protocol
--------

For each record, :class:`Ingestor` computes its :func:`~obsidian_core.events.event_key`
and looks it up in the authoritative archive itself: the source's raw log for
the record's day (the same file the record would be appended to). There is no
separate index that could drift from the archive.

* ``NEW``: the key is not in the archive. The record is appended.
* ``KNOWN``: the key is in the archive with the same observation. Nothing is
  written.
* ``CONFLICT``: the key is in the archive with a different observation (the
  source changed what it reports for the same event). Nothing is written; the
  existing archive entry stays authoritative and the result carries both
  digests so the caller can report it.

Known keys are cached per ``(source, day)`` after the first read. The cache
assumes this ingestor is the only writer to those logs while it runs; call
:meth:`Ingestor.refresh` after other writers have appended.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from .events import event_key, observation_digest, validate_event
from .raw import RawRecord
from .raw_store import RawStore


class IngestStatus(Enum):
    NEW = "new"
    KNOWN = "known"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IngestResult:
    """Outcome of ingesting one record."""

    status: IngestStatus
    event_key: str
    record_id: str
    path: Path
    existing_record_id: str | None = None

    @property
    def written(self) -> bool:
        return self.status is IngestStatus.NEW


@dataclass(frozen=True)
class _Known:
    digest: str
    record_id: str


class Ingestor:
    """Persist raw events exactly once, using the raw archive as the authority."""

    def __init__(self, store: RawStore):
        self.store = store
        self._known: dict[tuple[str, date], dict[str, _Known]] = {}

    def refresh(self) -> None:
        """Forget cached archive contents; the next lookup re-reads the logs."""
        self._known.clear()

    def classify(self, record: RawRecord) -> IngestResult:
        """Return what ingesting a record would do, without writing anything."""
        validate_event(record)

        key = event_key(record)
        day = record.timestamp.date()
        known = self._archive(record.source, day).get(key)
        path = self.store.vault.path / self.store.day_path(record.source, day)

        if known is None:
            return IngestResult(IngestStatus.NEW, key, record.record_id, path)

        status = (
            IngestStatus.KNOWN
            if known.digest == observation_digest(record)
            else IngestStatus.CONFLICT
        )

        return IngestResult(status, key, record.record_id, path, known.record_id)

    def ingest(self, record: RawRecord) -> IngestResult:
        """Append a record unless the archive already holds its event."""
        result = self.classify(record)

        if result.status is not IngestStatus.NEW:
            return result

        path = self.store.append(record)
        self._archive(record.source, record.timestamp.date())[result.event_key] = _Known(
            observation_digest(record), record.record_id
        )

        return IngestResult(IngestStatus.NEW, result.event_key, record.record_id, path)

    def ingest_many(self, records: list[RawRecord]) -> list[IngestResult]:
        """Ingest records in order; duplicates within the batch are KNOWN."""
        return [self.ingest(record) for record in records]

    def _archive(self, source: str, day: date) -> dict[str, _Known]:
        cache_key = (source, day)

        if cache_key not in self._known:
            try:
                records = self.store.read_day(source, day)
            except FileNotFoundError:
                records = []

            index: dict[str, _Known] = {}

            for stored in records:
                # The first stored occurrence is authoritative if a legacy
                # archive already holds duplicates.
                index.setdefault(
                    event_key(stored), _Known(observation_digest(stored), stored.record_id)
                )

            self._known[cache_key] = index

        return self._known[cache_key]
