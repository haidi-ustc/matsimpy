"""
Symmetry analysis implementation for crystals and molecules.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
import os
import json

try:
    import spglib

    HAS_SPGLIB = True
except ImportError:
    HAS_SPGLIB = False
    spglib = None

from ..core import Crystal, Molecule, Lattice, Element


class SymmetryAnalyzer:
    """
    Analyze symmetry of crystal structures and molecules.

    For crystals: Determines space group, point group, and symmetry operations.
    For molecules: Determines point group.
    """

    def __init__(self, symprec: float = 1e-5, angle_tolerance: float = -1.0):
        """
        Initialize symmetry analyzer.

        Args:
            symprec: Symmetry search tolerance (default: 1e-5)
            angle_tolerance: Angle tolerance in degrees (default: -1.0 for automatic)
        """
        self.symprec = symprec
        self.angle_tolerance = angle_tolerance
        self._symmetry_data = None
        self._load_symmetry_data()

    def _load_symmetry_data(self):
        """Load symmetry data from YAML/JSON files."""
        try:
            # Load from same directory (symmetry folder)
            data_dir = os.path.dirname(__file__)
            json_path = os.path.join(data_dir, "symm_data.json")
            yaml_path = os.path.join(data_dir, "symm_data.yaml")

            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    self._symmetry_data = json.load(f)
            elif os.path.exists(yaml_path):
                try:
                    import yaml

                    with open(yaml_path, "r") as f:
                        self._symmetry_data = yaml.safe_load(f)
                except ImportError:
                    # Fallback: try to parse as JSON-like structure
                    self._symmetry_data = None
        except Exception:
            self._symmetry_data = None

    def analyze_crystal(self, crystal: Crystal) -> Dict[str, Any]:
        """
        Analyze crystal symmetry.

        Args:
            crystal: Crystal structure to analyze

        Returns:
            Dictionary containing:
            - space_group_number: International space group number
            - space_group_symbol: Space group symbol (Hermann-Mauguin)
            - point_group: Point group symbol
            - crystal_system: Crystal system name
            - hall_symbol: Hall symbol
            - wyckoff_positions: List of Wyckoff positions
            - symmetry_operations: List of symmetry operations
        """
        if not HAS_SPGLIB:
            raise ImportError(
                "spglib is required for crystal symmetry analysis. "
                "Install it with: pip install spglib"
            )

        # Convert crystal to spglib format
        lattice = crystal.lattice.lattice_vectors
        positions = crystal.frac_positions
        numbers = [self._element_to_number(spec) for spec in crystal.species]

        # Get space group information
        dataset = spglib.get_symmetry_dataset(
            (lattice, positions, numbers),
            symprec=self.symprec,
            angle_tolerance=self.angle_tolerance,
        )

        if dataset is None:
            return {
                "space_group_number": None,
                "space_group_symbol": None,
                "point_group": None,
                "crystal_system": None,
                "hall_symbol": None,
                "wyckoff_positions": [],
                "symmetry_operations": [],
            }

        # Handle both dict and object interface (spglib compatibility)
        if hasattr(dataset, "number"):
            # Object interface (newer spglib)
            space_group_number = int(dataset.number)
            space_group_symbol = dataset.international
            point_group = dataset.pointgroup
            hall_symbol = dataset.hall
            rotations = dataset.rotations
            translations = dataset.translations
            origin_shift = dataset.origin_shift
            equivalent_atoms = dataset.equivalent_atoms
            wyckoffs = getattr(dataset, "wyckoffs", [])
        else:
            # Dict interface (older spglib)
            space_group_number = int(dataset["number"])
            space_group_symbol = dataset["international"]
            point_group = dataset["pointgroup"]
            hall_symbol = dataset["hall"]
            rotations = dataset["rotations"]
            translations = dataset["translations"]
            origin_shift = dataset["origin_shift"]
            equivalent_atoms = dataset["equivalent_atoms"]
            wyckoffs = dataset.get("wyckoffs", [])

        # Get Wyckoff positions
        wyckoff = self._get_wyckoff_positions(
            crystal, {"equivalent_atoms": equivalent_atoms, "wyckoffs": wyckoffs}
        )

        return {
            "space_group_number": space_group_number,
            "space_group_symbol": space_group_symbol,
            "point_group": point_group,
            "crystal_system": self._get_crystal_system(space_group_number),
            "hall_symbol": hall_symbol,
            "wyckoff_positions": wyckoff,
            "symmetry_operations": self._format_symmetry_operations(
                {"rotations": rotations, "translations": translations}
            ),
            "rotation_matrices": (
                rotations.tolist() if hasattr(rotations, "tolist") else list(rotations)
            ),
            "translation_vectors": (
                translations.tolist()
                if hasattr(translations, "tolist")
                else list(translations)
            ),
            "origin_shift": (
                origin_shift.tolist()
                if hasattr(origin_shift, "tolist")
                else list(origin_shift)
            ),
            "equivalent_atoms": (
                equivalent_atoms.tolist()
                if hasattr(equivalent_atoms, "tolist")
                else list(equivalent_atoms)
            ),
        }

    def analyze_molecule(
        self, molecule: Molecule, tolerance: float = 0.1
    ) -> Dict[str, Any]:
        """
        Analyze molecule point group symmetry.

        Args:
            molecule: Molecule structure to analyze
            tolerance: Distance tolerance for symmetry detection (Angstroms)

        Returns:
            Dictionary containing:
            - point_group: Point group symbol
            - symmetry_operations: List of symmetry operations
            - rotation_axes: List of rotation axes
            - mirror_planes: List of mirror planes
            - inversion_center: Whether inversion center exists
            - order: Point group order
        """
        if self._symmetry_data is None:
            # Try to load data again
            self._load_symmetry_data()
            if self._symmetry_data is None:
                raise RuntimeError(
                    "Symmetry data not loaded. Cannot analyze molecule symmetry. "
                    "Make sure symm_data.json or symm_data.yaml exists in the symmetry directory."
                )

        # Center molecule at origin
        center = molecule.get_center_of_mass()
        centered_positions = molecule.positions - center

        # Detect point group
        point_group = self._detect_point_group(
            centered_positions, molecule.species, tolerance
        )

        # Get symmetry operations
        sym_ops = self._get_molecule_symmetry_operations(
            centered_positions, molecule.species, point_group, tolerance
        )

        return {
            "point_group": point_group,
            "symmetry_operations": sym_ops,
            "rotation_axes": self._find_rotation_axes(centered_positions, tolerance),
            "mirror_planes": self._find_mirror_planes(centered_positions, tolerance),
            "inversion_center": self._has_inversion_center(
                centered_positions, tolerance
            ),
            "order": self._get_point_group_order(point_group),
        }

    def _element_to_number(self, element: Union[str, int]) -> int:
        """
        Convert element symbol to atomic number.

        Uses the Element class from core.periodic_table for proper
        element-to-atomic-number conversion.
        """
        if isinstance(element, int):
            return element

        try:
            elem = Element.get_element(str(element))
            return elem.atomic_no
        except (ValueError, AttributeError):
            # Fallback: try to get from ELEMENTS list directly
            from ..core.periodic_table import ELEMENTS

            try:
                symbol = str(element).capitalize()
                if symbol in ELEMENTS:
                    return ELEMENTS.index(symbol) + 1
            except (ValueError, AttributeError):
                pass
            # Last resort: return 1 (H) if element not found
            return 1

    def _get_crystal_system(self, space_group_number: int) -> str:
        """Get crystal system from space group number."""
        if 1 <= space_group_number <= 2:
            return "Triclinic"
        elif 3 <= space_group_number <= 15:
            return "Monoclinic"
        elif 16 <= space_group_number <= 74:
            return "Orthorhombic"
        elif 75 <= space_group_number <= 142:
            return "Tetragonal"
        elif 143 <= space_group_number <= 167:
            return "Trigonal"
        elif 168 <= space_group_number <= 194:
            return "Hexagonal"
        elif 195 <= space_group_number <= 230:
            return "Cubic"
        else:
            return "Unknown"

    def _get_wyckoff_positions(self, crystal: Crystal, dataset: Dict) -> List[Dict]:
        """Get Wyckoff positions for crystal."""
        wyckoff_list = []
        equivalent_atoms = dataset["equivalent_atoms"]
        wyckoff_letters = dataset.get("wyckoffs", [])

        # Group atoms by Wyckoff position
        wyckoff_dict = {}
        for i, (wyckoff, equiv) in enumerate(zip(wyckoff_letters, equivalent_atoms)):
            if wyckoff not in wyckoff_dict:
                wyckoff_dict[wyckoff] = []
            wyckoff_dict[wyckoff].append(
                {
                    "atom_index": i,
                    "equivalent_index": int(equiv),
                    "position": crystal.frac_positions[i].tolist(),
                    "species": crystal.species[i],
                }
            )

        # Convert to list format
        for letter, atoms in sorted(wyckoff_dict.items()):
            wyckoff_list.append(
                {"letter": letter, "multiplicity": len(atoms), "atoms": atoms}
            )

        return wyckoff_list

    def _format_symmetry_operations(self, dataset: Dict) -> List[Dict]:
        """Format symmetry operations for output."""
        ops = []
        rotations = dataset["rotations"]
        translations = dataset["translations"]

        for rot, trans in zip(rotations, translations):
            ops.append({"rotation": rot.tolist(), "translation": trans.tolist()})

        return ops

    def _detect_point_group(
        self, positions: np.ndarray, species: List[str], tolerance: float
    ) -> str:
        """
        Detect point group for molecule.

        This is a simplified implementation. A full implementation would
        require more sophisticated symmetry detection algorithms.
        """
        n_atoms = len(positions)

        # Check for high symmetry cases
        if n_atoms == 1:
            return "Kh"  # Full spherical symmetry

        # Check for linear molecules
        if self._is_linear(positions, tolerance):
            # Check for center of inversion
            if self._has_inversion_center(positions, tolerance):
                return "D∞h"
            else:
                return "C∞v"

        # Check for spherical molecules (full symmetry)
        if self._is_spherical(positions, tolerance):
            return "Kh"

        # Check for tetrahedral symmetry
        if self._has_tetrahedral_symmetry(positions, tolerance):
            return "Td"

        # Check for octahedral symmetry
        if self._has_octahedral_symmetry(positions, tolerance):
            return "Oh"

        # Default: detect based on rotation axes and mirror planes
        rotation_axes = self._find_rotation_axes(positions, tolerance)
        mirror_planes = self._find_mirror_planes(positions, tolerance)
        has_inversion = self._has_inversion_center(positions, tolerance)

        # Determine point group from symmetry elements
        return self._point_group_from_elements(
            rotation_axes, mirror_planes, has_inversion
        )

    def _is_linear(self, positions: np.ndarray, tolerance: float) -> bool:
        """Check if molecule is linear."""
        if len(positions) < 3:
            return True

        # Check if all atoms are roughly collinear
        center = np.mean(positions, axis=0)
        centered = positions - center

        # Find principal axis
        _, _, v = np.linalg.svd(centered)
        principal_axis = v[0]

        # Check if all atoms are close to this axis
        for pos in centered:
            dist_to_axis = np.linalg.norm(
                pos - np.dot(pos, principal_axis) * principal_axis
            )
            if dist_to_axis > tolerance:
                return False

        return True

    def _is_spherical(self, positions: np.ndarray, tolerance: float) -> bool:
        """Check if molecule has spherical symmetry."""
        if len(positions) < 4:
            return False

        # Check if all atoms are roughly equidistant from center
        center = np.mean(positions, axis=0)
        distances = [np.linalg.norm(pos - center) for pos in positions]

        if len(set(np.round(distances, 2))) == 1:
            # Check multiple high-order rotation axes
            return True

        return False

    def _has_tetrahedral_symmetry(
        self, positions: np.ndarray, tolerance: float
    ) -> bool:
        """Check for tetrahedral (Td) symmetry."""
        if len(positions) != 4:
            return False

        # Check if 4 atoms form a tetrahedron
        center = np.mean(positions, axis=0)
        distances = [np.linalg.norm(pos - center) for pos in positions]

        # All atoms should be equidistant from center
        if len(set(np.round(distances, 1))) > 1:
            return False

        # Check distances between atoms (should be equal for tetrahedron)
        atom_distances = []
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.linalg.norm(positions[i] - positions[j])
                atom_distances.append(dist)

        # All edge lengths should be equal
        if len(set(np.round(atom_distances, 1))) > 1:
            return False

        return True

    def _has_octahedral_symmetry(self, positions: np.ndarray, tolerance: float) -> bool:
        """Check for octahedral (Oh) symmetry."""
        if len(positions) != 6:
            return False

        # Check if 6 atoms form an octahedron
        center = np.mean(positions, axis=0)
        distances = [np.linalg.norm(pos - center) for pos in positions]

        # All atoms should be equidistant from center
        if len(set(np.round(distances, 1))) > 1:
            return False

        return True

    def _find_rotation_axes(
        self, positions: np.ndarray, tolerance: float
    ) -> List[Dict]:
        """Find rotation axes in molecule."""
        axes = []
        center = np.mean(positions, axis=0)

        # Check for C2, C3, C4, C5, C6 axes
        for order in [2, 3, 4, 5, 6]:
            axis = self._find_rotation_axis(positions, center, order, tolerance)
            if axis is not None:
                axes.append({"order": order, "axis": axis.tolist()})

        return axes

    def _find_rotation_axis(
        self, positions: np.ndarray, center: np.ndarray, order: int, tolerance: float
    ) -> Optional[np.ndarray]:
        """Find rotation axis of given order."""
        # Simplified: check common axes
        test_axes = [
            np.array([1, 0, 0]),
            np.array([0, 1, 0]),
            np.array([0, 0, 1]),
            np.array([1, 1, 0]) / np.sqrt(2),
            np.array([1, 0, 1]) / np.sqrt(2),
            np.array([0, 1, 1]) / np.sqrt(2),
        ]

        for axis in test_axes:
            if self._has_rotation_symmetry(positions, center, axis, order, tolerance):
                return axis

        return None

    def _has_rotation_symmetry(
        self,
        positions: np.ndarray,
        center: np.ndarray,
        axis: np.ndarray,
        order: int,
        tolerance: float,
    ) -> bool:
        """Check if molecule has rotation symmetry around given axis."""
        angle = 2 * np.pi / order
        rotation_matrix = self._rotation_matrix(axis, angle)

        # Check if rotating positions yields equivalent structure
        rotated = (positions - center) @ rotation_matrix.T + center

        # Check if rotated positions match original (within tolerance)
        for orig_pos in positions:
            matched = False
            for rot_pos in rotated:
                if np.linalg.norm(orig_pos - rot_pos) < tolerance:
                    matched = True
                    break
            if not matched:
                return False

        return True

    def _rotation_matrix(self, axis: np.ndarray, angle: float) -> np.ndarray:
        """Generate rotation matrix for rotation around axis by angle."""
        axis = axis / np.linalg.norm(axis)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        # Rodriguez formula
        K = np.array(
            [[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]]
        )

        R = np.eye(3) * cos_a + sin_a * K + (1 - cos_a) * np.outer(axis, axis)

        return R

    def _find_mirror_planes(
        self, positions: np.ndarray, tolerance: float
    ) -> List[Dict]:
        """Find mirror planes in molecule."""
        planes = []
        center = np.mean(positions, axis=0)

        # Check common mirror planes
        test_normals = [
            np.array([1, 0, 0]),
            np.array([0, 1, 0]),
            np.array([0, 0, 1]),
            np.array([1, 1, 0]) / np.sqrt(2),
        ]

        for normal in test_normals:
            if self._has_mirror_symmetry(positions, center, normal, tolerance):
                planes.append({"normal": normal.tolist()})

        return planes

    def _has_mirror_symmetry(
        self,
        positions: np.ndarray,
        center: np.ndarray,
        normal: np.ndarray,
        tolerance: float,
    ) -> bool:
        """Check if molecule has mirror symmetry."""
        # Reflect positions across plane
        reflected = positions.copy()
        for i, pos in enumerate(positions):
            vec = pos - center
            # Reflect across plane: r' = r - 2*(r·n)*n
            reflected[i] = pos - 2 * np.dot(vec, normal) * normal

        # Check if reflected positions match original
        for orig_pos in positions:
            matched = False
            for ref_pos in reflected:
                if np.linalg.norm(orig_pos - ref_pos) < tolerance:
                    matched = True
                    break
            if not matched:
                return False

        return True

    def _has_inversion_center(self, positions: np.ndarray, tolerance: float) -> bool:
        """Check if molecule has inversion center."""
        center = np.mean(positions, axis=0)

        # Check if inverting through center gives equivalent structure
        inverted = 2 * center - positions

        # Check if inverted positions match original
        for orig_pos in positions:
            matched = False
            for inv_pos in inverted:
                if np.linalg.norm(orig_pos - inv_pos) < tolerance:
                    matched = True
                    break
            if not matched:
                return False

        return True

    def _point_group_from_elements(
        self, rotation_axes: List[Dict], mirror_planes: List[Dict], has_inversion: bool
    ) -> str:
        """Determine point group from symmetry elements."""
        # Simplified point group detection
        if has_inversion and len(rotation_axes) > 0:
            max_order = max([ax["order"] for ax in rotation_axes])
            if max_order >= 6:
                return "Oh" if len(mirror_planes) > 3 else "Ih"
            elif max_order >= 4:
                return "Oh" if len(mirror_planes) > 3 else "D4h"
            elif max_order >= 3:
                return "D3d" if len(mirror_planes) > 0 else "D3"
            elif max_order == 2:
                return "D2h" if len(mirror_planes) > 0 else "D2"

        if len(rotation_axes) > 0:
            max_order = max([ax["order"] for ax in rotation_axes])
            if max_order >= 4:
                return "D4" if len(mirror_planes) > 0 else "C4"
            elif max_order >= 3:
                return "D3" if len(mirror_planes) > 0 else "C3"
            elif max_order == 2:
                return "D2" if len(mirror_planes) > 0 else "C2"

        if len(mirror_planes) > 0:
            return "Cs"

        return "C1"  # No symmetry

    def _get_point_group_order(self, point_group: str) -> int:
        """Get order of point group from symmetry data if available."""
        # Try to get from space group encoding data
        if self._symmetry_data and "space_group_encoding" in self._symmetry_data:
            # Search for space groups with this point group
            for sg_data in self._symmetry_data["space_group_encoding"].values():
                if sg_data.get("point_group") == point_group:
                    return sg_data.get("order", 1)

        # Fallback to hardcoded map
        order_map = {
            "C1": 1,
            "Ci": 2,
            "Cs": 2,
            "C2": 2,
            "C3": 3,
            "C4": 4,
            "C5": 5,
            "C6": 6,
            "C2v": 4,
            "C3v": 6,
            "C4v": 8,
            "C5v": 10,
            "C6v": 12,
            "C2h": 4,
            "C3h": 6,
            "C4h": 8,
            "C5h": 10,
            "C6h": 12,
            "D2": 4,
            "D3": 6,
            "D4": 8,
            "D5": 10,
            "D6": 12,
            "D2h": 8,
            "D3h": 12,
            "D4h": 16,
            "D5h": 20,
            "D6h": 24,
            "D2d": 8,
            "D3d": 12,
            "D4d": 16,
            "D5d": 20,
            "D6d": 24,
            "S2": 2,
            "S4": 4,
            "S6": 6,
            "S8": 8,
            "T": 12,
            "Th": 24,
            "Td": 24,
            "O": 24,
            "Oh": 48,
            "I": 60,
            "Ih": 120,
            "C∞v": float("inf"),
            "D∞h": float("inf"),
            "Kh": float("inf"),
        }
        return order_map.get(point_group, 1)

    def get_space_group_info(self, space_group_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get space group information from symmetry data.

        Args:
            space_group_symbol: Space group symbol (e.g., 'Pm-3m', 'Fd-3m')

        Returns:
            Dictionary with space group information or None if not found
        """
        if self._symmetry_data is None:
            self._load_symmetry_data()

        if self._symmetry_data and "space_group_encoding" in self._symmetry_data:
            return self._symmetry_data["space_group_encoding"].get(space_group_symbol)

        return None

    def get_point_group_encoding(self, point_group: str) -> Optional[str]:
        """
        Get point group encoding from symmetry data.

        Args:
            point_group: Point group symbol (e.g., 'm-3m', 'mm2')

        Returns:
            Encoding string or None if not found
        """
        if self._symmetry_data is None:
            self._load_symmetry_data()

        if self._symmetry_data and "point_group_encoding" in self._symmetry_data:
            return self._symmetry_data["point_group_encoding"].get(point_group)

        return None

    def get_generator_matrix(self, generator_name: str) -> Optional[np.ndarray]:
        """
        Get generator matrix from symmetry data.

        Args:
            generator_name: Generator name (e.g., 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n')

        Returns:
            Generator matrix as numpy array or None if not found
        """
        if self._symmetry_data is None:
            self._load_symmetry_data()

        if self._symmetry_data and "generator_matrices" in self._symmetry_data:
            gen_data = self._symmetry_data["generator_matrices"].get(generator_name)
            if gen_data:
                return np.array(gen_data)

        return None

    def _get_molecule_symmetry_operations(
        self,
        positions: np.ndarray,
        species: List[str],
        point_group: str,
        tolerance: float,
    ) -> List[Dict]:
        """Get symmetry operations for molecule."""
        ops = []
        center = np.mean(positions, axis=0)

        # Identity operation
        ops.append(
            {
                "type": "identity",
                "rotation": np.eye(3).tolist(),
                "translation": [0, 0, 0],
            }
        )

        # Add rotation operations
        rotation_axes = self._find_rotation_axes(positions, tolerance)
        for axis_info in rotation_axes:
            order = axis_info["order"]
            axis = np.array(axis_info["axis"])
            for n in range(1, order):
                angle = 2 * np.pi * n / order
                rot_matrix = self._rotation_matrix(axis, angle)
                ops.append(
                    {
                        "type": f"rotation_{order}",
                        "rotation": rot_matrix.tolist(),
                        "translation": [0, 0, 0],
                        "axis": axis.tolist(),
                        "angle": np.degrees(angle),
                    }
                )

        # Add mirror operations
        mirror_planes = self._find_mirror_planes(positions, tolerance)
        for plane_info in mirror_planes:
            normal = np.array(plane_info["normal"])
            # Reflection matrix: I - 2*n*n^T
            refl_matrix = np.eye(3) - 2 * np.outer(normal, normal)
            ops.append(
                {
                    "type": "mirror",
                    "rotation": refl_matrix.tolist(),
                    "translation": [0, 0, 0],
                    "normal": normal.tolist(),
                }
            )

        # Add inversion if present
        if self._has_inversion_center(positions, tolerance):
            ops.append(
                {
                    "type": "inversion",
                    "rotation": (-np.eye(3)).tolist(),
                    "translation": [0, 0, 0],
                }
            )

        return ops


