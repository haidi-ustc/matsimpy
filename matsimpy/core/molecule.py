import numpy as np
from typing import List, Optional, Dict, Any, Union
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
        self.site_properties = site_properties or []  # Make public for consistency
        self._sites = self._initialize_sites()

    def _initialize_sites(self) -> List[Site]:
        """
        Initializes the list of Site objects.

        Returns:
            List[Site]: A list of Site objects.
        """
        if self.site_properties and len(self.site_properties) == len(self.species):
            return [Site(position=pos, specie=spec, properties=props) 
                    for pos, spec, props in zip(self.positions, self.species, self.site_properties)]
        else:
            return [Site(position=pos, specie=spec) 
                    for pos, spec in zip(self.positions, self.species)]

    @property
    def sites(self) -> List[Site]:
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
            masses = np.array([Element.get_element(specie).atomic_mass for specie in self.species])
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
        # Update sites
        self._sites = self._initialize_sites()

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
        # Update sites
        self._sites = self._initialize_sites()
    
    def add_atom(self, species: str, position: List[float], site_properties: Optional[Dict[str, Any]] = None) -> None:
        """
        Adds an atom to the molecule and updates sites.
        
        Args:
            species (str): Atomic species.
            position (List[float]): Atomic position (must be 3D).
            site_properties (Optional[Dict[str, Any]]): Optional site properties for the new atom.
        """
        super().add_atom(species, position)
        # Update site properties list if needed
        # Only maintain site_properties if we're actively using them
        if site_properties is not None:
            if not self.site_properties:
                # Initialize with empty dicts for existing atoms
                self.site_properties = [{}] * (len(self.species) - 1)
            self.site_properties.append(site_properties)
        elif self.site_properties:
            # If we have site_properties, maintain them (add empty dict)
            self.site_properties.append({})
        self._sites = self._initialize_sites()

    def remove_atom(self, index: int) -> None:
        """
        Removes an atom from the molecule and updates sites.
        
        Args:
            index (int): Index of atom to be removed.
        """
        super().remove_atom(index)
        if self.site_properties and len(self.site_properties) > index:
            self.site_properties.pop(index)
        self._sites = self._initialize_sites()
    
    def substitute(self, indices: Union[int, List[int], 'AtomSelection'], 
                   new_species: Union[str, List[str], Dict[str, str]]) -> None:
        """
        Substitute atoms with new species.
        
        This is a common operation for modifying molecules. For functional
        style (returning new object), use matsimpy.transformation.substitute().
        
        Args:
            indices: Atom index, list of indices, or AtomSelection object to substitute
            new_species: New species symbol, list of symbols, or dict mapping old->new species
            
        Raises:
            IndexError: If index is out of range
            ValueError: If number of indices doesn't match number of species
            KeyError: If dict mapping doesn't contain a species
            
        Examples:
            >>> molecule.substitute(0, 'N')  # Substitute atom at index 0
            >>> molecule.substitute([0, 1], ['N', 'O'])  # Substitute multiple
            >>> # Using AtomSelection
            >>> from matsimpy.utils.selection import AtomSelection
            >>> sel = AtomSelection(molecule).by_species('C')
            >>> molecule.substitute(sel, 'N')  # Substitute selected atoms
            >>> # Using dict mapping (maps old species to new species)
            >>> molecule.substitute([0, 1, 2], {'C': 'N', 'O': 'S'})
        """
        super().substitute(indices, new_species)
        # Update sites after substitution
        self._sites = self._initialize_sites()

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
        if self.site_properties:
            d["site_properties"] = self.site_properties
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
        return cls(species, positions, site_properties=site_properties)

    def to_crystal(self, vacuum: float = 15.0) -> Crystal:
        """
        Convert a Molecule to a Crystal structure by automatically creating a box
        with vacuum padding around the molecule.
    
        Args:
            vacuum (float): Vacuum padding in Angstroms to add around the molecule.
                           Default is 15.0 Å.
    
        Returns:
            Crystal: The Crystal structure with the molecule centered in a cubic box.
        """
        if len(self.positions) == 0:
            raise ValueError("Cannot convert empty molecule to crystal")
        
        # Calculate bounding box of the molecule
        positions = np.array(self.positions)
        min_coords = np.min(positions, axis=0)
        max_coords = np.max(positions, axis=0)
        
        # Calculate the size needed for the box (including vacuum padding)
        box_size = (max_coords - min_coords) + 2 * vacuum
        
        # Ensure minimum box size (in case molecule is a single atom or very small)
        min_box_size = 2 * vacuum
        box_size = np.maximum(box_size, min_box_size)
        
        # Center the molecule in the box
        # Shift positions so that the bounding box is centered at origin
        center_offset = (min_coords + max_coords) / 2
        centered_positions = positions - center_offset
        
        # Shift to center of box (add half the box size)
        centered_positions = centered_positions + box_size / 2
        
        # Create cubic lattice vectors
        lattice_vectors = [
            [box_size[0], 0.0, 0.0],
            [0.0, box_size[1], 0.0],
            [0.0, 0.0, box_size[2]]
        ]
        
        # Create Crystal with Cartesian coordinates
        crystal = Crystal(
            list(self.species),
            centered_positions.tolist(),
            Lattice(lattice_vectors),
            coords_are_cartesian=True
        )
        
        return crystal

    def __str__(self):
        """
        Human-readable string representation of Molecule.
        
        Note: Atoms are displayed sorted by atomic number for readability,
        but the internal structure (species, positions) maintains the original order.
        Use sort_atoms() if you want to actually reorder the internal data.
        """
        from tabulate import tabulate
        
        info = f"{self.__class__.__name__}: {self.formula}\n"
        info += f"  Sites: {len(self)} atoms\n"
        
        # Center of mass
        try:
            com = self.get_center_of_mass()
            info += f"  Center of mass: ({com[0]:.4f}, {com[1]:.4f}, {com[2]:.4f}) Å\n"
        except (ValueError, AttributeError):
            info += "\n"
        
        # Atom coordinates and properties table
        has_properties = any(site.properties for site in self.sites)
        headers = ["Element", "Cartesian Coordinates"]
        if has_properties:
            headers.append("Properties")
        
        # Sort sites by element for display only (by atomic number, then by Cartesian coordinates)
        # Note: This does NOT change the internal order - just for display
        sorted_sites = sorted(
            self.sites,
            key=lambda s: (Element.get_element(s.specie).atomic_no, s.position[0], s.position[1], s.position[2])
        )
        
        rows = []
        for site in sorted_sites:
            element = str(site.specie)
            cart_coords = f"({site.position[0]:.4f}, {site.position[1]:.4f}, {site.position[2]:.4f})"
            row = [element, cart_coords]
            if has_properties:
                props_str = ", ".join(f"{k}={v}" for k, v in site.properties.items()) if site.properties else ""
                row.append(props_str)
            rows.append(row)
        
        info += tabulate(rows, headers=headers, tablefmt="plain", stralign="left")
        
        return info

    def __repr__(self):
        """Unambiguous string representation of Molecule for debugging."""
        # Compact representation with key info
        return (
            f"{self.__class__.__name__}(formula='{self.formula}', "
            f"nsites={len(self)})"
        )

    def get_moment_of_inertia(self) -> np.ndarray:
        """
        Calculates the moment of inertia tensor of the molecule around its center of mass.
    
        Returns:
            np.ndarray: The moment of inertia tensor as a 3x3 numpy array.
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
            # Preserve site properties if available
            site_props = getattr(result, 'site_properties', None)
            return cls(result.species, result.cart_positions.tolist(), site_properties=site_props)
        
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
    
    @property
    def calc(self):
        """
        Get attached calculator.
        
        Returns:
            Calculator or None: The attached calculator, or None if none attached
        """
        return getattr(self, '_calculator', None)
    
    @calc.setter
    def calc(self, calculator):
        """
        Attach a calculator to this structure.
        
        Args:
            calculator: Calculator object (e.g., LennardJones, Mattersim, VASP)
            
        Raises:
            TypeError: If calculator is not a Calculator instance
        """
        from ..calculator.base import Calculator
        if calculator is not None and not isinstance(calculator, Calculator):
            raise TypeError(
                f"Calculator must be a Calculator instance, got {type(calculator)}"
            )
        self._calculator = calculator
    
    def get_potential_energy(self) -> float:
        """
        Get potential energy from attached calculator.
        
        Returns:
            float: Potential energy in eV
            
        Raises:
            ValueError: If no calculator attached or calculation not performed
        """
        if self.calc is None:
            raise ValueError("No calculator attached. Set molecule.calc = calculator first.")
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_potential_energy()
    
    def get_forces(self) -> np.ndarray:
        """
        Get forces from attached calculator.
        
        Returns:
            np.ndarray: Forces array of shape (N, 3) in eV/Å
            
        Raises:
            ValueError: If no calculator attached or calculation not performed
        """
        if self.calc is None:
            raise ValueError("No calculator attached. Set molecule.calc = calculator first.")
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_forces()
    
    def perturb(self, amplitude: float, indices: Optional[Union[List[int], 'AtomSelection']] = None, 
                seed: Optional[int] = None, inplace: bool = True) -> 'Molecule':
        """
        Add random perturbations to atomic positions.
        
        Convenience method that calls the transformation module's perturb_positions function.
        By default, modifies the structure in-place.
        
        Args:
            amplitude: Maximum perturbation amplitude (Angstroms)
            indices: Atom indices to perturb (default: all atoms).
                    Can be a list of indices or an AtomSelection object.
            seed: Random seed for reproducibility
            inplace: If True, modify this molecule in-place (default: True).
                    If False, return a new Molecule object.
        
        Returns:
            Molecule: Structure with perturbed positions (self if inplace=True, new object if inplace=False)
            
        Examples:
            >>> from matsimpy.core import Molecule
            >>> from matsimpy.utils.selection import AtomSelection
            >>> molecule = Molecule(['H', 'O', 'H'], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])
            >>> # Perturb all atoms by up to 0.1 Angstrom
            >>> molecule.perturb(0.1)
            >>> # Perturb specific atoms without modifying original
            >>> perturbed = molecule.perturb(0.1, indices=[0, 1], inplace=False)
            >>> # Perturb using AtomSelection
            >>> sel = AtomSelection(molecule).by_species('H')
            >>> molecule.perturb(0.1, indices=sel)
        """
        # Handle AtomSelection object
        from ..utils.selection import AtomSelection
        if isinstance(indices, AtomSelection):
            if indices.structure is not self:
                raise ValueError("AtomSelection must be created from this structure")
            indices = indices.indices
        
        from ..transformation.atomic import perturb_positions
        result = perturb_positions(self, amplitude, indices=indices, seed=seed, inplace=inplace)
        if inplace:
            # Update self with result's attributes
            self.positions = result.positions
            self._sites = result._sites
            self._cached_com = None  # Invalidate center of mass cache
            return self
        return result

