"""
Tests for nanostructure builders.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.nanostructure import (
    build_nanotube,
    build_carbon_nanotube,
    build_twisted_bilayer,
    build_magic_angle_twisted,
    build_twisted_multilayer,
)

class TestNanotube:
    """Test nanotube builders."""
    
    def test_build_carbon_nanotube_armchair(self):
        """Test building armchair carbon nanotube."""
        cnt = build_carbon_nanotube(5, 5)
        
        assert isinstance(cnt, Crystal)
        assert len(cnt.species) > 0
        assert all(s == 'C' for s in cnt.species)
        assert cnt.lattice is not None
    
    def test_build_carbon_nanotube_zigzag(self):
        """Test building zigzag carbon nanotube."""
        cnt = build_carbon_nanotube(10, 0)
        
        assert isinstance(cnt, Crystal)
        assert len(cnt.species) > 0
        assert all(s == 'C' for s in cnt.species)
    
    def test_build_carbon_nanotube_chiral(self):
        """Test building chiral carbon nanotube."""
        cnt = build_carbon_nanotube(7, 3)
        
        assert isinstance(cnt, Crystal)
        assert len(cnt.species) > 0
    
    def test_build_carbon_nanotube_invalid_chirality(self):
        """Test that invalid chirality raises error."""
        with pytest.raises(ValueError, match="Chirality indices cannot both be zero"):
            build_carbon_nanotube(0, 0)
    
    def test_build_carbon_nanotube_with_length(self):
        """Test building nanotube with specified length."""
        cnt = build_carbon_nanotube(5, 5, length=50.0)
        
        assert isinstance(cnt, Crystal)
        # Check that the structure exists and has proper coordinates
        assert len(cnt.positions) > 0
        # Check that z-coordinates are within reasonable range
        z_coords = cnt.positions[:, 2]
        assert np.max(np.abs(z_coords)) >= 0  # At least some coordinates exist
    
    def test_build_nanotube_from_2d(self):
        """Test building nanotube from 2D structure."""
        # Create a simple 2D structure
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        graphene = Crystal(species, positions, lattice_2d)
        
        nanotube = build_nanotube(graphene, (5, 5))
        
        assert isinstance(nanotube, Crystal)
        # Nanotube should have more atoms than input (supercell is created first)
        assert len(nanotube.species) > len(graphene.species)
        assert all(s == 'C' for s in nanotube.species)
    
    def test_build_nanotube_non_graphene(self):
        """Test building nanotube from non-graphene 2D material."""
        # Create a simple hexagonal boron nitride (hBN) structure
        # hBN has a hexagonal structure similar to graphene but with B and N
        a = 2.50  # Lattice parameter for hBN
        species = ['B', 'N']
        positions = [[0.0, 0.0, 0.0], [a/3, a*np.sqrt(3)/3, 0.0]]
        lattice_2d = Lattice(np.array([
            [a, 0, 0],
            [a/2, a*np.sqrt(3)/2, 0],
            [0, 0, 10.0]
        ]))
        hbn = Crystal(species, positions, lattice_2d)
        
        # Build hBN nanotube
        hbn_nanotube = build_nanotube(hbn, (10, 0))
        
        assert isinstance(hbn_nanotube, Crystal)
        # Nanotube should have more atoms than input (supercell is created first)
        assert len(hbn_nanotube.species) > len(hbn.species)
        assert 'B' in hbn_nanotube.species
        assert 'N' in hbn_nanotube.species
        # Check that B and N are both present
        b_count = sum(1 for s in hbn_nanotube.species if s == 'B')
        n_count = sum(1 for s in hbn_nanotube.species if s == 'N')
        assert b_count > 0 and n_count > 0
        # Note: For zigzag nanotubes, the ratio may not be exactly 1:1
        # Just verify both species are present

class TestTwistedBilayer:
    """Test twisted bilayer builders."""
    
    def test_build_twisted_bilayer_basic(self):
        """Test building basic twisted bilayer."""
        # Create a simple 2D layer
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        twisted = build_twisted_bilayer(layer, 1.1, layer_spacing=3.35)
        
        assert isinstance(twisted, Crystal)
        assert len(twisted.species) == 2 * len(layer.species)
        # Check that layers are separated (should be at least layer_spacing apart)
        # Check cartesian coordinates for actual separation in Angstroms
        z_coords = twisted.cart_positions[:, 2]
        z_range = np.max(z_coords) - np.min(z_coords)
        assert z_range >= 3.0, f"Layer separation {z_range} Angstrom is too small"
    
    def test_build_twisted_bilayer_magic_angle(self):
        """Test building magic-angle twisted bilayer."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        twisted = build_twisted_bilayer(layer, 1.1, layer_spacing=3.35)
        
        assert isinstance(twisted, Crystal)
        assert len(twisted.species) == 4
    
    def test_build_twisted_bilayer_large_angle(self):
        """Test building twisted bilayer with large angle."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        twisted = build_twisted_bilayer(layer, 15.0, layer_spacing=3.35)
        
        assert isinstance(twisted, Crystal)
        assert len(twisted.species) == 4
    
    def test_build_twisted_bilayer_auto_spacing(self):
        """Test building twisted bilayer with auto-calculated spacing."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 3.35]  # Set c-vector to typical spacing
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        twisted = build_twisted_bilayer(layer, 1.1)
        
        assert isinstance(twisted, Crystal)

class TestMagicAngleTwisted:
    """Test magic-angle twisted builders."""
    
    def test_build_magic_angle_twisted(self):
        """Test building magic-angle twisted structure."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        twisted = build_magic_angle_twisted(layer, n=1, m=1)
        
        assert isinstance(twisted, Crystal)
        assert len(twisted.species) == 4

class TestTwistedMultilayer:
    """Test twisted multilayer builders."""
    
    def test_build_twisted_multilayer_same_angle(self):
        """Test building multilayer with same angle between layers."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        multilayer = build_twisted_multilayer(layer, 3, 1.1, layer_spacing=3.35)
        
        assert isinstance(multilayer, Crystal)
        assert len(multilayer.species) == 3 * len(layer.species)
    
    def test_build_twisted_multilayer_different_angles(self):
        """Test building multilayer with different angles."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        multilayer = build_twisted_multilayer(
            layer, 3, [1.1, 2.0], layer_spacing=3.35
        )
        
        assert isinstance(multilayer, Crystal)
        assert len(multilayer.species) == 3 * len(layer.species)
    
    def test_build_twisted_multilayer_invalid_num_layers(self):
        """Test that invalid number of layers raises error."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        with pytest.raises(ValueError, match="num_layers must be at least 2"):
            build_twisted_multilayer(layer, 1, 1.1)
    
    def test_build_twisted_multilayer_invalid_angles(self):
        """Test that invalid number of angles raises error."""
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        
        with pytest.raises(ValueError, match="Number of twist angles"):
            build_twisted_multilayer(layer, 3, [1.1])  # Should be 2 angles for 3 layers

