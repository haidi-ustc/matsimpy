"""
Molecule-specific structure builders.

Provides tools for building and manipulating molecular structures.
"""

from typing import List, Optional, Union, Dict
import numpy as np
from ...core import Molecule


def build_linear_molecule(
    species: List[str],
    bond_lengths: List[float],
    axis: List[float] = [1, 0, 0]
) -> Molecule:
    """
    Build linear molecule along an axis.
    
    Args:
        species: List of atomic species
        bond_lengths: List of bond lengths (n-1 for n atoms)
        axis: Direction vector for molecule axis
    
    Returns:
        Linear molecule
        
    Examples:
        >>> from matsimpy.generation.builders import build_linear_molecule
        >>> # Build CO2: O=C=O
        >>> co2 = build_linear_molecule(['O', 'C', 'O'], [1.16, 1.16])
    """
    if len(bond_lengths) != len(species) - 1:
        raise ValueError(f"Need {len(species)-1} bond lengths for {len(species)} atoms")
    
    axis = np.array(axis, dtype=np.float64)
    axis = axis / np.linalg.norm(axis)
    
    positions = []
    current_pos = np.array([0.0, 0.0, 0.0])
    positions.append(current_pos.copy())
    
    for length in bond_lengths:
        current_pos += axis * length
        positions.append(current_pos.copy())
    
    return Molecule(species, positions, coords_are_cartesian=True)


def build_bent_molecule(
    species: List[str],
    bond_lengths: List[float],
    angles: List[float],
    plane_normal: List[float] = [0, 0, 1]
) -> Molecule:
    """
    Build bent molecule (e.g., H2O, bent triatomic).
    
    Args:
        species: List of atomic species
        bond_lengths: List of bond lengths
        angles: List of bond angles in degrees
        plane_normal: Normal vector to molecular plane
    
    Returns:
        Bent molecule
        
    Examples:
        >>> from matsimpy.generation.builders import build_bent_molecule
        >>> # Build H2O with HOH angle of 104.5°
        >>> h2o = build_bent_molecule(['O', 'H', 'H'], [0.96, 0.96], [104.5])
    """
    if len(species) != 3:
        raise NotImplementedError("Currently only supports triatomic bent molecules")
    
    # Central atom at origin
    positions = [np.array([0.0, 0.0, 0.0])]
    
    # First bond along x-axis
    positions.append(np.array([bond_lengths[0], 0.0, 0.0]))
    
    # Second bond at angle
    angle_rad = np.radians(angles[0])
    x = bond_lengths[1] * np.cos(angle_rad)
    y = bond_lengths[1] * np.sin(angle_rad)
    positions.append(np.array([x, y, 0.0]))
    
    return Molecule(species, positions, coords_are_cartesian=True)


def build_from_smiles(smiles: str) -> Molecule:
    """
    Build molecule from SMILES string.
    
    Args:
        smiles: SMILES string representation
    
    Returns:
        Molecule structure
        
    Examples:
        >>> from matsimpy.generation.builders import build_from_smiles
        >>> # Build benzene
        >>> benzene = build_from_smiles('c1ccccc1')
    
    Note:
        Requires RDKit package.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        raise ImportError("RDKit required for SMILES parsing. Install with: pip install rdkit")
    
    # Parse SMILES
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")
    
    # Add hydrogens
    mol = Chem.AddHs(mol)
    
    # Generate 3D coordinates
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    
    # Extract coordinates
    conf = mol.GetConformer()
    species = [atom.GetSymbol() for atom in mol.GetAtoms()]
    positions = []
    for i in range(mol.GetNumAtoms()):
        pos = conf.GetAtomPosition(i)
        positions.append([pos.x, pos.y, pos.z])
    
    return Molecule(species, positions, coords_are_cartesian=True)


def build_from_xyz_string(xyz_string: str) -> Molecule:
    """
    Build molecule from XYZ format string.
    
    Args:
        xyz_string: XYZ format string
    
    Returns:
        Molecule structure
        
    Examples:
        >>> xyz = '''3
        ... Water molecule
        ... O  0.000  0.000  0.000
        ... H  0.758  0.587  0.000
        ... H -0.758  0.587  0.000'''
        >>> h2o = build_from_xyz_string(xyz)
    """
    lines = xyz_string.strip().split('\n')
    n_atoms = int(lines[0])
    
    species = []
    positions = []
    
    for i in range(2, 2 + n_atoms):
        parts = lines[i].split()
        species.append(parts[0])
        positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
    
    return Molecule(species, positions, coords_are_cartesian=True)


def combine_molecules(
    molecules: List[Molecule],
    positions: Optional[List[List[float]]] = None,
    bond_indices: Optional[List[tuple]] = None
) -> Molecule:
    """
    Combine multiple molecules into one.
    
    Args:
        molecules: List of molecules to combine
        positions: Optional positions for each molecule's center
        bond_indices: Optional list of (mol1_idx, atom1, mol2_idx, atom2) to bond
    
    Returns:
        Combined molecule
        
    Examples:
        >>> from matsimpy.generation.builders import combine_molecules
        >>> combined = combine_molecules([mol1, mol2], positions=[[0,0,0], [5,0,0]])
    """
    all_species = []
    all_positions = []
    
    if positions is None:
        positions = [[0, 0, 0] for _ in molecules]
    
    for mol, offset in zip(molecules, positions):
        offset = np.array(offset, dtype=np.float64)
        all_species.extend(mol.species)
        all_positions.extend(mol.cart_positions + offset)
    
    return Molecule(all_species, all_positions, coords_are_cartesian=True)


__all__ = [
    'build_linear_molecule',
    'build_bent_molecule',
    'build_from_smiles',
    'build_from_xyz_string',
    'combine_molecules',
]

