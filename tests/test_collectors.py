from datetime import UTC, datetime

import pytest

from obsidian_core.collectors import Collector, Provenance, provenance_for, stamp
from obsidian_core.events import PROVENANCE_KEY, SCHEMA_VERSION, SCHEMA_VERSION_KEY, event_key

from .collector_fakes import ListCollector, event

NOW = datetime(2026, 11, 23, 12, tzinfo=UTC)


def test_fake_satisfies_the_protocol():
    assert isinstance(ListCollector([]), Collector)


def test_provenance_round_trips():
    p = Provenance("sensor:a", "1", NOW, "memory://sensor")
    assert Provenance.from_dict(p.to_dict()) == p
    assert "source_uri" not in Provenance("x", "1", NOW).to_dict()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"collector": "", "collector_version": "1", "collected_at": NOW},
        {"collector": "x", "collector_version": "", "collected_at": NOW},
        {"collector": "x", "collector_version": "1", "collected_at": datetime(2026, 1, 1)},  # noqa: DTZ001
    ],
)
def test_provenance_validation(kwargs):
    with pytest.raises(ValueError):
        Provenance(**kwargs)


def test_stamp_adds_envelope_and_provenance_without_changing_identity():
    collector = ListCollector([])
    record = event(1)
    stamped = stamp(record, provenance_for(collector, NOW))

    assert stamped.metadata[SCHEMA_VERSION_KEY] == SCHEMA_VERSION
    assert stamped.metadata[PROVENANCE_KEY] == {
        "collector": "sensor:a",
        "collector_version": "1",
        "collected_at": NOW.isoformat(),
        "source_uri": "memory://sensor",
    }
    assert Provenance.of(stamped) == provenance_for(collector, NOW)
    assert Provenance.of(record) is None
    assert event_key(stamped) == event_key(record)
