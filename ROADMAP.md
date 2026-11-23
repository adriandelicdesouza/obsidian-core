# Roadmap

Current version: 0.4.0.

## Done

- Frontmatter and Obsidian property parsing and writing.
- `[[wiki link]]` parsing and creation.
- Raw (immutable, append-only) and generated record stores.
- Versioning and relationships between entities.
- Test suite and CI (`.github/workflows/ci.yml`).
- v0.4 ingestion protocol: raw-event schema and versioning, event identity,
  idempotent ingestion, collectors and provenance, checkpoints, reconciliation,
  Git adapter and Git activity notes (see `docs/ARCHITECTURE.md`).
- Release notes in `CHANGELOG.md`, from 0.3.0.

## Next

1. Search foundation. The README lists search as a future goal, and there is no search module in `src/obsidian_core` yet.
2. Parser consistency. `RawParser` moved to JSON value extraction in a recent change. Check that `GeneratedParser` follows the same convention.
