import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WikiLink:
    """A parsed Obsidian wiki link."""

    target: str
    display: str

    def __str__(self) -> str:
        """Render the wiki link as Obsidian Markdown."""
        if self.display == self.target:
            return f"[[{self.target}]]"

        return f"[[{self.target}|{self.display}]]"


WIKI_LINK_PATTERN = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")


def parse_wiki_links(content: str) -> list[WikiLink]:
    """Return all Obsidian wiki links found in Markdown content."""
    links = []

    for match in WIKI_LINK_PATTERN.finditer(content):
        target = match.group(1).strip()
        display = match.group(2)

        if display is None:
            display = target
        else:
            display = display.strip()

        links.append(
            WikiLink(
                target=target,
                display=display,
            )
        )

    return links


def create_wiki_link(
    target: str,
    alias: str | None = None,
) -> str:
    """Create an Obsidian wiki link."""
    target = target.strip()

    if not target:
        raise ValueError("Wiki link target cannot be empty")

    if "[[" in target or "]]" in target:
        raise ValueError("Wiki link target contains invalid syntax")

    if alias is None:
        return f"[[{target}]]"

    alias = alias.strip()

    if not alias:
        raise ValueError("Wiki link alias cannot be empty")

    if "[[" in alias or "]]" in alias:
        raise ValueError("Wiki link alias contains invalid syntax")

    return f"[[{target}|{alias}]]"
