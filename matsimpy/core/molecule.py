import numpy as np
from typing import List
from monty.json import MSONable
from .lattice import Lattice 
from .composition import Composition

import numpy as np
from typing import List
from monty.json import MSONable
from .lattice import Lattice
from .structure import Structure
from .crystal import Crystal
from .composition import Composition
from .periodic_table import  Element


class Molecule(Structure):
    """
    A class representing a molecule.

    Args:
        species (List[str]): A list of atomic symbols.
        positions (List[List[float]]): A list of atomic positions.
    """

    def __init__(self, species: List[str], positions: List[List[float]]):
        """
        Initializes the Molecule object.

        Args:
            species (List[str]): A list of atomic symbols.
            positions (List[List[float]]): A list of atomic positions.
        """
        super().__init__(species, positions, None)

    def get_center_of_mass(self) -> List[float]:
        """
        Calculates the center of mass of the molecule.

        Returns:
            List[float]: The center of mass as a list of three floats.
        """
        masses = np.array([Element(specie).atomic_mass for specie in self.species])
        center_of_mass = np.average(self.positions, weights=masses, axis=0)
        return center_of_mass.tolist()

    def translate(self, vector: List[float]):
        """
        Translates the molecule by a given vector.

        Args:
            vector (List[float]): The vector by which to translate the molecule.
        """
        self.positions += np.array(vector)

    def rotate(self, angle: float, axis: List[float]):
        """
        Rotates the molecule by a given angle around a given axis.

        Args:
            angle (float): The angle in degrees by which to rotate the molecule.
            axis (List[float]): The axis around which to rotate the molecule.
        """
        from scipy.spatial.transform import Rotation

        rotation = Rotation.from_rotvec(np.radians(angle) * np.array(axis))
        self.positions = rotation.apply(self.positions)

    def as_dict(self):
        """
        Returns a dictionary representation of the Molecule object.

        Returns:
            dict: A dictionary representation of the Molecule object.
        """
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "species": self.species,
            "positions": self.positions.tolist()
        }
        return d

    @classmethod
    def from_dict(cls, d):
        """
        Creates a Molecule object from a dictionary representation.

        Args:
            d (dict): A dictionary representation of a Molecule object.

        Returns:
            Molecule: A Molecule object.
        """
        species = d["species"]
        positions = d["positions"]
        return cls(species, positions)


    def to_crystal(self, scale: float = None) -> Structure:
        """
        Convert a Molecule to a Crystal structure by automatically defining the lattice scale.
    
        Args:
            scale (float): The scale factor to be used to define the lattice vectors.
    
        Returns:
            Structure: The Crystal structure.
        """
        molecule = self.molecule
        max_distance = 0
        for i, pos_i in enumerate(molecule.positions):
            for j, pos_j in enumerate(molecule.positions):
                if i >= j:
                    continue
                distance = np.linalg.norm(pos_i - pos_j)
                if distance > max_distance:
                    max_distance = distance
    
        if scale is None or max_distance / scale > 15:
            # If scale is not supplied or is not reasonable, define scale based on max distance
            scale = max_distance / 5
    
        # Define lattice vectors based on the scale factor
        lattice_vectors = [[scale, 0, 0], [0, scale, 0], [0, 0, scale]]
    
        # Create Crystal structure with the same species and positions as the Molecule
        crystal = Structure(molecule.species, molecule.positions, Lattice(lattice_vectors))
    
        return crystal

    def __str__(self):
        return f"{self.__class__.__name__} with {len(self)} atoms "

    def __repr__(self):
        return f"{self.__class__.__name__}(species={self.species}, positions={self.positions.tolist()})"

    def get_moment_of_inertia(self) -> List[float]:
        """
        Calculates the moment of inertia tensor of the molecule around its center of mass.
    
        Returns:
            List[float]: The moment of inertia tensor as a flattened list of 6 floats.
        """
        masses = np.array([Element(specie).atomic_mass for specie in self.species])
        com = self.get_center_of_mass()
        positions = self.positions - com
        moment_tensor = np.zeros((3, 3))
        for i in range(len(self.species)):
            r = positions[i]
            moment_tensor[0, 0] += masses[i] * (r[1]**2 + r[2]**2)
            moment_tensor[1, 1] += masses[i] * (r[0]**2 + r[2]**2)
            moment_tensor[2, 2] += masses[i] * (r[0]**2 + r[1]**2)
            moment_tensor[0, 1] -= masses[i] * r[0] * r[1]
            moment_tensor[0, 2] -= masses[i] * r[0] * r[2]
            moment_tensor[1, 2] -= masses[i] * r[1] * r[2]
            moment_tensor[1, 0] = moment_tensor[0, 1]
            moment_tensor[2, 0] = moment_tensor[0, 2]
            moment_tensor[2, 1] = moment_tensor[1, 2]
        #eigenvalues, eigenvectors = np.linalg.eigh(moment_tensor)
        return moment_tensor

