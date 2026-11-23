# Architecture (v0.4)

This document describes the ingestion architecture added in v0.4 and the public
API boundaries between its parts. It describes the code as implemented; each
section names the module that owns the behaviour.

```
External source (git, ESP32, server, ...)
      │
      ▼
Collector  ─────────────── source adapter: knows the source, nothing else
      │  Observation(record, cursor)
      ▼
stamp(record, provenance) ─ adds schema_version + provenance metadata
      │
      ▼
Ingestor  ──────────────── idempotent boundary: NEW / KNOWN / CONFLICT
      │  NEW only
      ▼
RawStore  ──────────────── append-only daily logs (unchanged since v0.3)
      │
      ▼
authoritative raw archive (Raw/<source>/YYYY/MM/DD.md in the vault)
      │
      ├──▶ reconcile()        compares source and archive; repairs by appending
      └──▶ presentation       e.g. GitActivityNotes: derived notes and wikilinks

CheckpointStore ─────────── per-collector cursor, outside the archive
```

Two distinctions run through the whole design:

    append-only  ≠  idempotent
    checkpoint   ≠  authoritative history

`RawStore` is append-only: appending the same record twice stores it twice.
Idempotency is provided one layer up, by `Ingestor`. Checkpoints only make
collection faster. The raw archive is the only record of what was observed.

## Raw-event envelope and schema versioning (`obsidian_core.events`)

A raw event is a `RawRecord`. `RawRecord` and its storage format are unchanged
from v0.3; v0.4 adds rules on top of them.

| Field | Owner | Meaning | In event identity |
|---|---|---|---|
| `timestamp` | generic | when the observation happened (timezone-aware) | yes (as a UTC instant) |
| `source` | generic | kind of source; selects `Raw/<source>/` | yes |
| `event_type` | generic | what was observed | yes |
| `identifiers` | source | source-native names of the event | yes |
| `payload` | source | the observation | only when `identifiers` is empty |
| `metadata` | generic + source | collection context | no |

Reserved metadata keys:

* `schema_version`: envelope version, currently `SCHEMA_VERSION = 1`. A record
  without it was written before v0.4 and is read as version 0.
* `provenance`: `{collector, collector_version, collected_at, source_uri?}`.

Source-specific data goes in `identifiers` (only what names the event) and
`payload`; it never adds envelope fields. All three mappings must be
JSON-native so the record survives the raw log round trip.
`validate_event()` enforces this before anything is written.

Versioning policy:

* `SCHEMA_VERSION` increases when the meaning of an envelope field or reserved
  key changes, or a reserved key is added.
* Readers accept every version up to `SCHEMA_VERSION`; unknown metadata keys
  are ignored.
* Ingestion refuses records with a version newer than the library knows.
* Old records are never rewritten to upgrade them.
* The event-key algorithm has its own `EVENT_KEY_VERSION`. Changing it would
  make every replayed event look new, so it needs an explicit migration and is
  never part of a schema bump.

### Identity

| | `RawRecord.record_id` | `event_key()` |
|---|---|---|
| Purpose | integrity of one stored record | deduplication across the archive |
| Covers | every field, including metadata | source, event type, UTC timestamp, identifiers (payload if no identifiers) |
| Length | 16 hex characters (64 bits) of SHA-256 | 64 hex characters (full SHA-256) |
| Changed in v0.4 | no | new |

`record_id` was kept as is. It is compared with a stored value for the same
record, so a 64-bit prefix gives roughly a 5 × 10⁻²⁰ chance that a corrupted
record passes. It changes when the same event is collected twice with
different provenance, which is why it is not used for deduplication.

`observation_digest()` covers everything except metadata. Same event key with a
different digest means the source now reports a different observation under the
same identity: a **conflict**.

## Ingestion (`obsidian_core.ingestion`)

`Ingestor(store)` is the only component that should append collected events.

* `classify(record)` returns what would happen without writing.
* `ingest(record)`: `NEW` appends; `KNOWN` writes nothing; `CONFLICT` writes
  nothing and reports the existing `record_id`.
* Lookups read the archive itself: the source's log for the record's day.
  There is no separate index that could disagree with the archive.
* Known keys are cached per `(source, day)`. The cache assumes a single writer;
  `refresh()` drops it.
* An archive file that fails its integrity check stops ingestion with an error
  instead of appending next to unknown state.

## Collectors and provenance (`obsidian_core.collectors`)

`Collector` is a `typing.Protocol`:

```python
class Collector(Protocol):
    name: str            # unique and stable; keys checkpoints and provenance
    version: str
    source: str          # the RawRecord.source it writes
    source_uri: str | None
    def collect(self, cursor: str | None) -> Iterator[Observation]: ...
```

Contract:

* `collect(None)` yields everything; `collect(cursor)` yields what comes after
  it.
* Every observation before a cursor is yielded before that cursor, so resuming
  from any yielded cursor loses nothing. Re-yielding is allowed.
* A cursor the collector cannot use raises `InvalidCursor` before anything is
  yielded.
* A collector never touches `RawStore`, checkpoints or the vault.

`Provenance` is attached by `stamp()` under the reserved key. It is archived
with each record and excluded from event identity.

## Checkpointing and recovery (`obsidian_core.checkpoints`)

`CheckpointStore(directory)` keeps `<collector>.json` per collector:
`{"format": 1, "collector", "cursor", "updated_at", "events_seen"}`, written
atomically (temporary file, fsync, rename). Keep the directory outside the
`Raw/` tree; deleting it loses no data.

