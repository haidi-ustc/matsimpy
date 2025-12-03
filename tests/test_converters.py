"""Tests for pymatgen and ASE converters."""
import unittest
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.io.converters import to_pymatgen, from_pymatgen, to_ase, from_ase
from tests.conftest import has_ase, has_pymatgen

class TestPymatgenConverters(unittest.TestCase):
    """Tests for pymatgen converters."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal_species = ['Si', 'O', 'O']
        self.crystal_positions = [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.crystal_species, self.crystal_positions, self.lattice)
        
        self.molecule_species = ['C', 'O', 'O']
        self.molecule_positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.molecule_species, self.molecule_positions)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_to_pymatgen_crystal(self):
        """Test converting Crystal to pymatgen Structure."""
        pymatgen_struct = to_pymatgen(self.crystal)
        self.assertIsNotNone(pymatgen_struct)
        self.assertEqual(len(pymatgen_struct), 3)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_from_pymatgen_crystal(self):
        """Test converting pymatgen Structure to Crystal."""
        from pymatgen.core import Structure as PymatgenStructure
        
        # Create pymatgen structure
        lattice_matrix = self.lattice.matrix
        pymatgen_struct = PymatgenStructure(
            lattice_matrix,
            self.crystal_species,
            self.crystal.cart_positions.tolist(),
            coords_are_cartesian=True
        )
        
        # Convert back
        crystal = from_pymatgen(pymatgen_struct)
        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(len(crystal), 3)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_to_pymatgen_molecule(self):
        """Test converting Molecule to pymatgen Molecule."""
        pymatgen_mol = to_pymatgen(self.molecule)
        self.assertIsNotNone(pymatgen_mol)
        self.assertEqual(len(pymatgen_mol), 3)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_from_pymatgen_molecule(self):
        """Test converting pymatgen Molecule to Molecule."""
        from pymatgen.core import Molecule as PymatgenMolecule
        
        # Create pymatgen molecule
        pymatgen_mol = PymatgenMolecule(
            self.molecule_species,
            self.molecule_positions
        )
        
        # Convert back
        molecule = from_pymatgen(pymatgen_mol)
        self.assertIsInstance(molecule, Molecule)
        self.assertEqual(len(molecule), 3)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_crystal_roundtrip_pymatgen(self):
        """Test roundtrip conversion Crystal -> pymatgen -> Crystal."""
        from pymatgen.core import Structure as PymatgenStructure
        
        # Convert to pymatgen
        pymatgen_struct = to_pymatgen(self.crystal)
        
        # Convert back
        crystal2 = from_pymatgen(pymatgen_struct)
        
        # Verify
        self.assertEqual(crystal2.species, self.crystal.species)
        np.testing.assert_array_almost_equal(
            crystal2.frac_positions,
            self.crystal.frac_positions,
            decimal=5
        )
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_molecule_roundtrip_pymatgen(self):
        """Test roundtrip conversion Molecule -> pymatgen -> Molecule."""
        from pymatgen.core import Molecule as PymatgenMolecule
        
        # Convert to pymatgen
        pymatgen_mol = to_pymatgen(self.molecule)
        
        # Convert back
        molecule2 = from_pymatgen(pymatgen_mol)
        
        # Verify
        self.assertEqual(molecule2.species, self.molecule.species)
        np.testing.assert_array_almost_equal(
            molecule2.positions,
            self.molecule.positions,
            decimal=5
        )
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_crystal_methods_pymatgen(self):
        """Test Crystal.to_pymatgen() and Crystal.from_pymatgen() methods."""
        from pymatgen.core import Structure as PymatgenStructure
        
        # Test instance method
        pymatgen_struct = self.crystal.to_pymatgen()
        self.assertIsInstance(pymatgen_struct, PymatgenStructure)
        
        # Test class method
        crystal2 = Crystal.from_pymatgen(pymatgen_struct)
        self.assertIsInstance(crystal2, Crystal)
    
    @unittest.skipUnless(has_pymatgen(), "pymatgen not installed")
    def test_molecule_methods_pymatgen(self):
        """Test Molecule.to_pymatgen() and Molecule.from_pymatgen() methods."""
        from pymatgen.core import Molecule as PymatgenMolecule
        
        # Test instance method
        pymatgen_mol = self.molecule.to_pymatgen()
        self.assertIsInstance(pymatgen_mol, PymatgenMolecule)
        
        # Test class method
        molecule2 = Molecule.from_pymatgen(pymatgen_mol)
        self.assertIsInstance(molecule2, Molecule)

class TestASEConverters(unittest.TestCase):
    """Tests for ASE converters."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal_species = ['Si', 'O', 'O']
        self.crystal_positions = [[0, 0, 0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.5]]
        self.lattice = Lattice.cubic(10.0)
        self.crystal = Crystal(self.crystal_species, self.crystal_positions, self.lattice)
        
        self.molecule_species = ['C', 'O', 'O']
        self.molecule_positions = [[0, 0, 0], [1.2, 0, 0], [-1.2, 0, 0]]
        self.molecule = Molecule(self.molecule_species, self.molecule_positions)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_to_ase_crystal(self):
        """Test converting Crystal to ASE Atoms."""
        ase_atoms = to_ase(self.crystal)
        self.assertIsNotNone(ase_atoms)
        self.assertEqual(len(ase_atoms), 3)
        # Check cell is set
        self.assertIsNotNone(ase_atoms.get_cell())
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_from_ase_crystal(self):
        """Test converting ASE Atoms to Crystal."""
        from ase import Atoms
        
        # Create ASE atoms with cell
        cell = self.lattice.matrix
        ase_atoms = Atoms(
            symbols=self.crystal_species,
            positions=self.crystal.cart_positions.tolist(),
            cell=cell,
            pbc=[True, True, True]
        )
        
        # Convert back
        crystal = from_ase(ase_atoms)
        self.assertIsInstance(crystal, Crystal)
        self.assertEqual(len(crystal), 3)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_to_ase_molecule(self):
        """Test converting Molecule to ASE Atoms."""
        ase_atoms = to_ase(self.molecule)
        self.assertIsNotNone(ase_atoms)
        self.assertEqual(len(ase_atoms), 3)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_from_ase_molecule(self):
        """Test converting ASE Atoms to Molecule."""
        from ase import Atoms
        
        # Create ASE atoms without cell
        ase_atoms = Atoms(
            symbols=self.molecule_species,
            positions=self.molecule_positions
        )
        
        # Convert back
        molecule = from_ase(ase_atoms)
        self.assertIsInstance(molecule, Molecule)
        self.assertEqual(len(molecule), 3)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_crystal_roundtrip_ase(self):
        """Test roundtrip conversion Crystal -> ASE -> Crystal."""
        # Convert to ASE
        ase_atoms = to_ase(self.crystal)
        
        # Convert back
        crystal2 = from_ase(ase_atoms)
        
        # Verify
        self.assertEqual(crystal2.species, self.crystal.species)
        np.testing.assert_array_almost_equal(
            crystal2.frac_positions,
            self.crystal.frac_positions,
            decimal=5
        )
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_molecule_roundtrip_ase(self):
        """Test roundtrip conversion Molecule -> ASE -> Molecule."""
        # Convert to ASE
        ase_atoms = to_ase(self.molecule)
        
        # Convert back
        molecule2 = from_ase(ase_atoms)
        
        # Verify
        self.assertEqual(molecule2.species, self.molecule.species)
        np.testing.assert_array_almost_equal(
            molecule2.positions,
            self.molecule.positions,
            decimal=5
        )
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_crystal_methods_ase(self):
        """Test Crystal.to_ase() and Crystal.from_ase() methods."""
        from ase import Atoms
        
        # Test instance method
        ase_atoms = self.crystal.to_ase()
        self.assertIsInstance(ase_atoms, Atoms)
        
        # Test class method
        crystal2 = Crystal.from_ase(ase_atoms)
        self.assertIsInstance(crystal2, Crystal)
    
    @unittest.skipUnless(has_ase(), "ASE not installed")
    def test_molecule_methods_ase(self):
        """Test Molecule.to_ase() and Molecule.from_ase() methods."""
        from ase import Atoms
        
        # Test instance method
        ase_atoms = self.molecule.to_ase()
        self.assertIsInstance(ase_atoms, Atoms)
        
        # Test class method
        molecule2 = Molecule.from_ase(ase_atoms)
        self.assertIsInstance(molecule2, Molecule)

if __name__ == '__main__':
    unittest.main()

