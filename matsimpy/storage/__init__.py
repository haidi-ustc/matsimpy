"""
Data storage module for MatSimPy.

Provides persistent storage for computation results, structures, and workflows
using maggma stores.

Usage:
    >>> from matsimpy.storage import DataStorage
    >>> from matsimpy import Crystal, Lattice
    >>>
    >>> storage = DataStorage()
    >>> from matsimpy.builders.bulk import from_prototype
    >>> crystal = from_prototype('diamond', 'Si', 5.43)  # Proper diamond structure
    >>> doc_id = storage.store_data(crystal)
    >>> retrieved = storage.retrieve_data(doc_id)
"""

try:
    from .maggma_store import DataStorage

    __all__ = ["DataStorage"]
except ImportError:
    class DataStorage:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "maggma is required for DataStorage. "
                "Install with: pip install maggma or pip install MatSimPy[storage]"
            )

    __all__ = ["DataStorage"]
