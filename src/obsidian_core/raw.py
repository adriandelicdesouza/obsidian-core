import hashlib
import json
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
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("RawRecord timestamp must be timezone-aware")

        if not self.source:
            raise ValueError("RawRecord source cannot be empty")

        if not self.event_type:
            raise ValueError("RawRecord event_type cannot be empty")

    @property
    def record_id(self) -> str:
        """Return a deterministic identifier derived from record contents."""
        canonical = json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "source": self.source,
                "event_type": self.event_type,
                "identifiers": self.identifiers,
                "metadata": self.metadata,
                "payload": self.payload,
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return digest[:16]
