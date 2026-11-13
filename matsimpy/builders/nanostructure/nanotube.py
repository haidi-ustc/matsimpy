"""
Nanotubes rolled from any 2D sheet.

The chiral vector C = n*a1 + m*a2 of the sheet becomes the tube circumference and
the shortest lattice vector T perpendicular to C becomes the tube axis. T is found
from the sheet's metric, so the same code handles hexagonal (60 or 120 degree basis),
square, rectangular and oblique lattices; graphene, h-BN, MoS2, phosphorene and so on.
Atoms keep their height above the sheet's mid-plane, so a three-layer sheet such as
MoS2 becomes three coaxial shells.
"""

from fractions import Fraction
from math import pi
from typing import Optional, Tuple

import numpy as np

from matsimpy.utils.tooling import tool

from ...core import Crystal, Lattice
from ._sheet import sheet_from_layer, tile

__all__ = ["build_nanotube", "build_carbon_nanotube", "nanotube_translation"]


def nanotube_translation(sheet_lattice: np.ndarray, n: int, m: int, max_index: int = 1000) -> Tuple[int, int]:
    """The shortest lattice vector T = t1*a1 + t2*a2 perpendicular to C = n*a1 + m*a2.

    Args:
        sheet_lattice: 2x2 array whose columns are a1 and a2.
        n, m: Chiral indices.
        max_index: Largest |t1| or |t2| searched.

    Returns:
        (t1, t2), oriented so that C x T points along +z.

    Raises:
        ValueError: If no such vector exists with indices up to ``max_index``; then the
            sheet has no translational period along the tube axis (e.g. a rectangular
            lattice whose a/b ratio is irrational, rolled along a diagonal).
    """
    metric = sheet_lattice.T @ sheet_lattice
    p, q = metric @ np.array([n, m], dtype=float)  # T . C = t1 * p + t2 * q
    scale = float(np.sqrt(metric[0, 0] * metric[1, 1]))
    if abs(q) < 1e-12 * scale:
        t1, t2 = 0, 1
    elif abs(p) < 1e-12 * scale:
        t1, t2 = 1, 0
    else:
        ratio = Fraction(-p / q).limit_denominator(max_index)  # t2 / t1
        t1, t2 = ratio.denominator, ratio.numerator
    chiral = sheet_lattice @ np.array([n, m], dtype=float)
    translation = sheet_lattice @ np.array([t1, t2], dtype=float)
    cosine = float(chiral @ translation) / (np.linalg.norm(chiral) * np.linalg.norm(translation))
    if abs(cosine) > 1e-9 or max(abs(t1), abs(t2)) > max_index:
        raise ValueError(
            f"The sheet has no lattice vector perpendicular to the chiral vector ({n}, {m}) "
            f"with indices up to {max_index}, so the tube would not be periodic. "
            "Roll it along a lattice direction whose perpendicular is also a lattice direction."
        )
    if chiral[0] * translation[1] - chiral[1] * translation[0] < 0:
        t1, t2 = -t1, -t2
    return t1, t2


