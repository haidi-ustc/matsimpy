"""
Atom selection utilities for structures.

Provides flexible atom selection functions that can be used for substitution,
analysis, transformations, and other operations.
"""

from typing import List, Union, Callable, Optional, Set
import numpy as np
from ..core import Crystal, Molecule


def select_by_species(
    structure: Union[Crystal, Molecule], species: Union[str, List[str]]
) -> List[int]:
    """
    Select atom indices by species.

    Args:
        structure: Crystal or Molecule to select from
        species: Species symbol or list of species symbols to select

    Returns:
        List of atom indices matching the species

    Examples:
        >>> indices = select_by_species(crystal, 'Si')
        >>> indices = select_by_species(crystal, ['Si', 'Ge'])
    """
    if isinstance(species, str):
        species = [species]

    return [i for i, spec in enumerate(structure.species) if spec in species]


def select_by_indices(
    structure: Union[Crystal, Molecule], indices: Union[int, List[int]]
) -> List[int]:
    """
    Select atom indices (validation and normalization).

    Args:
        structure: Crystal or Molecule to select from
        indices: Atom index or list of indices

    Returns:
        List of valid atom indices

    Raises:
        IndexError: If any index is out of range

    Examples:
        >>> indices = select_by_indices(crystal, 0)
        >>> indices = select_by_indices(crystal, [0, 1, 2])
    """
    if isinstance(indices, int):
        indices = [indices]

    # Validate indices
    max_idx = len(structure) - 1
    for idx in indices:
        if not (0 <= idx <= max_idx):
            raise IndexError(f"Atom index {idx} is out of range [0, {max_idx}]")

    return list(indices)


def select_by_position(
    structure: Union[Crystal, Molecule],
    center: List[float],
    radius: float,
    use_cartesian: bool = True,
) -> List[int]:
    """
    Select atoms within a radius of a center point.

    Args:
        structure: Crystal or Molecule to select from
        center: Center point [x, y, z] in Angstroms
        radius: Selection radius in Angstroms
        use_cartesian: If True, use Cartesian coordinates (default).
                      If False, use fractional coordinates (Crystal only)

    Returns:
        List of atom indices within the radius

    Examples:
        >>> # Select atoms within 5 Å of origin
        >>> indices = select_by_position(crystal, [0, 0, 0], 5.0)
        >>> # Select atoms within 2 Å of a point
        >>> indices = select_by_position(molecule, [1, 1, 1], 2.0)
    """
    center = np.array(center, dtype=np.float64)

    if use_cartesian:
        if isinstance(structure, Crystal):
            positions = structure.cart_positions
        else:
            positions = structure.positions
    else:
        if isinstance(structure, Molecule):
            raise ValueError("Fractional coordinates not available for Molecule")
        positions = structure.frac_positions

    # Calculate distances
    distances = np.linalg.norm(positions - center, axis=1)

    # Select atoms within radius
    return np.where(distances <= radius)[0].tolist()


def select_by_box(
    structure: Union[Crystal, Molecule],
    min_coords: List[float],
    max_coords: List[float],
    use_cartesian: bool = True,
) -> List[int]:
    """
    Select atoms within a rectangular box.

    Args:
        structure: Crystal or Molecule to select from
        min_coords: Minimum coordinates [x_min, y_min, z_min]
        max_coords: Maximum coordinates [x_max, y_max, z_max]
        use_cartesian: If True, use Cartesian coordinates (default).
                      If False, use fractional coordinates (Crystal only)

    Returns:
        List of atom indices within the box

    Examples:
        >>> # Select atoms in a box
        >>> indices = select_by_box(crystal, [0, 0, 0], [5, 5, 5])
    """
    min_coords = np.array(min_coords, dtype=np.float64)
    max_coords = np.array(max_coords, dtype=np.float64)

    if use_cartesian:
        if isinstance(structure, Crystal):
            positions = structure.cart_positions
        else:
            positions = structure.positions
    else:
        if isinstance(structure, Molecule):
            raise ValueError("Fractional coordinates not available for Molecule")
        positions = structure.frac_positions

    # Select atoms within box
    mask = np.all((positions >= min_coords) & (positions <= max_coords), axis=1)
    return np.where(mask)[0].tolist()


def select_by_property(
    structure: Union[Crystal, Molecule],
    property_key: str,
    value: Union[any, List[any]] = None,
    condition: Optional[Callable] = None,
) -> List[int]:
    """
    Select atoms by site properties.

    Args:
        structure: Crystal or Molecule to select from
        property_key: Property key to check
        value: If provided, select atoms where property equals this value.
               If None, select atoms that have this property (any value).
        condition: Optional callable that takes property value and returns bool.
                  If provided, overrides value matching.

    Returns:
        List of atom indices matching the property condition

    Examples:
        >>> # Select atoms with charge property
        >>> indices = select_by_property(crystal, 'charge')
        >>> # Select atoms with charge == -2
        >>> indices = select_by_property(crystal, 'charge', value=-2)
        >>> # Select atoms with charge > 0
        >>> indices = select_by_property(crystal, 'charge', condition=lambda x: x > 0)
    """
    if not hasattr(structure, "site_properties"):
        return []

    site_properties = structure.site_properties
    if not site_properties:
        return []

    indices = []
    for i, props in enumerate(site_properties):
        if props and property_key in props:
            prop_value = props[property_key]

            if condition is not None:
                if condition(prop_value):
                    indices.append(i)
            elif value is not None:
                if isinstance(value, list):
                    if prop_value in value:
                        indices.append(i)
                else:
                    if prop_value == value:
                        indices.append(i)
            else:
                # Just check if property exists
                indices.append(i)

    return indices


