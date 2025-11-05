import numpy as np
from typing import List,Optional,Dict,Any
from monty.json import MSONable
from .lattice import Lattice
from .structure import Structure
from .crystal import Crystal
from .composition import Composition
from .periodic_table import  Element
from .site import Site
from scipy.spatial.distance import cdist


class Molecule(Structure):
    """
    A class representing a molecule.

    Args:
        species (List[str]): A list of atomic symbols.
        positions (List[List[float]]): A list of atomic positions.
    """

    def __init__(self, species: List[str], 
            positions: List[List[float]],
            site_properties: Optional[List[Dict[str, Any]]] = None):
        """
        Initializes the Molecule object.

        Args:
            species (List[str]): A list of atomic symbols.
            positions (List[List[float]]): A list of atomic positions.
        """
        super().__init__(species, positions, None)
        self._site_properties = site_properties or []
        self._sites = self._initialize_sites()

    def _initialize_sites(self) -> List[Site]:
        """
        Initializes the list of Site objects.

        Returns:
            List[Site]: A list of Site objects.
        """
        sites=[]
        if self._site_properties:
            assert(len(self.species)==len(self._site_properties))
            for i, (pos, specie) in enumerate(zip(self.positions, self.species)):
                  sites.append(Site(position=pos, specie=specie, properties=self._site_properties[i]))
        else:
            for i, (pos, specie) in enumerate(zip(self.positions, self.species)):
                sites.append(Site(position=pos, specie=specie))
        return sites

    @property
    def sites(self):
        return self._sites

    def __getitem__(self, item):
        return self.sites[item]

    def get_center_of_mass(self) -> List[float]:
        """
        Calculates the center of mass of the molecule with caching.

        Returns:
            List[float]: The center of mass as a list of three floats.
        """
        if not hasattr(self, '_cached_com'):
            # Use cached Element instances for better performance
            masses = np.array([
                Element.get_element(specie).atomic_mass if hasattr(Element, 'get_element') 
                else Element(specie).atomic_mass 
                for specie in self.species
            ])
            center_of_mass = np.average(self.positions, weights=masses, axis=0)
            self._cached_com = center_of_mass.tolist()
        return self._cached_com

    def translate(self, vector: List[float]):
        """
        Translates the molecule by a given vector.

        Args:
            vector (List[float]): The vector by which to translate the molecule.
        """
        self.positions += np.array(vector)
        # Invalidate center of mass cache
        if hasattr(self, '_cached_com'):
            del self._cached_com

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
        # Invalidate center of mass cache
        if hasattr(self, '_cached_com'):
            del self._cached_com

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
            "positions": self.positions.tolist(),
        }
        if self._site_properties:
            d["site_properties"] = self._site_properties
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
        site_properties = d.get("site_properties", [])
        return cls(species, positions, site_properties)

    def to_crystal(self, scale: float = None) -> Crystal:
        """
        Convert a Molecule to a Crystal structure by automatically defining the lattice scale.
    
        Args:
            scale (float): The scale factor to be used to define the lattice vectors.
    
        Returns:
            Crystal: The Crystal structure.
        """
        # FIX: Use self instead of self.molecule
        max_distance = 0
        for i, pos_i in enumerate(self.positions):
            for j, pos_j in enumerate(self.positions):
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
    
        # FIX: Return Crystal, not Structure
        crystal = Crystal(self.species, self.positions, Lattice(lattice_vectors))
    
        return crystal

    def __str__(self):
        """Human-readable string representation of Molecule."""
        info = f"{self.__class__.__name__}: {self.formula}\n"
        info += f"  Sites: {len(self)} atoms\n"
        
        # Center of mass
        try:
            com = self.get_center_of_mass()
            info += f"  Center of mass: ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}) Å"
        except (ValueError, AttributeError):
            pass
        
        return info

    def __repr__(self):
        """Unambiguous string representation of Molecule for debugging."""
        # Compact representation with key info
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)})"
        )

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

    def get_neighbor_list(self, atom_index: int, cutoff: float) -> List[int]:
          """
          Returns a list of atoms within a cutoff radius of the specified atom.

          Args:
              atom_index (int): Index of the target atom.
              cutoff (float): Cutoff radius.

          Returns:
              List[int]: List of indices of neighboring atoms.
          """
          distances = cdist([self.positions[atom_index]], self.positions)[0]
          neighbors = [i for i, d in enumerate(distances) if d < cutoff and i != atom_index]
          return neighbors

    def get_all_neighbor_lists(self, cutoff: float):
        """
        Returns a list of neighbor lists for all atoms in the structure.
    
        Args:
            cutoff (float): Cutoff radius.
    
        Returns:
            List[List[int]]: List of neighbor lists for all atoms.
        """
        neighbor_lists = []
        for i in range(len(self)):
            neighbor_list = self.get_neighbor_list(i, cutoff)
            neighbor_lists.append(neighbor_list)
        return neighbor_lists
    
    @classmethod
    def from_file(cls, filename: str, format: Optional[str] = None) -> 'Molecule':
        """
        Create a Molecule from a file.
        
        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json
        
        Args:
            filename: Path to the structure file
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
        
        Returns:
            Molecule: Molecule structure from the file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is not supported or file format is invalid
        """
        from ..io import detect_format, get_reader_writer
        from ..io import read_XYZ, read_PDB, read_MOL, from_json
        from ..core import Crystal
        
        # Detect format if not specified
        if format is None:
            format_ext = detect_format(filename)
            if format_ext is None:
                raise ValueError(f"Could not detect file format from extension: {filename}")
        else:
            # Map format string to extension
            format_map = {
                'xyz': '.xyz', 'pdb': '.pdb', 'mol': '.mol', 'json': '.json'
            }
            format_ext = format_map.get(format.lower(), f'.{format.lower()}')
        
        # Get appropriate reader
        reader_name, _ = get_reader_writer(format_ext)
        if reader_name is None:
            raise ValueError(f"Unsupported format for Molecule: {format_ext}")
        
        # Call appropriate reader function
        readers = {
            'read_XYZ': read_XYZ,
            'read_PDB': lambda f: read_PDB(f, as_crystal=False),
            'read_MOL': read_MOL,
            'from_json': lambda f: from_json(filename=f),
        }
        
        reader = readers.get(reader_name)
        if reader is None:
            raise ValueError(f"Reader not found for format: {format_ext}")
        
        result = reader(filename)
        
        # Ensure we return a Molecule
        if isinstance(result, Crystal):
            # Convert crystal to molecule if needed
            return cls(result.species, result.cart_positions.tolist())
        
        return result
    
    def to_file(self, filename: str, format: Optional[str] = None) -> None:
        """
        Write Molecule to a file.
        
        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json
        
        Args:
            filename: Output filename
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
        
        Raises:
            ValueError: If format is not supported
        """
        from ..io import detect_format, get_reader_writer
        from ..io import write_XYZ, write_PDB, write_MOL, to_json
        
        # Detect format if not specified
        if format is None:
            format_ext = detect_format(filename)
            if format_ext is None:
                raise ValueError(f"Could not detect file format from extension: {filename}")
        else:
            # Map format string to extension
            format_map = {
                'xyz': '.xyz', 'pdb': '.pdb', 'mol': '.mol', 'json': '.json'
            }
            format_ext = format_map.get(format.lower(), f'.{format.lower()}')
        
        # Get appropriate writer
        _, writer_name = get_reader_writer(format_ext)
        if writer_name is None:
            raise ValueError(f"Unsupported format for Molecule: {format_ext}")
        
        # Call appropriate writer function
        writers = {
            'write_XYZ': write_XYZ,
            'write_PDB': write_PDB,
            'write_MOL': write_MOL,
            'to_json': lambda s, f: to_json(s, filename=f),
        }
        
        writer = writers.get(writer_name)
        if writer is None:
            raise ValueError(f"Writer not found for format: {format_ext}")
        
        writer(self, filename)
    
    def to_pymatgen(self):
        """
        Convert Molecule to pymatgen Molecule.
        
        Returns:
            pymatgen.core.structure.Molecule: pymatgen Molecule object
            
        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import to_pymatgen
        return to_pymatgen(self)
    
    def to_ase(self):
        """
        Convert Molecule to ASE Atoms.
        
        Returns:
            ase.Atoms: ASE Atoms object
            
        Raises:
            ImportError: If ASE is not installed
        """
        from ..io.converters import to_ase
        return to_ase(self)
    
    @classmethod
    def from_pymatgen(cls, pymatgen_molecule):
        """
        Create Molecule from pymatgen Molecule.
        
        Args:
            pymatgen_molecule: pymatgen.core.structure.Molecule object
            
        Returns:
            Molecule: MatSimPy Molecule object
            
        Raises:
            ImportError: If pymatgen is not installed
        """
        from ..io.converters import from_pymatgen
        return from_pymatgen(pymatgen_molecule)
    
    @classmethod
    def from_ase(cls, ase_atoms):
        """
        Create Molecule from ASE Atoms.
        
        Args:
            ase_atoms: ase.Atoms object (without cell or with cell=False)
            
        Returns:
            Molecule: MatSimPy Molecule object
            
        Raises:
            ImportError: If ASE is not installed
        """
        from ..io.converters import from_ase
        result = from_ase(ase_atoms)
        if not isinstance(result, Molecule):
            raise ValueError("ASE Atoms without cell/PBC will be converted to Molecule")
        return result
    
    def to_code(self, code: str, filename: str, **kwargs) -> None:
        """
        Write input file for a DFT code.
        
        Generic interface for writing DFT code input files. Supports multiple
        codes through the code parameter. Molecules are typically treated as
        isolated systems in a large cell.
        
        Args:
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Output filename
            **kwargs: Additional parameters for the DFT code input
                     (code-specific parameters)
        
        Raises:
            ValueError: If code is not supported
            NotImplementedError: If code interface is not yet implemented
        
        Examples:
            >>> molecule.to_code('quantum_espresso', 'mol_scf.in')
            >>> molecule.to_code('qe', 'molecule.in')
        """
        from ..code import get_code_interface
        
        try:
            interface = get_code_interface(code)
            write_input = interface['write_input']
            write_input(self, filename, **kwargs)
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e
    
    @classmethod
    def from_code(cls, code: str, filename: str, **kwargs) -> 'Molecule':
        """
        Read structure from DFT code output file.
        
        Generic interface for reading structures from DFT code output files.
        Currently not implemented.
        
        Args:
            code: DFT code name (e.g., 'quantum_espresso', 'qe', 'vasp')
            filename: Path to output file
            **kwargs: Additional parameters for parsing
        
        Returns:
            Molecule: Molecule structure from the output file
        
        Raises:
            ValueError: If code is not supported
            NotImplementedError: Output parsing not yet implemented
        
        Examples:
            >>> molecule = Molecule.from_code('quantum_espresso', 'mol_scf.out')
        """
        from ..code import get_code_interface
        
        try:
            interface = get_code_interface(code)
            read_output = interface['read_output']
            # TODO: Implement output parsing
            raise NotImplementedError(f"Reading {code} output files not yet implemented")
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

