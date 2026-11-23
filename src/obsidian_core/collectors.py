"""Generic collector interface and source provenance.

A collector reads an external source and yields observations. It knows its
source; it does not know about ``RawStore``, deduplication or checkpoint files.
The boundary is::

    Collector.collect(cursor) -> Observation(record, cursor), ...
            │
            ▼
    stamp(record, provenance)      adds schema_version + provenance metadata
            │
            ▼
    Ingestor.ingest(record)        idempotent, archive-authoritative

Lifecycle
---------

1. The runner loads the collector's checkpoint, if any, and passes its cursor
   to :meth:`Collector.collect` (``None`` means "from the beginning").
2. The collector yields observations in an order where every observation that
   precedes a cursor has been yielded before that cursor. Resuming from any
   yielded cursor therefore loses nothing. Replaying some observations is
   allowed: ingestion is idempotent.
3. If the collector cannot use a cursor (for example the commit it names no
   longer exists), it raises :class:`InvalidCursor` before yielding anything.
   The runner then collects from the beginning.
4. A collector is restartable: ``collect`` may be called again at any time.

Provenance
----------

:class:`Provenance` records where a record came from: the collector's name and
version, an optional source location, and when it was collected. It is stored
under the reserved ``provenance`` metadata key, so it is kept in the archive
but excluded from event identity.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from .events import PROVENANCE_KEY, with_envelope
from .raw import RawRecord


class InvalidCursor(ValueError):
    """Raised by a collector that cannot resume from the given cursor."""


@dataclass(frozen=True)
class Provenance:
    """Where and how a raw event was collected."""

    collector: str
    collector_version: str
    collected_at: datetime
    source_uri: str | None = None

    def __post_init__(self) -> None:
        if not self.collector:
            raise ValueError("Provenance collector cannot be empty")

        if not self.collector_version:
            raise ValueError("Provenance collector_version cannot be empty")

        if self.collected_at.tzinfo is None or self.collected_at.utcoffset() is None:
            raise ValueError("Provenance collected_at must be timezone-aware")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "collector": self.collector,
            "collector_version": self.collector_version,
            "collected_at": self.collected_at.isoformat(),
        }

        if self.source_uri is not None:
            data["source_uri"] = self.source_uri

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        return cls(
            collector=data["collector"],
            collector_version=data["collector_version"],
            collected_at=datetime.fromisoformat(data["collected_at"]),
            source_uri=data.get("source_uri"),
        )

    @classmethod
    def of(cls, record: RawRecord) -> Provenance | None:
        """Return the provenance stored on a record, if any."""
        data = record.metadata.get(PROVENANCE_KEY)

        return cls.from_dict(data) if isinstance(data, dict) else None


@dataclass(frozen=True)
class Observation:
    """One collected event and the cursor that resumes collection after it."""

    record: RawRecord
    cursor: str | None


@runtime_checkable
class Collector(Protocol):
    """A source adapter that yields raw observations."""

    name: str
    """Unique, stable collector name, used for checkpoints and provenance."""

    version: str
    """Collector version, recorded in provenance."""

    source: str
    """The ``RawRecord.source`` this collector writes."""

    source_uri: str | None
    """Optional location of the source (a path or URL), recorded in provenance."""

    def collect(self, cursor: str | None) -> Iterator[Observation]:
        """Yield observations after ``cursor`` (or all of them when ``None``)."""
        ...


def provenance_for(collector: Collector, collected_at: datetime | None = None) -> Provenance:
    """Build the provenance for one collection run."""
    return Provenance(
        collector=collector.name,
        collector_version=collector.version,
        collected_at=collected_at or datetime.now(UTC),
        source_uri=collector.source_uri,
    )


def stamp(record: RawRecord, provenance: Provenance) -> RawRecord:
    """Return a record with the envelope schema version and provenance set."""
    return with_envelope(record, provenance.to_dict())