def select_by_custom(
    structure: Union[Crystal, Molecule], condition: Callable[[int], bool]
) -> List[int]:
    """
    Select atoms using a custom condition function.

    Args:
        structure: Crystal or Molecule to select from
        condition: Function that takes atom index and returns bool

    Returns:
        List of atom indices where condition returns True

    Examples:
        >>> # Select every other atom
        >>> indices = select_by_custom(crystal, lambda i: i % 2 == 0)
        >>> # Select atoms with even indices
        >>> indices = select_by_custom(crystal, lambda i: i % 2 == 0)
    """
    return [i for i in range(len(structure)) if condition(i)]


def combine_selections(
    indices_list: List[List[int]], operation: str = "union"
) -> List[int]:
    """
    Combine multiple selection results using set operations.

    Args:
        indices_list: List of index lists to combine
        operation: 'union' (OR), 'intersection' (AND), or 'difference' (subtract)

    Returns:
        Combined list of indices

    Examples:
        >>> si_indices = select_by_species(crystal, 'Si')
        >>> surface_indices = select_by_position(crystal, [0, 0, 0], 5.0)
        >>> # Combine: Si atoms OR surface atoms
        >>> combined = combine_selections([si_indices, surface_indices], 'union')
        >>> # Combine: Si atoms AND surface atoms
        >>> combined = combine_selections([si_indices, surface_indices], 'intersection')
    """
    if not indices_list:
        return []

    if len(indices_list) == 1:
        return indices_list[0]

    # Convert to sets for efficient operations
    sets = [set(indices) for indices in indices_list]

    if operation == "union" or operation == "or":
        result = set()
        for s in sets:
            result |= s
        return sorted(list(result))

    elif operation == "intersection" or operation == "and":
        result = sets[0]
        for s in sets[1:]:
            result &= s
        return sorted(list(result))

    elif operation == "difference" or operation == "subtract":
        result = sets[0]
        for s in sets[1:]:
            result -= s
        return sorted(list(result))

    else:
        raise ValueError(
            f"Unknown operation: {operation}. Use 'union', 'intersection', or 'difference'"
        )


def select_all(structure: Union[Crystal, Molecule]) -> List[int]:
    """
    Select all atoms in the structure.

    Args:
        structure: Crystal or Molecule to select from

    Returns:
        List of all atom indices

    Examples:
        >>> indices = select_all(crystal)
    """
    return list(range(len(structure)))


def select_none(structure: Union[Crystal, Molecule]) -> List[int]:
    """
    Select no atoms (empty selection).

    Useful for building complex selections or as a starting point.

    Args:
        structure: Crystal or Molecule (unused, for API consistency)

    Returns:
        Empty list

    Examples:
        >>> indices = select_none(crystal)
    """
    return []


