class ObsidianCoreError(Exception):
    """Base exception for obsidian-core."""


class VaultError(ObsidianCoreError):
    """Raised when a vault operation is invalid."""