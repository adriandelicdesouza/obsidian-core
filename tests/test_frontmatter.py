from obsidian_core.frontmatter import Frontmatter


def test_parse_properties():
    content = """---
title: Test Note
count: 42
favorite: true
tags:
  - test
  - example
---

# Test Note

Body content.
"""

    frontmatter = Frontmatter.parse(content)

    assert frontmatter.get("title") == "Test Note"
    assert frontmatter.get("count") == 42
    assert frontmatter.get("favorite") is True
    assert frontmatter.get("tags") == ["test", "example"]


def test_empty_frontmatter():
    content = """---
---

# Test
"""

    frontmatter = Frontmatter.parse(content)

    assert frontmatter.data == {}


def test_no_frontmatter():
    content = "# Test\n\nNo properties."

    frontmatter = Frontmatter.parse(content)

    assert frontmatter.data == {}


def test_modify_property():
    frontmatter = Frontmatter({"title": "Old"})

    frontmatter.set("title", "New")
    frontmatter.set("count", 10)

    assert frontmatter.get("title") == "New"
    assert frontmatter.get("count") == 10


def test_delete_property():
    frontmatter = Frontmatter({
        "title": "Test",
        "draft": True,
    })

    frontmatter.delete("draft")

    assert not frontmatter.has("draft")
    assert frontmatter.get("title") == "Test"


def test_serialize_properties():
    frontmatter = Frontmatter({
        "title": "Test",
        "count": 42,
        "tags": ["one", "two"],
    })

    result = frontmatter.to_yaml()

    assert result.startswith("---\n")
    assert "title: Test" in result
    assert "count: 42" in result
    assert "- one" in result
    assert "- two" in result
    assert result.endswith("---\n")
