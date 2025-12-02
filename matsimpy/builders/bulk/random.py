"""
Random bulk crystal generation.

Generate random crystal structures with symmetry constraints using PyXtal.
"""

from typing import List, Optional
from ...core import Crystal, Lattice


def random_crystal(
    dim: int, group: int, species: List[str], num_ions: List[int], **kwargs
) -> Crystal:
    """
    Generate a random crystal using PyXtal.

    Args:
        dim: The dimensionality of the crystal (2 or 3)
        group: The space group number
        species: List of chemical symbols for the atoms in the crystal
        num_ions: List of integers representing the number of ions of each species
        **kwargs: Additional keyword arguments to pass to PyXtal

    Returns:
        Crystal: A random crystal object

    Raises:
        ImportError: If pyxtal package is not installed

    Examples:
        >>> from matsimpy.builders.bulk import random_crystal
        >>> # Generate random SiO2 in space group 1
        >>> crystal = random_crystal(3, 1, ['Si', 'O'], [1, 2])
    """
    try:
        import pyxtal
    except ImportError:
        raise ImportError(
            "The pyxtal package is required to generate random crystals. "
            "Install with: pip install pyxtal"
        )

    try:
        # Use the correct PyXtal API: pyxtal.pyxtal class with from_random method
        from pyxtal import pyxtal
        
        pyxtal_crystal = pyxtal()
        pyxtal_crystal.from_random(dim, group, species, num_ions, **kwargs)
        
        # Check if generation was successful
        if not getattr(pyxtal_crystal, 'valid', False):
            raise ValueError("PyXtal failed to generate a valid crystal structure")
        
        # Try to convert to pymatgen first (most reliable method)
        try:
            if hasattr(pyxtal_crystal, 'to_pymatgen'):
                pymatgen_struct = pyxtal_crystal.to_pymatgen()
                # Convert pymatgen Structure to MatSimPy Crystal
                from ...io.converters import from_pymatgen
                return from_pymatgen(pymatgen_struct)
        except (AttributeError, ImportError):
            pass  # Fall through to direct attribute access
        
        # Fallback: Extract directly from pyxtal object
        # PyXtal objects typically have 'struc' attribute with the structure
        if hasattr(pyxtal_crystal, 'struc'):
            struc = pyxtal_crystal.struc
            # Extract species and positions from structure
            if hasattr(struc, 'species'):
                species_list = [str(s.symbol) if hasattr(s, 'symbol') else str(s) 
                               for s in struc.species]
            else:
                raise AttributeError("PyXtal structure does not have species attribute")
            
            # Get fractional coordinates
            if hasattr(struc, 'frac_coords'):
                positions = struc.frac_coords.tolist() if hasattr(struc.frac_coords, 'tolist') else struc.frac_coords
            elif hasattr(struc, 'coords'):
                positions = struc.coords.tolist() if hasattr(struc.coords, 'tolist') else struc.coords
            else:
                raise AttributeError("PyXtal structure does not have position attributes")
            
            # Get lattice
            if hasattr(struc, 'lattice'):
                if hasattr(struc.lattice, 'matrix'):
                    lattice_matrix = struc.lattice.matrix
                else:
                    raise AttributeError("PyXtal lattice does not have matrix attribute")
            else:
                raise AttributeError("PyXtal structure does not have lattice attribute")
        else:
            # Try accessing attributes directly on pyxtal_crystal
            # Some versions may have structure data directly accessible
            if hasattr(pyxtal_crystal, 'species'):
                species_list = [str(s.symbol) if hasattr(s, 'symbol') else str(s) 
                               for s in pyxtal_crystal.species]
            else:
                raise AttributeError("PyXtal crystal does not have species or struc attribute")
            
            if hasattr(pyxtal_crystal, 'frac_coords'):
                positions = pyxtal_crystal.frac_coords.tolist() if hasattr(pyxtal_crystal.frac_coords, 'tolist') else pyxtal_crystal.frac_coords
            else:
                raise AttributeError("PyXtal crystal does not have frac_coords or struc attribute")
            
            if hasattr(pyxtal_crystal, 'lattice') and hasattr(pyxtal_crystal.lattice, 'matrix'):
                lattice_matrix = pyxtal_crystal.lattice.matrix
            else:
                raise AttributeError("PyXtal crystal does not have lattice.matrix or struc attribute")
        
        lattice = Lattice(lattice_matrix)
        return Crystal(species_list, positions, lattice)
        
    except (AttributeError, ValueError, TypeError) as e:
        # Re-raise with more informative message
        raise RuntimeError(
            f"Failed to extract structure from PyXtal crystal object: {e}. "
            f"This may be due to a PyXtal API change. Please check your PyXtal version."
        ) from e


__all__ = ["random_crystal"]
