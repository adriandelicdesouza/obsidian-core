# obsidian-core

A lightweight Python library for interacting with Obsidian vaults programmatically.

`obsidian-core` provides a server-native abstraction over an Obsidian vault without requiring the Obsidian desktop application to run.

The project is designed for automation running on a Linux homeserver where the Obsidian vault is stored directly on the filesystem and accessed by Obsidian Desktop from another machine.

## Goals

* Provide a lightweight Obsidian-aware Python API.
* Read and write Markdown notes safely.
* Parse and modify YAML frontmatter and Obsidian properties.
* Create and parse `[[wiki links]]`.
* Store raw data as immutable, append-only records.
* Generate timestamped and versioned content.
* Preserve human-written knowledge.
* Generate and maintain relationships between entities.
* Provide a foundation for future search and RAG systems.
* Remain independent of the Obsidian desktop application.

## Architecture

The library sits between automation services and the Obsidian vault.

```
Git ────────┐
ESP32 ──────┤
Server ─────┤
Future ─────┘
      │
      ▼
obsidian-core
      │
      ▼
Obsidian vault
      │
      ▼
Obsidian Desktop
```

The vault remains the storage and presentation layer while automation services interact with it through `obsidian-core`.

## Data pipeline

The project separates authoritative raw observations from derived information.

    RawRecord
        │
        ▼
    RawStore
        │
        ▼
    RawParser
        │
        ▼
    Analysis / Generator
        │
        ▼
    GeneratedRecord
        │
        ▼
    GeneratedStore
        │
        ▼
    Obsidian

### Raw data

`RawRecord` represents an original observation produced by a machine, service, or other external source.

`RawStore` persists raw records as append-only daily logs in the vault. Raw records are the authoritative representation of the underlying observation. The stored record includes its source, timestamp, event type, identifiers, metadata, payload, and deterministic record ID.

`RawParser` reads stored raw logs back into `RawRecord` objects. During parsing, it reconstructs each record and verifies its stored record ID against the calculated value. A mismatch causes parsing to fail, providing an integrity check for stored raw data.

Raw data should not be silently rewritten or replaced by analysis results.

### Analysis and generation

Analysis and generator components operate on raw or parsed data to produce derived information.

The analysis layer is intentionally separate from raw storage. It may interpret, summarize, classify, or otherwise transform observations, but it does not become authoritative merely because it produces a conclusion.

### Generated data

`GeneratedRecord` represents derived information produced by an analysis or generator.

Generated records retain provenance through:

- timestamp
- generator identity
- generator version
- source record IDs
- metadata
- generated content
- optional reference to a previous generated record

This allows generated output to be associated with the raw observations from which it was derived and allows generated history to evolve without losing previous results.

`GeneratedStore` persists generated records as append-only daily logs. Generated records are derived data and do not replace the authoritative raw records.

### Obsidian

Obsidian acts as the filesystem-backed storage and presentation layer.

Raw and generated records are stored as Markdown files within the vault. Human-readable notes can coexist with generated information, while the raw and generated stores maintain their respective data boundaries.

The intended flow is therefore:

1. An external source produces an observation.
2. The observation is represented as a `RawRecord`.
3. `RawStore` persists the original observation.
4. `RawParser` reconstructs and validates stored raw records.
5. An analysis or generator derives new information.
6. The result is represented as a `GeneratedRecord`.
7. `GeneratedStore` persists the derived result and its provenance.
8. Obsidian provides the human-readable vault representation.

The key distinction is **authority versus derivation**: raw observations are authoritative, while generated information is derived and must retain enough provenance to trace it back to its sources.

## Design principles

### Human knowledge is protected

Human-written knowledge must remain intact.

Automation may derive information from human-written content and append generated material, but it must not silently rewrite or destroy the original content.

### Raw data is authoritative

When hardware or external services provide real observations, the original records are authoritative.

Raw records are:

* immutable
* append-only
* timestamped
* attributed to their source
* retained in their original form

Algorithms may interpret raw data but must not replace it.

### Generated information is derived

Generated content can evolve.

Generated records retain:

* timestamp
* generator
* generator version
* generated output
* source references
* optional metadata

Generated records can also reference a previous generated record, allowing generated history to be tracked over time.

### Obsidian is the storage layer

The project does not require Obsidian to be running on the homeserver.

The library operates directly against the vault's underlying files.

Obsidian Desktop can independently open and display the same vault.

## Current capabilities

### Vault

* Vault path validation
* Note retrieval
* File existence checks
* Vault-relative path resolution
* Protection against paths escaping the vault

### Notes

* Markdown reading and writing
* Safe content appending
* Generated content appending
* Note deletion with safeguards
* Vault-relative note paths

### Frontmatter

* YAML frontmatter parsing
* Property access
* Property modification
* Property deletion
* Property serialization

### Links

* `[[wiki link]]` parsing
* Wiki link creation
* Link detection
* Relationship extraction

### Raw data

* Immutable raw records
* Append-only storage
* Source metadata
* Timestamps
* Original payload preservation

### Generated content

* Generated records
* Timestamped generated sections
* Generator identification
* Generator versioning
* Source references
* Generated record identifiers
* Append-only generated history

### Relationships

* Entity identification
* Entity relationships
* Relationship extraction
* Relationship provenance

### Versioning

* Generated record identifiers
* Successor relationships
* Generated record chains

## Example

A generated record can be appended to an existing note while preserving its existing contents:

```
from datetime import UTC, datetime

from obsidian_core import GeneratedRecord, Vault

vault = Vault("/home/user/Documents/Obsidian/Knowledge Base")

note = vault.note("40 - Knowledge/Devices/Device A.md")

record = GeneratedRecord(
    timestamp=datetime.now(UTC),
    generator="esp32-analysis",
    generator_version="1.0",
    content="Device A was observed by [[ESP32-01]].",
)

note.append_generated(record)
```

The integration does not need to know how the Markdown file is structured internally.

## Roadmap

The following capabilities are planned and are not currently part of the `0.1.0` API:

* Full-text search
* Indexing
* Entity graph
* Semantic search
* RAG integration

## Project structure

```
obsidian-core/
├── src/
│   └── obsidian_core/
│       ├── __init__.py
│       ├── vault.py
│       ├── note.py
│       ├── frontmatter.py
│       ├── links.py
│       ├── raw.py
│       ├── generated.py
│       ├── generated_parser.py
│       ├── generated_store.py
│       ├── raw_parser.py
│       ├── raw_store.py
│       ├── relationships.py
│       ├── versioning.py
│       └── exceptions.py
├── tests/
├── docs/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

## Development

Create a virtual environment:

```
python3 -m venv .venv
```

Activate it:

```
source .venv/bin/activate
```

Install the project with development dependencies:

```
pip install -e ".[dev]"
```

Run tests:

```
pytest
```

Run linting:

```
ruff check .
```

## Status

**Version 0.1.0 — Early development**

The current release provides the core vault, note, frontmatter, link, raw data, generated content, relationship, and versioning APIs described above.

The API is intentionally expected to change while the underlying architecture is established. Roadmap items are not considered part of the current stable API.
