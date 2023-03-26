import re
import re
from collections import Counter

class Composition:
    """
    A class representing the composition of a chemical formula.

    Args:
        formula (str): A string representing the chemical formula.

    Attributes:
        formula (str): The chemical formula.
        composition (collections.Counter): A Counter object representing the composition of the formula.

    Examples:
        >>> c = Composition('H2O')
        >>> c.formula
        'H2O'
        >>> c.composition
        Counter({'H': 2, 'O': 1})
        >>> c['H']
        2
    """
    def __init__(self, formula: str):
        self.formula = formula
        self.composition = self._parse_formula(formula)

    def _parse_formula(self, formula: str) -> Counter:
        """
        Parse the given chemical formula and return a Counter object with elements and their counts.

        Args:
            formula (str): A string representing the chemical formula.

        Returns:
            collections.Counter: A Counter object representing the composition of the formula.

        Examples:
            >>> c = Composition._parse_formula('H2O')
            >>> c
            Counter({'H': 2, 'O': 1})
        """

        element_pattern = r"([A-Z][a-z]*)(\d*)"
        elements_counts = re.findall(element_pattern, formula)

        composition = Counter()
        for element, count in elements_counts:
            composition[element] += int(count) if count else 1

        return composition

    def __getitem__(self, element: str) -> int:
        """Get the count of the specified element in the composition.

        Args:
            element (str): A string representing the element to get the count of.

        Returns:
            int: The count of the specified element.

        Examples:
            >>> c = Composition('H2O')
            >>> c['H']
            2
        """
        return self.composition[element]

    def __str__(self) -> str:
        return self.formula

    def __repr__(self) -> str:
        return f"Composition('{self.formula}')"

