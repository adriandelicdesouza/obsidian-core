import pytest

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
    frontmatter = Frontmatter(
        {
            "title": "Test",
            "draft": True,
        }
    )

    frontmatter.delete("draft")

    assert not frontmatter.has("draft")
    assert frontmatter.get("title") == "Test"


def test_serialize_properties():
    frontmatter = Frontmatter(
        {
            "title": "Test",
            "count": 42,
            "tags": ["one", "two"],
        }
    )

    result = frontmatter.to_yaml()

    assert result.startswith("---\n")
    assert "title: Test" in result
    assert "count: 42" in result
    assert "- one" in result
    assert "- two" in result
    assert result.endswith("---\n")


def test_invalid_yaml():
    content = """---
title: [invalid
---
"""

    with pytest.raises(ValueError, match="Invalid frontmatter YAML"):
        Frontmatter.parse(content)


def test_missing_closing_delimiter():
    content = """---
title: Test
"""

    with pytest.raises(
        ValueError,
        match="Frontmatter closing delimiter not found",
    ):
        Frontmatter.parse(content)


def test_non_dictionary_yaml():
    content = """---
- one
- two
---
"""

    with pytest.raises(
        ValueError,
        match="must contain a mapping",
    ):
        Frontmatter.parse(content)


def test_duplicate_properties():
    content = """---
title: First
title: Second
---
"""

    with pytest.raises(
        ValueError,
        match="Duplicate frontmatter property",
    ):
        Frontmatter.parse(content)
