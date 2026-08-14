from obsidian_core.links import WikiLink, parse_wiki_links


def test_parse_simple_wiki_link():
    assert parse_wiki_links("[[Linux Homeserver]]") == [
        WikiLink(
            target="Linux Homeserver",
            display="Linux Homeserver",
        )
    ]


def test_parse_wiki_link():
    assert parse_wiki_links("[[ESP32]]") == [
        WikiLink(
            target="ESP32",
            display="ESP32",
        )
    ]


def test_parse_nested_wiki_link():
    assert parse_wiki_links("[[Devices/ESP32]]") == [
        WikiLink(
            target="Devices/ESP32",
            display="Devices/ESP32",
        )
    ]


def test_parse_wiki_link_with_alias():
    assert parse_wiki_links("[[ESP32|Living Room Sensor]]") == [
        WikiLink(
            target="ESP32",
            display="Living Room Sensor",
        )
    ]


def test_parse_multiple_wiki_links():
    content = """
# Devices

[[ESP32]]
[[Linux Homeserver]]
[[Devices/ESP32]]
"""

    assert parse_wiki_links(content) == [
        WikiLink(target="ESP32", display="ESP32"),
        WikiLink(
            target="Linux Homeserver",
            display="Linux Homeserver",
        ),
        WikiLink(
            target="Devices/ESP32",
            display="Devices/ESP32",
        ),
    ]


def test_parse_content_without_wiki_links():
    assert parse_wiki_links("# No links here") == []