from .generated import GeneratedRecord


def is_successor(
    previous: GeneratedRecord,
    current: GeneratedRecord,
) -> bool:
    """Return whether current is the successor of previous."""

    return current.previous_generated_id == previous.generated_id


def generation_chain(
    records: list[GeneratedRecord],
) -> list[GeneratedRecord]:
    """Return generated records ordered from oldest to newest."""

    if not records:
        return []

    current = next(
        (record for record in records if record.previous_generated_id is None),
        None,
    )

    if current is None:
        raise ValueError("Generation chain must have a starting record")

    chain = [current]

    while True:
        successors = [
            record for record in records if record.previous_generated_id == current.generated_id
        ]

        if not successors:
            break

        if len(successors) > 1:
            raise ValueError("Generation chain has multiple successors")

        current = successors[0]
        chain.append(current)

    if len(chain) != len(records):
        raise ValueError("Records do not form a single generation chain")

    return chain
