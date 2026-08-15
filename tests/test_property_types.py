from datetime import date, datetime

from obsidian_core.frontmatter import Frontmatter


def test_text_property():
    frontmatter = Frontmatter(
        {
            "title": "Test Note",
        }
    )

    assert frontmatter.get("title") == "Test Note"


def test_number_properties():
    frontmatter = Frontmatter(
        {
            "integer": 42,
            "decimal": 3.14,
        }
    )

    assert frontmatter.get("integer") == 42
    assert frontmatter.get("decimal") == 3.14


def test_checkbox_properties():
    frontmatter = Frontmatter(
        {
            "enabled": True,
            "disabled": False,
        }
    )

    assert frontmatter.get("enabled") is True
    assert frontmatter.get("disabled") is False


def test_list_property():
    frontmatter = Frontmatter(
        {
            "items": ["one", "two", "three"],
        }
    )

    assert frontmatter.get("items") == ["one", "two", "three"]


def test_tags_property():
    frontmatter = Frontmatter(
        {
            "tags": ["journal", "project", "server"],
        }
    )

    assert frontmatter.get("tags") == [
        "journal",
        "project",
        "server",
    ]


def test_date_property():
    frontmatter = Frontmatter(
        {
            "date": date(2026, 8, 7),
        }
    )

    result = frontmatter.to_yaml()

    parsed = Frontmatter.parse(result)

    assert parsed.get("date") == date(2026, 8, 7)


def test_datetime_property():
    value = datetime(2026, 8, 7, 15, 30, 0)  # noqa: DTZ001

    frontmatter = Frontmatter(
        {
            "timestamp": value,
        }
    )

    result = frontmatter.to_yaml()

    parsed = Frontmatter.parse(result)

    assert parsed.get("timestamp") == value


def test_link_property():
    frontmatter = Frontmatter(
        {
            "related": "[[Linux Homeserver]]",
        }
    )

    result = frontmatter.to_yaml()

    parsed = Frontmatter.parse(result)

    assert parsed.get("related") == "[[Linux Homeserver]]"


def test_link_list_property():
    frontmatter = Frontmatter(
        {
            "related": [
                "[[Linux Homeserver]]",
                "[[ESP32]]",
            ],
        }
    )

    result = frontmatter.to_yaml()

    parsed = Frontmatter.parse(result)

    assert parsed.get("related") == [
        "[[Linux Homeserver]]",
        "[[ESP32]]",
    ]
