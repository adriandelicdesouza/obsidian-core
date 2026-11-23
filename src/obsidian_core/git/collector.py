"""Collect Git commits as raw events.

Mapping to the generic raw-event envelope (see :mod:`obsidian_core.events`):

==============  ============================================================
``source``      ``"git"`` (configurable)
``event_type``  ``"commit"``
``timestamp``   committer date, with the committer's UTC offset
``identifiers`` ``{"repository": <name>, "commit": <full hash>}``
``payload``     subject, body, author (name, email, date), committer (name,
                email), parents, files_changed, insertions, deletions
==============  ============================================================

The committer date is used because it is when the commit entered the
history being collected; the author date is kept in the payload. The ref being
collected is not part of the observation, so the same commit reached from two
branches is one event. Merge commits report no file statistics (``git log``
shows no diff for them by default).

Cursor: the full hash of the last commit yielded. Commits are yielded oldest
first in reverse topological order, so every ancestor of a cursor commit has
been yielded before it, and resuming with ``<cursor>..<ref>`` loses nothing.
Commits on merged side branches may be yielded again on resume; ingestion
reports those as ``KNOWN``. A cursor that no longer exists or is not an
ancestor of the ref (history rewritten, branch reset) raises
:class:`~obsidian_core.collectors.InvalidCursor`, and the runner restarts
from the beginning.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from ..collectors import InvalidCursor, Observation
from ..raw import RawRecord

_FIELDS = ["%H", "%P", "%an", "%ae", "%aI", "%cn", "%ce", "%cI", "%s", "%b"]
_FORMAT = "%x1e" + "%x1f".join(_FIELDS) + "%x1f"
_HASH = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


class GitError(RuntimeError):
    """Raised when git fails for a reason other than an unusable cursor."""


class GitCollector:
    """Collector for the commits reachable from one ref of one repository."""

    version = "1"
    event_type = "commit"

    def __init__(
        self,
        repo_path: str | Path,
        *,
        repository: str | None = None,
        ref: str = "HEAD",
        source: str = "git",
        git: str = "git",
    ):
        if not ref or ref.startswith("-"):
            raise ValueError(f"Invalid ref: {ref!r}")

        self.repo_path = Path(repo_path).expanduser().resolve()
        self.repository = repository or self.repo_path.name
        self.ref = ref
        self.source = source
        self.git = git
        self.name = f"git:{self.repository}" + ("" if ref == "HEAD" else f"@{ref}")
        self.source_uri: str | None = self.repo_path.as_uri()

    def collect(self, cursor: str | None) -> Iterator[Observation]:
        tip = self._rev_parse(self.ref)

        if tip is None:
            if self._run("rev-parse", "--git-dir", check=False).returncode != 0:
                raise GitError(f"Not a git repository: {self.repo_path}")
            if cursor is not None:
                raise InvalidCursor(f"{self.ref} has no commits")
            return

        if cursor is not None:
            self._check_cursor(cursor, tip)
            revision = f"{cursor}..{tip}"
        else:
            revision = tip

        output = self._run(
            "-c",
            "i18n.logOutputEncoding=UTF-8",
            "log",
            "--reverse",
            "--topo-order",
            "--no-color",
            "--numstat",
            f"--format={_FORMAT}",
            revision,
            "--",
        ).stdout

        for chunk in output.split("\x1e")[1:]:
            record = self._record(chunk)
            yield Observation(record, record.identifiers["commit"])

    def _check_cursor(self, cursor: str, tip: str) -> None:
        if not _HASH.match(cursor):
            raise InvalidCursor(f"Not a full commit hash: {cursor!r}")

        if self._rev_parse(cursor) != cursor:
            raise InvalidCursor(f"Commit {cursor} no longer exists")

        ancestor = self._run("merge-base", "--is-ancestor", cursor, tip, check=False)

        if ancestor.returncode == 1:
            raise InvalidCursor(f"Commit {cursor} is not an ancestor of {self.ref}")

        if ancestor.returncode != 0:
            raise GitError(ancestor.stderr.strip())

    def _rev_parse(self, revision: str) -> str | None:
        result = self._run(
            "rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{commit}}",
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def _record(self, chunk: str) -> RawRecord:
        parts = chunk.split("\x1f", len(_FIELDS))

        if len(parts) != len(_FIELDS) + 1:
            raise GitError("Unexpected git log output")

        sha, parents, an, ae, adate, cn, ce, cdate, subject, body, stats = parts
        files = insertions = deletions = 0

        for line in stats.strip("\n").splitlines():
            columns = line.split("\t", 2)

            if len(columns) != 3:
                continue

            files += 1
            insertions += int(columns[0]) if columns[0].isdigit() else 0
            deletions += int(columns[1]) if columns[1].isdigit() else 0

        return RawRecord(
            timestamp=datetime.fromisoformat(cdate),
            source=self.source,
            event_type=self.event_type,
            identifiers={"repository": self.repository, "commit": sha},
            payload={
                "subject": subject,
                "body": body.strip(),
                "author": {"name": an, "email": ae, "date": adate},
                "committer": {"name": cn, "email": ce},
                "parents": parents.split(),
                "files_changed": files,
                "insertions": insertions,
                "deletions": deletions,
            },
        )

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [self.git, "-C", str(self.repo_path), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitError(f"git executable not found: {self.git}") from exc

        if check and result.returncode != 0:
            raise GitError(result.stderr.strip() or f"git {args[0]} failed")

        return result
