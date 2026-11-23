from datetime import date

import pytest

from obsidian_core import RawStore, Vault, parse_wiki_links
from obsidian_core.checkpoints import CheckpointStore, run_collector
from obsidian_core.frontmatter import Frontmatter
from obsidian_core.git import GitActivityNotes, GitCollector
from obsidian_core.git.activity import ForeignNoteError, WriteStatus
from obsidian_core.ingestion import Ingestor

from .git_fakes import commit, init

DAY = date(2026, 11, 23)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "vault").mkdir()
    return Vault(tmp_path / "vault")


@pytest.fixture
def notes(vault):
    return GitActivityNotes(vault, RawStore(vault))


def collect(vault, repo, state):
    return run_collector(GitCollector(repo), Ingestor(RawStore(vault)), CheckpointStore(state))


@pytest.fixture
def two_repos(tmp_path, vault):
    core = init(tmp_path / "core")
    web = init(tmp_path / "web")
    commit(core, "Add ingestion [[draft]] #wip", "2026-11-23T09:15:00+00:00")
    commit(web, "Fix layout", "2026-11-23T11:30:00+00:00", {"a.css": "x\ny\n"})
    commit(core, "Next day", "2026-11-24T08:00:00+00:00")
    collect(vault, core, tmp_path / "s1")
    collect(vault, web, tmp_path / "s2")
    return core, web


def test_note_links_day_raw_log_and_repositories(two_repos, notes):
    content = notes.render(DAY)
    targets = {link.target for link in parse_wiki_links(content)}

    assert targets == {
        "2026-11-23",
        "Raw/git/2026/11/23",
        "Repositories/core",
        "Repositories/web",
    }


def test_commit_text_cannot_inject_links_or_tags(two_repos, notes):
    content = notes.render(DAY)

    assert "draft" not in {link.target for link in parse_wiki_links(content)}
    assert r"\[\[draft\]\] \#wip" in content


def test_note_traces_back_to_raw_records(two_repos, vault, notes):
    content = notes.render(DAY)
    records = RawStore(vault).read_day("git", DAY)
    properties = Frontmatter.parse(content)

    assert properties.get("source_records") == [r.record_id for r in records]
    assert properties.get("commits") == 2
    assert properties.get("repositories") == ["core", "web"]
    for record in records:
        assert f"record `{record.record_id}`" in content


def test_days_are_separate(two_repos, notes):
    assert "Next day" not in notes.render(DAY)
    assert "Next day" in notes.render(date(2026, 11, 24))
    assert notes.render(date(2026, 11, 25)) is None


def test_writing_is_idempotent(two_repos, notes):
    first = notes.write(DAY)
    text = first.path.read_text()
    second = notes.write(DAY)

    assert first.status is WriteStatus.CREATED
    assert second.status is WriteStatus.UNCHANGED
    assert second.path.read_text() == text
    assert first.path.relative_to(notes.vault.path).as_posix() == "Git Activity/2026/11/2026-11-23.md"


def test_reprocessing_does_not_duplicate_relationships(two_repos, notes, tmp_path, vault):
    before = notes.relationships(DAY)
    # Replaying collection (lost checkpoints) must not change the note.
    collect(vault, two_repos[0], tmp_path / "fresh")
    notes.write(DAY)
    notes.write(DAY)

    after = notes.relationships(DAY)
    assert after == before
    assert len({r.target for r in after}) == len(after) == 4


def test_new_commits_update_the_generated_note(two_repos, notes, tmp_path, vault):
    notes.write(DAY)
    commit(two_repos[1], "Late fix", "2026-11-23T22:00:00+00:00")
    collect(vault, two_repos[1], tmp_path / "s2")

    result = notes.write(DAY)

    assert result.status is WriteStatus.UPDATED
    assert "Late fix" in result.path.read_text()


def test_hand_written_note_is_never_overwritten(two_repos, notes, vault):
    note = vault.note(notes.note_path(DAY))
    note.write("# My own notes\n")

    with pytest.raises(ForeignNoteError):
        notes.write(DAY)

    assert note.read() == "# My own notes\n"


def test_configurable_link_rules(two_repos, vault):
    notes = GitActivityNotes(
        vault, RawStore(vault), daily_note_format="Daily/%Y/%m-%d", repository_folder=None
    )
    targets = {link.target for link in parse_wiki_links(notes.render(DAY))}

    assert {"Daily/2026/11-23", "core", "web"} <= targets


def test_unsafe_repository_names_become_safe_targets(vault, tmp_path):
    repo = init(tmp_path / "x")
    commit(repo, "c", "2026-11-23T09:00:00+00:00")
    run_collector(
        GitCollector(repo, repository="a|b#c"),
        Ingestor(RawStore(vault)),
        CheckpointStore(tmp_path / "s"),
    )

    content = GitActivityNotes(vault, RawStore(vault)).render(DAY)

    assert "Repositories/a-b-c" in {link.target for link in parse_wiki_links(content)}


def test_raw_archive_is_untouched_by_presentation(two_repos, notes, vault):
    raw = vault.path / RawStore(vault).day_path("git", DAY)
    before = raw.read_text()
    notes.write(DAY)
    assert raw.read_text() == before
