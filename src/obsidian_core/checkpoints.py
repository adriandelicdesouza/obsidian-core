"""Checkpointing and recovery for long-running collectors.

A checkpoint is a collection optimisation, not history. It stores one opaque
cursor per collector so the next run can skip what was already collected. The
raw archive stays the only authoritative record of what was observed:

* A checkpoint is saved only after every observation up to its cursor has been
  ingested. A crash between ingestion and saving leaves an older checkpoint,
  and the next run replays a few observations, which ingestion reports as
  ``KNOWN``.
* A missing, unreadable, corrupt or mismatched checkpoint is never fatal. The
  run starts from the beginning of the source, which is always safe because
  ingestion is idempotent. A corrupt file is moved aside, not deleted, so it
  can be inspected.
* Checkpoints are stored as JSON files outside the raw tree (by default, the
  caller chooses the directory). Deleting all of them loses no data.

File format (``<collector>.json``)::

    {"format": 1, "collector": "git:core", "cursor": "<opaque>",
     "updated_at": "<ISO 8601>", "events_seen": 42}
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from .collectors import Collector, InvalidCursor, provenance_for, stamp
from .ingestion import Ingestor, IngestResult, IngestStatus

CHECKPOINT_FORMAT = 1


class CheckpointStatus(Enum):
    VALID = "valid"
    MISSING = "missing"
    CORRUPT = "corrupt"
    INVALID = "invalid"


@dataclass(frozen=True)
class Checkpoint:
    collector: str
    cursor: str
    updated_at: datetime
    events_seen: int = 0


@dataclass(frozen=True)
class CheckpointLoad:
    """Result of loading a checkpoint; ``checkpoint`` is set only when VALID."""

    status: CheckpointStatus
    checkpoint: Checkpoint | None = None
    detail: str = ""


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


class CheckpointStore:
    """Persist one checkpoint file per collector in a directory."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def path_for(self, collector: str) -> Path:
        if not collector:
            raise ValueError("Collector name cannot be empty")

        return self.directory / f"{_SAFE_NAME.sub('_', collector)}.json"

    def load(self, collector: str) -> CheckpointLoad:
        path = self.path_for(collector)

        if not path.exists():
            return CheckpointLoad(CheckpointStatus.MISSING)

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            moved = self._quarantine(path)
            return CheckpointLoad(CheckpointStatus.CORRUPT, detail=f"{exc}; moved to {moved}")

        problem = self._problem(data, collector)

        if problem:
            return CheckpointLoad(CheckpointStatus.INVALID, detail=problem)

        return CheckpointLoad(
            CheckpointStatus.VALID,
            Checkpoint(
                collector=data["collector"],
                cursor=data["cursor"],
                updated_at=datetime.fromisoformat(data["updated_at"]),
                events_seen=data.get("events_seen", 0),
            ),
        )

    def save(self, checkpoint: Checkpoint) -> Path:
        """Write a checkpoint atomically (temporary file, fsync, rename)."""
        path = self.path_for(checkpoint.collector)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "format": CHECKPOINT_FORMAT,
            "collector": checkpoint.collector,
            "cursor": checkpoint.cursor,
            "updated_at": checkpoint.updated_at.isoformat(),
            "events_seen": checkpoint.events_seen,
        }
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

        return path

    def clear(self, collector: str) -> None:
        """Remove a collector's checkpoint; the next run starts from the beginning."""
        self.path_for(collector).unlink(missing_ok=True)

    @staticmethod
    def _problem(data: object, collector: str) -> str:
        if not isinstance(data, dict):
            return "checkpoint is not a JSON object"

        if data.get("format") != CHECKPOINT_FORMAT:
            return f"unsupported checkpoint format {data.get('format')!r}"

        if data.get("collector") != collector:
            return f"checkpoint belongs to {data.get('collector')!r}"

        if not isinstance(data.get("cursor"), str) or not data["cursor"]:
            return "checkpoint cursor missing"

        try:
            updated = datetime.fromisoformat(data["updated_at"])
        except (KeyError, TypeError, ValueError):
            return "checkpoint updated_at missing or invalid"

        if updated.tzinfo is None:
            return "checkpoint updated_at is not timezone-aware"

        seen = data.get("events_seen", 0)
        if isinstance(seen, bool) or not isinstance(seen, int) or seen < 0:
            return "checkpoint events_seen invalid"

        return ""

    @staticmethod
    def _quarantine(path: Path) -> Path:
        stamp_ = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        moved = path.with_name(f"{path.name}.corrupt-{stamp_}")
        os.replace(path, moved)
        return moved


@dataclass
class RunReport:
    """Summary of one collector run."""

    collector: str
    checkpoint_status: CheckpointStatus
    started_from: str | None
    cursor: str | None = None
    new: int = 0
    known: int = 0
    conflicts: list[IngestResult] = field(default_factory=list)
    restarted_from_beginning: bool = False
    detail: str = ""

    @property
    def seen(self) -> int:
        return self.new + self.known + len(self.conflicts)


def run_collector(
    collector: Collector,
    ingestor: Ingestor,
    checkpoints: CheckpointStore,
    *,
    checkpoint_every: int = 100,
    collected_at: datetime | None = None,
) -> RunReport:
    """Collect, ingest idempotently and checkpoint one collector.

    Checkpoints are saved every ``checkpoint_every`` observations and at the
    end, each time only for observations already ingested. If the collector or
    ingestion raises, the last saved checkpoint stays and the error propagates.
    """
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every must be at least 1")

    loaded = checkpoints.load(collector.name)
    start = loaded.checkpoint.cursor if loaded.checkpoint else None
    report = RunReport(collector.name, loaded.status, start, cursor=start, detail=loaded.detail)
    provenance = provenance_for(collector, collected_at)
    seen_before = loaded.checkpoint.events_seen if loaded.checkpoint else 0
    pending = 0

    def save() -> None:
        if report.cursor is not None:
            checkpoints.save(
                Checkpoint(
                    collector.name,
                    report.cursor,
                    datetime.now(UTC),
                    seen_before + report.seen,
                )
            )

    try:
        observations = iter(collector.collect(start))
        first = next(observations, None)
    except InvalidCursor as exc:
        if start is None:
            raise
        report.restarted_from_beginning = True
        report.detail = f"cursor {start!r} rejected: {exc}"
        report.started_from = None
        report.cursor = None
        seen_before = 0
        checkpoints.clear(collector.name)
        observations = iter(collector.collect(None))
        first = next(observations, None)

    current = first

    while current is not None:
        record = current.record

        if record.source != collector.source:
            raise ValueError(
                f"Collector {collector.name!r} yielded source {record.source!r}, "
                f"expected {collector.source!r}"
            )

        result = ingestor.ingest(stamp(record, provenance))

        if result.status is IngestStatus.NEW:
            report.new += 1
        elif result.status is IngestStatus.KNOWN:
            report.known += 1
        else:
            report.conflicts.append(result)

        if current.cursor is not None:
            report.cursor = current.cursor
            pending += 1

        if pending >= checkpoint_every:
            save()
            pending = 0

        current = next(observations, None)

    save()

    return report