def analyze_symmetry(
    structure: Union[Crystal, Molecule],
    symprec: float = 1e-5,
    angle_tolerance: float = -1.0,
    tolerance: float = 0.1,
) -> Dict[str, Any]:
    """
    Convenience function to analyze symmetry of a structure.

    Args:
        structure: Crystal or Molecule structure
        symprec: Symmetry precision for crystals (default: 1e-5)
        angle_tolerance: Angle tolerance for crystals (default: -1.0)
        tolerance: Distance tolerance for molecules (default: 0.1 Angstroms)

    Returns:
        Dictionary with symmetry information

    Examples:
        >>> from matsimpy import Crystal, Lattice
        >>> crystal = Crystal(['Si', 'Si'], [[0,0,0], [0.25,0.25,0.25]],
        ...                   Lattice.cubic(5.43))
        >>> result = analyze_symmetry(crystal)
        >>> print(result['space_group_symbol'])
        'Fd-3m'
    """
    analyzer = SymmetryAnalyzer(symprec=symprec, angle_tolerance=angle_tolerance)

    if isinstance(structure, Crystal):
        return analyzer.analyze_crystal(structure)
    elif isinstance(structure, Molecule):
        return analyzer.analyze_molecule(structure, tolerance=tolerance)
    else:
        raise TypeError(f"Unsupported structure type: {type(structure)}")


