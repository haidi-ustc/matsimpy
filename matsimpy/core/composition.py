import re
import json
from collections import Counter
from monty.json import MSONable
from .periodic_table import  Element

class Composition(MSONable):
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
    def __init__(self, formula: str ,sort_by: str = 'alphabet'):
        self.composition = self._parse_formula(formula)
        self.formula = self._chemical_formula(sort_by=sort_by)

    def _chemical_formula(self, sort_by: str = 'alphabet') -> str:
        element_counts = self.composition
        if sort_by == 'alphabet':
            sorted_elements = sorted(element_counts.items(), key=lambda x: x[0])
        elif sort_by == 'element':
            sorted_elements = sorted(element_counts.items(), key=lambda x: Element(x[0]).atomic_no)
        else:
            raise ValueError("sort_by must be either 'alphabet' or 'Element.Z'")
    
        formula = ''.join([f'{element}{count if count > 1 else ""}' for element, count in sorted_elements])
        return formula

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

        def parse_subformula(sub_formula, count):
            sub_counts = re.findall(element_pattern, sub_formula)
            for element, sub_count in sub_counts:
                composition[element] += int(sub_count) if sub_count else 1 * count

        element_pattern = r"([A-Z][a-z]*)(\d*)"
        group_pattern = r"\(([^\)]+)\)(\d*)"

        composition = Counter()

        groups = re.findall(group_pattern, formula)
        for group, count in groups:
            parse_subformula(group, int(count) if count else 1)
            formula = formula.replace(f"({group}){count}", "")

        parse_subformula(formula, 1)

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

    def as_dict(self):
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "formula": self.formula
        }
        return d

    @classmethod
    def from_dict(cls, d):
        formula = d["formula"]
        return cls(formula=formula)

    def to_json(self):
        return json.dumps(self.as_dict())

    @classmethod
    def from_json(cls, json_string):
        return cls.from_dict(json.loads(json_string))


    def __eq__(self, other):
        if isinstance(other, Composition):
            return self.composition == other.composition
        else:
            return False

    @property
    def mass(self):
        """
        Calculate the mass of the composition with cached Element instances.

        Returns:
            float: The mass of the composition.

        Examples:
            >>> c = Composition('H2O')
            >>> c.mass
            18.01528
        """
        mass = 0.0
        for element, count in self.composition.items():
            # Use cached Element.get_element for better performance
            elem = Element.get_element(element) if hasattr(Element, 'get_element') else Element(element)
            mass += elem.atomic_mass * count
        return mass

    def mass_fractions(self):
        """
        Calculate the mass fractions of the composition.

        Returns:
            dict: A dictionary containing the mass fractions of the composition.
        """
        total_mass = self.mass
        fractions = {}
        for element, count in self.composition.items():
            # Use cached Element.get_element for better performance
            elem = Element.get_element(element) if hasattr(Element, 'get_element') else Element(element)
            mass_fraction = elem.atomic_mass * count / total_mass
            fractions[element] = mass_fraction
        return fractions

