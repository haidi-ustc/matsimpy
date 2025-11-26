import numpy as np
import warnings
from typing import List, Optional, Dict, Any, Union, Tuple
from monty.json import MSONable
from .lattice import Lattice
from .structure import Structure
from .crystal import Crystal
from .composition import Composition
from .periodic_table import Element
from .site import Site
from scipy.spatial.distance import cdist


class Molecule(Structure):
    """
    A class representing a molecule.

    Args:
        species (List[str]): A list of atomic symbols.
        positions (List[List[float]]): A list of atomic positions.
    """

    def __init__(
        self,
        species: List[str],
        positions: List[List[float]],
        site_properties: Optional[List[Dict[str, Any]]] = None,
    ):
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
            return [
                Site(position=pos, specie=spec, properties=props)
                for pos, spec, props in zip(
                    self.positions, self.species, self.site_properties
                )
            ]
        else:
            return [
                Site(position=pos, specie=spec)
                for pos, spec in zip(self.positions, self.species)
            ]

    @property
    def sites(self) -> List[Site]:
        return self._sites

    def __getitem__(self, item):
        return self.sites[item]

    def get_center_of_mass(self) -> List[float]:
        """
        Calculate center of mass of the molecule with caching.

        Computes weighted average of atomic positions using atomic masses.
        Result is cached for performance - invalidated when structure changes.

        Returns:
            Center of mass coordinates as [x, y, z] in Angstroms.

        Examples:
            >>> molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
            >>> com = molecule.get_center_of_mass()
            >>> print(com)  # Weighted average based on C and O masses
        """
        if not hasattr(self, "_cached_com") or self._cached_com is None:
            # Use cached Element instances for better performance
            masses = np.array(
                [Element.get_element(specie).atomic_mass for specie in self.species]
            )
            center_of_mass = np.average(self.positions, weights=masses, axis=0)
            self._cached_com = center_of_mass.tolist()
        return self._cached_com

    def translate(self, vector: List[float]) -> None:
        """
        Translate the molecule by a given vector (in-place).

        Args:
            vector: Translation vector [dx, dy, dz] in Angstroms.

        Examples:
            >>> molecule.translate([1.0, 0.0, 0.0])  # Move 1 Å along x-axis
        """
        self.positions += np.array(vector)
        # Invalidate center of mass cache
        if hasattr(self, "_cached_com"):
            self._cached_com = None
        # Update sites
        self._sites = self._initialize_sites()

    def rotate(self, angle: float, axis: List[float]) -> None:
        """
        Rotate the molecule around an axis (in-place).

        Args:
            angle: Rotation angle in degrees.
            axis: Rotation axis vector [x, y, z] (will be normalized).

        Examples:
            >>> molecule.rotate(90, [0, 0, 1])  # 90° rotation around z-axis
        """
        from scipy.spatial.transform import Rotation

        rotation = Rotation.from_rotvec(np.radians(angle) * np.array(axis))
        self.positions = rotation.apply(self.positions)
        # Invalidate center of mass cache
        if hasattr(self, "_cached_com"):
            self._cached_com = None
        # Update sites
        self._sites = self._initialize_sites()

    def add_atom(
        self,
        species: Union[str, List[str]],
        position: Union[List[float], List[List[float]]],
        site_properties: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    ) -> None:
        """
        Add one or more atoms to the molecule and update sites.

        Performs chemical reasonableness checks on interatomic distances.
        Prevents adding duplicate atoms at the same position or atoms that are too close.

        Args:
            species: Atomic species (single string or list of strings).
            position: Atomic position(s). Either a single 3D coordinate or list of coordinates.
            site_properties: Optional site properties (single dict or list of dicts).
                           If list, must match length of species.

        Raises:
            ValueError: If site_properties length doesn't match number of atoms added.
            ValueError: If duplicate positions are detected (distance < 1e-6 Å).
            ValueError: If atoms are too close (distance < 0.5 Å).

        Examples:
            >>> molecule.add_atom('H', [0, 0, 0])  # Add single atom
            >>> molecule.add_atom(['H', 'O'], [[0, 0, 0], [1.2, 0, 0]])  # Add multiple
            >>> molecule.add_atom(['H', 'O'], [[0, 0, 0], [1.2, 0, 0]],
            ...                   [{'charge': 1}, {'charge': -2}])  # With properties
        """
        # Chemical reasonableness check - validate interatomic distances
        # Convert to array for processing
        if isinstance(position, list):
            if len(position) == 0:
                # Empty list - nothing to check
                new_positions = []
            elif isinstance(position[0], (int, float)):
                # Single position [x, y, z]
                new_positions = [position]
            else:
                # Multiple positions [[x1,y1,z1], [x2,y2,z2], ...]
                new_positions = position
        else:
            new_positions = [position]

        # Check for duplicates within new positions
        if len(new_positions) > 1:
            new_positions_array = np.array(new_positions, dtype=np.float64)
            # Check pairwise distances within new positions
            for i in range(len(new_positions_array)):
                for j in range(i + 1, len(new_positions_array)):
                    dist = np.linalg.norm(
                        new_positions_array[i] - new_positions_array[j]
                    )
                    if dist < 1e-6:  # Essentially zero distance (duplicate)
                        raise ValueError(
                            f"Duplicate positions detected in new atoms: "
                            f"positions {i} and {j} are at the same location "
                            f"({new_positions[i]})."
                        )
                    elif dist < 0.5:  # Too close
                        raise ValueError(
                            f"Atoms being added are too close: distance between "
                            f"positions {i} and {j} is {dist:.6f} Å. "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Check each new position against existing atoms
        if len(self.positions) > 0:
            for idx, new_pos in enumerate(new_positions):
                if len(new_pos) == 3:  # Valid 3D position
                    new_pos_array = np.array(new_pos, dtype=np.float64).reshape(1, 3)
                    min_distance = np.min(cdist(new_pos_array, self.positions))

                    # Raise error for duplicates or too close
                    if min_distance < 1e-6:  # Essentially zero distance (duplicate)
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: atom already exists "
                            f"at this location (distance: {min_distance:.6f} Å)."
                        )
                    elif min_distance < 0.5:  # Too close
                        raise ValueError(
                            f"Cannot add atom at position {new_pos}: too close to existing "
                            f"atom (distance: {min_distance:.6f} Å). "
                            f"Minimum allowed distance is 0.5 Angstrom."
                        )

        # Determine number of atoms being added
        n_atoms_before = len(self.species)

        # Call parent to add atoms
        super().add_atom(species, position)

        n_atoms_added = len(self.species) - n_atoms_before

        # Invalidate center of mass cache
        if hasattr(self, "_cached_com"):
            self._cached_com = None

        # Update site properties
        if site_properties is not None:
            # Normalize to list
            if isinstance(site_properties, dict):
                site_properties_list = [site_properties] * n_atoms_added
            else:
                site_properties_list = site_properties

            # Validate length
            if len(site_properties_list) != n_atoms_added:
                raise ValueError(
                    f"Number of site_properties ({len(site_properties_list)}) "
                    f"must match number of atoms added ({n_atoms_added})"
                )

            # Initialize site_properties if needed
            if not self.site_properties:
                self.site_properties = [{}] * n_atoms_before

            self.site_properties.extend(site_properties_list)
        elif self.site_properties:
            # Maintain existing site_properties with empty dicts
            self.site_properties.extend([{}] * n_atoms_added)

        # Reinitialize sites
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

    def substitute(
        self,
        indices: Union[int, List[int], "AtomSelection"],
        new_species: Union[str, List[str], Dict[str, str]],
    ) -> None:
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
        # Call parent implementation to handle the actual substitution
        # and cache invalidation (formula, composition)
        super().substitute(indices, new_species)

        # Molecule-specific updates: reinitialize sites with updated species
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
            [0.0, 0.0, box_size[2]],
        ]

        # Create Crystal with Cartesian coordinates
        crystal = Crystal(
            list(self.species),
            centered_positions.tolist(),
            Lattice(lattice_vectors),
            coords_are_cartesian=True,
        )

        return crystal

    def __str__(self):
        """
        Human-readable string representation of Molecule.

        Note: Atoms are displayed in their original insertion order to match
        the internal structure (species, positions). Use sort_atoms() if you
        want to actually reorder the internal data.
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

        # Display sites in insertion order to match internal species ordering
        display_sites = list(self.sites)

        rows = []
        for site in display_sites:
            element = str(site.specie)
            cart_coords = f"({site.position[0]:.4f}, {site.position[1]:.4f}, {site.position[2]:.4f})"
            row = [element, cart_coords]
            if has_properties:
                props_str = (
                    ", ".join(f"{k}={v}" for k, v in site.properties.items())
                    if site.properties
                    else ""
                )
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
            moment_tensor[0, 0] += masses[i] * (r[1] ** 2 + r[2] ** 2)
            moment_tensor[1, 1] += masses[i] * (r[0] ** 2 + r[2] ** 2)
            moment_tensor[2, 2] += masses[i] * (r[0] ** 2 + r[1] ** 2)
            moment_tensor[0, 1] -= masses[i] * r[0] * r[1]
            moment_tensor[0, 2] -= masses[i] * r[0] * r[2]
            moment_tensor[1, 2] -= masses[i] * r[1] * r[2]
            moment_tensor[1, 0] = moment_tensor[0, 1]
            moment_tensor[2, 0] = moment_tensor[0, 2]
            moment_tensor[2, 1] = moment_tensor[1, 2]
        # eigenvalues, eigenvectors = np.linalg.eigh(moment_tensor)
        return moment_tensor

    def get_neighbor_list(
        self, cutoff: float, atom_index: Optional[int] = None, **kwargs
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Get neighbor list with consistent interface.

        Args:
            cutoff: Cutoff radius in Angstroms.
            atom_index: Optional atom index. If None, returns neighbors for all atoms.
                       If specified, returns neighbors only for that atom.
            **kwargs: Ignored (for compatibility with Crystal interface)

        Returns:
            Dict mapping atom index to list of (neighbor_index, distance) tuples.
            If atom_index is provided, dict contains only that entry.
            If atom_index is None, dict contains entries for all atoms.

        Raises:
            IndexError: If atom_index is out of range.

        Examples:
            >>> molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
            >>> # Get neighbors for specific atom
            >>> neighbors = molecule.get_neighbor_list(2.0, atom_index=0)
            >>> print(neighbors)  # {0: [(1, 1.2)]} - atom 1 is within 2.0 Å
            >>> # Get neighbors for all atoms
            >>> all_neighbors = molecule.get_neighbor_list(2.0)
            >>> print(all_neighbors)  # {0: [(1, 1.2)], 1: [(0, 1.2)]}
        """
        if atom_index is not None:
            # Single atom query
            if not (0 <= atom_index < len(self)):
                raise IndexError(
                    f"Atom index {atom_index} is out of range [0, {len(self)-1}]"
                )

            distances = cdist([self.positions[atom_index]], self.positions)[0]
            neighbors = [
                (i, float(d))
                for i, d in enumerate(distances)
                if d < cutoff and i != atom_index
            ]
            return {atom_index: neighbors}
        else:
            # All atoms query
            distances = cdist(self.positions, self.positions)
            neighbors_dict = {}
            for i in range(len(self)):
                neighbors = [
                    (j, float(distances[i, j]))
                    for j in range(len(self))
                    if distances[i, j] < cutoff and j != i
                ]
                neighbors_dict[i] = neighbors
            return neighbors_dict

    def get_all_neighbor_lists(self, cutoff: float) -> List[List[int]]:
        """
        Get neighbor lists for all atoms using vectorized operations.

        Optimized implementation using distance matrix and vectorization
        instead of loop-based approach. Much faster for large molecules.

        Args:
            cutoff: Cutoff radius in Angstroms.

        Returns:
            List of neighbor lists for all atoms. Each inner list contains
            indices of neighbors within cutoff distance of that atom.

        Raises:
            ValueError: If cutoff is negative.

        Examples:
            >>> molecule = Molecule(['C', 'O', 'H'], [[0,0,0], [1.2,0,0], [2.5,0,0]])
            >>> all_neighbors = molecule.get_all_neighbor_lists(2.0)
            >>> print(all_neighbors)  # [[1], [0], []]

        Notes:
            - Uses vectorized operations for better performance
            - Time complexity: O(n²) for distance matrix, but vectorized
            - Memory complexity: O(n²) for distance matrix
            - For n > 1000 atoms, consider using spatial trees
        """
        if cutoff < 0:
            raise ValueError(f"Cutoff must be non-negative, got {cutoff}")

        if len(self.positions) == 0:
            return []

        # Use vectorized operations for performance
        positions = np.array(self.positions)

        # Compute all pairwise distances at once
        distance_matrix = cdist(positions, positions)

        # Ignore self-distances by setting diagonal to infinity
        np.fill_diagonal(distance_matrix, np.inf)

        # Find neighbors using vectorized operations
        neighbor_lists = []
        for i in range(len(positions)):
            # Use boolean mask for efficient filtering
            mask = distance_matrix[i] < cutoff
            neighbors = np.where(mask)[0].tolist()
            neighbor_lists.append(neighbors)

        return neighbor_lists

    @classmethod
    def from_file(
        cls, filename: str, format: Optional[str] = None, **kwargs
    ) -> "Molecule":
        """
        Create a Molecule from a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json

        This method uses the high-level read() interface. For more control,
        use matsimpy.io.read() directly.

        Args:
            filename: Path to the structure file
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
            **kwargs: Additional arguments passed to the format-specific reader
                     (e.g., as_crystal for PDB format)

        Returns:
            Molecule: Molecule structure from the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is not supported or file format is invalid
            TypeError: If file contains a Crystal instead of Molecule

        Examples:
            >>> molecule = Molecule.from_file('molecule.xyz')
            >>> molecule = Molecule.from_file('molecule.pdb', as_crystal=False)
        """
        from ..io import read
        from ..core import Crystal

        result = read(filename, format=format, **kwargs)

        # Ensure we return a Molecule
        if isinstance(result, Crystal):
            # Convert crystal to molecule if needed
            # Preserve site properties if available
            site_props = getattr(result, "site_properties", None)
            return cls(
                result.species,
                result.cart_positions.tolist(),
                site_properties=site_props,
            )

        if not isinstance(result, Molecule):
            raise TypeError(
                f"File contains {type(result).__name__}, not Molecule. "
                f"Use Crystal.from_file() for crystal structures."
            )

        return result

    def to_file(self, filename: str, format: Optional[str] = None, **kwargs) -> None:
        """
        Write Molecule to a file.

        Automatically detects file format from extension if not specified.
        Supported formats: .xyz, .pdb, .mol, .json

        This method uses the high-level write() interface. For more control,
        use matsimpy.io.write() directly.

        Args:
            filename: Output filename
            format: Optional format specification (e.g., 'xyz', 'pdb').
                   If None, format is detected from file extension.
            **kwargs: Additional arguments passed to the format-specific writer
                     (e.g., title for file headers)

        Raises:
            ValueError: If format is not supported

        Examples:
            >>> molecule.to_file('molecule.xyz')
            >>> molecule.to_file('molecule.pdb', title='Water')
        """
        from ..io import write

        write(self, filename, format=format, **kwargs)

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
            write_input = interface["write_input"]
            write_input(self, filename, **kwargs)
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

    @classmethod
    def from_code(cls, code: str, filename: str, **kwargs) -> "Molecule":
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
            read_output = interface["read_output"]
            # TODO: Implement output parsing
            raise NotImplementedError(
                f"Reading {code} output files not yet implemented"
            )
        except ValueError as e:
            raise ValueError(f"Unsupported DFT code: {code}") from e

    @property
    def calc(self):
        """
        Get attached calculator.

        Returns:
            Calculator or None: The attached calculator, or None if none attached
        """
        return getattr(self, "_calculator", None)

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
            raise ValueError(
                "No calculator attached. Set molecule.calc = calculator first."
            )
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
            raise ValueError(
                "No calculator attached. Set molecule.calc = calculator first."
            )
        if not self.calc._calculation_performed:
            self.calc.calculate(self)
        return self.calc.get_forces()

    def perturb(
        self,
        amplitude: float,
        indices: Optional[Union[List[int], "AtomSelection"]] = None,
        seed: Optional[int] = None,
        inplace: bool = True,
    ) -> "Molecule":
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

        result = perturb_positions(
            self, amplitude, indices=indices, seed=seed, inplace=inplace
        )
        if inplace:
            # Update self with result's attributes
            self.positions = result.positions
            self._sites = result._sites
            self._cached_com = None  # Invalidate center of mass cache
            return self
        return result
