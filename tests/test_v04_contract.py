"""Cross-component contract tests for the v0.4 ingestion protocol (#67).

They exercise the full path a real deployment uses:

    git repository -> GitCollector -> run_collector -> Ingestor -> RawStore
                                         |                 ^
                                  CheckpointStore     reconcile
                                                          |
                                   RawStore -> GitActivityNotes -> vault notes
"""

import ast
from datetime import date
from pathlib import Path

import pytest

import obsidian_core
from obsidian_core import (
    SCHEMA_VERSION,
    CheckpointStatus,
    CheckpointStore,
    Ingestor,
    IngestStatus,
    Provenance,
    RawParser,
    RawStore,
    Vault,
    event_key,
    parse_wiki_links,
    reconcile,
    run_collector,
)
from obsidian_core.events import SCHEMA_VERSION_KEY
from obsidian_core.git import GitActivityNotes, GitCollector

from .git_fakes import commit, git, init

DAY = date(2026, 11, 23)
PACKAGE = Path(obsidian_core.__file__).parent


@pytest.fixture
def env(tmp_path):
    (tmp_path / "vault").mkdir()
    vault = Vault(tmp_path / "vault")
    repo = init(tmp_path / "core")
    return vault, repo, CheckpointStore(tmp_path / "state")


def archive(vault, day=DAY):
    return RawStore(vault).read_day("git", day)


def run(vault, repo, checkpoints, **kwargs):
    return run_collector(GitCollector(repo), Ingestor(RawStore(vault)), checkpoints, **kwargs)


def test_generic_modules_do_not_depend_on_git_or_obsidian_presentation():
    generic = ["events", "ingestion", "collectors", "checkpoints", "reconciliation", "raw_store"]

    for module in generic:
        tree = ast.parse((PACKAGE / f"{module}.py").read_text())
        imported = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}

        assert not any("git" in name for name in imported), module
        assert not any(name.endswith(("links", "relationships", "note")) for name in imported), module


def test_git_adapter_never_writes_the_archive_directly():
    for path in (PACKAGE / "git").glob("*.py"):
        source = path.read_text()
        assert "store.append" not in source, path.name
        assert "RawStore(" not in source, path.name
        assert ".write(" not in source or path.name == "activity.py", path.name


def test_full_pipeline_new_duplicate_checkpoint_reconcile_notes(env):
    vault, repo, checkpoints = env
    shas = [commit(repo, f"c{n}", f"2026-11-23T1{n}:00:00+00:00") for n in range(5)]

    # 1. new events
    first = run(vault, repo, checkpoints, checkpoint_every=2)
    assert (first.new, first.known) == (5, 0)
    assert checkpoints.load("git:core").checkpoint.cursor == shas[-1]

    # 2. identity, schema version and provenance on every archived record
    records = archive(vault)
    assert [r.identifiers["commit"] for r in records] == shas
    assert all(r.metadata[SCHEMA_VERSION_KEY] == SCHEMA_VERSION for r in records)
    assert all(Provenance.of(r).collector == "git:core" for r in records)
    assert len({event_key(r) for r in records}) == 5

    # 3. duplicate observations never create raw records, whatever the checkpoint says
    for damage in ("lost", "corrupt"):
        if damage == "lost":
            checkpoints.clear("git:core")
        else:
            checkpoints.path_for("git:core").write_text("{")
        replay = run(vault, repo, checkpoints)
        assert (replay.new, replay.known) == (0, 5)
        assert archive(vault) == records

    # 4. reconciliation agrees with the archive and does not write
    log = vault.path / RawStore(vault).day_path("git", DAY)
    before = log.read_text()
    report = reconcile(GitCollector(repo), Ingestor(RawStore(vault)), checkpoints=checkpoints)
    assert report.consistent and report.present == 5
    assert report.checkpoint_status is CheckpointStatus.VALID
    assert log.read_text() == before

    # 5. presentation: one note, links to day, raw log and repository, idempotent
    notes = GitActivityNotes(vault, RawStore(vault))
    written = notes.write(DAY)
    again = notes.write(DAY)
    links = [link.target for link in parse_wiki_links(written.path.read_text())]
    assert sorted(links) == ["2026-11-23", "Raw/git/2026/11/23", "Repositories/core"]
    assert again.status.value == "unchanged"


def test_gap_recovery_through_reconciliation(env):
    vault, repo, checkpoints = env
    for n in range(4):
        commit(repo, f"c{n}", f"2026-11-23T1{n}:00:00+00:00")
    run(vault, repo, checkpoints)

    # Lose the archive (e.g. restore of an older vault backup) but keep the checkpoint.
    log = vault.path / RawStore(vault).day_path("git", DAY)
    text = log.read_text()
    first_only = text[: text.index("\n## ", text.index("\n## ") + 1) + 1]
    log.write_text(first_only)  # keep the first record only
    assert len(archive(vault)) == 1

    normal = run(vault, repo, checkpoints)
    assert normal.new == 0  # the checkpoint hides the gap ...

    report = reconcile(
        GitCollector(repo), Ingestor(RawStore(vault)), checkpoints=checkpoints, repair=True
    )
    assert report.checkpoint_ahead_of_archive  # ... reconciliation finds it
    assert report.repaired == 3
    assert [r.payload["subject"] for r in archive(vault)] == ["c0", "c1", "c2", "c3"]
    assert log.read_text().startswith(first_only)


def test_history_rewrite_is_reported_not_erased(env):
    vault, repo, checkpoints = env
    base = commit(repo, "base", "2026-11-23T09:00:00+00:00")
    commit(repo, "dropped", "2026-11-23T10:00:00+00:00")
    run(vault, repo, checkpoints)
    git(repo, "reset", "-q", "--hard", base)
    commit(repo, "replacement", "2026-11-23T11:00:00+00:00")

    run(vault, repo, checkpoints)
    report = reconcile(GitCollector(repo), Ingestor(RawStore(vault)))

    assert [r.payload["subject"] for r in report.archive_only] == ["dropped"]
    assert [r.payload["subject"] for r in archive(vault)] == ["base", "dropped", "replacement"]


def test_v03_archives_remain_readable_and_deduplicated(env):
    vault, repo, checkpoints = env
    sha = commit(repo, "legacy", "2026-11-23T09:00:00+00:00")
    [obs] = list(GitCollector(repo).collect(None))
    # A record written by a v0.3 writer: no schema_version, no provenance.
    RawStore(vault).append(obs.record)

    report = run(vault, repo, checkpoints)

    assert report.known == 1 and report.new == 0
    [stored] = RawParser.parse(
        (vault.path / RawStore(vault).day_path("git", DAY)).read_text()
    )
    assert stored.identifiers["commit"] == sha
    assert SCHEMA_VERSION_KEY not in stored.metadata


def test_ingest_status_values_are_stable():
    assert {s.value for s in IngestStatus} == {"new", "known", "conflict"}
