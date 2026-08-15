from datetime import UTC, datetime

import pytest

from obsidian_core import GeneratedRecord, generation_chain, is_successor


def make_record(
    timestamp: datetime,
    content: str,
    previous_generated_id: str | None = None,
) -> GeneratedRecord:
    return GeneratedRecord(
        timestamp=timestamp,
        generator="test-generator",
        generator_version="1",
        content=content,
        previous_generated_id=previous_generated_id,
    )


def test_generation_chain_single_record():
    record = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )

    assert generation_chain([record]) == [record]


def test_generation_chain_multiple_records():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )
    third = make_record(
        datetime(2026, 8, 1, 14, 0, tzinfo=UTC),
        "third",
        previous_generated_id=second.generated_id,
    )

    assert generation_chain([third, first, second]) == [first, second, third]


def test_generation_chain_orders_records_oldest_to_newest():
    first = make_record(
        datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 11, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )
    third = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "third",
        previous_generated_id=second.generated_id,
    )

    result = generation_chain([third, second, first])

    assert result[0] is first
    assert result[1] is second
    assert result[2] is third


def test_generation_chain_requires_starting_record():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
        previous_generated_id="missing-id",
    )

    with pytest.raises(
        ValueError,
        match="Generation chain must have a starting record",
    ):
        generation_chain([first])


def test_generation_chain_rejects_multiple_starting_records():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
    )

    with pytest.raises(ValueError, match="single generation chain"):
        generation_chain([first, second])


def test_generation_chain_rejects_multiple_successors():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )
    third = make_record(
        datetime(2026, 8, 1, 14, 0, tzinfo=UTC),
        "third",
        previous_generated_id=first.generated_id,
    )

    with pytest.raises(
        ValueError,
        match="Generation chain has multiple successors",
    ):
        generation_chain([first, second, third])


def test_generation_chain_rejects_disconnected_records():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )
    disconnected = make_record(
        datetime(2026, 8, 1, 14, 0, tzinfo=UTC),
        "disconnected",
        previous_generated_id="unknown-id",
    )

    with pytest.raises(
        ValueError,
        match="single generation chain",
    ):
        generation_chain([first, second, disconnected])


def test_generation_chain_rejects_incomplete_chain():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id="missing-id",
    )

    with pytest.raises(
        ValueError,
        match="single generation chain",
    ):
        generation_chain([first, second])


def test_generation_chain_rejects_missing_successor():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id="unknown-id",
    )

    with pytest.raises(
        ValueError,
        match="single generation chain",
    ):
        generation_chain([first, second])


def test_generation_chain_empty_records():
    assert generation_chain([]) == []


def test_is_successor_returns_true_for_consecutive_records():
    previous = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "previous",
    )
    current = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "current",
        previous_generated_id=previous.generated_id,
    )

    assert is_successor(previous, current) is True


def test_is_successor_returns_false_for_unrelated_records():
    previous = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "previous",
    )
    current = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "current",
        previous_generated_id="unrelated-id",
    )

    assert is_successor(previous, current) is False


def test_is_successor_returns_false_when_current_has_no_previous():
    previous = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "previous",
    )
    current = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "current",
    )

    assert is_successor(previous, current) is False


def test_previous_generated_id_relationship():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )

    assert second.previous_generated_id == first.generated_id
    assert is_successor(first, second)
    assert not is_successor(second, first)


def test_generation_chain_preserves_record_objects():
    first = make_record(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        "first",
    )
    second = make_record(
        datetime(2026, 8, 1, 13, 0, tzinfo=UTC),
        "second",
        previous_generated_id=first.generated_id,
    )

    result = generation_chain([second, first])

    assert result == [first, second]
    assert result[0] is first
    assert result[1] is second