# Roadmap

Current version: 0.3.0.

## Done

- Frontmatter and Obsidian property parsing and writing.
- `[[wiki link]]` parsing and creation.
- Raw (immutable, append-only) and generated record stores.
- Versioning and relationships between entities.
- Test suite and CI (`.github/workflows/ci.yml`).

## Next

1. Search foundation. The README lists search as a future goal, and there is no search module in `src/obsidian_core` yet.
2. Parser consistency. `RawParser` moved to JSON value extraction in a recent change. Check that `GeneratedParser` follows the same convention.
3. Release notes for each version bump, starting with 0.3.0.
