"""
Molecule-specific structural operations.

Provides operations specific to molecular structures like fragmentation,
merging, and conformer generation.
"""

from numbers import Integral
from typing import Dict, List, Optional, Tuple
import copy
import numpy as np
from ...core import Molecule
from .._helpers import copy_site_properties


def fragment_molecule(
    molecule: Molecule,
    break_indices: List[Tuple[int, int]],
    cutoff: float = 1.8,
) -> List[Molecule]:
    """
    Fragment molecule by breaking bonds.

    Args:
        molecule: Molecule to fragment
        break_indices: List of (atom1, atom2) pairs to break
        cutoff: Distance cutoff in Angstroms used to infer the molecular graph

    Returns:
        List of molecular fragments

    Examples:
        >>> from matsimpy.transformation.structural import fragment_molecule
        >>> # Break bond between atoms 1 and 2
        >>> fragments = fragment_molecule(mol, [(1, 2)])
    """
    n_atoms = len(molecule)
    if n_atoms == 0:
        return []
    if cutoff <= 0:
        raise ValueError("cutoff must be positive")

    broken = set()
    for atom1, atom2 in break_indices:
        if not (0 <= atom1 < n_atoms and 0 <= atom2 < n_atoms):
            raise IndexError("break_indices contain atom index outside molecule")
        if atom1 == atom2:
            raise ValueError("Cannot break a bond from an atom to itself")
        broken.add(tuple(sorted((atom1, atom2))))

    neighbors = molecule.get_neighbor_list(cutoff=cutoff)
    graph: Dict[int, set[int]] = {i: set() for i in range(n_atoms)}
    for atom, atom_neighbors in neighbors.items():
        for neighbor, _distance in atom_neighbors:
            edge = tuple(sorted((atom, neighbor)))
            if edge in broken:
                continue
            graph[atom].add(neighbor)
            graph[neighbor].add(atom)

    fragments = []
    seen = set()
    source_site_properties = list(molecule.site_properties)
    for start in range(n_atoms):
        if start in seen:
            continue
        stack = [start]
        component = []
        seen.add(start)
        while stack:
            atom = stack.pop()
            component.append(atom)
            for neighbor in graph[atom]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)

        component.sort()
        site_properties = (
            [source_site_properties[i] for i in component]
            if source_site_properties
            else None
        )
        fragments.append(
            Molecule(
                [molecule.species[i] for i in component],
                molecule.positions[component].tolist(),
                site_properties=site_properties,
            )
        )

    return fragments


def align_molecules(
    molecule1: Molecule, molecule2: Molecule, indices1: List[int], indices2: List[int]
) -> Molecule:
    """
    Align molecule2 to molecule1 using specified atom pairs.

    Args:
        molecule1: Reference molecule
        molecule2: Molecule to align
        indices1: Atom indices in molecule1
        indices2: Atom indices in molecule2

    Returns:
        Aligned molecule2

    Examples:
        >>> from matsimpy.transformation.structural import align_molecules
        >>> # Align using atoms 0,1,2 of each molecule
        >>> aligned = align_molecules(mol1, mol2, [0,1,2], [0,1,2])
    """
    indices1 = list(indices1)
    indices2 = list(indices2)
    if len(indices1) != len(indices2):
        raise ValueError("Must have same number of indices")
    if not indices1:
        raise ValueError("Must provide at least one atom pair for alignment")
    if len(set(indices1)) != len(indices1) or len(set(indices2)) != len(indices2):
        raise ValueError("Alignment indices must not contain duplicates")

    for name, indices, molecule in (
        ("indices1", indices1, molecule1),
        ("indices2", indices2, molecule2),
    ):
        for index in indices:
            if not isinstance(index, Integral):
                raise TypeError(f"{name} must contain integer atom indices")
            if index < 0 or index >= len(molecule):
                raise IndexError(f"{name} contains atom index outside molecule")

    index_array1 = np.array(indices1, dtype=int)
    index_array2 = np.array(indices2, dtype=int)

    # Get coordinates
    coords1 = molecule1.positions[index_array1]
    coords2 = molecule2.positions[index_array2]

    # Center both sets
    center1 = np.mean(coords1, axis=0)
    center2 = np.mean(coords2, axis=0)
    coords1_centered = coords1 - center1
    coords2_centered = coords2 - center2

    # Find rotation matrix using SVD
    H = np.dot(coords2_centered.T, coords1_centered)
    U, S, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)

    # Handle reflection
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = np.dot(Vt.T, U.T)

    # Apply transformation to molecule2
    aligned_coords = np.dot(molecule2.positions - center2, R) + center1

    return Molecule(
        list(molecule2.species),
        aligned_coords.tolist(),
        site_properties=copy_site_properties(molecule2),
    )


