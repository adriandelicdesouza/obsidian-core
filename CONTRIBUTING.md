# Contributing to Obsidian Core

Thank you for contributing to Obsidian Core.

Obsidian Core focuses on predictable storage APIs, data integrity, testability, and clean Python interfaces. Contributions should preserve these principles.

## Development Setup

Clone the repository:

```
git clone https://github.com/adriandelicdesouza/obsidian-core.git
cd obsidian-core
```

Create and activate a virtual environment:

```
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and development dependencies:

```
pip install -e ".[dev]"
```

Run the test suite:

```
pytest -q
```

## Project Structure

The main source code is located under:

```
src/obsidian_core/
```

Tests are located under:

```
tests/
```

The project currently includes components for:

* Raw record storage
* Generated record storage
* Record parsing and serialization
* Vault and note management
* Data integrity validation

## Issues

Before starting substantial work, check the existing GitHub issues:

[https://github.com/adriandelicdesouza/obsidian-core/issues](https://github.com/adriandelicdesouza/obsidian-core/issues)

For larger changes, open or comment on an issue before implementing the change. This helps avoid duplicated work and keeps the project architecture consistent.

## Branching

Create a dedicated branch for each change.

Use descriptive branch names such as:

```
feature/add-batch-reading
fix/raw-store-validation
test/generated-parser-validation
refactor/storage-api
```

Avoid committing directly to `main`.

## Making Changes

Keep changes focused and minimal.

When modifying a public API:

1. Update the implementation.
2. Update existing tests.
3. Add tests for new behavior.
4. Run the complete test suite.
5. Update documentation when appropriate.

For storage-related changes, pay particular attention to:

* Path consistency
* `date` / `datetime` handling
* Timezone awareness
* Append-only behavior
* Round-trip parsing
* Data integrity validation
* Backwards compatibility

## Tests

Tests are written using `pytest`.

Run the complete test suite:

```
pytest -q
```

Run a specific test file:

```
pytest -q tests/test_raw_store.py
```

Run a specific test:

```
pytest -q tests/test_raw_store.py::test_append_creates_daily_file
```

New functionality should include corresponding tests.

For bug fixes, preferably add a regression test demonstrating the original failure.

## Code Style

Follow standard Python conventions and keep code readable.

Prefer:

* Clear and descriptive names
* Small, focused methods
* Type annotations
* Explicit behavior over implicit behavior
* Standard-library solutions where practical

Avoid:

* Unnecessary abstractions
* Unrelated refactoring
* Breaking public APIs without discussion
* Silent data corruption or loss

## Commits

Write concise commit messages describing the change.

Examples:

```
Add GeneratedStore append_many support
Fix RawStore date-based API
Add GeneratedParser integrity validation tests
Refactor storage path handling
```

Keep commits focused on a single logical change.

## Pull Requests

Push your branch:

```
git push -u origin <branch-name>
```

Then open a pull request against `main`.

A good pull request should include:

* A clear title
* A concise description of the change
* The related issue
* Tests covering the change
* Any relevant design considerations

For example:

**Title**

```
Add GeneratedStore append_many support
```

**Body**

```
Closes #5

Adds batch append support to GeneratedStore and tests
that records targeting the same and different days are
written to the correct files.
```

## Pull Request Checklist

Before requesting review:

* [ ] The change addresses the intended issue.
* [ ] Tests have been added or updated.
* [ ] `pytest -q` passes.
* [ ] No unrelated files or changes are included.
* [ ] Public API changes are documented where appropriate.
* [ ] The branch is up to date with `main` when necessary.
* [ ] The pull request description explains the change.

## Data Integrity

Obsidian Core treats stored records as data that should be reliably recoverable.

Changes involving serialization or parsing should preserve round-trip behavior:

```
Record
  ↓
Storage
  ↓
Markdown
  ↓
Parser
  ↓
Record
```

Where integrity identifiers are used, parsers should detect modifications rather than silently accepting corrupted or altered records.

## Reporting Bugs

When reporting a bug, include:

* What you expected to happen
* What actually happened
* Steps to reproduce the issue
* Relevant error messages
* Python version
* Operating system
* A minimal example when possible

Avoid including sensitive data in issue reports.

## Feature Requests

Feature requests are welcome.

Explain:

* The problem the feature solves
* The proposed behavior
* Why the existing API is insufficient
* Any compatibility considerations

Features that substantially change the public API should be discussed before implementation.

## License

By contributing to this repository, you agree that your contributions may be distributed under the project's existing license.
