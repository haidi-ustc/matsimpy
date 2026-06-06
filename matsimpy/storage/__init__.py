"""
Data storage module for MatSimPy.

Provides persistent storage for computation results, structures, and workflows.

Architecture::

    DataStorage (facade) ──► DocumentCodec ──► DocumentEnvelope
         │
         └──► StoreBackend (protocol)
               ├── MemoryBackend  (in-memory, for testing)
               └── MaggmaBackend  (file-based, for production)

Usage::

    >>> from matsimpy.storage import DataStorage
    >>> storage = DataStorage()  # defaults to MemoryBackend
    >>> doc_id = storage.store_data(crystal)
    >>> crystal = storage.retrieve_data(doc_id)
"""

from .facade import DataStorage
from .memory_store import MemoryBackend

try:
    from .maggma_store import MaggmaBackend
except ImportError:
    MaggmaBackend = None  # type: ignore

__all__ = ["DataStorage", "MemoryBackend", "MaggmaBackend"]
