"""
ParameterSweep class for generating structures with varying parameters.

Provides functionality to generate multiple structures by varying transformation
parameters systematically.
"""

import itertools
from typing import Callable, Iterable, List, Optional, Union, Any, Dict, Iterator, Tuple
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
        custom_combinations: Optional[
            Union[
                Iterable[Dict[str, Dict[str, Any]]],
                Callable[[Dict[str, Dict[str, Any]]], Iterable[Dict[str, Dict[str, Any]]]],
            ]
        ] = None,
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
                  - 'custom': Use caller-provided custom_combinations
            custom_combinations: For custom mode, either an iterable of combination
                                 dictionaries or a callable that receives
                                 transformations and returns that iterable.

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
        self.custom_combinations = custom_combinations

        # Validate transformations
        self._validate_transformations()
        if self.mode == "custom" and self.custom_combinations is None:
            raise ValueError(
                "custom_combinations must be provided when mode='custom'"
            )
        if (
            self.mode == "custom"
            and not callable(self.custom_combinations)
            and hasattr(self.custom_combinations, "__len__")
            and len(self.custom_combinations) == 0
        ):
            raise ValueError("custom_combinations must contain at least one combination")

        self._length = self._compute_length()

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

    def _iter_combinations(self) -> Iterator[Dict[str, Any]]:
        """Iterate over parameter combinations based on mode."""
        if self.mode == "cartesian":
            yield from self._iter_cartesian()
        elif self.mode == "zip":
            yield from self._iter_zip()
        else:  # custom
            yield from self._iter_custom()

    def _iter_transformation_combinations(
        self, transform_name: str
    ) -> Iterator[Dict[str, Any]]:
        """Iterate over one transformation's parameter combinations."""
        param_dict = self.transformations[transform_name]["params"]
        param_names = list(param_dict.keys())
        param_value_lists = [param_dict[pname] for pname in param_names]

        for param_combo in itertools.product(*param_value_lists):
            yield {
                param_names[index]: param_combo[index]
                for index in range(len(param_names))
            }

    def _iter_cartesian(self) -> Iterator[Dict[str, Any]]:
        """Generate Cartesian product of all parameter combinations lazily."""
        transform_names = list(self.transformations.keys())

        def recurse(index: int, combo: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
            if index == len(transform_names):
                yield dict(combo)
                return

            transform_name = transform_names[index]
            for params in self._iter_transformation_combinations(transform_name):
                combo[transform_name] = params
                yield from recurse(index + 1, combo)
            combo.pop(transform_name, None)

        yield from recurse(0, {})

    def _iter_zip(self) -> Iterator[Dict[str, Any]]:
        """Generate zip-style combinations (parallel iteration)."""
        transform_names = list(self.transformations.keys())
        max_length = self._length or 0

        # Generate combinations by zipping
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

            yield combo_dict

    def _iter_custom(self) -> Iterator[Dict[str, Any]]:
        """Use explicit caller-provided combinations."""
        if self.custom_combinations is None:
            raise ValueError(
                "custom_combinations must be provided when mode='custom'"
            )

        if callable(self.custom_combinations):
            combinations = self.custom_combinations(self.transformations)
        else:
            combinations = self.custom_combinations

        yielded = False
        for index, combo in enumerate(combinations):
            self._validate_custom_combo(combo, index)
            yielded = True
            yield combo

        if not yielded:
            raise ValueError("custom_combinations must contain at least one combination")

    def _validate_custom_combo(self, combo: Dict[str, Any], index: int) -> None:
        """Validate one custom parameter combination."""
        expected_names = set(self.transformations)
        if not isinstance(combo, dict):
            raise TypeError(
                f"custom combination {index} must be a dictionary"
            )
        combo_names = set(combo)
        if combo_names != expected_names:
            raise ValueError(
                f"custom combination {index} must include exactly these "
                f"transformations: {sorted(expected_names)}"
            )
        for transform_name, params in combo.items():
            if not isinstance(params, dict):
                raise TypeError(
                    f"custom combination {index} for '{transform_name}' "
                    "must be a parameter dictionary"
                )

    def _compute_length(self) -> Optional[int]:
        """Compute length when it is knowable without materializing combinations."""
        if self.mode == "cartesian":
            length = 1
            for config in self.transformations.values():
                for param_values in config["params"].values():
                    length *= len(param_values)
            return length

        if self.mode == "zip":
            return max(
                len(param_values)
                for config in self.transformations.values()
                for param_values in config["params"].values()
            )

        if self.custom_combinations is None:
            return None
        if callable(self.custom_combinations):
            return None
        try:
            return len(self.custom_combinations)  # type: ignore[arg-type]
        except TypeError:
            return None

    def __len__(self) -> int:
        """Return number of structures to generate."""
        if self._length is None:
            raise TypeError(
                "ParameterSweep length is unavailable for this custom combination iterable"
            )
        return self._length

    def __iter__(self) -> Iterator[Tuple[Union[Crystal, Molecule], Dict[str, Any]]]:
        """Iterate over generated structures."""
        for combo in self._iter_combinations():
            # Start with base structure
            structure = self.base_structure.copy()

            # Apply transformations in order
            for transform_name, param_combo in combo.items():
                config = self.transformations[transform_name]
                func = config["func"]

                # Call function with parameters
                # Transformation functions always return new structures
                structure = func(structure, **param_combo)

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
        combinations = self._length if self._length is not None else "unknown"
        return f"ParameterSweep(mode='{self.mode}', combinations={combinations})"


__all__ = ["ParameterSweep"]
