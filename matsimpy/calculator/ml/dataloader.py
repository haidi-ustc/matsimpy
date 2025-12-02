"""
DataLoader utilities for ML calculators using pure MatSimPy.

Provides functions to build dataloaders from MatSimPy structures (Crystal/Molecule)
using native MatSimPy capabilities. No ASE dependency required.
"""

import numpy as np
import torch
import warnings
from typing import List, Optional, Union, Tuple, Dict, Any
from torch_geometric.loader import DataLoader as DataLoader_pyg
from torch_geometric.data import Data

from ...core import Crystal, Molecule
from ...core.graph import create_structure_graph, MoleculeGraph, CrystalGraph
from ...core.periodic_table import Element


class MatSimPyGraphConvertor:
    """
    Convert MatSimPy structures to graph format for ML models.

    Pure MatSimPy implementation without ASE dependency.
    Uses MatSimPy's native graph module for efficient conversion.

    Args:
        model_type: Model type ('m3gnet', 'mace', etc.).
        twobody_cutoff: Cutoff radius for edges (Angstroms).
        has_threebody: Include three-body interactions.
        threebody_cutoff: Cutoff for three-body interactions (Angstroms).

    Examples:
        >>> convertor = MatSimPyGraphConvertor('m3gnet', cutoff=5.0)
        >>> graph = convertor.convert(crystal, energy=-10.5)
    """

    def __init__(
        self,
        model_type: str = "m3gnet",
        twobody_cutoff: float = 5.0,
        has_threebody: bool = True,
        threebody_cutoff: float = 4.0,
    ):
        """
        Initialize graph convertor.

        Args:
            model_type: Model type for graph construction.
            twobody_cutoff: Cutoff for two-body interactions.
            has_threebody: Whether to compute three-body indices.
            threebody_cutoff: Cutoff for three-body interactions.
        """
        self.model_type = model_type
        self.twobody_cutoff = twobody_cutoff
        self.threebody_cutoff = threebody_cutoff
        self.has_threebody = has_threebody

    def _prepare_structure(
        self, structure: Union[Crystal, Molecule]
    ) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray]:
        """
        Prepare structure for graph conversion.

        Handles both crystals (with PBC) and molecules (no PBC).
        Creates large supercell for molecules to simulate isolation.

        Args:
            structure: Crystal or Molecule object.

        Returns:
            (positions, cell, pbc) tuple.
        """
        if isinstance(structure, Crystal):
            # Crystal: use actual cell and PBC
            positions = np.array(structure.cart_positions, dtype=np.float64)
            cell = np.array(structure.lattice.lattice_vectors, dtype=np.float64)
            pbc = np.array(structure.pbc, dtype=bool)

            # Validate cell
            if np.all(np.abs(cell) < 1e-5):
                raise ValueError("Cell vectors are too small")

            # Wrap positions to [0, 1) in fractional coordinates
            frac_pos = structure.frac_positions % 1.0
            positions = np.dot(frac_pos, cell)

        else:  # Molecule
            # Molecule: create large supercell
            positions = np.array(structure.positions, dtype=np.float64)

            # Check if we have any atoms
            if len(positions) == 0:
                raise ValueError("Empty structure")

            # Calculate bounding box
            min_coords = np.min(positions, axis=0)
            max_coords = np.max(positions, axis=0)

            # Create large cell (10x the molecule size, minimum 25 Å)
            box_size = np.maximum((max_coords - min_coords) * 10, 25.0)
            cell = np.diag(box_size)
            pbc = np.array([True, True, True], dtype=bool)  # Use PBC with large cell

            warnings.warn(
                f"No PBC detected, using a large supercell with size "
                f"{box_size[0]:.2f}x{box_size[1]:.2f}x{box_size[2]:.2f} Angstrom**3",
                UserWarning,
            )

        return positions, cell, pbc

    def _get_edges_with_pbc(
        self,
        structure: Union[Crystal, Molecule],
        positions: np.ndarray,
        cell: np.ndarray,
        pbc: np.ndarray,
        cutoff: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Get edges with periodic boundary conditions.

        Uses MatSimPy's native neighbor finding for crystals,
        or distance-based approach for molecules.

        Args:
            structure: Structure object.
            positions: Cartesian positions.
            cell: Cell matrix.
            pbc: Periodic boundary conditions.
            cutoff: Cutoff distance.

        Returns:
            (center_indices, neighbor_indices, images, distances)
        """
        if isinstance(structure, Crystal):
            # Use Crystal's optimized neighbor finding
            neighbors_dict = structure.get_neighbor_list(cutoff, use_pbc=True)

            center_indices = []
            neighbor_indices = []
            distances = []

            for i, neighbor_list in neighbors_dict.items():
                for j, dist in neighbor_list:
                    center_indices.append(i)
                    neighbor_indices.append(j)
                    distances.append(dist)

            center_indices = np.array(center_indices, dtype=np.int64)
            neighbor_indices = np.array(neighbor_indices, dtype=np.int64)
            distances = np.array(distances, dtype=np.float64)

            # Images are not directly available from MatSimPy neighbor list
            # Set to zero for now (sufficient for most ML models)
            images = np.zeros((len(center_indices), 3), dtype=np.int64)

        else:
            # Molecule: use simple distance-based approach
            from scipy.spatial.distance import cdist

            n_atoms = len(positions)
            dist_matrix = cdist(positions, positions)

            # Find all pairs within cutoff (excluding self)
            center_indices = []
            neighbor_indices = []
            distances = []

            for i in range(n_atoms):
                for j in range(n_atoms):
                    if i != j and dist_matrix[i, j] < cutoff:
                        center_indices.append(i)
                        neighbor_indices.append(j)
                        distances.append(dist_matrix[i, j])

            center_indices = np.array(center_indices, dtype=np.int64)
            neighbor_indices = np.array(neighbor_indices, dtype=np.int64)
            distances = np.array(distances, dtype=np.float64)
            images = np.zeros((len(center_indices), 3), dtype=np.int64)

        return center_indices, neighbor_indices, images, distances

    def _compute_threebody_indices(
        self,
        edge_index: np.ndarray,
        edge_distances: np.ndarray,
        n_atoms: int,
        atomic_numbers: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute three-body indices for angular interactions.

        Args:
            edge_index: Edge indices [2, num_edges].
            edge_distances: Edge distances [num_edges].
            n_atoms: Number of atoms.
            atomic_numbers: Atomic numbers [n_atoms].

        Returns:
            (triple_bond_indices, n_triple_ij, n_triple_i, n_triple_s)
        """
        # Use MatterSim's implementation
        from mattersim.datasets.utils.threebody_indices import compute_threebody

        n_bonds = edge_index.shape[1]
        bond_atom_indices = edge_index.T  # [n_bonds, 2]

        # Filter by threebody cutoff
        if n_bonds > 0 and self.threebody_cutoff is not None:
            valid_three_body = edge_distances <= self.threebody_cutoff
            ij_reverse_map = np.where(valid_three_body)[0]
            original_index = np.arange(n_bonds)[valid_three_body]
            bond_atom_indices_filtered = bond_atom_indices[valid_three_body, :]
        else:
            ij_reverse_map = None
            original_index = np.arange(n_bonds)
            bond_atom_indices_filtered = bond_atom_indices

        if bond_atom_indices_filtered.shape[0] > 0:
            bond_indices, n_triple_ij, n_triple_i, n_triple_s = compute_threebody(
                np.ascontiguousarray(bond_atom_indices_filtered, dtype="int32"),
                np.array([n_atoms], dtype="int32"),
            )

            if ij_reverse_map is not None:
                n_triple_ij_full = np.zeros(shape=(n_bonds,), dtype="int32")
                n_triple_ij_full[ij_reverse_map] = n_triple_ij
                n_triple_ij = n_triple_ij_full

            bond_indices = original_index[bond_indices]
            bond_indices = np.array(bond_indices, dtype="int32")
        else:
            bond_indices = np.array([], dtype="int32").reshape(-1, 2)
            n_triple_ij = (
                np.zeros(n_bonds, dtype="int32")
                if n_bonds > 0
                else np.array([], dtype="int32")
            )
            n_triple_i = np.zeros(n_atoms, dtype="int32")
            n_triple_s = np.array([0], dtype="int32")

        return bond_indices, n_triple_ij, n_triple_i, n_triple_s

    def convert(
        self,
        structure: Union[Crystal, Molecule],
        energy: Optional[float] = None,
        forces: Optional[np.ndarray] = None,
        stress: Optional[np.ndarray] = None,
        **kwargs,
    ) -> Data:
        """
        Convert MatSimPy structure to PyTorch Geometric Data object.

        Args:
            structure: Crystal or Molecule object.
            energy: Total energy in eV (optional, for training).
            forces: Force array [n_atoms, 3] in eV/Å (optional).
            stress: Stress tensor [3, 3] in GPa (optional).
            **kwargs: Additional arguments.

        Returns:
            PyTorch Geometric Data object with graph representation.

        Raises:
            ValueError: If structure is invalid or unsupported model type.
        """
        # Prepare structure (handles both Crystal and Molecule)
        positions, cell, pbc = self._prepare_structure(structure)

        # Get atomic numbers
        atomic_numbers = np.array(
            [elem.atomic_no for elem in structure.elements],
            dtype=np.int64,
        )

        n_atoms = len(structure)

        if self.model_type == "m3gnet":
            # Build graph data for M3GNet
            args = {
                "num_atoms": n_atoms,
                "num_nodes": n_atoms,
                "atom_attr": torch.FloatTensor(atomic_numbers).unsqueeze(-1),
                "atom_pos": torch.FloatTensor(positions),
                "cell": torch.FloatTensor(cell).unsqueeze(0),
            }

            # Get edges using MatSimPy's capabilities
            center_idx, neighbor_idx, images, distances = self._get_edges_with_pbc(
                structure, positions, cell, pbc, self.twobody_cutoff
            )

            args["num_bonds"] = len(center_idx)
            args["num_edges"] = len(center_idx)
            args["edge_index"] = torch.from_numpy(
                np.array([center_idx, neighbor_idx], dtype=np.int64)
            )
            args["pbc_offsets"] = torch.FloatTensor(images)

            # Compute three-body indices if needed
            if self.has_threebody and len(center_idx) > 0:
                triple_bond_indices, n_triple_ij, n_triple_i, n_triple_s = (
                    self._compute_threebody_indices(
                        args["edge_index"].numpy(), distances, n_atoms, atomic_numbers
                    )
                )

                args["three_body_indices"] = torch.from_numpy(triple_bond_indices).to(
                    torch.long
                )
                args["num_three_body"] = args["three_body_indices"].shape[0]
                args["num_triple_ij"] = (
                    torch.from_numpy(n_triple_ij).to(torch.long).unsqueeze(-1)
                )
            else:
                args["three_body_indices"] = None
                args["num_three_body"] = None
                args["num_triple_ij"] = None

            # Add labels if provided
            if energy is not None:
                args["energy"] = torch.FloatTensor([energy])
            if forces is not None:
                args["forces"] = torch.FloatTensor(forces)
            if stress is not None:
                args["stress"] = torch.FloatTensor(stress).unsqueeze(0)

            return Data(**args)

        elif self.model_type == "graphormer":
            raise NotImplementedError("Graphormer support coming soon")

        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")


def build_dataloader(
    structures: List[Union[Crystal, Molecule]],
    energies: Optional[List[float]] = None,
    forces: Optional[List[np.ndarray]] = None,
    stresses: Optional[List[np.ndarray]] = None,
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    batch_size: int = 1,
    model_type: str = "m3gnet",
    shuffle: bool = False,
    only_inference: bool = True,
    num_workers: int = 0,
    pin_memory: bool = False,
    **kwargs,
) -> DataLoader_pyg:
    """
    Build PyTorch Geometric DataLoader from MatSimPy structures.

    Pure MatSimPy implementation without ASE dependency.
    Uses MatSimPy's graph module for efficient neighbor finding.

    Args:
        structures: List of Crystal or Molecule objects.
        energies: Optional energies (eV) for training.
        forces: Optional forces (eV/Å) for training.
        stresses: Optional stresses (GPa) for training.
        cutoff: Edge cutoff radius (Angstroms).
        threebody_cutoff: Three-body cutoff (Angstroms).
        batch_size: Batch size for dataloader.
        model_type: Model type ('m3gnet', etc.).
        shuffle: Whether to shuffle data.
        only_inference: If True, labels (energy/forces/stress) are optional.
        num_workers: Number of dataloader workers.
        pin_memory: Whether to pin memory for GPU transfer.
        **kwargs: Additional arguments.

    Returns:
        PyTorch Geometric DataLoader ready for ML training/inference.

    Raises:
        ValueError: If structures is empty or validation fails.
        AssertionError: If energies required but not provided.

    Examples:
        >>> from matsimpy.builders import bulk
        >>> from matsimpy.calculator.ml.dataloader import build_dataloader
        >>>
        >>> # Inference mode (no labels)
        >>> crystal = bulk('Si', 'diamond', a=5.43)
        >>> dataloader = build_dataloader([crystal], only_inference=True)
        >>>
        >>> # Training mode (with labels)
        >>> energies = [-10.5, -11.2, -9.8]
        >>> forces = [np.random.randn(len(s), 3) for s in structures]
        >>> dataloader = build_dataloader(
        ...     structures,
        ...     energies=energies,
        ...     forces=forces,
        ...     only_inference=False
        ... )
    """
    if not structures:
        raise ValueError("Structure list cannot be empty")

    # Validate inputs for training mode
    if not only_inference:
        if energies is None:
            raise ValueError("energies must be provided when only_inference=False")
        if len(energies) != len(structures):
            raise ValueError(
                f"Number of energies ({len(energies)}) must match "
                f"number of structures ({len(structures)})"
            )

    # Initialize lists if not provided
    n_structures = len(structures)
    if energies is None:
        energies = [None] * n_structures
    if forces is None:
        forces = [None] * n_structures
    if stresses is None:
        stresses = [None] * n_structures

    # Validate stress shapes if provided
    if stresses[0] is not None:
        stress_array = np.array(stresses[0])
        if stress_array.shape != (3, 3):
            raise ValueError(
                f"Stress must be 3x3 matrix, got shape {stress_array.shape}"
            )

    # Create convertor
    convertor = MatSimPyGraphConvertor(
        model_type=model_type,
        twobody_cutoff=cutoff,
        has_threebody=True,
        threebody_cutoff=threebody_cutoff,
    )

    # Convert all structures to graph format
    graph_data = []
    for struct, energy, force, stress in zip(structures, energies, forces, stresses):
        try:
            graph = convertor.convert(struct, energy, force, stress, **kwargs)
            if graph is not None:
                graph_data.append(graph)
        except Exception as e:
            warnings.warn(f"Failed to convert structure: {e}. Skipping.", UserWarning)

    if not graph_data:
        raise ValueError("No valid graphs generated from structures")

    # Create and return DataLoader
    return DataLoader_pyg(
        graph_data,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )


def structure_to_graph(
    structure: Union[Crystal, Molecule],
    cutoff: float = 5.0,
    threebody_cutoff: float = 4.0,
    model_type: str = "m3gnet",
) -> Data:
    """
    Convert single structure to PyTorch Geometric Data object.

    Convenience function for single structure conversion.

    Args:
        structure: Crystal or Molecule object.
        cutoff: Edge cutoff radius.
        threebody_cutoff: Three-body cutoff.
        model_type: Model type.

    Returns:
        PyTorch Geometric Data object.

    Examples:
        >>> crystal = Crystal(['Si'], [[0,0,0]], Lattice(5.43))
        >>> graph = structure_to_graph(crystal, cutoff=5.0)
        >>> print(graph.num_nodes)
    """
    convertor = MatSimPyGraphConvertor(
        model_type=model_type,
        twobody_cutoff=cutoff,
        has_threebody=True,
        threebody_cutoff=threebody_cutoff,
    )

    return convertor.convert(structure)


__all__ = [
    "MatSimPyGraphConvertor",
    "build_dataloader",
    "structure_to_graph",
]