def generate_conformers(
    molecule: Molecule, n_conformers: int = 10, energy_window: float = 10.0, **kwargs
) -> List[Molecule]:
    """
    Generate molecular conformers.

    Args:
        molecule: Base molecule
        n_conformers: Number of conformers to generate
        energy_window: Energy window in kcal/mol
        **kwargs: Additional parameters

    Returns:
        List of conformer molecules

    Examples:
        >>> from matsimpy.transformation.structural import generate_conformers
        >>> conformers = generate_conformers(mol, n_conformers=10)

    Note:
        Requires RDKit for conformer generation.
    """
    if n_conformers < 1:
        raise ValueError("n_conformers must be at least 1")

    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError as e:
        raise ImportError(
            "RDKit is required for conformer generation. "
            "Install with: pip install rdkit or pip install MatSimPy[builders]"
        ) from e

    rdkit_mol = Chem.RWMol()
    for symbol in molecule.species:
        rdkit_mol.AddAtom(Chem.Atom(symbol))

    for atom, atom_neighbors in molecule.get_neighbor_list(
        kwargs.get("bond_cutoff", 1.8)
    ).items():
        for neighbor, _distance in atom_neighbors:
            if atom < neighbor:
                rdkit_mol.AddBond(atom, neighbor, Chem.BondType.SINGLE)

    mol = rdkit_mol.GetMol()
    Chem.SanitizeMol(mol, catchErrors=True)

    params = AllChem.ETKDGv3()
    params.randomSeed = int(kwargs.get("seed", 42))
    params.pruneRmsThresh = float(kwargs.get("prune_rms", 0.1))
    conformer_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=n_conformers, params=params))
    if not conformer_ids:
        raise RuntimeError("RDKit failed to generate any conformers")

    energies = []
    if kwargs.get("optimize", True):
        try:
            results = AllChem.MMFFOptimizeMoleculeConfs(mol)
            energies = [energy for status, energy in results if status in (0, 1)]
        except Exception:
            try:
                results = AllChem.UFFOptimizeMoleculeConfs(mol)
                energies = [energy for status, energy in results if status in (0, 1)]
            except Exception:
                energies = []

    keep_ids = conformer_ids
    if energies and len(energies) == len(conformer_ids):
        min_energy = min(energies)
        keep_ids = [
            conf_id
            for conf_id, energy in zip(conformer_ids, energies)
            if energy - min_energy <= energy_window
        ]

    conformers = []
    site_properties = list(molecule.site_properties) if molecule.site_properties else None
    for conf_id in keep_ids[:n_conformers]:
        conf = mol.GetConformer(conf_id)
        positions = []
        for idx in range(mol.GetNumAtoms()):
            pos = conf.GetAtomPosition(idx)
            positions.append([pos.x, pos.y, pos.z])
        conformers.append(
            Molecule(
                list(molecule.species),
                positions,
                site_properties=site_properties,
            )
        )

    return conformers


def merge_molecules(
    molecule1: Molecule,
    molecule2: Molecule,
    bond_atom1: int,
    bond_atom2: int,
    remove_atoms: Optional[List[int]] = None,
) -> Molecule:
    """
    Merge two molecules by forming a bond.

    Args:
        molecule1: First molecule
        molecule2: Second molecule
        bond_atom1: Atom in molecule1 to bond
        bond_atom2: Atom in molecule2 to bond
        remove_atoms: Atoms to remove after merging (e.g., hydrogens)

    Returns:
        Merged molecule

    Examples:
        >>> from matsimpy.transformation.structural import merge_molecules
        >>> # Merge at specific atoms
        >>> merged = merge_molecules(mol1, mol2, 5, 0)
    """
    # Align molecule2 so bond_atom2 is near bond_atom1
    bond_pos1 = molecule1.positions[bond_atom1]
    bond_pos2 = molecule2.positions[bond_atom2]

    # Translate molecule2
    offset = bond_pos1 - bond_pos2
    new_positions2 = molecule2.positions + offset

    # Combine
    all_species = list(molecule1.species) + list(molecule2.species)
    all_positions = np.vstack([molecule1.positions, new_positions2])
    if molecule1.site_properties or molecule2.site_properties:
        props1 = (
            [copy.deepcopy(prop) for prop in molecule1.site_properties]
            if molecule1.site_properties
            else [{} for _ in molecule1.species]
        )
        props2 = (
            [copy.deepcopy(prop) for prop in molecule2.site_properties]
            if molecule2.site_properties
            else [{} for _ in molecule2.species]
        )
        all_site_properties: Optional[list[dict]] = props1 + props2
    else:
        all_site_properties = None

    # Remove specified atoms
    if remove_atoms is not None:
        mask = np.ones(len(all_species), dtype=bool)
        mask[remove_atoms] = False
        all_species = [s for i, s in enumerate(all_species) if mask[i]]
        all_positions = all_positions[mask]
        if all_site_properties is not None:
            all_site_properties = [
                prop for i, prop in enumerate(all_site_properties) if mask[i]
            ]

    return Molecule(
        all_species,
        all_positions.tolist(),
        site_properties=all_site_properties,
    )


__all__ = [
    "fragment_molecule",
    "align_molecules",
    "generate_conformers",
    "merge_molecules",
]
