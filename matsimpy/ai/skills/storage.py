"""Storage skill — persistent data storage and retrieval."""

from matsimpy.storage import DataStorage, MemoryBackend
from matsimpy.io import read as io_read
from matsimpy.ai.skill import FunctionDef

SKILL_NAME = "storage"
SKILL_DESCRIPTION = "Data storage: store, retrieve, and query structures"
SKILL_KEYWORDS: list[str] = [
    "store", "retrieve", "query", "database", "storage",
]


# Session-level in-memory store
_store = DataStorage(backend=MemoryBackend())


def _store_structure(path, metadata=None):
    s = io_read(path)
    doc_id = _store.store_data(s, metadata=metadata or {})
    return {
        "doc_id": doc_id,
        "formula": s.formula,
        "num_atoms": len(s),
    }


def _retrieve_structure(doc_id):
    s = _store.retrieve_data(doc_id)
    return {
        "formula": s.formula,
        "num_atoms": len(s),
        "structure": str(s),
    }


def _query_structures(key, value, limit=20):
    results = _store.query({f"metadata.{key}": value}, limit=limit)
    return {
        "count": len(results),
        "results": [
            {"formula": r.formula if hasattr(r, 'formula') else str(r)}
            for r in results[:limit]
        ],
    }


def get_functions() -> list[FunctionDef]:
    return [
        FunctionDef(
            name="store_structure",
            description="Store a structure file in the session database with optional metadata",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to structure file"},
                    "metadata": {"type": "object", "description": "Optional key-value metadata"},
                },
                "required": ["path"],
            },
            callable=_store_structure,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="retrieve_structure",
            description="Retrieve a stored structure by its document ID",
            parameters={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string", "description": "Document ID returned by store_structure"},
                },
                "required": ["doc_id"],
            },
            callable=_retrieve_structure,
            skill=SKILL_NAME,
        ),
        FunctionDef(
            name="query_structures",
            description="Query stored structures by metadata key-value pair",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Metadata key to search"},
                    "value": {"type": "string", "description": "Metadata value to match"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                },
                "required": ["key", "value"],
            },
            callable=_query_structures,
            skill=SKILL_NAME,
        ),
    ]
