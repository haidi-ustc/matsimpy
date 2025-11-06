"""
BatchProcessor class for processing multiple structures efficiently.

Provides parallel processing capabilities for applying transformations
to large batches of structures.
"""

from typing import List, Callable, Union, Any, Optional, Dict
from dataclasses import dataclass
from ..base import _validate_structure
from ...core import Crystal, Molecule


@dataclass
class BatchResult:
    """
    Result of batch processing for a single structure.
    
    Attributes:
        structure: Transformed structure (None if failed)
        success: Whether transformation succeeded
        error: Error message if failed
        index: Original index in input list
    """
    structure: Optional[Union[Crystal, Molecule]] = None
    success: bool = True
    error: Optional[str] = None
    index: int = -1


class BatchProcessor:
    """
    Process multiple structures with transformations in parallel.
    
    Provides efficient batch processing with:
    - Parallel processing using multiprocessing
    - Progress tracking (optional)
    - Error handling strategies
    - Result metadata
    
    Attributes:
        transformations: List of transformation functions to apply
        n_workers: Number of worker processes
        progress: Whether to show progress bar
        error_handling: Error handling strategy ('skip', 'raise', 'log')
    
    Examples:
        >>> from matsimpy.transformation.composite import BatchProcessor
        >>> from matsimpy.transformation import make_supercell, apply_strain
        >>> 
        >>> transformations = [
        ...     lambda s: make_supercell(s, [2, 2, 2]),
        ...     lambda s: apply_strain(s, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
        ... ]
        >>> 
        >>> processor = BatchProcessor(
        ...     transformations=transformations,
        ...     n_workers=4,
        ...     progress=True,
        ...     error_handling='skip'
        ... )
        >>> 
        >>> crystals = [crystal1, crystal2, ..., crystal1000]
        >>> results = processor.process(crystals)
        >>> 
        >>> # Check results
        >>> for result in results:
        ...     if result.success:
        ...         print(f"Success: {result.structure.formula}")
        ...     else:
        ...         print(f"Failed: {result.error}")
    """
    
    def __init__(
        self,
        transformations: List[Callable],
        n_workers: int = 4,
        progress: bool = True,
        error_handling: str = 'skip'
    ):
        """
        Initialize batch processor.
        
        Args:
            transformations: List of transformation functions to apply in sequence
            n_workers: Number of worker processes for parallel processing
            progress: If True, show progress bar (requires tqdm)
            error_handling: Error handling strategy:
                          - 'skip': Skip failed structures, continue processing
                          - 'raise': Raise exception on first error
                          - 'log': Log errors but continue processing
        
        Raises:
            ValueError: If error_handling is invalid
        """
        if not transformations:
            raise ValueError("At least one transformation must be provided")
        
        if error_handling not in ['skip', 'raise', 'log']:
            raise ValueError(
                f"Invalid error_handling: {error_handling}. "
                f"Must be 'skip', 'raise', or 'log'"
            )
        
        self.transformations = transformations
        self.n_workers = n_workers
        self.progress = progress
        self.error_handling = error_handling
    
    def _apply_transformations(self, structure: Union[Crystal, Molecule]) -> Union[Crystal, Molecule]:
        """
        Apply all transformations to a single structure.
        
        Args:
            structure: Structure to transform
        
        Returns:
            Transformed structure
        
        Raises:
            Exception: If transformation fails (depending on error_handling)
        """
        _validate_structure(structure)
        
        result = structure
        for transform in self.transformations:
            result = transform(result)
        
        return result
    
    def _process_single(self, item: tuple) -> BatchResult:
        """
        Process a single structure (for parallel processing).
        
        Args:
            item: Tuple of (index, structure)
        
        Returns:
            BatchResult with structure and metadata
        """
        index, structure = item
        
        try:
            transformed = self._apply_transformations(structure)
            return BatchResult(
                structure=transformed,
                success=True,
                index=index
            )
        except Exception as e:
            return BatchResult(
                structure=None,
                success=False,
                error=str(e),
                index=index
            )
    
    def process(self, structures: List[Union[Crystal, Molecule]]) -> List[BatchResult]:
        """
        Process batch of structures.
        
        Args:
            structures: List of structures to process
        
        Returns:
            List of BatchResult objects
        
        Examples:
            >>> results = processor.process([crystal1, crystal2, crystal3])
            >>> successful = [r.structure for r in results if r.success]
        """
        if not structures:
            return []
        
        # Prepare items with indices
        items = [(i, s) for i, s in enumerate(structures)]
        
        # Process in parallel or sequential
        if self.n_workers > 1 and len(structures) > 1:
            results = self._process_parallel(items)
        else:
            results = self._process_sequential(items)
        
        # Sort by original index
        results.sort(key=lambda r: r.index)
        
        # Handle errors based on strategy
        self._handle_errors(results)
        
        return results
    
    def _process_sequential(self, items: List[tuple]) -> List[BatchResult]:
        """Process structures sequentially."""
        results = []
        
        # Try to use tqdm for progress if available
        if self.progress:
            try:
                from tqdm import tqdm
                items_iter = tqdm(items, desc="Processing structures")
            except ImportError:
                items_iter = items
        else:
            items_iter = items
        
        for item in items_iter:
            result = self._process_single(item)
            results.append(result)
            
            # Raise on error if error_handling is 'raise'
            if not result.success and self.error_handling == 'raise':
                raise RuntimeError(
                    f"Transformation failed at index {result.index}: {result.error}"
                )
        
        return results
    
    def _process_parallel(self, items: List[tuple]) -> List[BatchResult]:
        """Process structures in parallel."""
        try:
            from multiprocessing import Pool
            from functools import partial
            
            process_func = self._process_single
            
            # Try to use tqdm for progress if available
            if self.progress:
                try:
                    from tqdm import tqdm
                    from functools import partial as partial_func
                    
                    with Pool(self.n_workers) as pool:
                        # Use imap for progress tracking
                        results = []
                        with tqdm(total=len(items), desc="Processing structures") as pbar:
                            for result in pool.imap(process_func, items):
                                results.append(result)
                                pbar.update(1)
                                
                                # Check for errors if error_handling is 'raise'
                                if not result.success and self.error_handling == 'raise':
                                    pool.terminate()
                                    raise RuntimeError(
                                        f"Transformation failed at index {result.index}: {result.error}"
                                    )
                        return results
                except ImportError:
                    # tqdm not available, use regular map
                    pass
            
            # Regular parallel processing without progress
            with Pool(self.n_workers) as pool:
                results = pool.map(process_func, items)
                
                # Check for errors if error_handling is 'raise'
                for result in results:
                    if not result.success and self.error_handling == 'raise':
                        raise RuntimeError(
                            f"Transformation failed at index {result.index}: {result.error}"
                        )
                
                return results
                
        except Exception as e:
            # Fallback to sequential if parallel fails
            import warnings
            warnings.warn(
                f"Parallel processing failed: {e}. Falling back to sequential.",
                UserWarning
            )
            return self._process_sequential(items)
    
    def _handle_errors(self, results: List[BatchResult]) -> None:
        """Handle errors based on error_handling strategy."""
        if self.error_handling == 'log':
            import logging
            logger = logging.getLogger(__name__)
            
            for result in results:
                if not result.success:
                    logger.warning(
                        f"Transformation failed at index {result.index}: {result.error}"
                    )
    
    def process_stream(self, structures) -> Any:
        """
        Process structures lazily (generator).
        
        Args:
            structures: Iterable of structures
        
        Yields:
            BatchResult objects as they are processed
        
        Examples:
            >>> for result in processor.process_stream(structures):
            ...     if result.success:
            ...         process_structure(result.structure)
        """
        items = [(i, s) for i, s in enumerate(structures)]
        
        if self.n_workers > 1 and len(items) > 1:
            # For parallel, we need to process all first
            # Could be optimized with async processing in future
            results = self._process_parallel(items)
            for result in results:
                yield result
        else:
            # Sequential processing - can yield immediately
            for item in items:
                result = self._process_single(item)
                
                if not result.success and self.error_handling == 'raise':
                    raise RuntimeError(
                        f"Transformation failed at index {result.index}: {result.error}"
                    )
                
                yield result
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BatchProcessor(transformations={len(self.transformations)}, "
            f"n_workers={self.n_workers}, error_handling='{self.error_handling}')"
        )


__all__ = ['BatchProcessor', 'BatchResult']

