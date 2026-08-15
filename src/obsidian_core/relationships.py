from dataclasses import dataclass

from .links import WikiLink, parse_wiki_links


@dataclass(frozen=True)
class Relationship:
    """A relationship between a source note and a linked target."""

    source: str
    target: str
    display: str

    @property
    def provenance(self) -> WikiLink:
        """Return the wiki link that produced this relationship."""
        return WikiLink(
            target=self.target,
            display=self.display,
        )


def extract_relationships(
    source: str,
    content: str,
) -> list[Relationship]:
    """Extract note relationships from wiki links in Markdown content."""
    return [
        Relationship(
            source=source,
            target=link.target,
            display=link.display,
        )
        for link in parse_wiki_links(content)
    ]
