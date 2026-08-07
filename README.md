# obsidian-core

A lightweight Python library for interacting with Obsidian vaults programmatically.

`obsidian-core` provides a server-native abstraction over an Obsidian vault without requiring the Obsidian desktop application to run.

The project is intended for automation running on a Linux homeserver where the Obsidian vault is stored directly on the filesystem and accessed by Obsidian Desktop from another machine.

## Goals

- Provide a lightweight Obsidian-aware Python API.
- Read and write Markdown notes safely.
- Understand YAML frontmatter and Obsidian properties.
- Create and manage `[[wiki links]]`.
- Store raw data as immutable, append-only records.
- Generate timestamped and versioned content.
- Preserve human-written knowledge.
- Generate and maintain relationships between entities.
- Provide a foundation for future search and RAG systems.
- Remain independent of the Obsidian desktop application.

## Architecture

The library sits between automation services and the Obsidian vault.

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

The vault remains the storage and presentation layer while automation services interact with it through `obsidian-core`.

## Design principles

### Human knowledge is protected

Human-written knowledge must remain intact.

Automation may derive information from human-written content and append generated material, but it must not silently rewrite or destroy the original content.

### Raw data is authoritative

When hardware or external services provide real observations, the original records are authoritative.

Raw records are:

- immutable
- append-only
- timestamped
- attributed to their source
- retained in their original form

Algorithms may interpret raw data but must not replace it.

### Generated information is derived

Generated content can evolve.

Every generated operation should retain:

- timestamp
- generator
- version
- generated output
- relevant source references

Previous generated output should remain recoverable.

### Obsidian is the storage layer

The project does not require Obsidian to be running on the homeserver.

The library operates directly against the vault's underlying files.

Obsidian Desktop can independently open and display the same vault.

## Planned capabilities

### Vault

- Vault discovery
- Note creation
- Note retrieval
- Note deletion with safeguards
- File existence checks
- Vault-relative paths

### Notes

- Markdown reading and writing
- Safe appending
- Generated sections
- Protected human content
- Atomic file operations

### Frontmatter

- YAML parsing
- Property access
- Property modification
- Property validation

### Links

- `[[wiki links]]`
- Link creation
- Link detection
- Entity references
- Relationship generation

### Raw data

- Immutable records
- Append-only storage
- Source metadata
- Timestamps
- Original payload preservation

### Generated content

- Timestamped sections
- Generator identification
- Versioning
- Append-only generated history

### Relationships

- Entity identification
- Entity relationships
- Conceptual links
- Relationship provenance

### Future

- Full-text search
- Indexing
- Entity graph
- Semantic search
- RAG integration

## Example

A future integration may look like:

    from obsidian_core import Vault

    vault = Vault("/home/user/Documents/Obsidian/Knowledge Base")

    note = vault.note("40 - Knowledge/Devices/Device A.md")

    note.append_generated(
        generator="esp32-analysis",
        content="Device A was observed by [[ESP32-01]]."
    )

The integration does not need to know how the Markdown file is structured internally.

## Project structure

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
    │       ├── versioning.py
    │       └── exceptions.py
    ├── tests/
    ├── docs/
    ├── pyproject.toml
    ├── README.md
    ├── LICENSE
    └── .gitignore

## Development

Create a virtual environment:

    python3 -m venv .venv

Activate it:

    source .venv/bin/activate

Install the project with development dependencies:

    pip install -e ".[dev]"

Run tests:

    pytest

Run linting:

    ruff check .

## Status

Early development.

The API is intentionally expected to change while the underlying architecture is established.