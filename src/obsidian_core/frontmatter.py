from dataclasses import dataclass
from typing import Any

import yaml


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(loader, node, deep=False):
    mapping = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in mapping:
            raise ValueError(f"Duplicate frontmatter property: {key}")

        mapping[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


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
            raise ValueError("Frontmatter closing delimiter not found")

        yaml_content = "".join(lines[1:closing_index])

        if not yaml_content.strip():
            return cls({})

        try:
            data = yaml.load(
                yaml_content,
                Loader=_UniqueKeyLoader,
            )
        except yaml.YAMLError as exc:
            raise ValueError("Invalid frontmatter YAML") from exc

        if data is None:
            return cls({})

        if not isinstance(data, dict):
            raise TypeError("Obsidian frontmatter must contain a mapping")

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
            indent=2,
        )

        return f"---\n{body}---\n"
