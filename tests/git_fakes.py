"""Helpers that build real throwaway git repositories for the adapter tests."""

import os
import subprocess

ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Ada",
    "GIT_AUTHOR_EMAIL": "ada@example.invalid",
    "GIT_COMMITTER_NAME": "Ada",
    "GIT_COMMITTER_EMAIL": "ada@example.invalid",
}


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], env=ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


def init(repo):
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    return repo


def commit(repo, message, when, files=None):
    for name, text in (files or {"file.txt": message}).items():
        (repo / name).write_text(text)
        git(repo, "add", name)
    env = {**ENV, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", message],
        env=env,
        check=True,
        capture_output=True,
    )
    return git(repo, "rev-parse", "HEAD")
