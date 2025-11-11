"""
LaTeX table export utilities for Crystal and Molecule structures.

Provides functions to export lists of structures to well-formatted LaTeX tables
for use in papers, reports, and documentation.
"""

from typing import List, Union, Optional, Callable
from ..core import Crystal, Molecule


def crystals_to_latex_table(
    crystals: List[Crystal],
    caption: str = "Crystal Structures",
    label: str = "tab:crystals",
    include_columns: Optional[List[str]] = None,
    custom_formatters: Optional[dict] = None
) -> str:
    """
    Export list of crystals to LaTeX table.
    
    Creates a professional LaTeX table with ID, formula, space group,
    and lattice parameters.
    
    Args:
        crystals: List of Crystal objects to export.
        caption: Table caption.
        label: LaTeX label for referencing.
        include_columns: List of columns to include. If None, uses default:
                        ['ID', 'Formula', 'Space Group', 'Lattice'].
                        Available: 'ID', 'Formula', 'Space Group', 'Lattice',
                        'Volume', 'Density', 'Atoms'.
        custom_formatters: Dictionary mapping column names to custom formatting functions.
                          Each function takes (crystal, index) and returns string.
    
    Returns:
        LaTeX table code as string.
        
    Examples:
        >>> from matsimpy.core import Crystal, Lattice
        >>> from matsimpy.io.latex import crystals_to_latex_table
        >>> 
        >>> crystals = [
        ...     Crystal(['Si'], [[0,0,0]], Lattice(5.43)),
        ...     Crystal(['Fe'], [[0,0,0]], Lattice(2.87))
        ... ]
        >>> latex = crystals_to_latex_table(crystals, caption="My Crystals")
        >>> print(latex)
    """
    if not crystals:
        raise ValueError("Crystal list cannot be empty")
    
    # Default columns
    if include_columns is None:
        include_columns = ['ID', 'Formula', 'Space Group', 'Lattice']
    
    # Start table
    num_cols = len(include_columns)
    col_spec = 'c' * num_cols
    
    lines = []
    lines.append(r'\begin{table}[htbp]')
    lines.append(r'    \centering')
    lines.append(f'    \\caption{{{caption}}}')
    lines.append(f'    \\label{{{label}}}')
    lines.append(f'    \\begin{{tabular}}{{{col_spec}}}')
    lines.append(r'        \toprule')
    
    # Header row
    header = ' & '.join(include_columns) + r' \\'
    lines.append(f'        {header}')
    lines.append(r'        \midrule')
    
    # Data rows
    for idx, crystal in enumerate(crystals, start=1):
        row_data = []
        
        for col in include_columns:
            if custom_formatters and col in custom_formatters:
                # Use custom formatter
                value = custom_formatters[col](crystal, idx)
            else:
                # Use default formatters
                value = _format_crystal_column(crystal, col, idx)
            
            row_data.append(value)
        
        row = ' & '.join(row_data) + r' \\'
        lines.append(f'        {row}')
    
    # End table
    lines.append(r'        \bottomrule')
    lines.append(r'    \end{tabular}')
    lines.append(r'\end{table}')
    
    return '\n'.join(lines)