| Checkpoint state | `load()` status | Run behaviour |
|---|---|---|
| none | `MISSING` | collect from the beginning |
| unreadable JSON | `CORRUPT` | file moved to `*.corrupt-<time>`, collect from the beginning |
| wrong format, collector, cursor or timestamp | `INVALID` | collect from the beginning |
| valid | `VALID` | collect after the cursor |
| valid but rejected by the collector | `VALID`, `restarted_from_beginning=True` | checkpoint cleared, collect from the beginning |

`run_collector(collector, ingestor, checkpoints)` saves a checkpoint every
`checkpoint_every` observations and at the end, each time covering only
observations already ingested. If the run fails, the last saved checkpoint
stays and the error propagates; the next run replays the uncheckpointed tail,
which ingestion reports as `KNOWN`.

## Reconciliation (`obsidian_core.reconciliation`)

`reconcile(collector, ingestor, since=None, checkpoints=None, repair=False)`
re-enumerates the source and compares it with the archive:

* `present`, `missing` (gaps), `conflicts`;
* `archive_only`: records this collector wrote (by provenance) that the source
  no longer reports, e.g. commits dropped by a history rewrite. Computed only
  for full enumerations, over every daily log of the source;
* `checkpoint_ahead_of_archive`: a gap sits at or before the checkpoint's
  cursor, so normal runs would never fill it.

Reconciliation never writes checkpoints. It changes the archive only with
`repair=True`, and only by appending missing events through `Ingestor`.
Conflicts and archive-only records are reported, never resolved. If the source
fails part-way, the report has `complete=False`; any repairs already made stay
(they are idempotent appends), and nothing is concluded about absence.

## Git adapter (`obsidian_core.git`)

Git-specific code lives only in `obsidian_core.git`. No generic module imports
it (a contract test checks this).

`GitCollector(repo_path, repository=None, ref="HEAD")` maps each commit to:

* `source="git"`, `event_type="commit"`, timestamp = committer date;
* `identifiers={"repository", "commit"}` (full hash);
* `payload`: subject, body, author (name, email, date), committer, parents,
  files changed, insertions, deletions (merges report no stats).

The cursor is the last commit hash. Commits come oldest first in reverse
topological order, so `<cursor>..<ref>` resumes without loss. A cursor that no
longer exists or is no longer an ancestor of the ref (rebase, reset) raises
`InvalidCursor`. The runner restarts from the beginning and the dropped commits
stay in the archive, where reconciliation reports them as archive-only.

Not included: a permanent or systemd Git logger. Scheduling collection is the
deployment's job.

## Obsidian relationships (`obsidian_core.git.activity`)

`GitActivityNotes(vault, store)` is presentation, downstream of the archive. It
writes `Git Activity/YYYY/MM/YYYY-MM-DD.md` with:

* `[[YYYY-MM-DD]]`, the daily note (`daily_note_format`);
* `[[Raw/git/YYYY/MM/DD|git raw log]]`, the source log;
* `[[Repositories/<repo>|<repo>]]` per repository (`repository_folder`);
* per commit: time, short hash, escaped subject, author, stats and the raw
  `record_id`; the frontmatter lists every `source_records` id.

The note is a pure function of the archive. Commits are deduplicated by event
key and the note is rewritten whole, so reprocessing never duplicates links.
A note at that path without `generator: obsidian-core.git-activity` is never
overwritten (`ForeignNoteError`). Commit text is escaped so it cannot create
links or tags.

## Public API boundaries

| Layer | Public names | May depend on |
|---|---|---|
| Storage | `RawRecord`, `RawStore`, `RawParser`, `Vault`, `Note` | — |
| Schema and identity | `SCHEMA_VERSION`, `event_key`, `EventSchemaError`; `events.validate_event`, `events.with_envelope`, `events.observation_digest` | storage |
| Ingestion | `Ingestor`, `IngestResult`, `IngestStatus` | schema, storage |
| Collection | `Collector`, `Observation`, `Provenance`, `InvalidCursor` | schema |
| Recovery | `Checkpoint`, `CheckpointStore`, `CheckpointStatus`, `run_collector`, `RunReport`, `reconcile`, `ReconciliationReport` | ingestion, collection |
| Git adapter | `obsidian_core.git.GitCollector`, `GitError` | collection |
| Presentation | `obsidian_core.git.GitActivityNotes` | storage, links, relationships |

The generic layers never import the Git adapter or the presentation layer.

## Implementation order

The v0.4 issues were implemented in their dependency order:

```
#63 schema/identity ─▶ #59 ingestion ─┬─▶ #62 collectors ─┐
                                      └─▶ #60 checkpoints ─┼─▶ #65 Git adapter ─▶ #66 notes
                                           #61 reconciliation ◀─┘
#67 contract tests and #68 this document close the milestone. #64 is independent.
```

## Usage

```python
from obsidian_core import CheckpointStore, Ingestor, RawStore, Vault, reconcile, run_collector
from obsidian_core.git import GitActivityNotes, GitCollector

vault = Vault("~/Documents/Obsidian/Knowledge Base")
store = RawStore(vault)
checkpoints = CheckpointStore("~/.local/state/obsidian-core/checkpoints")

collector = GitCollector("~/obsidian-core")
report = run_collector(collector, Ingestor(store), checkpoints)

# Periodically, or after restoring a backup:
check = reconcile(collector, Ingestor(store), checkpoints=checkpoints)

GitActivityNotes(vault, store).write_days(check.days)
```
