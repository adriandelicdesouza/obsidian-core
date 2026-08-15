from obsidian_core.links import WikiLink
from obsidian_core.relationships import (
    Relationship,
    extract_relationships,
)


def test_extract_simple_relationship():
    relationships = extract_relationships(
        "Linux Homeserver",
        "[[ESP32]]",
    )

    assert relationships == [
        Relationship(
            source="Linux Homeserver",
            target="ESP32",
            display="ESP32",
        )
    ]


def test_extract_nested_relationship():
    relationships = extract_relationships(
        "Devices",
        "[[Devices/ESP32]]",
    )

    assert relationships == [
        Relationship(
            source="Devices",
            target="Devices/ESP32",
            display="Devices/ESP32",
        )
    ]


def test_extract_relationship_with_alias():
    relationships = extract_relationships(
        "Devices",
        "[[ESP32|Living Room Sensor]]",
    )

    assert relationships == [
        Relationship(
            source="Devices",
            target="ESP32",
            display="Living Room Sensor",
        )
    ]


def test_extract_multiple_relationships():
    relationships = extract_relationships(
        "Home",
        """
[[Linux Homeserver]]
[[ESP32]]
[[Devices/ESP32]]
""",
    )

    assert relationships == [
        Relationship(
            source="Home",
            target="Linux Homeserver",
            display="Linux Homeserver",
        ),
        Relationship(
            source="Home",
            target="ESP32",
            display="ESP32",
        ),
        Relationship(
            source="Home",
            target="Devices/ESP32",
            display="Devices/ESP32",
        ),
    ]


def test_relationship_preserves_provenance():
    relationship = extract_relationships(
        "Home",
        "[[ESP32|Living Room Sensor]]",
    )[0]

    assert relationship.provenance == WikiLink(
        target="ESP32",
        display="Living Room Sensor",
    )


def test_extract_relationships_without_links():
    assert extract_relationships(
        "Home",
        "# Home\n\nNo links here.",
    ) == []