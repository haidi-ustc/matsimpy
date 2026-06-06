"""
Document codec for encoding/decoding MatSimPy objects to/from DocumentEnvelopes.

Separates serialization concerns from backend persistence.
"""

from __future__ import annotations

from typing import Optional

from monty.json import MSONable

from ..core import Structure
from .schema import DocumentEnvelope


class DocumentCodec:
    """Encodes MatSimPy objects ↔ DocumentEnvelope for persistence."""

    def encode(
        self,
        obj: MSONable,
        metadata: Optional[dict] = None,
        schema_version: str = "1.0.0",
    ) -> DocumentEnvelope:
        """Encode a MatSimPy object into a DocumentEnvelope.

        Args:
            obj: Any MSONable MatSimPy object (Crystal, Molecule, etc.).
            metadata: Optional user-provided metadata dict.
            schema_version: Envelope schema version.

        Returns:
            DocumentEnvelope with stable content-addressed ID.

        Raises:
            ValueError: If metadata keys collide with reserved fields.
        """
        if metadata:
            DocumentEnvelope.validate_metadata(metadata)

        payload = obj.as_dict()
        doc_id = DocumentEnvelope.generate_id(payload, metadata)

        return DocumentEnvelope(
            doc_id=doc_id,
            payload=payload,
            schema_version=schema_version,
            metadata=metadata or {},
        )

    def decode(self, envelope: DocumentEnvelope):
        """Decode a DocumentEnvelope back into a MatSimPy object.

        Uses monty's MontyDecoder for polymorphic deserialization,
        which reconstructs the correct subclass (Crystal or Molecule).

        Returns:
            Crystal or Molecule (or the raw payload dict if not MSONable).
        """
        from monty.json import MontyDecoder
        return MontyDecoder().process_decoded(envelope.payload)


__all__ = ["DocumentCodec"]
