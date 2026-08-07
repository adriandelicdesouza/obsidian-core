from dataclasses import dataclass, field
from datetime import datetime
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

    @property
    def generated_id(self) -> str:
        """Return a deterministic identifier for this generated record."""
        timestamp = self.timestamp.astimezone().strftime(
            "%Y%m%dT%H%M%S.%f%z"
        )

        return (
            f"{timestamp}-"
            f"{self.generator}-"
            f"{self.generator_version}"
        )