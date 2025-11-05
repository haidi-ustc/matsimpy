import numpy as np
from tabulate import tabulate
from typing import List, Optional, Union, Dict, Tuple
from scipy.spatial import cKDTree
from .structure import Structure
from .lattice import Lattice
from .periodic_table import Element
from .site import CrystalSite

class Crystal(Structure):
    def __init__(self, species: Union[List[str], List[int], List[Element]],
            positions: List[List[float]], 
            lattice: Lattice,
            pbc: Optional[List[bool]] = None,
            coords_are_cartesian: bool = False,
            site_properties: Optional[List[dict]] = None):  # Add site_properties as an optional argument)
        super().__init__(species, positions, lattice)
        self.lattice = lattice

        if coords_are_cartesian:
            self.cart_positions = np.array(positions)
            self.frac_positions = self._convert_to_fractional()
        else:
            self.frac_positions = np.array(positions)
            self.cart_positions = self._convert_to_cartesian()

        self.positions = self.frac_positions  # Set self.positions as the same as self.frac_positions by default
        self.site_properties = site_properties or []
        self._sites = self._initialize_sites()  # Add this line to initialize the _sites attribute
        self.pbc = pbc or [True, True, True]
        
        # Add neighbor tree cache for optimized neighbor finding
        self._neighbor_tree: Optional[cKDTree] = None
        self._neighbor_tree_cutoff: Optional[float] = None
        self._neighbor_tree_positions: Optional[np.ndarray] = None
    
    def add_atom(self, species: str, position: List[float]) -> None:
        """
        Adds an atom to the crystal structure and updates coordinates.
        
        Args:
            species (str): Atomic species.
            position (List[float]): Atomic position (fractional coordinates).
        """
        super().add_atom(species, position)
        # Update fractional and cartesian positions
        self.frac_positions = self.positions
        self.cart_positions = self._convert_to_cartesian()
        # Invalidate neighbor tree
        self._neighbor_tree = None
        self._neighbor_tree_positions = None
        # Reinitialize sites
        self._sites = self._initialize_sites()
    
    def remove_atom(self, index: int) -> None:
        """
        Removes an atom from the crystal structure and updates coordinates.
        
        Args:
            index (int): Index of atom to be removed.
        """
        super().remove_atom(index)
        # Update fractional and cartesian positions
        self.frac_positions = self.positions
        self.cart_positions = self._convert_to_cartesian()
        # Invalidate neighbor tree
        self._neighbor_tree = None
        self._neighbor_tree_positions = None
        # Reinitialize sites
        self._sites = self._initialize_sites()

    def _initialize_sites(self) -> List[CrystalSite]:
        """
        Initializes the list of CrystalSite objects.

        Returns:
            List[CrystalSite]: A list of CrystalSite objects.
        """
        sites = []
        if self.site_properties:
            assert(len(self.species) == len(self.site_properties))
            for i, (pos, specie) in enumerate(zip(self.positions, self.species)):
                sites.append(CrystalSite(position=pos, specie=specie, lattice=self.lattice, properties=self.site_properties[i], coords_are_cartesian=False))
        else:
            for i, (pos, specie) in enumerate(zip(self.positions, self.species)):
                sites.append(CrystalSite(position=pos, specie=specie, lattice=self.lattice, coords_are_cartesian=False))
        return sites

    @property
    def sites(self):
        return self._sites

    def as_dict(self):
        d = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "pbc": self.pbc,
            "lattice": self.lattice.as_dict(),
            "species": self.species,
            "positions": self.positions.tolist(),
            "site_properties": self.site_properties  # Add site_properties to the dictionary
        }
        return d

    @classmethod
    def from_dict(cls, d):
        species = d["species"]
        positions = d["positions"]
