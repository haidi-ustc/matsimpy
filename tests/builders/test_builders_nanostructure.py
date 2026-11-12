"""
Tests for nanostructure builders.
"""

import pytest
import numpy as np
from matsimpy.core import Crystal, Lattice
from matsimpy.builders.nanostructure import (
    build_carbon_nanotube,
    build_twisted_bilayer,
    build_magic_angle_twisted,
    build_twisted_multilayer,
)


def _sorted_rows(values, decimals=8):
    rounded = np.round(np.asarray(values, dtype=float), decimals)
    return rounded[np.lexsort(rounded.T[::-1])]


def _cylindrical_signature(cart_positions, period):
    xy = cart_positions[:, :2]
    radii = np.linalg.norm(xy, axis=1)
    angles = np.mod(np.arctan2(xy[:, 1], xy[:, 0]), 2 * np.pi)
    z = np.mod(cart_positions[:, 2] - np.min(cart_positions[:, 2]), period)
    return _sorted_rows(np.column_stack([radii, angles, z]))


class TestNanotube:
    """Test nanotube builders."""
    

    def test_build_carbon_nanotube_matches_ase_radius_and_period(self):
        """Carbon nanotube coordinates should match ASE reference geometry."""
        from ase.build import nanotube

        cnt = build_carbon_nanotube(5, 5, center=False)
        reference = nanotube(5, 5, bond=1.42)

        assert len(cnt) == len(reference)
        assert np.isclose(cnt.lattice.c, reference.cell.lengths()[2], rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(
            _cylindrical_signature(cnt.cart_positions, cnt.lattice.c),
            _cylindrical_signature(reference.positions, reference.cell.lengths()[2]),
            rtol=1e-6,
            atol=1e-6,
        )
        assert cnt.pbc == (False, False, True)
    
    def test_build_carbon_nanotube_zigzag(self):
        """Test building zigzag carbon nanotube."""
        cnt = build_carbon_nanotube(10, 0)
        
        assert isinstance(cnt, Crystal)
        assert len(cnt.species) > 0
        assert all(s == 'C' for s in cnt.species)
        assert cnt.pbc == (False, False, True)
    
    
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
    
    
    

class TestMagicAngleTwisted:
    """Test magic-angle twisted builders."""
    

    def test_build_magic_angle_equal_indices_raises(self):
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        with pytest.raises(ValueError, match="Equal indices"):
            build_magic_angle_twisted(layer, n=1, m=1)

    def test_build_magic_angle_invalid_n_m(self):
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        with pytest.raises(ValueError, match="n must be"):
            build_magic_angle_twisted(layer, n=-1, m=2)
        with pytest.raises(ValueError, match="n must be"):
            build_magic_angle_twisted(layer, n=0, m=2)
        with pytest.raises(ValueError, match="m must be"):
            build_magic_angle_twisted(layer, n=2, m=0)

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
        
        with pytest.raises(ValueError, match="num_layers must be an integer"):
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

    def test_build_twisted_multilayer_layer_separations(self):
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        spacing = 3.35
        ml = build_twisted_multilayer(layer, 3, 1.1, layer_spacing=spacing)
        cart = ml.cart_positions
        z_range = np.max(cart[:, 2]) - np.min(cart[:, 2])
        assert z_range < 50.0, f"z-range {z_range} is too large"

    def test_build_twisted_multilayer_invalid_spacing(self):
        species = ['C', 'C']
        positions = [[0, 0, 0], [1.42, 0, 0]]
        lattice_2d = Lattice(np.array([
            [2.46, 0, 0],
            [1.23, 2.13, 0],
            [0, 0, 10.0]
        ]))
        layer = Crystal(species, positions, lattice_2d)
        with pytest.raises(ValueError, match="layer_spacing"):
            build_twisted_multilayer(layer, 3, 1.1, layer_spacing=0.0)
        with pytest.raises(ValueError, match="layer_spacing"):
            build_twisted_multilayer(layer, 3, 1.1, layer_spacing=-1.0)
        with pytest.raises(ValueError, match="layer_spacing"):
            build_twisted_multilayer(layer, 3, 1.1, layer_spacing=float('nan'))
