"""Raw-event schema, versioning policy and event identity.

A raw event is stored as a :class:`~obsidian_core.raw.RawRecord`. This module
defines the envelope rules that every ingested record follows, without changing
``RawRecord`` itself or its ``record_id``.

Envelope
--------

Generic fields (required, owned by obsidian-core):

``timestamp``
    When the observation happened at the source. Timezone-aware.
``source``
    The kind of source (for example ``"git"``). Selects the raw log directory.
``event_type``
    What was observed (for example ``"commit"``).
``identifiers``
    Source-native identifiers that name the observed thing, such as a
    repository name and commit hash. They take part in event identity.
``payload``
    The observation itself. Source-specific; only the collector interprets it.
``metadata``
    Collection context. Two keys are reserved (see below). Other keys are
    allowed and are not part of event identity.

Reserved metadata keys:

``schema_version``
    Integer version of this envelope. Records written before v0.4 have no
    version and are read as version 0.
``provenance``
    Where the record came from: which collector, which version, which source
    location, and when it was collected (see :mod:`obsidian_core.collectors`).

Source-specific data belongs in ``identifiers`` (only what names the event)
and ``payload`` (everything else). It never adds fields to the envelope.

All three mappings must hold JSON-native values only (``dict`` with string
keys, ``list``, ``str``, ``int``, ``float``, ``bool``, ``None``). The raw log
stores them as JSON; a value that does not survive the round trip, such as a
tuple or a ``datetime``, would fail the parser's integrity check later.

Versioning policy
-----------------

* ``SCHEMA_VERSION`` increases only when the meaning of an envelope field or a
  reserved key changes. Adding a new optional reserved key also increases it.
* Readers accept every version up to ``SCHEMA_VERSION``. Unknown metadata keys
  are kept and ignored.
* Ingestion refuses records that claim a version newer than this library
  knows, so an old writer cannot misread or append beside newer events.
* The authoritative archive is never rewritten to upgrade old records. Older
  records stay valid at their recorded version.
* Event identity has its own version (``EVENT_KEY_VERSION``). Changing how the
  key is computed would make replayed events look new, so it requires an
  explicit migration and is never done as part of a schema bump.

Identity
--------

Two different identities exist, for two different jobs:

``RawRecord.record_id`` (16 hex characters of SHA-256, unchanged)
    An integrity check for one stored record. The parser recomputes it and
    compares it with the stored value. A corrupted record would have to
    produce the same 64-bit prefix by chance to pass, a probability of about
    5e-20 per record. It covers the whole record, including collection
    metadata, so it changes when the same event is collected twice at
    different times. It is therefore not used for deduplication.

:func:`event_key` (64 hex characters of SHA-256)
    The identity of the observation for idempotent ingestion. It covers
    ``source``, ``event_type``, the timestamp as a UTC instant, and
    ``identifiers``. Collection metadata is excluded, so replaying the same
    observation yields the same key. When ``identifiers`` is empty there is
    nothing that names the event, so the ``payload`` is included as well
    (content identity). The full digest is used because the key is compared
    across the whole archive, where a 64-bit prefix would leave the collision
    question open; nothing existing depended on a shorter form.

:func:`observation_digest`
    A digest of everything except ``metadata``. Two records with the same
    event key but different digests mean the source reported a different
    observation under the same identity: a conflict, which ingestion reports
    and never resolves by rewriting the archive.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC
from typing import Any

from .raw import RawRecord

SCHEMA_VERSION = 1
"""Current raw-event envelope version."""

EVENT_KEY_VERSION = 1
"""Version of the :func:`event_key` algorithm. Changing it needs a migration."""

SCHEMA_VERSION_KEY = "schema_version"
PROVENANCE_KEY = "provenance"
RESERVED_METADATA_KEYS = frozenset({SCHEMA_VERSION_KEY, PROVENANCE_KEY})


class EventSchemaError(ValueError):
    """Raised when a record does not follow the raw-event envelope rules."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _utc_instant(record: RawRecord) -> str:
    return record.timestamp.astimezone(UTC).isoformat()


def event_key(record: RawRecord) -> str:
    """Return the deduplication identity of a raw event."""
    parts: dict[str, Any] = {
        "v": EVENT_KEY_VERSION,
        "source": record.source,
        "event_type": record.event_type,
        "timestamp": _utc_instant(record),
        "identifiers": record.identifiers,
    }

    if not record.identifiers:
        parts["payload"] = record.payload

    return hashlib.sha256(_canonical(parts).encode("utf-8")).hexdigest()


def observation_digest(record: RawRecord) -> str:
    """Return a digest of the observation, excluding collection metadata."""
    parts = {
        "source": record.source,
        "event_type": record.event_type,
        "timestamp": _utc_instant(record),
        "identifiers": record.identifiers,
        "payload": record.payload,
    }

    return hashlib.sha256(_canonical(parts).encode("utf-8")).hexdigest()


def schema_version_of(record: RawRecord) -> int:
    """Return the envelope version of a record; 0 for pre-v0.4 records."""
    version = record.metadata.get(SCHEMA_VERSION_KEY, 0)

    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise EventSchemaError(f"Invalid schema_version: {version!r}")

    return version


def _check_json_native(name: str, value: Any) -> None:
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise EventSchemaError(f"{name} is not JSON-serialisable: {exc}") from exc

    if json.loads(encoded) != value:
        raise EventSchemaError(f"{name} does not survive a JSON round trip")


def validate_event(record: RawRecord) -> None:
    """Check that a record follows the envelope rules before it is ingested."""
    if not isinstance(record.identifiers, dict) or not isinstance(record.metadata, dict):
        raise EventSchemaError("identifiers and metadata must be mappings")

    for name in ("identifiers", "metadata"):
        mapping = getattr(record, name)

        if not all(isinstance(key, str) for key in mapping):
            raise EventSchemaError(f"{name} keys must be strings")

        _check_json_native(name, mapping)

    _check_json_native("payload", record.payload)

    if any("\n" in key or ":**" in key for key in [*record.identifiers, *record.metadata]):
        raise EventSchemaError("Mapping keys cannot contain newlines or ':**'")

    if "\n" in record.source or "\n" in record.event_type:
        raise EventSchemaError("source and event_type cannot contain newlines")

    if "/" in record.source or record.source in {".", ".."}:
        raise EventSchemaError("source cannot contain path separators")

    version = schema_version_of(record)

    if version > SCHEMA_VERSION:
        raise EventSchemaError(
            f"Record schema_version {version} is newer than supported {SCHEMA_VERSION}"
        )


def with_envelope(
    record: RawRecord,
    provenance: dict[str, Any] | None = None,
) -> RawRecord:
    """Return a copy of a record stamped with the schema version and provenance."""
    metadata = dict(record.metadata)
    metadata[SCHEMA_VERSION_KEY] = SCHEMA_VERSION

    if provenance is not None:
        metadata[PROVENANCE_KEY] = provenance

    return replace(record, metadata=metadata)
