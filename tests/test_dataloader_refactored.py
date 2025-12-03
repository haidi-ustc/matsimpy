"""Tests for refactored dataloader (pure MatSimPy, no ASE)."""
import os
import unittest
import warnings
import numpy as np

from matsimpy.core import Crystal, Molecule, Lattice
from tests.conftest import has_torch, has_torch_geometric

# Conditional imports - only import if torch is available
if has_torch() and has_torch_geometric():
    from matsimpy.calculator.ml.dataloader import (
        MatSimPyGraphConvertor,
        build_dataloader,
        structure_to_graph,
    )
else:
    # Dummy classes/functions to prevent import errors
    MatSimPyGraphConvertor = None
    build_dataloader = None
    structure_to_graph = None

class TestMatSimPyGraphConvertor(unittest.TestCase):
    """Test MatSimPyGraphConvertor class."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        self.molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        if has_torch() and has_torch_geometric():
            self.convertor = MatSimPyGraphConvertor('m3gnet', twobody_cutoff=5.0)
        else:
            self.convertor = None
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_initialization(self):
        """Test convertor initialization."""
        self.assertEqual(self.convertor.model_type, 'm3gnet')
        self.assertEqual(self.convertor.twobody_cutoff, 5.0)
        self.assertTrue(self.convertor.has_threebody)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_convert_crystal(self):
        """Test converting crystal to graph."""
        graph = self.convertor.convert(self.crystal)
        
        self.assertIsNotNone(graph)
        self.assertEqual(graph.num_atoms, 1)
        self.assertIsNotNone(graph.atom_attr)
        self.assertIsNotNone(graph.atom_pos)
        self.assertIsNotNone(graph.cell)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_convert_molecule(self):
        """Test converting molecule to graph."""
        graph = self.convertor.convert(self.molecule)
        
        self.assertIsNotNone(graph)
        self.assertEqual(graph.num_atoms, 2)
        self.assertIsNotNone(graph.edge_index)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_convert_with_energy(self):
        """Test conversion with energy label."""
        graph = self.convertor.convert(self.crystal, energy=-10.5)
        
        self.assertIsNotNone(graph.energy)
        self.assertAlmostEqual(graph.energy.item(), -10.5)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_convert_with_forces(self):
        """Test conversion with force labels."""
        forces = np.array([[0.1, 0.2, 0.3]])
        graph = self.convertor.convert(self.crystal, forces=forces)
        
        self.assertIsNotNone(graph.forces)
        self.assertEqual(graph.forces.shape, (1, 3))
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_convert_with_stress(self):
        """Test conversion with stress labels."""
        stress = np.eye(3) * 0.1
        graph = self.convertor.convert(self.crystal, stress=stress)
        
        self.assertIsNotNone(graph.stress)
        self.assertEqual(graph.stress.shape, (1, 3, 3))

class TestBuildDataloader(unittest.TestCase):
    """Test build_dataloader function."""
    
    def setUp(self):
        """Set up test structures."""
        self.crystals = [
            Crystal(['Si'], [[0, 0, 0]], Lattice(5.43)),
            Crystal(['Fe'], [[0, 0, 0]], Lattice(2.87)),
        ]
        self.molecules = [
            Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]]),
            Molecule(['H', 'H', 'O'], [[0, 0, 0], [0.76, 0.59, 0], [-0.76, 0.59, 0]]),
        ]
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_build_dataloader_inference(self):
        """Test building dataloader for inference."""
        dataloader = build_dataloader(
            self.crystals,
            cutoff=5.0,
            batch_size=1,
            only_inference=True
        )
        
        self.assertIsNotNone(dataloader)
        self.assertEqual(len(dataloader), 2)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_build_dataloader_with_labels(self):
        """Test building dataloader with training labels."""
        energies = [-10.5, -11.2]
        forces = [np.array([[0.1, 0.2, 0.3]]), np.array([[0.2, 0.3, 0.4]])]
        
        dataloader = build_dataloader(
            self.crystals,
            energies=energies,
            forces=forces,
            cutoff=5.0,
            only_inference=False
        )
        
        self.assertIsNotNone(dataloader)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_build_dataloader_molecules(self):
        """Test building dataloader from molecules."""
        dataloader = build_dataloader(
            self.molecules,
            cutoff=3.0,
            batch_size=2,
            only_inference=True
        )
        
        self.assertIsNotNone(dataloader)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_build_dataloader_mixed_structures(self):
        """Test with mixed crystal and molecule structures."""
        mixed = self.crystals + self.molecules
        
        dataloader = build_dataloader(
            mixed,
            cutoff=5.0,
            only_inference=True
        )
        
        self.assertEqual(len(dataloader), 4)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_empty_structures_raises_error(self):
        """Test that empty structure list raises error."""
        with self.assertRaises(ValueError):
            build_dataloader([], only_inference=True)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_missing_energies_in_training_mode_raises_error(self):
        """Test that missing energies in training mode raises error."""
        with self.assertRaises(ValueError):
            build_dataloader(self.crystals, only_inference=False)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_batch_size_parameter(self):
        """Test that batch_size parameter works."""
        dataloader = build_dataloader(
            self.crystals,
            batch_size=2,
            only_inference=True
        )
        
        # Check dataloader was created
        self.assertIsNotNone(dataloader)

class TestStructureToGraph(unittest.TestCase):
    """Test structure_to_graph convenience function."""
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_crystal_to_graph(self):
        """Test converting crystal to graph."""
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        graph = structure_to_graph(crystal, cutoff=5.0)
        
        self.assertIsNotNone(graph)
        self.assertEqual(graph.num_atoms, 1)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_molecule_to_graph(self):
        """Test converting molecule to graph."""
        molecule = Molecule(['C', 'O'], [[0, 0, 0], [1.2, 0, 0]])
        graph = structure_to_graph(molecule, cutoff=3.0)
        
        self.assertIsNotNone(graph)
        self.assertEqual(graph.num_atoms, 2)

class TestGraphProperties(unittest.TestCase):
    """Test graph properties match expectations."""
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_graph_has_required_properties(self):
        """Test that graph has all required properties for M3GNet."""
        crystal = Crystal(['Si', 'Si'], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice(5.43))
        graph = structure_to_graph(crystal, cutoff=5.0)
        
        # Check required properties
        self.assertTrue(hasattr(graph, 'num_atoms'))
        self.assertTrue(hasattr(graph, 'num_nodes'))
        self.assertTrue(hasattr(graph, 'atom_attr'))
        self.assertTrue(hasattr(graph, 'atom_pos'))
        self.assertTrue(hasattr(graph, 'cell'))
        self.assertTrue(hasattr(graph, 'edge_index'))
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_atomic_numbers_correct(self):
        """Test that atomic numbers are correctly set."""
        crystal = Crystal(['Si', 'O'], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice(10))
        graph = structure_to_graph(crystal, cutoff=5.0)
        
        # Si = 14, O = 8
        atom_numbers = graph.atom_attr.squeeze().numpy()
        self.assertEqual(atom_numbers[0], 14)
        self.assertEqual(atom_numbers[1], 8)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_positions_preserved(self):
        """Test that positions are correctly preserved."""
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        graph = structure_to_graph(crystal, cutoff=5.0)
        
        # Check positions shape
        self.assertEqual(graph.atom_pos.shape[0], 1)
        self.assertEqual(graph.atom_pos.shape[1], 3)

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_single_atom_crystal(self):
        """Test single atom crystal."""
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        dataloader = build_dataloader([crystal], only_inference=True)
        
        self.assertEqual(len(dataloader), 1)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_large_molecule(self):
        """Test molecule with many atoms."""
        n = 20
        molecule = Molecule(
            ['C'] * n,
            [[i * 0.5, 0, 0] for i in range(n)]
        )
        
        with warnings.catch_warnings():
            # Suppress expected warning about no PBC for molecules
            warnings.filterwarnings("ignore", category=UserWarning, message="No PBC detected")
            graph = structure_to_graph(molecule, cutoff=2.0)
        
        self.assertEqual(graph.num_atoms, n)
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_invalid_stress_shape_raises_error(self):
        """Test that invalid stress shape raises error."""
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        
        # Wrong shape stress
        with self.assertRaises(ValueError):
            build_dataloader(
                [crystal],
                stresses=[np.array([1, 2, 3])],  # Wrong shape
                only_inference=False,
                energies=[-10.0]
            )

class TestBackwardCompatibility(unittest.TestCase):
    """Test that refactored version maintains compatibility."""
    
    @unittest.skipUnless(has_torch() and has_torch_geometric(), "torch or torch_geometric not installed")
    def test_dataloader_interface_unchanged(self):
        """Test that public interface hasn't changed."""
        # Old code should still work
        crystal = Crystal(['Si'], [[0, 0, 0]], Lattice(5.43))
        dataloader = build_dataloader([crystal], cutoff=5.0, only_inference=True)
        
        self.assertIsNotNone(dataloader)

if __name__ == '__main__':
    unittest.main()

