from obsidian_core import Vault


def test_read_properties(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("Test.md")

    note.write(
        """---
title: Original
tags:
- test
---

# Human Knowledge

This content must remain untouched.
"""
    )

    assert note.properties.get("title") == "Original"
    assert note.properties.get("tags") == ["test"]


def test_set_property_preserves_body(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("Test.md")

    original_body = """# Human Knowledge

This content must remain untouched.
"""

    note.write(
        """---
title: Original
---

"""
        + original_body
    )

    note.set_property("title", "Updated")

    content = note.read()

    assert "title: Updated" in content
    assert original_body in content


def test_add_property(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("Test.md")

    note.write("# Human Knowledge\n")

    note.set_property("type", "device")

    content = note.read()

    assert content.startswith("---\n")
    assert "type: device" in content
    assert "# Human Knowledge\n" in content


def test_delete_property_preserves_body(tmp_path):
    vault = Vault(tmp_path)

    note = vault.note("Test.md")

    note.write(
        """---
title: Test
draft: true
---

# Human Knowledge

Do not modify this.
"""
    )

    note.delete_property("draft")

    content = note.read()

    assert "draft:" not in content
    assert "title: Test" in content
    assert "# Human Knowledge\n" in content
    assert "Do not modify this." in content

def test_property_modification_preserves_frontmatter_semantics(tmp_path):
    vault = Vault(tmp_path)
    note = vault.note("Test.md")

    note.write(
        """---
title: "Original"
tags:
  - test
  - example
---

# Human Knowledge

This content must remain untouched.
"""
    )

    note.set_property("title", "Updated")

    properties = note.properties

    assert properties.get("title") == "Updated"
    assert properties.get("tags") == ["test", "example"]

    assert "# Human Knowledge" in note.read()
    assert "This content must remain untouched." in note.read()

def test_delete_property_preserves_frontmatter_semantics(tmp_path):
    vault = Vault(tmp_path)
    note = vault.note("Test.md")

    note.write(
        """---
title: Test
tags:
  - one
  - two
draft: true
---

# Human Knowledge
"""
    )

    note.delete_property("draft")

    properties = note.properties

    assert properties.get("title") == "Test"
    assert properties.get("tags") == ["one", "two"]
    assert not properties.has("draft")

    assert "# Human Knowledge" in note.read()