def get_conventional_cell(
    crystal: Crystal, symprec: float = 1e-5, angle_tolerance: float = -1.0
) -> Crystal:
    """
    Get the standard conventional cell of a crystal structure.

    Uses spglib to standardize the cell to the conventional cell representation
    according to the International Tables for Crystallography.

    Args:
        crystal: Crystal structure to convert
        symprec: Symmetry search tolerance (default: 1e-5)
        angle_tolerance: Angle tolerance in degrees (default: -1.0 for automatic)

    Returns:
        Crystal: New Crystal object with standardized conventional cell

    Examples:
        >>> from matsimpy.builders.bulk import from_prototype
        >>> from matsimpy.symmetry import get_conventional_cell
        >>> # Start with primitive cell
        >>> primitive = from_prototype('diamond', 'Si', 5.43)
        >>> print(len(primitive))  # 2 atoms (primitive)
        2
        >>> # Get conventional cell
        >>> conventional = get_conventional_cell(primitive)
        >>> print(len(conventional))  # 8 atoms (conventional)
        8
    """
    try:
        import spglib
    except ImportError:
        raise ImportError(
            "spglib is required for conventional cell conversion. "
            "Install it with: pip install spglib"
        )

    from ..core import Element, Lattice

    # Convert crystal to spglib format
    lattice = crystal.lattice.lattice_vectors
    positions = crystal.frac_positions
    # Get atomic numbers for spglib
    numbers = [elem.atomic_no for elem in crystal.elements]

    # Get standardized conventional cell
    cell = (lattice, positions, numbers)
    std_cell = spglib.standardize_cell(
        cell, symprec=symprec, angle_tolerance=angle_tolerance
    )

    if std_cell is None:
        # If standardization fails, return a copy of the original
        return crystal.copy()

    std_lattice, std_positions, std_numbers = std_cell

    # Convert atomic numbers back to species
    std_species = [Element.from_Z(n).symbol for n in std_numbers]

    # Create new crystal with conventional cell
    conventional = Crystal(
        species=std_species,
        positions=std_positions.tolist(),
        lattice=Lattice(std_lattice),
        pbc=crystal.pbc.copy() if hasattr(crystal.pbc, "copy") else list(crystal.pbc),
        coords_are_cartesian=False,
    )

    # Copy site properties if they exist and match atom count
    if hasattr(crystal, "site_properties") and len(crystal.site_properties) == len(
        crystal.species
    ):
        # Map site properties (this is approximate - may need refinement)
        conventional.site_properties = [{}] * len(conventional.species)

    return conventional
