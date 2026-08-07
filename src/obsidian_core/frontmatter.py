from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class Frontmatter:
    """Parsed YAML frontmatter from an Obsidian note."""

    data: dict[str, Any]

    @classmethod
    def parse(cls, content: str) -> "Frontmatter":
        """Parse frontmatter from complete Markdown content."""
        if not content.startswith("---"):
            return cls({})

        lines = content.splitlines(keepends=True)

        if not lines or lines[0].strip() != "---":
            return cls({})

        closing_index = None

        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break

        if closing_index is None:
            return cls({})

        yaml_content = "".join(lines[1:closing_index])
        data = yaml.safe_load(yaml_content)

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise ValueError("Obsidian frontmatter must contain a mapping")

        return cls(data)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a property value."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a property value."""
        self.data[key] = value

    def delete(self, key: str) -> None:
        """Delete a property if it exists."""
        self.data.pop(key, None)

    def has(self, key: str) -> bool:
        """Return whether a property exists."""
        return key in self.data

    def to_yaml(self) -> str:
        """Serialize properties into an Obsidian frontmatter block."""
        body = yaml.safe_dump(
            self.data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

        return f"---\n{body}---\n"
