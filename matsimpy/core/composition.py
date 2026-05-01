"""
Composition module for MatSimPy.

This module provides the Composition class for representing and manipulating
chemical compositions. It supports formula parsing, mass calculations, and
various output formats (HTML, LaTeX).

The Composition class is designed to be efficient with caching for frequently
accessed properties like atomic mass calculations.

Example:
    >>> from matsimpy.core.composition import Composition
    >>> comp = Composition('H2O')
    >>> print(comp.formula)
    H2O
    >>> print(comp.mass)
    18.01528
    >>> print(comp['H'])
    2
    >>> print(comp.mass_fractions())
    {'H': 0.111898..., 'O': 0.888102...}
"""

import re
import json
import math
import functools
import types
from collections import Counter
from typing import Optional, Dict, List, Tuple, Any, Mapping
from monty.json import MSONable
from .periodic_table import Element, ELEMENTS, DUMMY_ELEMENTS

# Valid element symbols: all real elements plus recognised dummy symbols ("X").
_VALID_ELEMENTS: frozenset = frozenset(ELEMENTS) | frozenset(DUMMY_ELEMENTS)

@functools.lru_cache(maxsize=256)
def _get_element_cached(symbol: str) -> Element:
    return Element.get_element(symbol)


class Composition(MSONable):
    """
    Chemical composition with formula parsing and property calculation.

    Parses chemical formulas and provides access to elemental composition,
    mass calculations, and formatted output (HTML, LaTeX).

    Args:
        formula: Chemical formula string (e.g., 'H2O', 'Fe2O3', 'Ca(OH)2').
        sort_by: Sorting method - None (original order), 'alphabet', or 'element'
                Default is None to preserve input formula order.

    Attributes:
        formula: Normalized chemical formula string.
        composition: Counter of element symbols to counts.

    Raises:
        ValueError: If formula is empty or has invalid format.

    Examples:
        >>> c = Composition('H2O')
        >>> c.formula
        'H2O'
        >>> c.composition
        Counter({'H': 2, 'O': 1})
        >>> c['H']
        2
        >>> c.mass
        18.01528
    """

    def __init__(self, formula: str, sort_by: Optional[str] = None):
        """
        Initialize Composition from chemical formula.

        Args:
            formula: Chemical formula string.
            sort_by: Sorting method - None (preserve original order), 'alphabet', or 'element'.
                    Default is None to preserve input formula order.

        Raises:
            ValueError: If formula is empty or invalid.
        """
        # Parse and validate formula, tracking element order
        self._composition, self._element_order = self._parse_formula(formula)
        self._input_formula = formula
        self._sort_by = sort_by
        self.formula = self._chemical_formula(sort_by=sort_by)

        # Cache for mass calculation
        self._cached_mass: Optional[float] = None

    @property
    def composition(self) -> Mapping[str, int]:
        """
        Element counts as an immutable mapping.

        Notes:
            This class is designed as an immutable value object. To prevent external
            mutation from invalidating internal caches (e.g. ``mass``), this property
            returns a read-only mapping view.

        If you need a mutable object for downstream APIs, use :meth:`as_counter`.
        """
        return types.MappingProxyType(dict(self._composition))

    def as_counter(self) -> Counter:
        """Return a mutable Counter copy of the element counts."""
        return Counter(self._composition)

    def _chemical_formula(self, sort_by: Optional[str] = None) -> str:
        """
        Generate chemical formula string from composition.

        Args:
            sort_by: Sorting method - None (preserve original order), 'alphabet', or 'element'.

        Returns:
            Formatted chemical formula string.

        Raises:
            ValueError: If sort_by is invalid.
        """
        element_counts = self._composition
        if sort_by is None:
            # Preserve original order from input formula
            # Use tracked order, then add any elements not in order
            seen = set()
            elements = []
            for element in self._element_order:
                if element in element_counts and element not in seen:
                    elements.append((element, element_counts[element]))
                    seen.add(element)
            for element, count in element_counts.items():
                if element not in seen:
                    elements.append((element, count))
        else:
            elements = self._get_sorted_element_counts(element_counts, sort_by)

        formula = "".join(
            [f'{element}{count if count > 1 else ""}' for element, count in elements]
        )
        return formula

    @staticmethod
    def _get_sorted_element_counts(
        element_counts: Dict[str, int], sort_by: Optional[str] = None
    ) -> List[Tuple[str, int]]:
        """
        Get sorted element counts.

        Helper method to eliminate code duplication in sorting logic.

        Args:
            element_counts: Dictionary mapping elements to counts.
            sort_by: Sorting method - None (original order), 'alphabet', or 'element'.

        Returns:
            List of (element, count) tuples (sorted or in original order).

        Raises:
            ValueError: If sort_by is not None, 'alphabet', or 'element'.
        """
        if sort_by is None:
            return list(element_counts.items())
        elif sort_by == "alphabet":
            return sorted(element_counts.items(), key=lambda x: x[0])
        elif sort_by == "element":
            return sorted(
                element_counts.items(),
                key=lambda x: Element.get_element(x[0]).atomic_no,
            )
        else:
            raise ValueError(
                f"sort_by must be None, 'alphabet', or 'element', got '{sort_by}'"
            )

    def _parse_formula(self, formula: str) -> Tuple[Counter, List[str]]:
        """
        Parse chemical formula into element counts, preserving element order.

        Supports nested grouping with parentheses and brackets, e.g. Ca(OH)2
        and K4[ON(SO3)2]2.

        Args:
            formula: Chemical formula string.

        Returns:
            Tuple of (Counter mapping element symbols to counts, list of elements in order).

        Raises:
            ValueError: If formula is empty or has invalid format.

        Examples:
            >>> c = Composition('H2O')
            >>> comp, order = c._parse_formula('H2O')
            >>> comp
            Counter({'H': 2, 'O': 1})
            >>> order
            ['H', 'O']
        """
        # Validate formula
        if not formula or not formula.strip():
            raise ValueError("Formula cannot be empty")

        # Basic format validation
        if not re.match(r"^[A-Za-z0-9()\[\]]+$", formula):
            raise ValueError(
                f"Invalid formula format: '{formula}'. "
                f"Formula must contain only letters, numbers, and grouping symbols ()[]."
            )

        opener_to_closer = {"(": ")", "[": "]"}
        closer_to_opener = {")": "(", "]": "["}

        def parse_int_at(idx: int) -> Tuple[int, int]:
            start = idx
            while idx < len(formula) and formula[idx].isdigit():
                idx += 1
            if idx == start:
                return 1, idx
            return int(formula[start:idx]), idx

        def parse_element_at(idx: int) -> Tuple[str, int]:
            if idx >= len(formula) or not formula[idx].isalpha() or not formula[idx].isupper():
                raise ValueError(f"Invalid element start at position {idx} in '{formula}'")
            j = idx + 1
            while j < len(formula) and formula[j].isalpha() and formula[j].islower():
                j += 1
            symbol = formula[idx:j]
            if symbol not in _VALID_ELEMENTS:
                raise ValueError(
                    f"Unknown element symbol '{symbol}' in formula '{formula}'. "
                    f"Formula must contain only valid element symbols."
                )
            return symbol, j

        stack: List[Counter] = [Counter()]
        group_stack: List[str] = []
        element_order: List[str] = []

        i = 0
        while i < len(formula):
            ch = formula[i]
            if ch in opener_to_closer:
                group_stack.append(ch)
                stack.append(Counter())
                i += 1
                continue

            if ch in closer_to_opener:
                if not group_stack or group_stack[-1] != closer_to_opener[ch]:
                    raise ValueError(f"Mismatched grouping at position {i} in '{formula}'")
                group_stack.pop()
                group_counts = stack.pop()
                i += 1
                multiplier, i = parse_int_at(i)
                for sym, cnt in group_counts.items():
                    stack[-1][sym] += cnt * multiplier
                continue

            if ch.isdigit():
                raise ValueError(f"Unexpected number at position {i} in '{formula}'")

            # Element
            symbol, i = parse_element_at(i)
            count, i = parse_int_at(i)
            stack[-1][symbol] += count
            if symbol not in element_order:
                element_order.append(symbol)

        if group_stack:
            raise ValueError(f"Unbalanced grouping in formula '{formula}'")

        composition = stack[0]
        if not composition:
            raise ValueError("No valid elements found in formula")

        return composition, element_order

    def __getitem__(self, element: str) -> int:
        """
        Get count of specified element.

        Args:
            element: Element symbol.

        Returns:
            Count of element in composition (0 if not present).

        Examples:
            >>> c = Composition('H2O')
            >>> c['H']
            2
            >>> c['C']
            0
        """
        return self._composition[element]

    def get(self, element: str, default: int = 0) -> int:
        """Get element count with an explicit default."""
        return int(self._composition.get(element, default))

    def require(self, element: str) -> int:
        """Get element count, raising KeyError if element is absent."""
        if element not in self._composition:
            raise KeyError(element)
        return int(self._composition[element])

    @property
    def canonical_formula(self) -> str:
        """Canonical formula independent of input ordering (atomic number order)."""
        return self._chemical_formula(sort_by="element")

    @property
    def reduced_formula(self) -> str:
        """
        Formula with element counts divided by their greatest common divisor.

        Returns the formula with each element count divided by the GCD of all
        counts. Element ordering is preserved from the current formula.

        Returns:
            str: Reduced chemical formula.

        Examples:
            >>> Composition('H4O2').reduced_formula
            'H2O'
            >>> Composition('Fe2O3').reduced_formula
            'Fe2O3'
            >>> Composition('C6H12O6').reduced_formula
            'CH2O'
        """
        counts = list(self._composition.values())
        gcd = counts[0]
        for c in counts[1:]:
            gcd = math.gcd(gcd, c)
        if gcd <= 1:
            return self.formula
        # Build formula preserving current element ordering
        seen = set()
        parts = []
        for element in self._element_order:
            if element in self._composition and element not in seen:
                reduced_count = self._composition[element] // gcd
                parts.append(f"{element}{reduced_count if reduced_count > 1 else ''}")
                seen.add(element)
        for element in self._composition:
            if element not in seen:
                reduced_count = self._composition[element] // gcd
                parts.append(f"{element}{reduced_count if reduced_count > 1 else ''}")
                seen.add(element)
        return "".join(parts)

    @property
    def anonymous_formula(self) -> str:
        """
        Formula with element symbols replaced by A, B, C... in atomic number order.

        Elements are sorted by atomic number ascending, then assigned labels
        A, B, C, ... following pymatgen convention.

        Returns:
            str: Anonymized chemical formula.

        Examples:
            >>> Composition('Fe2O3').anonymous_formula
            'A2B3'
            >>> Composition('CaTiO3').anonymous_formula
            'A3BC'
            >>> Composition('NaCl').anonymous_formula
            'AB'
        """
        import string

        # Sort by atomic number ascending
        sorted_elements = sorted(
            self._composition.items(),
            key=lambda x: Element.get_element(x[0]).atomic_no,
        )
        # Assign labels A, B, C, ...
        labels = {}
        for i, (element, _) in enumerate(sorted_elements):
            labels[element] = string.ascii_uppercase[i]

        # Build formula in sorted (atomic number) order
        parts = []
        for element, count in sorted_elements:
            label = labels[element]
            parts.append(f"{label}{count if count > 1 else ''}")
        return "".join(parts)

    def __str__(self) -> str:
        """
        String representation of the composition.

        Returns:
            str: The chemical formula string.

        Example:
            >>> c = Composition('H2O')
            >>> str(c)
            'H2O'
        """
        return self.formula

    def __repr__(self) -> str:
        """
        Unambiguous representation for debugging.

        Returns:
            str: A string that can be used to recreate the Composition object.

        Example:
            >>> c = Composition('H2O')
            >>> repr(c)
            "Composition('H2O')"
        """
        return f"Composition('{self.formula}')"

    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another Composition.

        Two compositions are equal if they have the same element counts,
        regardless of formula string representation.

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if compositions are equal, False otherwise.

        Example:
            >>> c1 = Composition('H2O')
            >>> c2 = Composition('H2O')
            >>> c3 = Composition('OH2')
            >>> c1 == c2
            True
            >>> c1 == c3
            True  # Same composition, different formula string
            >>> c1 == 'H2O'
            False
        """
        if isinstance(other, Composition):
            return self.composition == other.composition
        return False

    def __hash__(self) -> int:
        """
        Hash based on element counts, consistent with __eq__.

        Two Composition objects that compare equal (same element counts) will
        always have the same hash, satisfying the Python hash contract.

        Returns:
            int: Hash value for use in sets and as dict keys.

        Example:
            >>> c1 = Composition('H2O')
            >>> c2 = Composition('OH2')
            >>> c1 == c2
            True
            >>> hash(c1) == hash(c2)
            True
        """
        return hash(frozenset(self.composition.items()))

    def __add__(self, other: "Composition") -> "Composition":
        """
        Add two Composition objects together.

        Combines the element counts from both compositions.

        Args:
            other: Another Composition object to add.

        Returns:
            New Composition with combined element counts.

        Examples:
            >>> c1 = Composition('H2O')
            >>> c2 = Composition('CO2')
            >>> c3 = c1 + c2
            >>> c3.composition
            Counter({'H': 2, 'O': 3, 'C': 1})
            >>> c3.formula
            'CH2O3'
        """
        if not isinstance(other, Composition):
            return NotImplemented

        # Combine the Counters
        combined = Counter(self.composition)
        combined.update(other.composition)

        # Build formula string from combined composition
        # Preserve order: first from self, then new elements from other
        seen = set()
        formula_parts = []

        # Add elements from self first
        for element, count in self.composition.items():
            new_count = combined[element]
            formula_parts.append(f'{element}{new_count if new_count > 1 else ""}')
            seen.add(element)

        # Add elements from other that aren't in self
        for element, count in other.composition.items():
            if element not in seen:
                new_count = combined[element]
                formula_parts.append(f'{element}{new_count if new_count > 1 else ""}')

        formula_str = "".join(formula_parts)

        # Create new Composition from the combined formula
        return Composition(formula_str, sort_by=None)

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation for serialization.

        Implements the MSONable interface for JSON serialization.
        The dictionary includes module and class information for proper
        deserialization.

        Returns:
            Dict[str, Any]: Dictionary containing:
                - @module: Module path of the class
                - @class: Class name
                - formula: Chemical formula string

        Example:
            >>> c = Composition('H2O')
            >>> d = c.as_dict()
            >>> d['formula']
            'H2O'
            >>> d['@class']
            'Composition'
        """
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "formula": self.formula,
            "sort_by": self._sort_by,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Composition":
        """
        Create Composition from dictionary representation.

        Implements the MSONable interface for JSON deserialization.
        Restores a Composition object from its dictionary representation.

        Args:
            d: Dictionary containing 'formula' key and optionally
               '@module' and '@class' keys.

        Returns:
            Composition: A new Composition instance.

        Raises:
            KeyError: If 'formula' key is missing from dictionary.

        Example:
            >>> d = {'@module': 'matsimpy.core.composition', '@class': 'Composition', 'formula': 'H2O'}
            >>> c = Composition.from_dict(d)
            >>> c.formula
            'H2O'
        """
        formula = d["formula"]
        sort_by = d.get("sort_by", None)
        return cls(formula=formula, sort_by=sort_by)

    def to_json(self) -> str:
        """
        Convert to JSON string representation.

        Serializes the Composition to a JSON string using the dictionary
        representation from as_dict().

        Returns:
            str: JSON string representation of the composition.

        Example:
            >>> c = Composition('H2O')
            >>> json_str = c.to_json()
            >>> 'H2O' in json_str
            True
        """
        return json.dumps(self.as_dict())

    @classmethod
    def from_json(cls, json_string: str) -> "Composition":
        """
        Create Composition from JSON string.

        Deserializes a Composition object from a JSON string representation.

        Args:
            json_string: JSON string containing composition data.

        Returns:
            Composition: A new Composition instance.

        Raises:
            json.JSONDecodeError: If json_string is not valid JSON.
            KeyError: If required keys are missing from the JSON data.

        Example:
            >>> c = Composition('H2O')
            >>> json_str = c.to_json()
            >>> c2 = Composition.from_json(json_str)
            >>> c2.formula
            'H2O'
            >>> c == c2
            True
        """
        return cls.from_dict(json.loads(json_string))

    @property
    def mass(self) -> float:
        """
        Calculate molecular/formula mass with caching.

        Uses cached Element instances for performance. Mass is cached after
        first calculation.

        Returns:
            Total mass in atomic mass units (amu).

        Examples:
            >>> c = Composition('H2O')
            >>> c.mass
            18.01528
            >>> c = Composition('Fe2O3')
            >>> c.mass
            159.6882
        """
        if self._cached_mass is not None:
            return self._cached_mass

        mass = 0.0
        for element, count in self._composition.items():
            elem = _get_element_cached(element)
            mass += elem.atomic_mass * count

        self._cached_mass = mass
        return mass

    def mass_fractions(self) -> Dict[str, float]:
        """
        Calculate mass fractions of each element.

        Mass fraction is the fraction of total mass contributed by each element (0-1).

        Returns:
            Dictionary mapping elements to mass fractions.

        Examples:
            >>> c = Composition('H2O')
            >>> fractions = c.mass_fractions()
            >>> fractions['H']  # ~0.112
            0.111898...
            >>> fractions['O']  # ~0.888
            0.888102...
            >>> sum(fractions.values())  # Should be 1.0
            1.0
        """
        total_mass = self.mass
        fractions = {}

        for element, count in self._composition.items():
            elem = _get_element_cached(element)
            mass_fraction = elem.atomic_mass * count / total_mass
            fractions[element] = mass_fraction

        return fractions

    def mole_fractions(self) -> Dict[str, float]:
        """
        Calculate mole fractions of each element.

        Mole fraction is the number of atoms of each element divided by the total
        number of atoms in the composition. This represents the fraction of atoms
        (or moles) contributed by each element.

        Returns:
            Dictionary mapping elements to mole fractions (0-1).

        Examples:
            >>> c = Composition('H2O')
            >>> fractions = c.mole_fractions()
            >>> fractions['H']  # 2/3 ≈ 0.667
            0.666666...
            >>> fractions['O']  # 1/3 ≈ 0.333
            0.333333...
            >>> sum(fractions.values())  # Should be 1.0
            1.0
            >>> c = Composition('Fe2O3')
            >>> fractions = c.mole_fractions()
            >>> fractions['Fe']  # 2/5 = 0.4
            0.4
            >>> fractions['O']  # 3/5 = 0.6
            0.6
        """
        total_atoms = sum(self._composition.values())
        if total_atoms == 0:
            return {}

        fractions = {}
        for element, count in self._composition.items():
            fractions[element] = count / total_atoms

        return fractions

    def to_html(self, sort_by: str = "alphabet") -> str:
        """
        Convert formula to HTML with subscript formatting.

        Args:
            sort_by: Sorting method - 'alphabet' (default) or 'element'.

        Returns:
            HTML string with subscripts.

        Raises:
            ValueError: If sort_by is invalid.

        Examples:
            >>> c = Composition('Fe2O3')
            >>> c.to_html()
            'Fe<sub>2</sub>O<sub>3</sub>'
            >>> c.to_html(sort_by='element')
            'Fe<sub>2</sub>O<sub>3</sub>'
        """
        return self._format_formula(
            sort_by=sort_by,
            subscript=lambda n: f"<sub>{n}</sub>",
            joiner="",
        )

    def to_latex(self, sort_by: str = "alphabet") -> str:
        """
        Convert formula to LaTeX with subscript formatting.

        Args:
            sort_by: Sorting method - 'alphabet' (default) or 'element'.

        Returns:
            LaTeX string with subscripts.

        Raises:
            ValueError: If sort_by is invalid.

        Examples:
            >>> c = Composition('Fe2O3')
            >>> c.to_latex()
            'Fe$_2$O$_3$'
            >>> c.to_latex(sort_by='element')
            'Fe$_2$O$_3$'
        """
        return self._format_formula(
            sort_by=sort_by,
            subscript=lambda n: f"$_{{{n}}}$",
            joiner="",
        )

    def _format_formula(
        self, sort_by: str, subscript, joiner: str = ""
    ) -> str:
        sorted_elements = self._get_sorted_element_counts(self._composition, sort_by)
        parts: List[str] = []
        for element, count in sorted_elements:
            parts.append(element)
            if count > 1:
                parts.append(subscript(count))
        return joiner.join(parts)
