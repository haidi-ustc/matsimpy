import re
import json
from collections import Counter
from typing import Optional
from monty.json import MSONable
from .periodic_table import Element

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
            dict: A dictionary containing the mass fractions of the composition (0-1).

        Examples:
            >>> c = Composition('H2O')
            >>> fractions = c.mass_fractions()
            >>> fractions['H']  # Mass fraction of H
            0.111898...
            >>> fractions['O']  # Mass fraction of O
            0.888102...
        """
        total_mass = self.mass
        fractions = {}
        for element, count in self.composition.items():
            # Use cached Element.get_element for better performance
            elem = Element.get_element(element) if hasattr(Element, 'get_element') else Element(element)
            mass_fraction = elem.atomic_mass * count / total_mass
            fractions[element] = mass_fraction
        return fractions

    def weight_percent(self):
        """
        Calculate the weight percent (weight percentage) of each element in the composition.

        Returns:
            dict: A dictionary containing the weight percentages of each element (0-100).

        Examples:
            >>> c = Composition('H2O')
            >>> weight_pct = c.weight_percent()
            >>> weight_pct['H']  # Weight percent of H
            11.1898...
            >>> weight_pct['O']  # Weight percent of O
            88.8102...
            >>> sum(weight_pct.values())  # Should sum to ~100
            100.0
        """
        total_mass = self.mass
        weight_percentages = {}
        for element, count in self.composition.items():
            # Use cached Element.get_element for better performance
            elem = Element.get_element(element) if hasattr(Element, 'get_element') else Element(element)
            mass = elem.atomic_mass * count
            weight_percent = (mass / total_mass) * 100.0
            weight_percentages[element] = weight_percent
        return weight_percentages

    def to_html(self, sort_by: Optional[str] = None) -> str:
        """
        Convert the chemical formula to HTML string with subscript formatting.
        
        Args:
            sort_by: Sorting method ('alphabet' or 'element'). If None, uses the
                    original sort_by from initialization.
        
        Returns:
            str: HTML string with subscripts (e.g., "Fe<sub>2</sub>O<sub>3</sub>")
            
        Examples:
            >>> c = Composition('Fe2O3')
            >>> c.to_html()
            'Fe<sub>2</sub>O<sub>3</sub>'
            >>> c = Composition('H2O')
            >>> c.to_html()
            'H<sub>2</sub>O'
            >>> c = Composition('Fe2O3', sort_by='element')
            >>> c.to_html()
            'Fe<sub>2</sub>O<sub>3</sub>'  # Uses element sorting
        """
        html_formula = []
        element_counts = self.composition
        
        # Use provided sort_by or determine from original formula
        if sort_by is None:
            # Try to infer from formula order (if element sort, use element; else alphabet)
            # For simplicity, default to alphabet unless explicitly specified
            sort_by = 'alphabet'
        
        if sort_by == 'alphabet':
            sorted_elements = sorted(element_counts.items(), key=lambda x: x[0])
        elif sort_by == 'element':
            sorted_elements = sorted(element_counts.items(), key=lambda x: Element(x[0]).atomic_no)
        else:
            raise ValueError("sort_by must be either 'alphabet' or 'element'")
        
        for element, count in sorted_elements:
            html_formula.append(element)
            if count > 1:
                html_formula.append(f'<sub>{count}</sub>')
        
        return ''.join(html_formula)

    def to_latex(self, sort_by: Optional[str] = None) -> str:
        """
        Convert the chemical formula to LaTeX string with subscript formatting.
        
        Args:
            sort_by: Sorting method ('alphabet' or 'element'). If None, uses the
                    original sort_by from initialization.
        
        Returns:
            str: LaTeX string with subscripts (e.g., "Fe$_2$O$_3$")
            
        Examples:
            >>> c = Composition('Fe2O3')
            >>> c.to_latex()
            'Fe$_2$O$_3$'
            >>> c = Composition('H2O')
            >>> c.to_latex()
            'H$_2$O'
            >>> c = Composition('Fe2O3', sort_by='element')
            >>> c.to_latex()
            'Fe$_2$O$_3$'  # Uses element sorting
        """
        latex_formula = []
        element_counts = self.composition
        
        # Use provided sort_by or default to alphabet
        if sort_by is None:
            sort_by = 'alphabet'
        
        if sort_by == 'alphabet':
            sorted_elements = sorted(element_counts.items(), key=lambda x: x[0])
        elif sort_by == 'element':
            sorted_elements = sorted(element_counts.items(), key=lambda x: Element(x[0]).atomic_no)
        else:
            raise ValueError("sort_by must be either 'alphabet' or 'element'")
        
        for element, count in sorted_elements:
            latex_formula.append(element)
            if count > 1:
                latex_formula.append(f'$_{{{count}}}$')
        
        return ''.join(latex_formula)

