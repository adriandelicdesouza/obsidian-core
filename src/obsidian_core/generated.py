import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class GeneratedRecord:
    """Derived content generated from one or more source records."""

    timestamp: datetime
    generator: str
    generator_version: str
    content: Any

    source_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_generated_id: str | None = None

    def __post_init__(self) -> None:
        """Validate generated record invariants."""

        if self.timestamp.tzinfo is None:
            raise ValueError("GeneratedRecord timestamp must be timezone-aware")

        if not self.generator:
            raise ValueError("GeneratedRecord generator cannot be empty")

        if not self.generator_version:
            raise ValueError("GeneratedRecord generator version cannot be empty")

        if self.previous_generated_id == "":
            raise ValueError("Previous generated ID cannot be empty")

    @property
    def generated_id(self) -> str:
        """Return a deterministic identifier for this generated record."""

        timestamp = self.timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%S.%f%z")

        content_hash = hashlib.sha256(str(self.content).encode("utf-8")).hexdigest()[:16]

        return f"{timestamp}-{self.generator}-{self.generator_version}-{content_hash}"
