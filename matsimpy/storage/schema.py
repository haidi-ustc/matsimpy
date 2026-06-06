"""
Document envelope and ID generation for MatSimPy storage.

Provides:
- DocumentEnvelope: wraps a core object's dict with metadata
- Stable, content-addressed document ID generation (sha256)
- Reserved field enforcement
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class DocumentEnvelope:
    """A document ready for persistence.

    Wraps a core object's serialized dict (payload) with metadata
    including a content-addressed stable ID, schema version, timestamp,
    and user-provided metadata.

    Reserved fields (doc_id, payload, schema_version, created_at, metadata)
    are enforced — user metadata must not collide with these keys.

    Attributes:
        doc_id: Stable hash-based ID (sha256 of canonical JSON payload).
        payload: The core object's ``as_dict()`` output.
        schema_version: Version of the envelope schema ("1.0.0").
        created_at: ISO 8601 UTC timestamp.
        metadata: Arbitrary user-provided tags/labels/provenance.
    """

    doc_id: str
    payload: dict
    schema_version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict = field(default_factory=dict)

    RESERVED_FIELDS = frozenset({
        "doc_id", "payload", "schema_version", "created_at", "metadata",
    })

    # ------------------------------------------------------------------
    @staticmethod
    def generate_id(payload: dict, metadata: Optional[dict] = None) -> str:
        """Generate a stable, content-addressed document ID.

        Uses sha256 of canonical JSON (sorted keys, deterministic encoding).
        Same payload + same metadata → same ID.

        Args:
            payload: The core object's ``as_dict()`` output.
            metadata: Optional user-provided metadata.

        Returns:
            Hex-encoded sha256 digest.
        """
        canonical = {
            "payload": payload,
            "meta": metadata or {},
        }
        serialized = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    @staticmethod
    def validate_metadata(metadata: dict) -> None:
        """Check that *metadata* keys do not collide with reserved fields.

        Raises:
            ValueError: If any key is reserved.
        """
        collision = DocumentEnvelope.RESERVED_FIELDS & set(metadata.keys())
        if collision:
            raise ValueError(
                f"Metadata keys collide with reserved fields: "
                f"{sorted(collision)}. Reserved: "
                f"{sorted(DocumentEnvelope.RESERVED_FIELDS)}"
            )

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        """Serialize to a plain dict for storage."""
        return {
            "doc_id": self.doc_id,
            "payload": self.payload,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DocumentEnvelope:
        """Deserialize from a plain dict."""
        return cls(
            doc_id=d["doc_id"],
            payload=d["payload"],
            schema_version=d.get("schema_version", "1.0.0"),
            created_at=d.get("created_at", ""),
            metadata=d.get("metadata", {}),
        )


def _stable_doc_id_legacy(document: dict) -> str:
    """Legacy MD5-based stable ID (compatibility helper).

    Used by MaggmaBackend for backward compatibility with existing stored data.
    """
    from monty.json import MontyEncoder

    stable_document = {
        key: value
        for key, value in document.items()
        if key not in {"doc_id", "stored_at"}
    }
    serialized = json.dumps(
        stable_document, sort_keys=True, cls=MontyEncoder
    )
    return hashlib.md5(serialized.encode()).hexdigest()


__all__ = ["DocumentEnvelope", "_stable_doc_id_legacy"]
