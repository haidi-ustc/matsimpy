"""
Lennard-Jones potential calculator.

Implements the Lennard-Jones (LJ) potential for classical simulations.
The LJ potential is commonly used for noble gases and simple molecular systems.
"""

import numpy as np
from typing import Optional, Dict, Tuple
from scipy.spatial import cKDTree
from .base import Calculator
from ..core import Crystal, Molecule


class LennardJones(Calculator):
    """
    Lennard-Jones potential calculator.
    
    The Lennard-Jones potential is given by:
        V(r) = 4*epsilon * [(sigma/r)^12 - (sigma/r)^6]
    
    where:
        - epsilon: Well depth (energy parameter)
        - sigma: Distance at which potential is zero (size parameter)
        - r: Distance between atoms
    
    Attributes:
        sigma (float): LJ size parameter in Å
        epsilon (float): LJ energy parameter in eV
        cutoff (float): Cutoff distance in Å (default: 3*sigma)
        rc_smooth (float): Smoothing distance for cutoff (default: cutoff)
        
    Example:
        >>> from matsimpy import Crystal, Lattice
        >>> from matsimpy.calculator import LennardJones
        >>> 
        >>> # Create Ar crystal
        >>> crystal = Crystal(['Ar'], [[0,0,0]], Lattice.cubic(5.0))
        >>> calc = LennardJones(sigma=3.4, epsilon=0.0104)
        >>> crystal.calc = calc
        >>> calc.calculate(crystal)
        >>> energy = calc.get_potential_energy()
    """
    
    def __init__(self, 
                 sigma: float = 3.4,
                 epsilon: float = 0.0104,
                 cutoff: Optional[float] = None,
                 rc_smooth: Optional[float] = None,
                 **kwargs):
        """
        Initialize Lennard-Jones calculator.
        
        Args:
            sigma: LJ size parameter in Å (default: 3.4 for Ar)
            epsilon: LJ energy parameter in eV (default: 0.0104 for Ar)
            cutoff: Cutoff distance in Å. If None, uses 3*sigma
            rc_smooth: Smoothing distance for cutoff. If None, uses cutoff
            **kwargs: Additional parameters (passed to parent)
        """
        super().__init__(sigma=sigma, epsilon=epsilon, **kwargs)
        
        # Set cutoff
        if cutoff is None:
            cutoff = 3.0 * sigma
        self.parameters['cutoff'] = cutoff
        
        # Set smoothing distance
        if rc_smooth is None:
            rc_smooth = cutoff
        self.parameters['rc_smooth'] = rc_smooth
        
    def _compute(self) -> None:
        """
        Compute LJ energy and forces.
        
        Stores results in self.results:
            - 'energy': Total potential energy in eV
            - 'forces': Forces array of shape (N, 3) in eV/Å
            - 'stress': Stress tensor (for crystals) in eV/Å³
        """
        if self.structure is None:
            raise ValueError("Structure not set. Call calculate(structure) first.")
            
        sigma = self.parameters['sigma']
        epsilon = self.parameters['epsilon']
        cutoff = self.parameters['cutoff']
        rc_smooth = self.parameters['rc_smooth']
        
        # Get positions (always use Cartesian)
        if isinstance(self.structure, Crystal):
            positions = self.structure.cart_positions
            lattice = self.structure.lattice
            pbc = self.structure.pbc
        else:
            # Molecule uses positions directly (Cartesian)
            positions = np.array(self.structure.positions)
            lattice = None
            pbc = [False, False, False]
        
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        stress = np.zeros((3, 3))
        
        # Build neighbor list using KDTree
        if lattice is not None and any(pbc):
            # For periodic systems, use minimum image convention
            energy, forces, stress = self._compute_periodic(
                positions, lattice, pbc, sigma, epsilon, cutoff, rc_smooth
            )
        else:
            # For non-periodic systems (molecules or non-periodic crystals)
            energy, forces = self._compute_non_periodic(
                positions, sigma, epsilon, cutoff, rc_smooth
            )
        
        # Store results
        self.results['energy'] = energy
        self.results['forces'] = forces
        if lattice is not None:
            self.results['stress'] = stress
        
    def _compute_non_periodic(self,
                             positions: np.ndarray,
                             sigma: float,
                             epsilon: float,
                             cutoff: float,
                             rc_smooth: float) -> Tuple[float, np.ndarray]:
        """
        Compute LJ energy and forces for non-periodic system.
        
        Args:
            positions: Atomic positions (N, 3)
            sigma: LJ size parameter
            epsilon: LJ energy parameter
            cutoff: Cutoff distance
            rc_smooth: Smoothing distance
            
        Returns:
            Tuple of (energy, forces)
        """
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        
        # Build KDTree for efficient neighbor finding
        tree = cKDTree(positions)
        
        # Find all pairs within cutoff
        pairs = tree.query_pairs(cutoff, output_type='ndarray')
        
        # Compute LJ interactions
        for i, j in pairs:
            r_vec = positions[j] - positions[i]
            r = np.linalg.norm(r_vec)
            
            if r < cutoff:
                # Apply smoothing function if rc_smooth < cutoff
                if rc_smooth < cutoff and r > rc_smooth:
                    # Smooth cutoff function (shifted Fermi)
                    f = 1.0 / (1.0 + np.exp((r - rc_smooth) / (cutoff - rc_smooth)))
                    df_dr = -f * (1.0 - f) / (cutoff - rc_smooth)
                else:
                    f = 1.0
                    df_dr = 0.0
                
                # LJ potential: V(r) = 4*epsilon * [(sigma/r)^12 - (sigma/r)^6]
                sr6 = (sigma / r) ** 6
                sr12 = sr6 ** 2
                v = 4.0 * epsilon * (sr12 - sr6) * f
                energy += v
                
                # Force: F = -dV/dr * r_hat
                # dV/dr = 4*epsilon * [12*sigma^12/r^13 - 6*sigma^6/r^7] * f
                #        + 4*epsilon * (sr12 - sr6) * df_dr
                dv_dr = 4.0 * epsilon * (
                    (12.0 * sr12 - 6.0 * sr6) / r * f +
                    (sr12 - sr6) * df_dr
                )
                force_vec = dv_dr * r_vec / r
                
                forces[i] -= force_vec
                forces[j] += force_vec
        
        return energy, forces
        
    def _compute_periodic(self,
                         positions: np.ndarray,
                         lattice,
                         pbc: list,
                         sigma: float,
                         epsilon: float,
                         cutoff: float,
                         rc_smooth: float) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Compute LJ energy and forces for periodic system.
        
        Uses minimum image convention for periodic boundary conditions.
        
        Args:
            positions: Atomic positions in fractional coordinates
            lattice: Lattice object
            pbc: Periodic boundary conditions [x, y, z]
            sigma: LJ size parameter
            epsilon: LJ energy parameter
            cutoff: Cutoff distance
            rc_smooth: Smoothing distance
            
        Returns:
            Tuple of (energy, forces, stress)
        """
        n_atoms = len(positions)
        energy = 0.0
        forces = np.zeros((n_atoms, 3))
        stress = np.zeros((3, 3))
        
        # Convert fractional to Cartesian for neighbor finding
        # positions are in fractional, convert using lattice matrix
        cart_positions = np.dot(positions, lattice.matrix)
        
        # Build KDTree
        tree = cKDTree(cart_positions)
        
        # Find pairs within cutoff (considering periodic images)
        # For simplicity, we'll check the first periodic image
        # In a full implementation, we'd check multiple images
        pairs = tree.query_pairs(cutoff, output_type='ndarray')
        
        # Compute interactions
        for i, j in pairs:
            # Get distance vector in Cartesian
            r_vec_cart = cart_positions[j] - cart_positions[i]
            
            # Apply minimum image convention
            # Convert to fractional using inverse matrix
            r_vec_frac = np.dot(r_vec_cart, lattice.inv_matrix)
            
            # Wrap to [-0.5, 0.5]
            r_vec_frac = r_vec_frac - np.round(r_vec_frac)
            
            # Convert back to Cartesian using matrix multiplication
            r_vec = np.dot(r_vec_frac, lattice.matrix)
            r = np.linalg.norm(r_vec)
            
            if r < cutoff and r > 1e-10:  # Avoid self-interaction
                # Apply smoothing
                if rc_smooth < cutoff and r > rc_smooth:
                    f = 1.0 / (1.0 + np.exp((r - rc_smooth) / (cutoff - rc_smooth)))
                    df_dr = -f * (1.0 - f) / (cutoff - rc_smooth)
                else:
                    f = 1.0
                    df_dr = 0.0
                
                # LJ potential
                sr6 = (sigma / r) ** 6
                sr12 = sr6 ** 2
                v = 4.0 * epsilon * (sr12 - sr6) * f
                energy += v
                
                # Force
                dv_dr = 4.0 * epsilon * (
                    (12.0 * sr12 - 6.0 * sr6) / r * f +
                    (sr12 - sr6) * df_dr
                )
                force_vec = dv_dr * r_vec / r
                
                # Forces stay in Cartesian for storage
                forces[i] -= force_vec
                forces[j] += force_vec
                
                # Stress contribution: -F * r (outer product)
                stress_contrib = -np.outer(force_vec, r_vec)
                stress += stress_contrib
        
        # Forces are already in Cartesian
        
        # Stress in eV/Å³ (volume is in Å³)
        volume = lattice.volume()  # volume is a method
        if volume > 0:
            stress = stress / volume
        
        return energy, forces, stress


__all__ = ['LennardJones']

