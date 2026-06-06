"""Tests for IO converters module."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.io import to_pymatgen, from_pymatgen, to_ase, from_ase
from tests.conftest import has_ase, has_pymatgen

class TestIOConverters(unittest.TestCase):
    """Tests for IO converter functions."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = from_prototype('diamond', 'Si', 5.43)
        self.molecule = Molecule(['C', 'O', 'O'], [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]])
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_to_pymatgen_crystal(self):
        """Test converting Crystal to pymatgen Structure."""
        pymatgen_struct = to_pymatgen(self.crystal)
        
        # Verify it's a pymatgen Structure
        from pymatgen.core import Structure
        self.assertIsInstance(pymatgen_struct, Structure)
        
        # Verify species match
        self.assertEqual(len(pymatgen_struct), len(self.crystal))
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_from_pymatgen_structure(self):
        """Test converting pymatgen Structure to Crystal."""
        from pymatgen.core import Structure, Lattice as PymatgenLattice
        
        # Create pymatgen structure
        lattice = PymatgenLattice.cubic(5.43)
        pymatgen_struct = Structure(lattice, ['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]])
        
        # Convert to MatSimPy
        crystal = from_pymatgen(pymatgen_struct)
        
        # Verify it's a Crystal
        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(len(crystal), 2)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_to_pymatgen_molecule(self):
        """Test converting Molecule to pymatgen Molecule."""
        pymatgen_mol = to_pymatgen(self.molecule)
        
        # Verify it's a pymatgen Molecule
        from pymatgen.core import Molecule as PymatgenMolecule
        self.assertIsInstance(pymatgen_mol, PymatgenMolecule)
        
        # Verify species match
        self.assertEqual(len(pymatgen_mol), len(self.molecule))
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_from_pymatgen_molecule(self):
        """Test converting pymatgen Molecule to Molecule."""
        from pymatgen.core import Molecule as PymatgenMolecule
        
        # Create pymatgen molecule
        pymatgen_mol = PymatgenMolecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        
        # Convert to MatSimPy
        molecule = from_pymatgen(pymatgen_mol)
        
        # Verify it's a Molecule
        self.assertIsInstance(molecule, Molecule)
        self.assertEqual(len(molecule), 2)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_pymatgen_roundtrip_crystal(self):
        """Test roundtrip conversion for Crystal."""
        # Convert to pymatgen and back
        pymatgen_struct = to_pymatgen(self.crystal)
        crystal2 = from_pymatgen(pymatgen_struct)
        
        # Verify structure matches
        self.assertEqual(crystal2.species, self.crystal.species)
        self.assertEqual(len(crystal2), len(self.crystal))
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_pymatgen_roundtrip_molecule(self):
        """Test roundtrip conversion for Molecule."""
        # Convert to pymatgen and back
        pymatgen_mol = to_pymatgen(self.molecule)
        molecule2 = from_pymatgen(pymatgen_mol)
        
        # Verify structure matches
        self.assertEqual(molecule2.species, self.molecule.species)
        self.assertEqual(len(molecule2), len(self.molecule))

    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_pymatgen_structure_methods(self):
        """Test Crystal/Molecule pymatgen convenience methods."""
        from pymatgen.core import Molecule as PymatgenMolecule
        from pymatgen.core import Structure as PymatgenStructure

        pymatgen_struct = self.crystal.to_pymatgen()
        self.assertIsInstance(pymatgen_struct, PymatgenStructure)
        self.assertIsInstance(Crystal.from_pymatgen(pymatgen_struct), Crystal)

        pymatgen_mol = self.molecule.to_pymatgen()
        self.assertIsInstance(pymatgen_mol, PymatgenMolecule)
        self.assertIsInstance(Molecule.from_pymatgen(pymatgen_mol), Molecule)
    
    def test_to_pymatgen_invalid_input(self):
        """Test converting invalid input to pymatgen."""
        with self.assertRaises(ValueError):
            to_pymatgen("not a structure")
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_to_ase_crystal(self):
        """Test converting Crystal to ASE Atoms."""
        ase_atoms = to_ase(self.crystal)
        
        # Verify it's an ASE Atoms object
        from ase import Atoms
        self.assertIsInstance(ase_atoms, Atoms)
        
        # Verify species match
        self.assertEqual(len(ase_atoms), len(self.crystal))
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_from_ase_atoms(self):
        """Test converting ASE Atoms to Crystal."""
        from ase import Atoms
        
        # Create ASE structure
        ase_atoms = Atoms('Si2', positions=[[0, 0, 0], [1.3575, 1.3575, 1.3575]], 
                        cell=[[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]], 
                        pbc=True)
        
        # Convert to MatSimPy
        crystal = from_ase(ase_atoms)
        
        # Verify it's a Crystal
        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(len(crystal), 2)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_to_ase_molecule(self):
        """Test converting Molecule to ASE Atoms."""
        ase_atoms = to_ase(self.molecule)
        
        # Verify it's an ASE Atoms object
        from ase import Atoms
        self.assertIsInstance(ase_atoms, Atoms)
        
        # Verify species match
        self.assertEqual(len(ase_atoms), len(self.molecule))

    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_from_ase_molecule(self):
        """Test converting non-periodic ASE Atoms to Molecule."""
        from ase import Atoms

        ase_atoms = Atoms('CO', positions=[[0, 0, 0], [1.2, 0, 0]])
        molecule = from_ase(ase_atoms)

        self.assertIsInstance(molecule, Molecule)
        self.assertEqual(len(molecule), 2)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_ase_roundtrip_crystal(self):
        """Test roundtrip conversion for Crystal via ASE."""
        # Convert to ASE and back
        ase_atoms = to_ase(self.crystal)
        crystal2 = from_ase(ase_atoms)
        
        # Verify structure matches
        self.assertEqual(crystal2.species, self.crystal.species)
        self.assertEqual(len(crystal2), len(self.crystal))
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_ase_roundtrip_molecule(self):
        """Test roundtrip conversion for Molecule via ASE."""
        # Convert to ASE and back
        ase_atoms = to_ase(self.molecule)
        molecule2 = from_ase(ase_atoms)
        
        # Verify structure matches
        self.assertEqual(molecule2.species, self.molecule.species)
        self.assertEqual(len(molecule2), len(self.molecule))

    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_ase_structure_methods(self):
        """Test Crystal/Molecule ASE convenience methods."""
        from ase import Atoms

        ase_crystal = self.crystal.to_ase()
        self.assertIsInstance(ase_crystal, Atoms)
        self.assertIsInstance(Crystal.from_ase(ase_crystal), Crystal)

        ase_molecule = self.molecule.to_ase()
        self.assertIsInstance(ase_molecule, Atoms)
        self.assertIsInstance(Molecule.from_ase(ase_molecule), Molecule)
    
    def test_to_ase_invalid_input(self):
        """Test converting invalid input to ASE."""
        with self.assertRaises(ValueError):
            to_ase("not a structure")
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_from_ase_invalid_input(self):
        """Test converting invalid input from ASE."""
        with self.assertRaises(ValueError):
            from_ase("not an ASE Atoms object")

if __name__ == '__main__':
    unittest.main()
