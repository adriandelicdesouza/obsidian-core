# Changelog

## 0.4.0

Ingestion protocol for collectors feeding the raw archive. Nothing existing
changes behaviour: `RawRecord`, `RawRecord.record_id`, `RawStore` and the raw
log format are as in 0.3.0, and 0.3.0 archives are read and deduplicated as is.

- Raw-event envelope, schema version 1 and event identity (`obsidian_core.events`, #63).
- Idempotent ingestion boundary, `Ingestor` (#59).
- `Collector` protocol and `Provenance` (#62).
- Checkpoints and `run_collector` (#60).
- `reconcile()` against the authoritative archive (#61).
- Git adapter `obsidian_core.git.GitCollector` (#65).
- Daily Git activity notes with wikilinks, `GitActivityNotes` (#66).
- Contract tests for the whole path (#67) and `docs/ARCHITECTURE.md` (#68).

## 0.3.0

- Frontmatter and Obsidian property parsing and writing.
- `[[wiki link]]` parsing and creation.
- Raw (immutable, append-only) and generated record stores.
- Versioning and relationships between entities.
- Test suite and CI.
