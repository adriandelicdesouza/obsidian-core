"""Git adapter: collects commits as raw events and relates them to the vault.

Everything Git-specific lives in this package. It consumes the generic
protocols (:mod:`obsidian_core.collectors`, :mod:`obsidian_core.ingestion`,
:mod:`obsidian_core.checkpoints`) and is never imported by them.
"""

from .activity import GitActivityNotes
from .collector import GitCollector, GitError

__all__ = ["GitActivityNotes", "GitCollector", "GitError"]
