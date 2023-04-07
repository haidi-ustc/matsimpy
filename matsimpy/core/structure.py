import numpy as np
from typing import List
import hashlib
from collections import Counter
from monty.json import MSONable

from .lattice import Lattice
from .composition import Composition

class Structure(MSONable):
    """
    A base class for representing crystal and molecule structures.

    Args:
        species (List[str]): List of atomic species.
        positions (List[List[float]]): List of atomic positions.
        lattice (Lattice): Structure's lattice.

    Attributes:
        species (Tuple[str]): Tuple of atomic species.
        positions (np.ndarray): Numpy array of atomic positions.
        lattice (Lattice): Structure's lattice.
        formula (str): Chemical formula of the structure.
        composition (Composition): Composition of the structure.

    Methods:
        as_dict(): Returns a dictionary representation of the structure.
        from_dict(d): Constructs the structure from a dictionary.
        get_formula(): Calculates the chemical formula of the structure.
        get_composition(): Calculates the composition of the structure.
        add_atom(species, position): Adds an atom to the structure.
        remove_atom(index): Removes an atom from the structure.
        get_neighbor_list(cutoff): Returns a list of atoms within a cutoff radius of each atom.

    """

    def __init__(self, species: List[str], positions: List[List[float]], lattice: Lattice):
        self.species = list(species)
        self.positions = np.array(positions)
        self.lattice = lattice
        self.formula = self.get_formula()
        self.composition = self.get_composition()

    def as_dict(self):
        """
        Returns a dictionary representation of the structure.

        Returns:
            (dict): Dictionary representation of the structure.
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": list(self.species),
            "positions": self.positions.tolist(),
            "lattice": self.lattice.as_dict()
        }
        return d

    @classmethod
    def from_dict(cls, d):
        """
        Constructs the structure from a dictionary.

        Args:
            d (dict): Dictionary representation of the structure.

        Returns:
            (Structure): Structure object.
        """
        species = d["species"]
        positions = d["positions"]
        lattice = Lattice.from_dict(d["lattice"])
        return cls(species, positions, lattice)

    def get_formula(self):
        """
        Calculates the chemical formula of the structure.

        Returns:
            (str): Chemical formula of the structure.
        """
        element_counter = Counter(self.species)
        formula = ""
        for element, count in element_counter.items():
            formula += element + str(count)
        return formula


    def __hash__(self):
        # Use hashlib to generate an MD5 hash of the Crystal object's dictionary representation
        hash_str = str(self.as_dict()).encode('utf-8')
        return int(hashlib.md5(hash_str).hexdigest(), 16)

    def get_composition(self):
        """
        Calculates the composition of the structure.

        Returns:
            (Composition): Composition object.
        """
        if self.formula is None:
            formula = self.get_formula()

        return Composition(self.formula)

    def add_atom(self, species: str, position: List[float]):
        """
        Adds an atom to the structure.

        Args:
            species (str): Atomic species.
            position (List[float]): Atomic position.
        """
        self.species += (species,)
        self.positions = np.vstack([self.positions, position])
        self.composition = self.get_composition()

    def remove_atom(self, index: int):
        """
        Removes an atom from the structure.

        Args:
            index (int): Index of atom to be removed.
        """

        if 0 <= index < len(self.species):
            self.species.pop(index)
            self.positions = np.delete(self.positions, index, axis=0)
            self.composition = self.get_composition()
        else:
            raise IndexError("Invalid atom index.")

    def get_neighbor_list(self, cutoff: float):
        """To be implemented by subclasses."""
        pass


    def __len__(self):
        return len(self.species)

