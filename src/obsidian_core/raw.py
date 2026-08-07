from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """Immutable representation of a raw machine-generated event."""

    timestamp: datetime
    source: str
    event_type: str
    identifiers: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: Any = None

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("RawRecord source cannot be empty")

        if not self.event_type:
            raise ValueError("RawRecord event_type cannot be empty")

    @property
    def record_id(self) -> str:
        """Return a stable human-readable identifier for the record."""
        timestamp = self.timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
        return f"{timestamp}-{self.source}-{self.event_type}"
