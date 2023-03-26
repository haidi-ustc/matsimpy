from .structure import Structure
from .lattice import Lattice
from typing import List

class Crystal(Structure):
    def __init__(self, species: List[str], positions: List[List[float]], lattice: Lattice):
        super().__init__(species, positions, lattice)



    def calculate_reciprocal_lattice(self) -> Lattice:
        """Calculate the reciprocal lattice."""
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))

        a_star = 2 * np.pi * np.cross(b, c) / volume
        b_star = 2 * np.pi * np.cross(c, a) / volume
        c_star = 2 * np.pi * np.cross(a, b) / volume

        reciprocal_lattice = Lattice([a_star, b_star, c_star])
        return reciprocal_lattice

    def get_planes_from_miller_indices(self, h, k, l):
        """Get the plane defined by the given Miller indices (h, k, l)."""
        reciprocal_lattice = self.calculate_reciprocal_lattice()
        g = h * reciprocal_lattice.lattice_vectors[0] + \
            k * reciprocal_lattice.lattice_vectors[1] + \
            l * reciprocal_lattice.lattice_vectors[2]
        return g

    def as_dict(self):
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "lattice": self.lattice.as_dict(),
            "species": self.species,
            "positions": self.positions.tolist()
        }
        return d

    def volume(self) -> float:
        """Calculate the volume of the crystal."""
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    def __str__(self):
        return f"{self.__class__.__name__} with {len(self)} atoms and a volume of {self.volume():.2f} Å^3"

    def __repr__(self):
        return f"{self.__class__.__name__}(species={self.species}, positions={self.positions.tolist()}, lattice={self.lattice.as_dict()})"



