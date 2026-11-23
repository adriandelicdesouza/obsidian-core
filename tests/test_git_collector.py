from datetime import datetime, timedelta, timezone

import pytest

from obsidian_core import RawStore, Vault
from obsidian_core.checkpoints import CheckpointStore, run_collector
from obsidian_core.collectors import Collector, InvalidCursor, Provenance
from obsidian_core.git import GitCollector, GitError
from obsidian_core.ingestion import Ingestor

from .git_fakes import commit, git, init

DAY = "2026-11-23T10:00:00+01:00"


@pytest.fixture
def repo(tmp_path):
    return init(tmp_path / "core")


def collected(collector, cursor=None):
    return list(collector.collect(cursor))


def test_is_a_generic_collector(repo):
    collector = GitCollector(repo)
    assert isinstance(collector, Collector)
    assert collector.name == "git:core"
    assert GitCollector(repo, ref="dev").name == "git:core@dev"
    assert collector.source == "git"
    assert collector.source_uri.startswith("file://")


def test_commit_maps_to_generic_envelope(repo):
    sha = commit(repo, "Add parser\n\nLonger body.", DAY, {"a.txt": "1\n2\n", "b.txt": "x\n"})

    [obs] = collected(GitCollector(repo))
    record = obs.record

    assert obs.cursor == sha
    assert record.source == "git"
    assert record.event_type == "commit"
    assert record.timestamp == datetime(2026, 11, 23, 10, tzinfo=timezone(timedelta(hours=1)))
    assert record.identifiers == {"repository": "core", "commit": sha}
    assert record.payload == {
        "subject": "Add parser",
        "body": "Longer body.",
        "author": {"name": "Ada", "email": "ada@example.invalid", "date": "2026-11-23T10:00:00+01:00"},
        "committer": {"name": "Ada", "email": "ada@example.invalid"},
        "parents": [],
        "files_changed": 2,
        "insertions": 3,
        "deletions": 0,
    }


def test_commits_are_oldest_first_and_cursor_resumes(repo):
    shas = [commit(repo, f"c{n}", f"2026-11-23T1{n}:00:00+00:00") for n in range(4)]
    collector = GitCollector(repo)

    assert [o.cursor for o in collected(collector)] == shas
    assert [o.cursor for o in collected(collector, shas[1])] == shas[2:]
    assert collected(collector, shas[-1]) == []


def test_unicode_and_special_characters_survive(repo):
    commit(repo, "Fix «ünïcode» | [[link]] #tag", DAY)
    [obs] = collected(GitCollector(repo))
    assert obs.record.payload["subject"] == "Fix «ünïcode» | [[link]] #tag"


def test_empty_repository_yields_nothing(repo):
    assert collected(GitCollector(repo)) == []


def test_not_a_repository(tmp_path):
    with pytest.raises(GitError):
        collected(GitCollector(tmp_path))


@pytest.mark.parametrize("cursor", ["nothex", "0" * 40])
def test_unknown_cursor_is_invalid(repo, cursor):
    commit(repo, "c", DAY)
    with pytest.raises(InvalidCursor):
        collected(GitCollector(repo), cursor)


def test_cursor_not_ancestor_after_reset_is_invalid(repo):
    base = commit(repo, "base", "2026-11-23T09:00:00+00:00")
    dropped = commit(repo, "dropped", "2026-11-23T10:00:00+00:00")
    git(repo, "reset", "-q", "--hard", base)
    commit(repo, "replacement", "2026-11-23T11:00:00+00:00")

    with pytest.raises(InvalidCursor):
        collected(GitCollector(repo), dropped)


def test_option_like_ref_is_rejected(repo):
    with pytest.raises(ValueError):
        GitCollector(repo, ref="--output=/tmp/x")


def test_merge_resume_loses_nothing(repo):
    commit(repo, "root", "2026-11-23T09:00:00+00:00")
    git(repo, "checkout", "-q", "-b", "side")
    side = commit(repo, "side", "2026-11-23T10:00:00+00:00", {"side.txt": "s"})
    git(repo, "checkout", "-q", "main")
    main = commit(repo, "main", "2026-11-23T11:00:00+00:00", {"main.txt": "m"})
    git(repo, "merge", "-q", "--no-edit", "side")
    merge = git(repo, "rev-parse", "HEAD")

    everything = {o.cursor for o in collected(GitCollector(repo))}
    assert {side, main, merge} <= everything

    for obs in collected(GitCollector(repo)):
        after = {o.cursor for o in collected(GitCollector(repo), obs.cursor)}
        before = set()
        for earlier in collected(GitCollector(repo)):
            before.add(earlier.cursor)
            if earlier.cursor == obs.cursor:
                break
        assert before | after == everything


def test_runner_ingests_git_once_with_provenance(repo, tmp_path):
    (tmp_path / "vault").mkdir()
    vault = Vault(tmp_path / "vault")
    ingestor = Ingestor(RawStore(vault))
    checkpoints = CheckpointStore(tmp_path / "state")
    first = commit(repo, "one", DAY)

    report = run_collector(GitCollector(repo), ingestor, checkpoints)
    assert (report.new, report.known) == (1, 0)
    assert checkpoints.load("git:core").checkpoint.cursor == first

    commit(repo, "two", "2026-11-23T12:00:00+01:00")
    report = run_collector(GitCollector(repo), ingestor, checkpoints)
    assert (report.new, report.known) == (1, 0)

    checkpoints.clear("git:core")
    report = run_collector(GitCollector(repo), Ingestor(RawStore(vault)), checkpoints)
    assert (report.new, report.known) == (0, 2)

    records = RawStore(vault).read_day("git", datetime.fromisoformat(DAY).date())
    assert [r.payload["subject"] for r in records] == ["one", "two"]
    assert Provenance.of(records[0]).collector == "git:core"


def test_runner_restarts_after_history_rewrite(repo, tmp_path):
    (tmp_path / "vault").mkdir()
    vault = Vault(tmp_path / "vault")
    checkpoints = CheckpointStore(tmp_path / "state")
    base = commit(repo, "base", "2026-11-23T09:00:00+00:00")
    commit(repo, "dropped", "2026-11-23T10:00:00+00:00")
    run_collector(GitCollector(repo), Ingestor(RawStore(vault)), checkpoints)

    git(repo, "reset", "-q", "--hard", base)
    commit(repo, "replacement", "2026-11-23T11:00:00+00:00")
    report = run_collector(GitCollector(repo), Ingestor(RawStore(vault)), checkpoints)

    assert report.restarted_from_beginning
    assert (report.new, report.known) == (1, 1)
    # The dropped commit stays in the authoritative archive.
    subjects = [r.payload["subject"] for r in RawStore(vault).read_day("git", datetime(2026, 11, 23).date())]  # noqa: DTZ001
    assert subjects == ["base", "dropped", "replacement"]
