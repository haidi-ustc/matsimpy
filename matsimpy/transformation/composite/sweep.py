"""
ParameterSweep class for generating structures with varying parameters.

Provides functionality to generate multiple structures by varying transformation
parameters systematically.
"""

import itertools
from typing import List, Callable, Union, Any, Dict, Iterator, Tuple
from ...core import Crystal, Molecule
from ..base import _validate_structure


class ParameterSweep:
    """
    Generate structures with varying parameters.

    Creates multiple structures by systematically varying transformation
    parameters. Supports different iteration modes:
    - 'cartesian': All combinations of parameters
    - 'zip': Parallel iteration (one from each parameter set)
    - 'custom': User-defined combination logic

    Attributes:
        base_structure: Base structure to transform
        transformations: Dictionary of transformations with parameter variations
        mode: Iteration mode ('cartesian', 'zip', or 'custom')

    Examples:
        >>> from matsimpy.transformation.composite import ParameterSweep
        >>> from matsimpy.transformation import apply_strain, make_supercell
        >>> from matsimpy.builders.bulk import from_prototype
        >>>
        >>> crystal = from_prototype('diamond', 'Si', 5.43)
        >>>
        >>> sweep = ParameterSweep(
        ...     base_structure=crystal,
        ...     transformations={
        ...         'strain': {
        ...             'func': apply_strain,
        ...             'params': {
        ...                 'strain_matrix': [
        ...                     [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
        ...                     [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
        ...                     [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
        ...                 ]
        ...             }
        ...         },
        ...         'supercell': {
        ...             'func': make_supercell,
        ...             'params': {
        ...                 'scaling_matrix': [[2,2,2], [3,3,3]]
        ...             }
        ...         }
        ...     },
        ...     mode='cartesian'
        ... )
        >>>
        >>> # Generate all combinations (3 strains × 2 supercells = 6 structures)
        >>> for struct, params in sweep:
        ...     print(f"Strain: {params['strain']}, Supercell: {params['supercell']}")
    """

    def __init__(
        self,
        base_structure: Union[Crystal, Molecule],
        transformations: Dict[str, Dict[str, Any]],
        mode: str = "cartesian",
    ):
        """
        Initialize parameter sweep.

        Args:
            base_structure: Base structure to transform
            transformations: Dictionary mapping transformation names to configs.
                            Each config should have:
                            - 'func': Transformation function
                            - 'params': Dictionary of parameter names to lists of values
            mode: Iteration mode:
                  - 'cartesian': All combinations (default)
                  - 'zip': Parallel iteration (one from each)
                  - 'custom': User-defined (not yet implemented)

        Raises:
            ValueError: If mode is invalid or transformations are malformed
        """
        _validate_structure(base_structure)

        if mode not in ["cartesian", "zip", "custom"]:
            raise ValueError(
                f"Invalid mode: {mode}. Must be 'cartesian', 'zip', or 'custom'"
            )

        self.base_structure = base_structure
        self.transformations = transformations
        self.mode = mode

        # Validate transformations
        self._validate_transformations()

        # Pre-compute parameter combinations
        self._combinations = self._generate_combinations()

    def _validate_transformations(self) -> None:
        """Validate transformation configurations."""
        if not self.transformations:
            raise ValueError("At least one transformation must be provided")

        for name, config in self.transformations.items():
            if "func" not in config:
                raise ValueError(f"Transformation '{name}' missing 'func'")
            if not callable(config["func"]):
                raise TypeError(f"Transformation '{name}' func must be callable")
            if "params" not in config:
                raise ValueError(f"Transformation '{name}' missing 'params'")
            if not isinstance(config["params"], dict):
                raise TypeError(f"Transformation '{name}' params must be a dictionary")

            # Check that all param values are lists
            for param_name, param_values in config["params"].items():
                if not isinstance(param_values, list):
                    raise TypeError(
                        f"Transformation '{name}' param '{param_name}' must be a list"
                    )
                if len(param_values) == 0:
                    raise ValueError(
                        f"Transformation '{name}' param '{param_name}' is empty"
                    )

    def _generate_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations based on mode."""
        if self.mode == "cartesian":
            return self._generate_cartesian()
        elif self.mode == "zip":
            return self._generate_zip()
        else:  # custom
            raise NotImplementedError("Custom mode not yet implemented")

    def _generate_cartesian(self) -> List[Dict[str, Any]]:
        """Generate Cartesian product of all parameter combinations."""
        # Get all transformation names and their parameter combinations
        transform_names = list(self.transformations.keys())

        # For each transformation, create list of (param_name, param_value) tuples
        transform_param_lists = []
        for name in transform_names:
            config = self.transformations[name]
            param_dict = config["params"]

            # Create list of all parameter combinations for this transformation
            param_names = list(param_dict.keys())
            param_value_lists = [param_dict[pname] for pname in param_names]

            # Cartesian product of all parameters for this transformation
            transform_combinations = []
            for param_combo in itertools.product(*param_value_lists):
                combo_dict = {
                    param_names[i]: param_combo[i] for i in range(len(param_names))
                }
                transform_combinations.append(combo_dict)

            transform_param_lists.append(transform_combinations)

        # Cartesian product across all transformations
        all_combinations = []
        for combo in itertools.product(*transform_param_lists):
            combo_dict = {}
            for i, name in enumerate(transform_names):
                combo_dict[name] = combo[i]
            all_combinations.append(combo_dict)

        return all_combinations

    def _generate_zip(self) -> List[Dict[str, Any]]:
        """Generate zip-style combinations (parallel iteration)."""
        transform_names = list(self.transformations.keys())

        # Get maximum length across all transformations
        max_length = 0
        for name in transform_names:
            config = self.transformations[name]
            param_dict = config["params"]
            # Get max length across all parameters in this transformation
            for param_values in param_dict.values():
                max_length = max(max_length, len(param_values))

        # Generate combinations by zipping
        all_combinations = []
        for idx in range(max_length):
            combo_dict = {}
            for name in transform_names:
                config = self.transformations[name]
                param_dict = config["params"]

                # For each parameter, take value at idx (or last if shorter)
                param_combo = {}
                for param_name, param_values in param_dict.items():
                    param_combo[param_name] = param_values[
                        min(idx, len(param_values) - 1)
                    ]
                combo_dict[name] = param_combo

            all_combinations.append(combo_dict)

        return all_combinations

    def __len__(self) -> int:
        """Return number of structures to generate."""
        return len(self._combinations)

    def __iter__(self) -> Iterator[Tuple[Union[Crystal, Molecule], Dict[str, Any]]]:
        """Iterate over generated structures."""
        for combo in self._combinations:
            # Start with base structure
            structure = self.base_structure.copy()

            # Apply transformations in order
            for transform_name, param_combo in combo.items():
                config = self.transformations[transform_name]
                func = config["func"]

                # Call function with parameters
                structure = func(structure, **param_combo, inplace=False)

            # Yield structure and metadata
            yield structure, combo

    def generate(self) -> List[Tuple[Union[Crystal, Molecule], Dict[str, Any]]]:
        """
        Generate all structures and return as list.

        Returns:
            List of (structure, parameters) tuples

        Examples:
            >>> structures = sweep.generate()
            >>> for struct, params in structures:
            ...     process(struct)
        """
        return list(self)

    def __repr__(self) -> str:
        """String representation."""
        return f"ParameterSweep(mode='{self.mode}', combinations={len(self)})"


__all__ = ["ParameterSweep"]