class AtomSelection:
    """
    Fluent API for atom selection.

    Provides a chainable interface for building complex atom selections.
    Can be used directly in substitution and other operations.

    Examples:
        >>> # Basic usage
        >>> sel = AtomSelection(crystal).by_species('Si')
        >>> crystal.substitute(sel, 'Ge')

        >>> # Chaining multiple criteria
        >>> sel = AtomSelection(crystal).by_species('Si').near([0,0,0], 5.0)
        >>> crystal.substitute(sel, 'Ge')

        >>> # Using with combine operations
        >>> sel1 = AtomSelection(crystal).by_species('Si')
        >>> sel2 = AtomSelection(crystal).near([0,0,0], 5.0)
        >>> combined = sel1 & sel2  # Intersection
        >>> crystal.substitute(combined, 'Ge')
    """

    def __init__(
        self, structure: Union[Crystal, Molecule], indices: Optional[List[int]] = None
    ):
        """
        Initialize AtomSelection.

        Args:
            structure: Crystal or Molecule to select from
            indices: Optional initial list of indices. If None, starts with all atoms.
        """
        self.structure = structure
        if indices is None:
            self._indices = set(range(len(structure)))
        else:
            self._indices = set(indices)

    @property
    def indices(self) -> List[int]:
        """Get the selected atom indices as a sorted list."""
        return sorted(list(self._indices))

    def by_species(self, species: Union[str, List[str]]) -> "AtomSelection":
        """
        Filter selection by species.

        Args:
            species: Species symbol or list of species symbols

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).by_species('Si')
            >>> sel = AtomSelection(crystal).by_species(['Si', 'Ge'])
        """
        selected = select_by_species(self.structure, species)
        self._indices &= set(selected)
        return self

    def by_indices(self, indices: Union[int, List[int]]) -> "AtomSelection":
        """
        Filter selection by specific indices.

        Args:
            indices: Atom index or list of indices

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).by_indices([0, 1, 2])
        """
        selected = select_by_indices(self.structure, indices)
        self._indices &= set(selected)
        return self

    def near(
        self, center: List[float], radius: float, use_cartesian: bool = True
    ) -> "AtomSelection":
        """
        Filter selection by position (within radius).

        Args:
            center: Center point [x, y, z]
            radius: Selection radius in Angstroms
            use_cartesian: If True, use Cartesian coordinates (default)

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).near([0, 0, 0], 5.0)
        """
        selected = select_by_position(self.structure, center, radius, use_cartesian)
        self._indices &= set(selected)
        return self

    def in_box(
        self,
        min_coords: List[float],
        max_coords: List[float],
        use_cartesian: bool = True,
    ) -> "AtomSelection":
        """
        Filter selection by box.

        Args:
            min_coords: Minimum coordinates [x_min, y_min, z_min]
            max_coords: Maximum coordinates [x_max, y_max, z_max]
            use_cartesian: If True, use Cartesian coordinates (default)

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).in_box([0, 0, 0], [5, 5, 5])
        """
        selected = select_by_box(self.structure, min_coords, max_coords, use_cartesian)
        self._indices &= set(selected)
        return self

    def by_property(
        self,
        property_key: str,
        value: Optional[any] = None,
        condition: Optional[Callable] = None,
    ) -> "AtomSelection":
        """
        Filter selection by site properties.

        Args:
            property_key: Property key to check
            value: Optional value to match
            condition: Optional callable for custom condition

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).by_property('charge')
            >>> sel = AtomSelection(crystal).by_property('charge', value=-2)
            >>> sel = AtomSelection(crystal).by_property('charge', condition=lambda x: x > 0)
        """
        selected = select_by_property(self.structure, property_key, value, condition)
        self._indices &= set(selected)
        return self

    def by_custom(self, condition: Callable[[int], bool]) -> "AtomSelection":
        """
        Filter selection using custom condition.

        Args:
            condition: Function that takes atom index and returns bool

        Returns:
            New AtomSelection with filtered indices

        Examples:
            >>> sel = AtomSelection(crystal).by_custom(lambda i: i % 2 == 0)
        """
        selected = select_by_custom(self.structure, condition)
        self._indices &= set(selected)
        return self

    def __and__(self, other: "AtomSelection") -> "AtomSelection":
        """
        Intersection: self & other (AND operation).

        Args:
            other: Another AtomSelection

        Returns:
            New AtomSelection with intersection of indices

        Examples:
            >>> sel1 = AtomSelection(crystal).by_species('Si')
            >>> sel2 = AtomSelection(crystal).near([0,0,0], 5.0)
            >>> combined = sel1 & sel2  # Si atoms AND near origin
        """
        if self.structure is not other.structure:
            raise ValueError("Cannot combine selections from different structures")
        return AtomSelection(self.structure, list(self._indices & other._indices))

    def __or__(self, other: "AtomSelection") -> "AtomSelection":
        """
        Union: self | other (OR operation).

        Args:
            other: Another AtomSelection

        Returns:
            New AtomSelection with union of indices

        Examples:
            >>> sel1 = AtomSelection(crystal).by_species('Si')
            >>> sel2 = AtomSelection(crystal).by_species('Ge')
            >>> combined = sel1 | sel2  # Si atoms OR Ge atoms
        """
        if self.structure is not other.structure:
            raise ValueError("Cannot combine selections from different structures")
        return AtomSelection(self.structure, list(self._indices | other._indices))

    def __sub__(self, other: "AtomSelection") -> "AtomSelection":
        """
        Difference: self - other (subtract operation).

        Args:
            other: Another AtomSelection

        Returns:
            New AtomSelection with difference of indices

        Examples:
            >>> sel1 = AtomSelection(crystal).by_species('Si')
            >>> sel2 = AtomSelection(crystal).near([0,0,0], 5.0)
            >>> combined = sel1 - sel2  # Si atoms NOT near origin
        """
        if self.structure is not other.structure:
            raise ValueError("Cannot combine selections from different structures")
        return AtomSelection(self.structure, list(self._indices - other._indices))

    def __len__(self) -> int:
        """Return the number of selected atoms."""
        return len(self._indices)

    def __bool__(self) -> bool:
        """Return True if any atoms are selected."""
        return len(self._indices) > 0

    def __iter__(self):
        """Iterate over selected indices."""
        return iter(sorted(self._indices))

    def __repr__(self) -> str:
        """String representation."""
        return f"AtomSelection({len(self._indices)} atoms from {self.structure.__class__.__name__})"


__all__ = [
    "select_by_species",
    "select_by_indices",
    "select_by_position",
    "select_by_box",
    "select_by_property",
    "select_by_custom",
    "combine_selections",
    "select_all",
    "select_none",
    "AtomSelection",
]
