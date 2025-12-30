"""
TransformationPipeline class for reusable transformation pipelines.

Provides a way to define transformation sequences once and apply them
to multiple structures.
"""

import json
from typing import List, Callable, Union, Any, Dict, Optional
from pathlib import Path
from ..base import _validate_structure
from ...core import Crystal, Molecule


class TransformationPipeline:
    """
    Reusable transformation pipeline for applying multiple transformations.

    A pipeline consists of a sequence of transformation steps that can be
    applied to one or more structures. Pipelines can be saved and loaded
    for reproducibility.

    Attributes:
        name: Name of the pipeline
        steps: List of transformation steps
        metadata: Additional metadata about the pipeline

    Examples:
        >>> from matsimpy.transformation.composite import TransformationPipeline
        >>> from matsimpy.transformation import translate, rotate, make_supercell
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> # Create pipeline
        >>> pipeline = TransformationPipeline("strain_study")
        >>> pipeline.add_step(translate, displacement=[0, 0, 0])
        >>> pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
        >>>
        >>> # Apply to structure
        >>> crystal = from_prototype('diamond', 'Si', 5.43)
        >>> result = pipeline.apply(crystal)
        >>>
        >>> # Apply to multiple structures
        >>> results = pipeline.apply_batch([crystal1, crystal2, crystal3])
    """

    def __init__(self, name: str = "pipeline"):
        """
        Initialize a transformation pipeline.

        Args:
            name: Name identifier for the pipeline
        """
        self.name = name
        self.steps: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

    def add_step(self, func: Callable, **kwargs) -> "TransformationPipeline":
        """
        Add a transformation step to the pipeline.

        Args:
            func: Transformation function to apply
            **kwargs: Arguments to pass to the transformation function

        Returns:
            self: Returns self for method chaining

        Examples:
            >>> pipeline = TransformationPipeline()
            >>> pipeline.add_step(translate, displacement=[1, 1, 1])
            >>> pipeline.add_step(rotate, angle=90, axis=[0, 0, 1])
        """
        if not callable(func):
            raise TypeError(f"func must be callable, got {type(func)}")

        self.steps.append(
            {
                "func": func,
                "kwargs": kwargs,
                "name": func.__name__ if hasattr(func, "__name__") else str(func),
            }
        )
        return self

    def apply(
        self, structure: Union[Crystal, Molecule]
    ) -> Union[Crystal, Molecule]:
        """
        Apply pipeline to a single structure.

        Always returns a new structure. For in-place modification, use the
        structure's methods directly.

        Args:
            structure: Crystal or Molecule to transform

        Returns:
            Transformed structure

        Examples:
            >>> crystal = from_prototype('diamond', 'Si', 5.43)
            >>> result = pipeline.apply(crystal)
        """
        _validate_structure(structure)

        if not self.steps:
            # No steps, return copy
            return structure.copy()

        # Apply all steps, always creating new objects
        result = structure.copy()
        for step in self.steps:
            step_func = step["func"]
            step_kwargs = step["kwargs"].copy()
            result = step_func(result, **step_kwargs)

        return result

    def apply_batch(
        self,
        structures: List[Union[Crystal, Molecule]],
        parallel: bool = False,
        n_workers: int = 4,
    ) -> List[Union[Crystal, Molecule]]:
        """
        Apply pipeline to multiple structures.

        Args:
            structures: List of structures to transform
            parallel: If True, use parallel processing (default: False)
            n_workers: Number of worker processes for parallel processing

        Returns:
            List of transformed structures

        Examples:
            >>> crystals = [crystal1, crystal2, crystal3]
            >>> results = pipeline.apply_batch(crystals)
            >>> # With parallel processing
            >>> results = pipeline.apply_batch(crystals, parallel=True, n_workers=4)
        """
        if not structures:
            return []

        if parallel:
            try:
                import multiprocessing
                from functools import partial

                # Use 'spawn' context to avoid fork() warnings in Python 3.12+
                # when running in multi-threaded environments
                ctx = multiprocessing.get_context("spawn")
                with ctx.Pool(n_workers) as pool:
                    results = pool.map(self.apply, structures)
                return results
            except Exception as e:
                # Fallback to sequential if parallel fails
                import warnings

                warnings.warn(
                    f"Parallel processing failed: {e}. Falling back to sequential.",
                    UserWarning,
                )

        # Sequential processing
        return [self.apply(s) for s in structures]

    def __len__(self) -> int:
        """Return number of steps in pipeline."""
        return len(self.steps)

    def __repr__(self) -> str:
        """String representation of pipeline."""
        return f"TransformationPipeline(name='{self.name}', steps={len(self.steps)})"

    def save(self, path: Union[str, Path]) -> None:
        """
        Save pipeline to file.

        Note: This saves the pipeline structure (function names and arguments),
        but not the actual function objects. Functions must be importable when
        loading the pipeline.

        Args:
            path: Path to save pipeline JSON file

        Examples:
            >>> pipeline.save('my_pipeline.json')
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare serializable representation
        pipeline_dict = {"name": self.name, "steps": [], "metadata": self.metadata}

        for step in self.steps:
            # Try to get function module and name
            func = step["func"]
            func_name = getattr(func, "__name__", str(func))
            func_module = getattr(func, "__module__", None)

            step_dict = {
                "func_module": func_module,
                "func_name": func_name,
                "kwargs": step["kwargs"],
            }
            pipeline_dict["steps"].append(step_dict)

        with open(path, "w") as f:
            json.dump(pipeline_dict, f, indent=2, default=str)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "TransformationPipeline":
        """
        Load pipeline from file.

        Args:
            path: Path to pipeline JSON file

        Returns:
            Loaded TransformationPipeline instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ImportError: If transformation functions cannot be imported

        Examples:
            >>> pipeline = TransformationPipeline.load('my_pipeline.json')
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Pipeline file not found: {path}")

        with open(path, "r") as f:
            pipeline_dict = json.load(f)

        pipeline = cls(name=pipeline_dict["name"])
        pipeline.metadata = pipeline_dict.get("metadata", {})

        # Load steps
        for step_dict in pipeline_dict["steps"]:
            func_module = step_dict.get("func_module")
            func_name = step_dict.get("func_name")
            kwargs = step_dict.get("kwargs", {})

            # Try to import function
            if func_module and func_name:
                try:
                    import importlib

                    module = importlib.import_module(func_module)
                    func = getattr(module, func_name)
                    pipeline.add_step(func, **kwargs)
                except (ImportError, AttributeError) as e:
                    raise ImportError(
                        f"Could not import function {func_module}.{func_name}: {e}"
                    )
            else:
                raise ValueError(f"Cannot load step: missing func_module or func_name")

        return pipeline


__all__ = ["TransformationPipeline"]
