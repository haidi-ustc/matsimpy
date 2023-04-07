import numpy as np
from .structure import Structure
from .lattice import Lattice
from typing import List,Optional,Union
from .periodic_table import  Element

class Crystal(Structure):
    def __init__(self, species: Union[List[str], List[int], List[Element]],
            positions: List[List[float]], 
            lattice: Lattice,
            pbc: Optional[List[bool]] = None,
            coords_are_cartesian: bool = False):
        super().__init__(species, positions, lattice)
        self.lattice = lattice

        if coords_are_cartesian:
            self.cart_positions = np.array(positions)
            self.frac_positions = self._convert_to_fractional()
        else:
            self.frac_positions = np.array(positions)
            self.cart_positions = self._convert_to_cartesian()

        self.positions = self.frac_positions  # Set self.positions as the same as self.frac_positions by default
        self.pbc = pbc or [True, True, True]

    def as_dict(self):
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "pbc": self.pbc,
            "lattice": self.lattice.as_dict(),
            "species": self.species,
            "positions": self.positions.tolist()
        }
        return d

    @property
    def volume(self) -> float:
        """Calculate the volume of the crystal."""
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    def __str__(self):
        return f"{self.__class__.__name__} with {len(self)} atoms and a volume of {self.volume:.2f} Å^3"

    def __repr__(self):
        return f"{self.__class__.__name__}(species={self.species}, positions={self.positions.tolist()}, lattice={self.lattice.as_dict()})"


    def _convert_to_cartesian(self):
        """
        Converts fractional coordinates to Cartesian coordinates.

        Args:
            frac_positions (np.ndarray): Numpy array of fractional positions.

        Returns:
            (np.ndarray): Numpy array of Cartesian positions.
        """
        return np.dot(self.frac_positions, self.lattice.matrix)

    def _convert_to_fractional(self):
        """
        Converts Cartesian coordinates to fractional coordinates.

        Args:
            cart_positions (np.ndarray): Numpy array of Cartesian positions.

        Returns:
            (np.ndarray): Numpy array of fractional positions.
        """
        return np.dot(self.cart_positions, np.linalg.inv(self.lattice.matrix))

    @staticmethod
    def from_POSCAR(filename: str) -> 'Crystal':
        with open(filename, 'r') as file:
            lines = file.readlines()

        # Read the lattice scale factor
        scale_factor = float(lines[1].strip())

        # Read the lattice vectors
        lattice_vectors = [list(map(float, line.strip().split())) for line in lines[2:5]]
        lattice_matrix = np.array(lattice_vectors) * scale_factor
        lattice = Lattice(lattice_matrix)

        # Read the atomic species and positions
        species = lines[5].strip().split()
        species_counts = list(map(int, lines[6].strip().split()))
        species_list = []
        for s, count in zip(species, species_counts):
            species_list.extend([s] * count)

        coords_are_cartesian = lines[7].strip().lower().startswith('c')
        positions = [list(map(float, line.strip().split())) for line in lines[8: 8 + sum(species_counts)]]

        return Crystal(species_list, positions, lattice, coords_are_cartesian=coords_are_cartesian)

    def density(self) -> float:
        """Calculate the density of the crystal."""
        mass = self.composition.mass()
        volume = self.volume
        return mass / volume

    def to_POSCAR(self, filename: Optional[str] = None) -> Optional[str]:
        # Prepare the POSCAR formatted string
        poscar_str = f"{self.__class__.__name__}\n"
        poscar_str += "1.0\n"
        for vector in self.lattice.lattice_vectors:
            poscar_str += f"{vector[0]:.8f} {vector[1]:.8f} {vector[2]:.8f}\n"

        unique_species, counts = np.unique(self.species, return_counts=True)
        poscar_str += " ".join(unique_species) + "\n"
        poscar_str += " ".join(map(str, counts)) + "\n"

        poscar_str += "Direct\n"
        for position in self.frac_positions:
            poscar_str += f"{position[0]:.8f} {position[1]:.8f} {position[2]:.8f}\n"

        if filename:
            with open(filename, 'w') as file:
                file.write(poscar_str)
        else:
            return poscar_str

    def to_quantum_espresso(self, filename: Optional[str] = None) -> Optional[str]:
        # Prepare the Quantum Espresso formatted string
        qe_str = "&system\n"
        qe_str += f"  ibrav = 0,\n"
        qe_str += f"  nat = {len(self)},\n"
        qe_str += f"  ntyp = {len(np.unique(self.species))},\n"
        qe_str += "/\n\n"

        qe_str += "ATOMIC_SPECIES\n"
        unique_species, _ = np.unique(self.species, return_counts=True)
        for s in unique_species:
            qe_str += f"{s} 1.0 {s}.UPF\n"

        qe_str += "\nCELL_PARAMETERS (angstrom)\n"
        for vector in self.lattice.lattice_vectors:
            qe_str += f"{vector[0]:.8f} {vector[1]:.8f} {vector[2]:.8f}\n"

        qe_str += "\nATOMIC_POSITIONS (angstrom)\n"
        for s, position in zip(self.species, self.cart_positions):
            qe_str += f"{s} {position[0]:.8f} {position[1]:.8f} {position[2]:.8f}\n"

        if filename:
            with open(filename, 'w') as file:
                file.write(qe_str)
        else:
            return qe_str

    @classmethod
    def random_crystal(cls, dim: int, group: int, species: list, num_ions: list, **kwargs):
        """
        Generate a random crystal using PyXtal.

        Args:
            dim (int): The dimensionality of the crystal (2 or 3).
            group (int): The space group number.
            species (list): List of chemical symbols for the atoms in the crystal.
            num_ions (list): List of integers representing the number of ions of each species.
            **kwargs: Additional keyword arguments to pass to PyXtal.

        Returns:
            (Crystal): A random crystal object.
        """
        try:
            import pyxtal
        except ImportError:
            raise ImportError("The pyxtal package is required to generate random crystals.")

        pyxtal_crystal = pyxtal.crystal.random_crystal(
            dim=dim,
            group=group,
            species=species,
            numIons=num_ions,
            **kwargs
        )

        #species = pyxtal_crystal.species
        #positions = pyxtal_crystal.frac_coords
        #lattice = Lattice(pyxtal_crystal.lattice.matrix)

        return cls(species, positions, lattice)