def molecules_to_latex_table(
    molecules: List[Molecule],
    caption: str = "Molecular Structures",
    label: str = "tab:molecules",
    include_columns: Optional[List[str]] = None,
    custom_formatters: Optional[dict] = None
) -> str:
    """
    Export list of molecules to LaTeX table.
    
    Creates a professional LaTeX table with ID, formula, point group,
    and molecular properties.
    
    Args:
        molecules: List of Molecule objects to export.
        caption: Table caption.
        label: LaTeX label for referencing.
        include_columns: List of columns to include. If None, uses default:
                        ['ID', 'Formula', 'Point Group', 'Atoms'].
                        Available: 'ID', 'Formula', 'Point Group', 'Atoms',
                        'Mass', 'COM'.
        custom_formatters: Dictionary mapping column names to custom formatting functions.
                          Each function takes (molecule, index) and returns string.
    
    Returns:
        LaTeX table code as string.
        
    Examples:
        >>> from matsimpy.core import Molecule
        >>> from matsimpy.io.latex import molecules_to_latex_table
        >>> 
        >>> molecules = [
        ...     Molecule(['C', 'O'], [[0,0,0], [1.2,0,0]]),
        ...     Molecule(['H', 'H', 'O'], [[0,0,0], [0.76,0.59,0], [-0.76,0.59,0]])
        ... ]
        >>> latex = molecules_to_latex_table(molecules, caption="My Molecules")
        >>> print(latex)
    """
    if not molecules:
        raise ValueError("Molecule list cannot be empty")
    
    # Default columns
    if include_columns is None:
        include_columns = ['ID', 'Formula', 'Point Group', 'Atoms']
    
    # Start table
    num_cols = len(include_columns)
    col_spec = 'c' * num_cols
    
    lines = []
    lines.append(r'\begin{table}[htbp]')
    lines.append(r'    \centering')
    lines.append(f'    \\caption{{{caption}}}')
    lines.append(f'    \\label{{{label}}}')
    lines.append(f'    \\begin{{tabular}}{{{col_spec}}}')
    lines.append(r'        \toprule')
    
    # Header row
    header = ' & '.join(include_columns) + r' \\'
    lines.append(f'        {header}')
    lines.append(r'        \midrule')
    
    # Data rows
    for idx, molecule in enumerate(molecules, start=1):
        row_data = []
        
        for col in include_columns:
            if custom_formatters and col in custom_formatters:
                # Use custom formatter
                value = custom_formatters[col](molecule, idx)
            else:
                # Use default formatters
                value = _format_molecule_column(molecule, col, idx)
            
            row_data.append(value)
        
        row = ' & '.join(row_data) + r' \\'
        lines.append(f'        {row}')
    
    # End table
    lines.append(r'        \bottomrule')
    lines.append(r'    \end{tabular}')
    lines.append(r'\end{table}')
    
    return '\n'.join(lines)


def _format_crystal_column(crystal: Crystal, column: str, index: int) -> str:
    """
    Format a single column value for crystal table.
    
    Args:
        crystal: Crystal object.
        column: Column name.
        index: Crystal index (1-based).
    
    Returns:
        Formatted string for LaTeX table cell.
    """
    if column == 'ID':
        return str(index)
    
    elif column == 'Formula':
        # Use LaTeX formatting from composition
        return crystal.composition.to_latex()
    
    elif column == 'Space Group':
        # Try to get space group if available
        if hasattr(crystal, 'space_group'):
            return str(crystal.space_group)
        else:
            return 'N/A'
    
    elif column == 'Lattice':
        # Format lattice parameters
        lat = crystal.lattice
        return (f'$a={lat.a:.3f}$, $b={lat.b:.3f}$, $c={lat.c:.3f}$ \\AA')
    
    elif column == 'Volume':
        return f'{crystal.volume:.2f}'
    
    elif column == 'Density':
        try:
            density = crystal.density()
            return f'{density:.3f}'
        except:
            return 'N/A'
    
    elif column == 'Atoms':
        return str(len(crystal))
    
    else:
        return 'N/A'


def _format_molecule_column(molecule: Molecule, column: str, index: int) -> str:
    """
    Format a single column value for molecule table.
    
    Args:
        molecule: Molecule object.
        column: Column name.
        index: Molecule index (1-based).
    
    Returns:
        Formatted string for LaTeX table cell.
    """
    if column == 'ID':
        return str(index)
    
    elif column == 'Formula':
        # Use LaTeX formatting from composition
        return molecule.composition.to_latex()
    
    elif column == 'Point Group':
        # Try to get point group if available
        if hasattr(molecule, 'point_group'):
            return str(molecule.point_group)
        else:
            return 'N/A'
    
    elif column == 'Atoms':
        return str(len(molecule))
    
    elif column == 'Mass':
        return f'{molecule.composition.mass:.2f}'
    
    elif column == 'COM':
        # Center of mass
        com = molecule.get_center_of_mass()
        return f'({com[0]:.2f}, {com[1]:.2f}, {com[2]:.2f})'
    
    else:
        return 'N/A'


