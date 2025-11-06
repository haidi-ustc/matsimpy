"""
Data storage module for MatSimPy.

Provides persistent storage for computation results, structures, and workflows
using maggma stores.

Usage:
    >>> from matsimpy.storage import DataStorage
    >>> from matsimpy import Crystal, Lattice
    >>> 
    >>> storage = DataStorage()
    >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
    >>> doc_id = storage.store_data(crystal)
    >>> retrieved = storage.retrieve_data(doc_id)
"""

try:
    from .maggma_store import DataStorage
    __all__ = ['DataStorage']
except ImportError:
    # If maggma is not available, provide informative error
    import warnings
    warnings.warn(
        "maggma is not installed. Data storage functionality is not available. "
        "Install with: pip install matsimpy[storage] or pip install maggma"
    )
    
    # Provide a placeholder class that raises informative error
    class DataStorage:
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "maggma is required for DataStorage. "
                "Install with: pip install maggma or pip install matsimpy[storage]"
            )
    
    __all__ = ['DataStorage']