@tool
def build_nanotube(
    base_2d: Crystal,
    chirality: Tuple[int, int],
    length: Optional[float] = None,
    periodic: bool = True,
    vacuum: float = 10.0,
    max_atoms: int = 20000,
) -> Crystal:
    """
    Roll a 2D sheet into a nanotube.

    Works for any 2D lattice whose chiral direction has a perpendicular lattice
    vector: hexagonal (graphene, h-BN, MoS2), square and rectangular (phosphorene)
    lattices for all chiralities, oblique lattices for commensurate directions.
    The chiral vector n*a1 + m*a2 is the circumference; the indices refer to the
    sheet's own a and b (for graphene in a 60-degree basis, (n, n) is armchair and
    (n, 0) zigzag; (n, m) and (m, n) are mirror images). Atoms at height h above the sheet's mid-plane end up at radius
    R + h, so thick sheets become coaxial shells. The tube axis is z, centred in
    the cell.

    Args:
        base_2d: The sheet: a crystal whose a and b vectors lie in the xy-plane.
        chirality: Chiral indices (n, m), not both zero.
        length: Minimum tube length in Angstroms; rounded up to whole periods
            (default: one period).
        periodic: Periodic along the axis (True) or a finite tube with vacuum at
            both ends (False).
        vacuum: Vacuum around the tube in Angstroms (and at the ends of a finite tube).
        max_atoms: Refuse to build tubes with more atoms than this.

    Returns:
        Crystal: The nanotube, periodic only along z when ``periodic``. Its metadata
        holds the chirality, radius (of the mid-plane) and translation indices.

    Examples:
        >>> from matsimpy.builders.nanostructure import build_nanotube
        >>> from matsimpy.core import Crystal, Lattice
        >>> hbn = Crystal(['B', 'N'], [[1/3, 2/3, 0.5], [2/3, 1/3, 0.5]],
        ...               Lattice.hexagonal(2.50, 15.0))
        >>> bnnt = build_nanotube(hbn, (8, 0))
        >>> square = Crystal(['Cu'], [[0, 0, 0.5]], Lattice.tetragonal(2.55, 15.0))
        >>> tube = build_nanotube(square, (10, 0))
    """
    sheet = sheet_from_layer(base_2d, "base_2d")
    n, m = (int(value) for value in chirality)
    if (n, m) != tuple(chirality):
        raise ValueError(f"chirality must be integers, got {chirality}")
    if n == 0 and m == 0:
        raise ValueError("Chirality indices cannot both be zero")
    if length is not None and not (np.isfinite(length) and length > 0):
        raise ValueError(f"length must be positive, got {length}")
    if not (np.isfinite(vacuum) and vacuum >= 0):
        raise ValueError(f"vacuum must be non-negative, got {vacuum}")

    t1, t2 = nanotube_translation(sheet.lattice, n, m)
    supercell = np.array([[n, t1], [m, t2]])
    chiral = sheet.lattice @ supercell[:, 0]
    translation = sheet.lattice @ supercell[:, 1]
    circumference = float(np.linalg.norm(chiral))
    period = float(np.linalg.norm(translation))
    radius = circumference / (2 * pi)
    periods = 1 if length is None else max(1, int(np.ceil(length / period - 1e-9)))
    count = abs(int(round(np.linalg.det(supercell)))) * len(sheet.species) * periods
    if count > max_atoms:
        raise ValueError(f"The ({n}, {m}) tube has {count} atoms, more than max_atoms={max_atoms}")

    index, frac = tile(sheet, supercell)
    heights = sheet.height[index] - (sheet.height.max() + sheet.height.min()) / 2
    if radius + heights.min() <= 0:
        raise ValueError(f"The ({n}, {m}) tube is too narrow for a sheet of this thickness")
    theta = 2 * pi * frac[:, 0]
    r = radius + heights
    outer = float(r.max())
    box = 2 * outer + vacuum
    axial = periods * period
    cell_c = axial if periodic else axial + vacuum
    z0 = 0.0 if periodic else vacuum / 2
    positions = np.concatenate([
        np.column_stack([box / 2 + r * np.cos(theta), box / 2 + r * np.sin(theta),
                         z0 + (frac[:, 1] + k) * period])
        for k in range(periods)
    ])
    species = [sheet.species[i] for i in index] * periods
    properties = None
    if sheet.site_properties:
        properties = [dict(sheet.site_properties[i]) for i in index] * periods
    return Crystal(
        species, positions.tolist(), Lattice.orthorhombic(box, box, cell_c),
        coords_are_cartesian=True, pbc=(False, False, periodic), site_properties=properties,
        metadata={"chirality": [n, m], "radius": radius, "translation": [t1, t2]},
    )


@tool
def build_carbon_nanotube(
    n: int,
    m: int,
    bond_length: float = 1.42,
    length: Optional[float] = None,
    periodic: bool = True,
    vacuum: float = 10.0,
) -> Crystal:
    """
    Build a carbon nanotube from chirality indices.

    Graphene is used in the usual 60-degree basis: (n, n) is armchair, (n, 0) zigzag.

    Args:
        n: First chirality index
        m: Second chirality index
        bond_length: C-C bond length in Angstroms (default: 1.42)
        length: Minimum tube length in Angstroms (default: one period)
        periodic: Periodic along the axis, or a finite tube with vacuum at the ends
        vacuum: Vacuum around the tube in Angstroms

    Returns:
        Crystal: Carbon nanotube along z

    Examples:
        >>> from matsimpy.builders.nanostructure import build_carbon_nanotube
        >>> armchair = build_carbon_nanotube(5, 5)
        >>> zigzag = build_carbon_nanotube(10, 0)
        >>> chiral = build_carbon_nanotube(7, 3)
    """
    if not (np.isfinite(bond_length) and bond_length > 0):
        raise ValueError(f"bond_length must be positive, got {bond_length}")
    return build_nanotube(_create_graphene_sheet(bond_length), (n, m), length=length,
                          periodic=periodic, vacuum=vacuum)


def _create_graphene_sheet(bond_length: float = 1.42) -> Crystal:
    """Graphene in a 60-degree basis (a1 = a x, a2 = a (1/2, sqrt(3)/2)), sheet at z = 0."""
    a = np.sqrt(3.0) * bond_length
    lattice = Lattice([[a, 0.0, 0.0], [0.5 * a, 0.5 * np.sqrt(3) * a, 0.0], [0.0, 0.0, 10.0]])
    return Crystal(["C", "C"], [[0.0, 0.0, 0.0], [1 / 3, 1 / 3, 0.0]], lattice)
