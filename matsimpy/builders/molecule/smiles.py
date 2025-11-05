"""
SMILES-based molecule generation.

Build molecules from SMILES strings using RDKit.
"""

from ...core import Molecule


def build_from_smiles(smiles: str, optimize: bool = True) -> Molecule:
    """
    Build molecule from SMILES string.
    
    Args:
        smiles: SMILES string representation
        optimize: If True, optimize geometry with force field
    
    Returns:
        Molecule structure
        
    Examples:
        >>> from matsimpy.builders.molecule import build_from_smiles
        >>> # Build benzene
        >>> benzene = build_from_smiles('c1ccccc1')
        >>> # Build water
        >>> water = build_from_smiles('O')
    
    Note:
        Requires RDKit package: pip install rdkit
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        raise ImportError(
            "RDKit required for SMILES parsing. Install with: pip install rdkit"
        )
    
    # Parse SMILES
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")
    
    # Add hydrogens
    mol = Chem.AddHs(mol)
    
    # Generate 3D coordinates
    AllChem.EmbedMolecule(mol, randomSeed=42)
    
    if optimize:
        AllChem.MMFFOptimizeMolecule(mol)
    
    # Extract coordinates
    conf = mol.GetConformer()
    species = [atom.GetSymbol() for atom in mol.GetAtoms()]
    positions = []
    for i in range(mol.GetNumAtoms()):
        pos = conf.GetAtomPosition(i)
        positions.append([pos.x, pos.y, pos.z])
    
    return Molecule(species, positions)


__all__ = ['build_from_smiles']

