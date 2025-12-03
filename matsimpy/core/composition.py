import re
import json
from collections import Counter
from typing import Optional, Dict, List, Tuple, Any
from monty.json import MSONable
from .periodic_table import Element


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
        # Initialize element cache for performance
        self._element_cache: Dict[str, Element] = {}

        # Parse and validate formula, tracking element order
        self.composition, self._element_order = self._parse_formula(formula)
        self.formula = self._chemical_formula(sort_by=sort_by)

        # Cache for mass calculation
        self._cached_mass: Optional[float] = None

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
        element_counts = self.composition
        if sort_by is None:
            # Preserve original order from input formula
            if hasattr(self, "_element_order"):
                # Use tracked order, then add any elements not in order (from parentheses)
                seen = set()
                elements = []
                for element in self._element_order:
                    if element in element_counts:
                        elements.append((element, element_counts[element]))
                        seen.add(element)
                # Add any remaining elements (from parentheses) in Counter order
                for element, count in element_counts.items():
                    if element not in seen:
                        elements.append((element, count))
            else:
                # Fallback: use Counter order
                elements = list(element_counts.items())
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

        Supports formulas with parentheses, e.g., Ca(OH)2.

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
        if not re.match(r"^[A-Za-z0-9()]+$", formula):
            raise ValueError(
                f"Invalid formula format: '{formula}'. "
                f"Formula must contain only letters, numbers, and parentheses."
            )

        def parse_subformula(sub_formula, count, track_order=True):
            """Parse a subformula and add to composition."""
            sub_counts = re.findall(element_pattern, sub_formula)
            for element, sub_count in sub_counts:
                composition[element] += (int(sub_count) if sub_count else 1) * count
                if track_order and element not in element_order:
                    element_order.append(element)

        element_pattern = r"([A-Z][a-z]*)(\d*)"
        group_pattern = r"\(([^\)]+)\)(\d*)"

        composition = Counter()
        element_order = []  # Track order of elements as they appear

        # Store original formula for order tracking
        original_formula = formula

        # Parse groups (parentheses) - elements in groups don't affect main order
        groups = re.findall(group_pattern, formula)
        for group, count in groups:
            parse_subformula(group, int(count) if count else 1, track_order=False)
            formula = formula.replace(f"({group}){count}", "")

        # Parse remaining formula - this determines the main order
        parse_subformula(formula, 1, track_order=True)

        # Validate that we got some elements
        if not composition:
            raise ValueError("No valid elements found in formula")

        return composition, element_order

    def _get_cached_element(self, symbol: str) -> Element:
        """
        Get Element instance with caching for performance.

        Args:
            symbol: Element symbol.

        Returns:
            Element instance (cached).
        """
        if symbol not in self._element_cache:
            self._element_cache[symbol] = Element.get_element(symbol)
        return self._element_cache[symbol]

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
        return self.composition[element]

    def __str__(self) -> str:
        """String representation (returns formula)."""
        return self.formula

    def __repr__(self) -> str:
        """Unambiguous representation for debugging."""
        return f"Composition('{self.formula}')"

    def __eq__(self, other) -> bool:
        """
        Check equality with another Composition.

        Args:
            other: Another Composition object.

        Returns:
            True if compositions are equal.
        """
        if isinstance(other, Composition):
            return self.composition == other.composition
        return False

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
        Convert to dictionary representation.

        Returns:
            Dictionary with module, class, and formula.
        """
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "formula": self.formula,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Composition":
        """
        Create Composition from dictionary.

        Args:
            d: Dictionary with 'formula' key.

        Returns:
            Composition instance.
        """
        formula = d["formula"]
        # Preserve original order by default
        return cls(formula=formula, sort_by=None)

    def to_json(self) -> str:
        """
        Convert to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.as_dict())

    @classmethod
    def from_json(cls, json_string: str) -> "Composition":
        """
        Create Composition from JSON string.

        Args:
            json_string: JSON string.

        Returns:
            Composition instance.
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
        for element, count in self.composition.items():
            elem = self._get_cached_element(element)
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

        for element, count in self.composition.items():
            elem = self._get_cached_element(element)
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
        total_atoms = sum(self.composition.values())
        if total_atoms == 0:
            return {}

        fractions = {}
        for element, count in self.composition.items():
            fractions[element] = count / total_atoms

        return fractions

    def to_html(self, sort_by: Optional[str] = None) -> str:
        """
        Convert formula to HTML with subscript formatting.

        Args:
            sort_by: Sorting method - 'alphabet' or 'element'.
                    If None, uses 'alphabet'.

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
        if sort_by is None:
            sort_by = "alphabet"

        sorted_elements = self._get_sorted_element_counts(self.composition, sort_by)

        html_parts = []
        for element, count in sorted_elements:
            html_parts.append(element)
            if count > 1:
                html_parts.append(f"<sub>{count}</sub>")

        return "".join(html_parts)

    def to_latex(self, sort_by: Optional[str] = None) -> str:
        """
        Convert formula to LaTeX with subscript formatting.

        Args:
            sort_by: Sorting method - 'alphabet' or 'element'.
                    If None, uses 'alphabet'.

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
        if sort_by is None:
            sort_by = "alphabet"

        sorted_elements = self._get_sorted_element_counts(self.composition, sort_by)

        latex_parts = []
        for element, count in sorted_elements:
            latex_parts.append(element)
            if count > 1:
                latex_parts.append(f"$_{{{count}}}$")

        return "".join(latex_parts)
