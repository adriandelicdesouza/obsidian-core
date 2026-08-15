import obsidian_core

EXPECTED_PUBLIC_API = {
    "Note",
    "Vault",
    "RawRecord",
    "RawStore",
    "RawParser",
    "GeneratedRecord",
    "GeneratedStore",
    "GeneratedParser",
    "WikiLink",
    "create_wiki_link",
    "parse_wiki_links",
    "Relationship",
    "extract_relationships",
    "generation_chain",
    "is_successor",
}


def test_all_contains_expected_public_api():
    assert set(obsidian_core.__all__) == EXPECTED_PUBLIC_API


def test_public_api_objects_are_importable():
    for name in EXPECTED_PUBLIC_API:
        assert hasattr(obsidian_core, name)


def test_all_has_no_duplicates():
    assert len(obsidian_core.__all__) == len(set(obsidian_core.__all__))
