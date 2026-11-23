"""In-memory collector used by the protocol tests."""

from datetime import UTC, datetime, timedelta

from obsidian_core.collectors import InvalidCursor, Observation
from obsidian_core.raw import RawRecord

BASE = datetime(2026, 11, 23, 9, 0, tzinfo=UTC)


def event(n, value=None, source="sensor"):
    return RawRecord(
        timestamp=BASE + timedelta(hours=n),
        source=source,
        event_type="reading",
        identifiers={"seq": n},
        payload={"value": n if value is None else value},
    )


class ListCollector:
    """Yields events in order; the cursor is the sequence number as text."""

    version = "1"
    source = "sensor"
    source_uri = "memory://sensor"

    def __init__(self, events, name="sensor:a", fail_after=None):
        self.name = name
        self.events = list(events)
        self.fail_after = fail_after
        self.calls = []

    def collect(self, cursor):
        self.calls.append(cursor)
        if cursor is not None and not any(str(e.identifiers["seq"]) == cursor for e in self.events):
            raise InvalidCursor(f"unknown position {cursor}")
        started = cursor is None
        emitted = 0
        for record in self.events:
            if started:
                if self.fail_after is not None and emitted >= self.fail_after:
                    raise RuntimeError("source went away")
                emitted += 1
                yield Observation(record, str(record.identifiers["seq"]))
            elif str(record.identifiers["seq"]) == cursor:
                started = True