def structures_to_latex_table(
    structures: List[Union[Crystal, Molecule]],
    caption: str = "Structures",
    label: str = "tab:structures",
    separate_by_type: bool = True
) -> str:
    """
    Export mixed list of structures to LaTeX table(s).
    
    Args:
        structures: List of Crystal and/or Molecule objects.
        caption: Base caption for table(s).
        label: Base label for table(s).
        separate_by_type: If True, create separate tables for crystals and molecules.
                         If False, create single table with type column.
    
    Returns:
        LaTeX table code as string (may include multiple tables).
        
    Examples:
        >>> structures = [crystal1, molecule1, crystal2, molecule2]
        >>> latex = structures_to_latex_table(structures, separate_by_type=True)
        >>> # Creates two tables: one for crystals, one for molecules
    """
    if not structures:
        raise ValueError("Structure list cannot be empty")
    
    if separate_by_type:
        # Separate into crystals and molecules
        crystals = [s for s in structures if isinstance(s, Crystal)]
        molecules = [s for s in structures if isinstance(s, Molecule) and not isinstance(s, Crystal)]
        
        tables = []
        
        if crystals:
            crystal_table = crystals_to_latex_table(
                crystals,
                caption=f"{caption} - Crystals",
                label=f"{label}:crystals"
            )
            tables.append(crystal_table)
        
        if molecules:
            molecule_table = molecules_to_latex_table(
                molecules,
                caption=f"{caption} - Molecules",
                label=f"{label}:molecules"
            )
            tables.append(molecule_table)
        
        return '\n\n'.join(tables)
    
    else:
        # Single table with type column
        include_columns = ['ID', 'Type', 'Formula', 'Atoms']
        
        lines = []
        lines.append(r'\begin{table}[htbp]')
        lines.append(r'    \centering')
        lines.append(f'    \\caption{{{caption}}}')
        lines.append(f'    \\label{{{label}}}')
        lines.append(f'    \\begin{{tabular}}{{cccc}}')
        lines.append(r'        \toprule')
        lines.append(r'        ID & Type & Formula & Atoms \\')
        lines.append(r'        \midrule')
        
        for idx, struct in enumerate(structures, start=1):
            struct_type = 'Crystal' if isinstance(struct, Crystal) else 'Molecule'
            formula = struct.composition.to_latex()
            n_atoms = len(struct)
            
            row = f'        {idx} & {struct_type} & {formula} & {n_atoms} \\\\'
            lines.append(row)
        
        lines.append(r'        \bottomrule')
        lines.append(r'    \end{tabular}')
        lines.append(r'\end{table}')
        
        return '\n'.join(lines)


def save_latex_table(
    structures: List[Union[Crystal, Molecule]],
    filename: str,
    **kwargs
) -> None:
    """
    Save structures as LaTeX table to file.
    
    Args:
        structures: List of structures to export.
        filename: Output filename (should end with .tex).
        **kwargs: Additional arguments passed to structures_to_latex_table().
    
    Examples:
        >>> crystals = [crystal1, crystal2, crystal3]
        >>> save_latex_table(crystals, 'crystals.tex', caption="My Structures")
    """
    latex_code = structures_to_latex_table(structures, **kwargs)
    
    with open(filename, 'w') as f:
        f.write(latex_code)


__all__ = [
    'crystals_to_latex_table',
    'molecules_to_latex_table',
    'structures_to_latex_table',
    'save_latex_table',
]