#        lattice = d.get("lattice").get("lattice_vectors")
        lattice = Lattice.from_dict(d["lattice"])
        site_properties = d.get("site_properties", [])
        coords_are_cartesian = d.get("coords_are_cartesian")
        pbc = d.get("pbc")
        return cls(species=species, positions=positions, lattice=lattice, pbc=pbc, 
                   site_properties = site_properties )

    @property
    def volume(self) -> float:
        """Calculate the volume of the crystal."""
        a, b, c = self.lattice.lattice_vectors
        volume = np.dot(a, np.cross(b, c))
        return abs(volume)

    def __str__(self):
        headers = ["Element", "Fractional Coordinates", "Cartesian Coordinates"]
        rows = []
        ret=f"{self.__class__.__name__} with {len(self)} atoms and a volume of {self.volume:.2f} Å^3"
        for site in self.sites:
            element = site.specie
            frac_coords = ", ".join(f"{coord:.4f}" for coord in site.frac_position)
            cart_coords = ", ".join(f"{coord:.4f}" for coord in site.cart_position)
            rows.append([element, frac_coords, cart_coords])
        return str(self.lattice)+'\n'+ret+'\n'+tabulate(rows, headers=headers, tablefmt="plain")

    def __repr__(self):
        return f"{self.__class__.__name__}(species={self.species}, positions={self.positions.tolist()}, lattice={self.lattice.as_dict()})"
  
    def __getitem__(self, item):
        return self.sites[item]

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
        # Use cached inverse matrix
        return np.dot(self.cart_positions, self.lattice.inv_matrix)

    def _get_periodic_images(self, cutoff: float) -> np.ndarray:
        """
        Get all periodic images within cutoff.
        
        Args:
            cutoff: Cutoff radius for neighbor finding
            
        Returns:
            np.ndarray: All positions including periodic images
        """
        # Calculate number of images needed
        max_dist = np.max(np.linalg.norm(self.lattice.lattice_vectors, axis=1))
        n_images = int(np.ceil(cutoff / max_dist)) + 1
        
        images = []
        for i in range(-n_images, n_images + 1):
            for j in range(-n_images, n_images + 1):
                for k in range(-n_images, n_images + 1):
                    if i == 0 and j == 0 and k == 0:
                        continue
                    shift = (i * self.lattice.lattice_vectors[0] + 
                            j * self.lattice.lattice_vectors[1] + 
                            k * self.lattice.lattice_vectors[2])
                    images.append(self.cart_positions + shift)
        
        if images:
            return np.vstack([self.cart_positions] + images)
        return self.cart_positions

    def get_neighbor_list(self, cutoff: float, 
                         use_pbc: bool = True) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list with optimized KDTree.
        
        Args:
            cutoff: Cutoff radius for neighbor finding
            use_pbc: Whether to use periodic boundary conditions
        
        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples
        """
        # Check if we need to rebuild tree
        n_atoms = len(self.cart_positions)
        rebuild_tree = (
            self._neighbor_tree is None or
            self._neighbor_tree_cutoff != cutoff or
            (use_pbc and self._neighbor_tree_positions is None) or
            (self._neighbor_tree_positions is not None and 
             len(self._neighbor_tree_positions) < n_atoms)  # Structure changed
        )
        
        if rebuild_tree:
            if use_pbc:
                positions = self._get_periodic_images(cutoff)
            else:
                positions = self.cart_positions
            
            self._neighbor_tree = cKDTree(positions)
            self._neighbor_tree_cutoff = cutoff
            self._neighbor_tree_positions = positions
        
        # Query neighbors
        neighbors_dict = {}
        n_atoms = len(self.cart_positions)
        for i, pos in enumerate(self.cart_positions):
            indices = self._neighbor_tree.query_ball_point(pos, cutoff)
            neighbors = []
            for idx in indices:
                if idx < n_atoms:
                    # Original atom
                    if idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        neighbors.append((idx, dist))
                else:
                    # Periodic image
                    image_idx = idx % n_atoms
                    if image_idx != i:
                        dist = np.linalg.norm(pos - self._neighbor_tree_positions[idx])
                        neighbors.append((image_idx, dist))
            
            neighbors_dict[i] = neighbors
        
        return neighbors_dict

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
        mass = self.composition.mass  # mass is a property, not a method
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

        # FIX: Extract from pyxtal_crystal
        species_list = pyxtal_crystal.species
        positions = pyxtal_crystal.frac_coords
        lattice = Lattice(pyxtal_crystal.lattice.matrix)

        return cls(species_list, positions, lattice)
    
    @classmethod
    def from_file(cls, filename: str, format: Optional[str] = None) -> 'Crystal':
        """
        Create a Crystal from a file.
        
        Automatically detects file format from extension if not specified.
        Supported formats: .vasp, .poscar, .contcar, .cif, .xsf, .json, .ase
        
        Args:
            filename: Path to the structure file
            format: Optional format specification (e.g., 'vasp', 'cif').
                   If None, format is detected from file extension.
        
        Returns:
            Crystal: Crystal structure from the file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is not supported or file format is invalid
        """
        from ..io import detect_format, get_reader_writer
        from ..io import (
            read_POSCAR, read_CIF, read_XSF, from_json, read_ASE
        )
        
        # Detect format if not specified
        if format is None:
            format_ext = detect_format(filename)
            if format_ext is None:
                raise ValueError(f"Could not detect file format from extension: {filename}")
        else:
            # Map format string to extension
            format_map = {
                'vasp': '.vasp', 'poscar': '.vasp', 'contcar': '.contcar',
                'cif': '.cif', 'xsf': '.xsf', 'json': '.json',
                'ase': '.ase'
            }
            format_ext = format_map.get(format.lower(), f'.{format.lower()}')
        
        # Get appropriate reader
        reader_name, _ = get_reader_writer(format_ext)
        if reader_name is None:
            raise ValueError(f"Unsupported format for Crystal: {format_ext}")
        
        # Call appropriate reader function
        readers = {
            'read_POSCAR': read_POSCAR,
            'read_CONTCAR': read_POSCAR,  # Alias
            'read_CIF': read_CIF,
            'read_XSF': read_XSF,
            'from_json': lambda f: from_json(filename=f),
            'read_ASE': read_ASE,
        }
        
        reader = readers.get(reader_name)
        if reader is None:
            raise ValueError(f"Reader not found for format: {format_ext}")
        
        return reader(filename)
    
    def to_file(self, filename: str, format: Optional[str] = None) -> None:
        """
        Write Crystal to a file.
        
        Automatically detects file format from extension if not specified.
        Supported formats: .vasp, .poscar, .contcar, .cif, .xsf, .json, .ase
        
        Args:
            filename: Output filename
            format: Optional format specification (e.g., 'vasp', 'cif').
                   If None, format is detected from file extension.
        
        Raises:
            ValueError: If format is not supported
        """
        from ..io import detect_format, get_reader_writer
        from ..io import (
            write_POSCAR, write_CIF, write_XSF, to_json, write_ASE
        )
        
        # Detect format if not specified
        if format is None:
            format_ext = detect_format(filename)
            if format_ext is None:
                raise ValueError(f"Could not detect file format from extension: {filename}")
        else:
            # Map format string to extension
            format_map = {
                'vasp': '.vasp', 'poscar': '.vasp', 'contcar': '.contcar',
                'cif': '.cif', 'xsf': '.xsf', 'json': '.json',
                'ase': '.ase'
            }
            format_ext = format_map.get(format.lower(), f'.{format.lower()}')
        
        # Get appropriate writer
        _, writer_name = get_reader_writer(format_ext)
        if writer_name is None:
            raise ValueError(f"Unsupported format for Crystal: {format_ext}")
        
        # Call appropriate writer function
        writers = {
            'write_POSCAR': write_POSCAR,
            'write_CONTCAR': write_POSCAR,  # Alias
            'write_CIF': write_CIF,
            'write_XSF': write_XSF,
            'to_json': lambda s, f: to_json(s, filename=f),
            'write_ASE': write_ASE,
        }
        
        writer = writers.get(writer_name)
        if writer is None:
            raise ValueError(f"Writer not found for format: {format_ext}")
        
        writer(self, filename)
    
    def to_pymatgen(self):
        """
        Convert Crystal to pymatgen Structure.
        
        Returns:
            pymatgen.core.Structure: pymatgen Structure object
            
        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import to_pymatgen
        return to_pymatgen(self)
    
    def to_ase(self):
        """
        Convert Crystal to ASE Atoms.
        
        Returns:
            ase.Atoms: ASE Atoms object
            
        Raises:
            ImportError: If ASE is not installed
        """
        from ..io.converters import to_ase
        return to_ase(self)
    
    @classmethod
    def from_pymatgen(cls, pymatgen_structure):
        """
        Create Crystal from pymatgen Structure.
        
        Args:
            pymatgen_structure: pymatgen.core.Structure object
            
        Returns:
            Crystal: MatSimPy Crystal object
            
        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import from_pymatgen
        return from_pymatgen(pymatgen_structure)
    
    @classmethod
    def from_ase(cls, ase_atoms):
        """
        Create Crystal from ASE Atoms.
        
        Args:
            ase_atoms: ase.Atoms object (must have cell and PBC)
            
        Returns:
            Crystal: MatSimPy Crystal object
            
        Raises:
            ImportError: If ASE is not installed
            ValueError: If ASE Atoms doesn't have cell information
        """
        from ..io.converters import from_ase
        result = from_ase(ase_atoms)
        if not isinstance(result, Crystal):
            raise ValueError("ASE Atoms must have cell and PBC for Crystal conversion")
        return result

