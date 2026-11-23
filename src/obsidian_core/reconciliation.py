"""Reconciliation of a source against the authoritative raw archive.

Checkpoints make collection fast; they say nothing about what the archive
actually holds. Reconciliation answers that question by re-enumerating the
source and comparing each observation with the archive:

``present``
    The archive holds the event with the same observation.
``missing``
    The source reports an event the archive does not hold: a gap. Gaps come
    from lost writes, a checkpoint saved ahead of the archive, a restored
    backup, or events collected before the collector existed.
``conflicts``
    The archive holds the event key with a different observation.
``archive_only``
    Archive records written by this collector (by provenance) that the source
    no longer reports, such as commits removed by a history rewrite. Only
    computed for a full enumeration (``since=None``), over every daily log
    of the collector's source.

Rules:

* The archive is never modified except by appending. With ``repair=True``,
  missing events are ingested through :class:`~obsidian_core.ingestion.Ingestor`
  (so a replay is still a no-op). Conflicts and archive-only records are only
  reported; deciding what they mean is the caller's job.
* Checkpoints are read, never written. ``checkpoint_ahead_of_archive`` is set
  when a missing event sits at or before the checkpoint's cursor, i.e. the
  checkpoint would have skipped it forever.
* A partial failure (the source raising mid-enumeration) returns a report
  with ``complete=False`` and the error. Whatever was already repaired stays,
  which is safe because those appends are idempotent; ``archive_only`` is
  left empty because an incomplete enumeration cannot prove absence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from .checkpoints import CheckpointStatus, CheckpointStore
from .collectors import Collector, Provenance, provenance_for, stamp
from .events import event_key
from .ingestion import Ingestor, IngestResult, IngestStatus
from .raw import RawRecord


@dataclass
class ReconciliationReport:
    collector: str
    since: str | None
    complete: bool = True
    error: str = ""
    examined: int = 0
    present: int = 0
    missing: list[RawRecord] = field(default_factory=list)
    repaired: int = 0
    conflicts: list[IngestResult] = field(default_factory=list)
    archive_only: list[RawRecord] = field(default_factory=list)
    days: list[date] = field(default_factory=list)
    checkpoint_status: CheckpointStatus | None = None
    checkpoint_cursor: str | None = None
    checkpoint_cursor_seen: bool = False
    checkpoint_ahead_of_archive: bool = False

    @property
    def consistent(self) -> bool:
        """True when the archive matches the source for everything examined."""
        return (
            self.complete
            and not self.conflicts
            and not self.archive_only
            and len(self.missing) == self.repaired
        )


def reconcile(
    collector: Collector,
    ingestor: Ingestor,
    *,
    since: str | None = None,
    checkpoints: CheckpointStore | None = None,
    repair: bool = False,
    collected_at: datetime | None = None,
) -> ReconciliationReport:
    """Compare what a source reports with the archive; optionally append gaps."""
    report = ReconciliationReport(collector.name, since)
    provenance = provenance_for(collector, collected_at)
    produced: set[str] = set()
    days: set[date] = set()
    missing_before_cursor = False

    if checkpoints is not None:
        loaded = checkpoints.load(collector.name)
        report.checkpoint_status = loaded.status
        report.checkpoint_cursor = loaded.checkpoint.cursor if loaded.checkpoint else None

    ingestor.refresh()

    try:
        for observation in collector.collect(since):
            record = stamp(observation.record, provenance)
            report.examined += 1
            produced.add(event_key(record))
            days.add(record.timestamp.date())

            result = ingestor.classify(record)

            if result.status is IngestStatus.KNOWN:
                report.present += 1
            elif result.status is IngestStatus.CONFLICT:
                report.conflicts.append(result)
            else:
                report.missing.append(record)
                if not report.checkpoint_cursor_seen:
                    missing_before_cursor = True
                if repair and ingestor.ingest(record).status is IngestStatus.NEW:
                    report.repaired += 1

            if (
                report.checkpoint_cursor is not None
                and observation.cursor == report.checkpoint_cursor
            ):
                report.checkpoint_cursor_seen = True
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed silently
        report.complete = False
        report.error = f"{type(exc).__name__}: {exc}"

    report.days = sorted(days)
    report.checkpoint_ahead_of_archive = (
        report.checkpoint_cursor_seen and missing_before_cursor
    )

    if report.complete and since is None:
        report.archive_only = _archive_only(
            collector, ingestor, sorted(days | set(_archived_days(collector, ingestor))), produced
        )

    return report


def _archived_days(collector: Collector, ingestor: Ingestor) -> list[date]:
    """Dates of every daily log for the collector's source (RawStore layout)."""
    base = ingestor.store.vault.path / ingestor.store.root / collector.source
    days = []

    for path in base.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9].md"):
        try:
            days.append(date(int(path.parent.parent.name), int(path.parent.name), int(path.stem)))
        except ValueError:
            continue

    return days


def _origin(record: RawRecord) -> Provenance | None:
    try:
        return Provenance.of(record)
    except (KeyError, TypeError, ValueError):
        return None


def _archive_only(
    collector: Collector,
    ingestor: Ingestor,
    days: list[date],
    produced: set[str],
) -> list[RawRecord]:
    found = []

    for day in days:
        try:
            records = ingestor.store.read_day(collector.source, day)
        except FileNotFoundError:
            continue

        for record in records:
            origin = _origin(record)

            ours = origin is not None and origin.collector == collector.name

            if ours and event_key(record) not in produced:
                found.append(record)

    return found
