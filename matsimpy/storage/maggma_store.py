"""
Maggma-based data storage implementation.

Provides persistent storage for MatSimPy data using maggma stores.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from pathlib import Path

try:
    from maggma.stores import MemoryStore, JSONStore
    MAGGMA_AVAILABLE = True
except ImportError:
    MAGGMA_AVAILABLE = False
    MemoryStore = None
    JSONStore = None

from monty.json import MSONable

logger = logging.getLogger(__name__)


class DataStorage(MSONable):
    """
    Module for persistent storage of computation results using maggma.
    
    Provides efficient data management with support for JSON-based storage
    and retrieval of structures, calculation results, and workflows.
    
    The storage integrates with MatSimPy's config system for default paths
    and supports both in-memory (for testing) and file-based storage.
    
    Attributes:
        store: Maggma store instance for data persistence
        store_type: Type of store ('memory' or 'json')
        store_path: Path to JSON store file (if using JSONStore)
        
    Example:
        >>> from matsimpy.storage import DataStorage
        >>> from matsimpy import Crystal, Lattice
        >>> 
        >>> # Initialize storage (uses config default or './materials_simulation_data.json')
        >>> storage = DataStorage()
        >>> 
        >>> # Store a crystal structure
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
        >>> doc_id = storage.store_data(crystal)
        >>> 
        >>> # Store calculation results with metadata
        >>> results = {'energy': -10.5, 'forces': [[0,0,0]]}
        >>> storage.store_data(results, metadata={'calculator': 'LJ', 'structure_id': doc_id})
        >>> 
        >>> # Retrieve data
        >>> crystal_dict = storage.retrieve_data(doc_id)
        >>> crystal_restored = Crystal.from_dict(crystal_dict)
        >>> 
        >>> # Query data
        >>> lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
    """
    
    def __init__(
        self,
        store_path: Optional[Union[str, Path]] = None,
        use_memory_store: bool = False,
        **kwargs
    ):
        """
        Initialize the Data Storage Module.
        
        Args:
            store_path: Path for JSON store (if not using memory store).
                       If None, uses config default or './materials_simulation_data.json'
            use_memory_store: Whether to use in-memory store (for testing)
            **kwargs: Additional arguments passed to store initialization
            
        Raises:
            ImportError: If maggma is not installed
        """
        if not MAGGMA_AVAILABLE:
            raise ImportError(
                "maggma is required for DataStorage. "
                "Install with: pip install maggma or pip install matsimpy[storage]"
            )
        
        if use_memory_store:
            self.store = MemoryStore(key='doc_id', **kwargs)
            self.store_type = 'memory'
            self.store_path = None
            self.store.connect()
            logger.info("Initialized in-memory data store")
        else:
            # Get default path from config if not provided
            if store_path is None:
                try:
                    from ..config import get_config
                    store_path = get_config('storage.default_path')
                    if store_path:
                        store_path = Path(store_path).expanduser()
                except ImportError:
                    pass
            
            # Fallback to default path
            if store_path is None:
                store_path = Path("./materials_simulation_data.json")
            else:
                store_path = Path(store_path)
            
            # Create directory if it doesn't exist
            store_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create empty JSON file if it doesn't exist (maggma requires file to exist)
            if not store_path.exists():
                with open(store_path, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created new JSON store file: {store_path}")
            
            # Initialize JSONStore
            self.store = JSONStore(str(store_path), key='doc_id', **kwargs)
            self.store_type = 'json'
            self.store_path = store_path
            
            # Connect to store
            self.store.connect()
            logger.info(f"Initialized JSON data store at {store_path}")
    
    def store_data(
        self,
        data: Union[Dict[str, Any], MSONable],
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store data in the persistent store.
        
        Supports storing:
        - MatSimPy objects (Crystal, Molecule, etc.) - automatically serialized
        - Dictionaries
        - Calculation results
        - Any MSONable object
        
        Args:
            data: Data to store (dict or MSONable object)
            doc_id: Optional document ID (auto-generated if not provided)
            metadata: Optional metadata to attach (e.g., calculator type, timestamp)
        
        Returns:
            str: Document ID of stored data
            
        Example:
            >>> storage = DataStorage()
            >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
            >>> doc_id = storage.store_data(crystal, metadata={'description': 'Si primitive cell'})
        """
        try:
            # Convert MSONable to dict
            if isinstance(data, MSONable):
                data_dict = data.as_dict()
            else:
                data_dict = data.copy() if isinstance(data, dict) else {'data': data}
            
            # Generate ID if not provided
            if doc_id is None:
                # Use hash of serialized data for consistent IDs
                serialized = json.dumps(data_dict, sort_keys=True, default=str)
                doc_id = hashlib.md5(serialized.encode()).hexdigest()
            
            # Add metadata with doc_id as the key
            data_dict['doc_id'] = doc_id
            data_dict['stored_at'] = datetime.now().isoformat()
            
            if metadata:
                data_dict['metadata'] = metadata
            
            # Store in database
            self.store.update(data_dict)
            
            logger.info(f"Stored data with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to store data: {str(e)}")
            raise
    
    def retrieve_data(
        self,
        doc_id: Optional[str] = None,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Retrieve data from the persistent store.
        
        Args:
            doc_id: Specific document ID to retrieve
            query: Query criteria for retrieval (e.g., {'metadata.calculator': 'LJ'})
            limit: Maximum number of documents to return
        
        Returns:
            Retrieved document(s). Returns dict for single doc_id, list for query.
            
        Example:
            >>> # Get specific document
            >>> doc = storage.retrieve_data(doc_id)
            >>> crystal = Crystal.from_dict(doc)
            >>> 
            >>> # Query multiple documents
            >>> results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
        """
        try:
            if doc_id:
                # Retrieve specific document
                result = self.store.query_one(criteria={'doc_id': doc_id})
                if result:
                    logger.info(f"Retrieved data with ID: {doc_id}")
                    return result
                else:
                    logger.warning(f"No data found with ID: {doc_id}")
                    return {}
            
            elif query:
                # Query multiple documents
                results = list(self.store.query(criteria=query, limit=limit))
                logger.info(f"Retrieved {len(results)} documents matching query")
                return results
            
            else:
                # Return all documents
                results = list(self.store.query(limit=limit))
                logger.info(f"Retrieved {len(results)} documents")
                return results
                
        except Exception as e:
            logger.error(f"Failed to retrieve data: {str(e)}")
            raise
    
    def delete_data(self, doc_id: str) -> bool:
        """
        Delete data from the store.
        
        Args:
            doc_id: Document ID to delete
        
        Returns:
            bool: Success status
        """
        try:
            # Check if document exists
            doc = self.store.query_one(criteria={'doc_id': doc_id})
            if not doc:
                logger.warning(f"No document found with ID: {doc_id}")
                return False
            
            # Delete document
            self.store.remove_docs(criteria={'doc_id': doc_id})
            logger.info(f"Deleted data with ID: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete data: {str(e)}")
            raise
    
    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in the store.
        
        Args:
            query: Optional query criteria
        
        Returns:
            int: Number of documents matching query
        """
        criteria = query or {}
        count = self.store.count(criteria=criteria)
        logger.info(f"Document count: {count}")
        return count
    
    def clear_store(self) -> None:
        """
        Clear all data from the store.
        
        Warning: This permanently deletes all stored data!
        """
        logger.warning("Clearing all data from store")
        self.store.remove_docs(criteria={})
    
    def close(self) -> None:
        """Close the data store connection."""
        # For JSONStore, ensure data is written to disk
        if self.store_type == 'json' and hasattr(self.store, 'update_json_file'):
            self.store.update_json_file()
        self.store.close()
        logger.info("Data store connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes store."""
        self.close()
    
    def as_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for MSONable."""
        return {
            '@module': self.__class__.__module__,
            '@class': self.__class__.__name__,
            'store_type': self.store_type,
            'store_path': str(self.store_path) if self.store_path else None
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataStorage':
        """
        Deserialize from dictionary for MSONable.
        
        Note: This recreates the storage but doesn't restore the store connection.
        You may need to reinitialize for full functionality.
        """
        store_type = d.get('store_type', 'memory')
        store_path = d.get('store_path')
        
        return cls(
            store_path=store_path,
            use_memory_store=(store_type == 'memory')
        )


__all__ = ['DataStorage']

