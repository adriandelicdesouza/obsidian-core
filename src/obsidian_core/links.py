from dataclasses import dataclass
import re


@dataclass(frozen=True)
class WikiLink:
    """A parsed Obsidian wiki link."""

    target: str
    display: str


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