"""
Surface slab generation.

A slab is cut from the bulk crystal parallel to the (hkl) plane of the bulk cell
given. Its a and b vectors are the shortest lattice vectors spanning the plane
(found from the bulk's full translation lattice, so a conventional input cell still
gives the smallest surface cell); a lies along x, b in the xy-plane and the surface
normal along z, with vacuum above and below. One layer is one interplanar spacing
d_hkl of the bulk and holds one primitive cell's worth of atoms.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional, Tuple

import numpy as np
import spglib

from matsimpy.utils.tooling import tool

from ...core import Crystal, Lattice

__all__ = ["generate_slab", "generate_symmetric_slab"]


def _check_inputs(bulk, miller_index, min_slab_size, min_vacuum_size, layers):
    if not isinstance(bulk, Crystal):
        raise TypeError("bulk must be a Crystal")
    if len(bulk) == 0:
        raise ValueError("bulk has no atoms")
    if len(miller_index) != 3 or any(
        isinstance(i, bool) or not float(i).is_integer() for i in miller_index
    ):
        raise ValueError(f"miller_index must be three integers, got {miller_index}")
    hkl = np.array([int(i) for i in miller_index])
    if not hkl.any():
        raise ValueError("Miller index cannot be (0, 0, 0)")
    if (layers is None) == (min_slab_size is None):
        raise ValueError("Give exactly one of min_slab_size (Angstrom) or layers")
    if min_slab_size is not None and not (np.isfinite(min_slab_size) and min_slab_size > 0):
        raise ValueError(f"min_slab_size must be positive, got {min_slab_size}")
    if layers is not None and (
        isinstance(layers, bool) or not isinstance(layers, (int, np.integer)) or layers < 1
    ):
        raise ValueError(f"layers must be a positive integer, got {layers}")
    if not (np.isfinite(min_vacuum_size) and min_vacuum_size >= 0):
        raise ValueError(f"min_vacuum_size must be non-negative, got {min_vacuum_size}")
    return hkl // np.gcd.reduce(np.abs(hkl))


def _extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """(g, x, y) with a*x + b*y = g = gcd(a, b) >= 0."""
    x0, y0, x1, y1 = 1, 0, 0, 1
    while b:
        q, a, b = a // b, b, a % b
        x0, x1 = x1, x0 - q * x1
        y0, y1 = y1, y0 - q * y1
    if a < 0:
        a, x0, y0 = -a, -x0, -y0
    return a, x0, y0


def _lattice_basis(generators: np.ndarray) -> np.ndarray:
    """A basis (rows) of the integer lattice spanned by the rows of ``generators``."""
    rows = [list(map(int, r)) for r in generators]
    basis = []
    for column in range(3):
        pivot_rows = [r for r in rows if r[column] != 0]
        others = [r for r in rows if r[column] == 0]
        while len(pivot_rows) > 1:
            pivot_rows.sort(key=lambda r: abs(r[column]))
            pivot = pivot_rows[0]
            reduced = []
            for r in pivot_rows[1:]:
                q = r[column] // pivot[column]
                r = [a - q * b for a, b in zip(r, pivot)]
                (reduced if r[column] != 0 else others).append(r)
            pivot_rows = [pivot] + reduced
        if pivot_rows:
            basis.append(pivot_rows[0])
        rows = others
    if len(basis) != 3:
        raise ValueError("The translations do not span three dimensions")  # pragma: no cover
    return np.array(basis)


def _primitive(bulk: Crystal, symprec: float):
    """The bulk's primitive cell in the bulk's own orientation.

    Returns ``(lattice rows, fractional positions, index of the bulk atom of each site)``.
    Atoms with different site properties (e.g. magnetic moments) are kept distinct.
    """
    kinds = {}
    numbers = []
    properties = bulk.site_properties or [{}] * len(bulk)
    for specie, props in zip(bulk.species, properties):
        key = (specie, repr(sorted(props.items())))
        numbers.append(kinds.setdefault(key, len(kinds) + 1))
    cell = (bulk.lattice.matrix, bulk.frac_positions, numbers)
    symmetry = spglib.get_symmetry(cell, symprec=symprec)
    translations = [np.zeros(3)]
    if symmetry is not None:
        identity = [np.array_equal(r, np.eye(3, dtype=int)) for r in symmetry["rotations"]]
        translations = [t % 1.0 for t, keep in zip(symmetry["translations"], identity) if keep]
    denominators = [Fraction(float(x)).limit_denominator(48).denominator for t in translations for x in t]
    scale = int(np.lcm.reduce(denominators)) if denominators else 1
    generators = np.vstack([scale * np.eye(3, dtype=int)] + [np.rint(scale * t).astype(int) for t in translations])
    basis = _lattice_basis(generators) / scale  # rows: primitive vectors in bulk fractional coordinates
    if np.linalg.det(basis) < 0:
        basis[2] *= -1
    lattice = basis @ bulk.lattice.matrix
    frac = bulk.frac_positions @ np.linalg.inv(basis)
    frac = np.mod(np.round(frac, 10), 1.0)
    kept, seen = [], []
    for i, f in enumerate(frac):
        if any(np.allclose(((f - g + 0.5) % 1.0) - 0.5, 0, atol=max(symprec, 1e-6)) for g in seen):
            continue
        seen.append(f)
        kept.append(i)
    expected = len(bulk) * abs(np.linalg.det(basis))
    if not np.isclose(len(kept), expected):
        raise ValueError(
            "Could not reduce the bulk to a primitive cell; pass primitive=False or adjust symprec"
        )
    return lattice, frac[kept], kept


def _surface_cell(lattice: np.ndarray, hkl: np.ndarray):
    """Integer in-plane vectors v1, v2 and stacking vector s of the plane hkl (in the lattice basis).

    v1 x v2 points along the plane normal; s has h.s = 1.
    """
    h, k, l = (int(x) for x in hkl)
    g, x, y = _extended_gcd(h, k)
    if g == 0:
        v1, v2, s = np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1 if l > 0 else -1])
    else:
        v1 = np.array([k // g, -h // g, 0])
        v2 = np.array([-l * x, -l * y, g])
        _, alpha, beta = _extended_gcd(g, l)
        s = np.array([alpha * x, alpha * y, beta])
    assert hkl @ v1 == 0 and hkl @ v2 == 0 and hkl @ s == 1
    # Lagrange-reduce the in-plane basis
    a, b = v1 @ lattice, v2 @ lattice
    while True:
        if b @ b < a @ a - 1e-10:
            v1, v2, a, b = v2, v1, b, a
        mu = int(round(float(a @ b) / float(a @ a)))
        if mu == 0:
            break
        v2, b = v2 - mu * v1, b - mu * a
    normal = np.linalg.solve(lattice, hkl.astype(float))  # reciprocal vector, along the normal
    if np.cross(a, b) @ normal < 0:
        v2 = -v2
    # make the stacking vector as perpendicular to the plane as possible
    stack = s @ lattice
    in_plane = np.column_stack([v1 @ lattice, v2 @ lattice])
    coefficients = np.linalg.lstsq(in_plane, stack, rcond=None)[0]
    s = s - np.rint(coefficients[0]).astype(int) * v1 - np.rint(coefficients[1]).astype(int) * v2
    return v1, v2, s


def _plane_gaps(heights: np.ndarray, period: float, tol: float = 1e-4):
    """Cut positions (in the middle of each gap between atomic planes) and the gap widths, widest first."""
    planes = np.unique(np.round(np.mod(heights, period) / tol) * tol)
    planes = planes[np.concatenate([[True], np.diff(planes) > tol])]
    following = np.append(planes[1:], planes[0] + period)
    gaps = following - planes
    cuts = np.mod(planes + gaps / 2, period)
    order = np.argsort(-np.round(gaps, 6), kind="stable")
    return cuts[order], gaps[order]


def _build(bulk, hkl, min_slab_size, min_vacuum_size, layers, center_slab, primitive, symprec, cut_index=0,
           extra_layers=0):
    if primitive:
        lattice, frac, source = _primitive(bulk, symprec)
    else:
        lattice, frac, source = bulk.lattice.matrix, bulk.frac_positions, list(range(len(bulk)))
        if np.linalg.det(lattice) < 0:
            raise ValueError("bulk lattice is left-handed")
    # the Miller indices in the basis used (rational when that is the primitive basis)
    hkl_lattice = lattice @ np.linalg.solve(bulk.lattice.matrix, hkl.astype(float))
    hkl_lattice = [Fraction(float(x)).limit_denominator(1000) for x in hkl_lattice]
    multiple = int(np.lcm.reduce([x.denominator for x in hkl_lattice]))
    hkl_int = np.array([int(x * multiple) for x in hkl_lattice])
    hkl_int //= np.gcd.reduce(np.abs(hkl_int))

    v1, v2, s = _surface_cell(lattice, hkl_int)
    a, b, stack = v1 @ lattice, v2 @ lattice, s @ lattice
    normal = np.cross(a, b)
    normal /= np.linalg.norm(normal)
    d = float(stack @ normal)
    if layers is None:
        layers = max(1, int(np.ceil(min_slab_size / d - 1e-9)))
    layers += extra_layers

    # atoms in the cell spanned by v1, v2, s (a primitive cell, as det = 1)
    transform = np.array([v1, v2, s])  # rows, in lattice coordinates
    cell_frac = np.mod(np.round(frac @ np.linalg.inv(transform), 10), 1.0)
    cuts, _ = _plane_gaps(cell_frac[:, 2] * d, d)
    cut = cuts[min(cut_index, len(cuts) - 1)] / d
    cell_frac[:, 2] = np.mod(cell_frac[:, 2] - cut, 1.0)

    rotation = np.array([a / np.linalg.norm(a), np.cross(normal, a / np.linalg.norm(a)), normal])
    a2, b2, stack2 = rotation @ a, rotation @ b, rotation @ stack
    inplane = np.array([a2[:2], b2[:2]])  # rows
    positions, index = [], []
    for layer in range(layers):
        f = cell_frac.copy()
        f[:, 2] += layer
        cart = f[:, :1] * a2 + f[:, 1:2] * b2 + f[:, 2:3] * stack2
        positions.append(cart)
        index.extend(source)
    cart = np.concatenate(positions)
    xy = np.linalg.solve(inplane.T, cart[:, :2].T).T
    xy = np.mod(np.round(xy, 10), 1.0)
    cart[:, :2] = xy @ inplane
    thickness = float(np.ptp(cart[:, 2]))
    c_length = layers * d + min_vacuum_size
    cart[:, 2] -= cart[:, 2].min()
    if center_slab:
        cart[:, 2] += (c_length - thickness) / 2
    if len(cart) != layers * len(frac):
        raise RuntimeError("slab atom count is wrong")  # pragma: no cover

    slab_lattice = Lattice([[a2[0], 0.0, 0.0], [b2[0], b2[1], 0.0], [0.0, 0.0, c_length]])
    properties = None
    if bulk.site_properties:
        properties = [dict(bulk.site_properties[i]) for i in index]
    return Crystal(
        [bulk.species[i] for i in index], cart.tolist(), slab_lattice, coords_are_cartesian=True,
        pbc=(True, True, False), site_properties=properties,
        metadata={"miller_index": [int(x) for x in hkl], "layers": layers, "d_spacing": d},
    ), len(cuts)


@tool
def generate_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: Optional[float] = None,
    min_vacuum_size: float = 15.0,
    layers: Optional[int] = None,
    center_slab: bool = True,
    primitive: bool = True,
    symprec: float = 1e-3,
) -> Crystal:
    """
    Cut a surface slab from a bulk crystal.

    The Miller indices refer to the bulk cell as given: use the conventional cell
    for the usual cubic or hexagonal indices. The slab's a and b are the shortest
    lattice vectors in the (hkl) plane, with a along x, b in the xy-plane and the
    surface normal along z. One layer is one interplanar spacing d_hkl and holds one
    primitive cell's worth of atoms. The cut is placed in the widest gap between
    atomic planes (so, for example, Si(111) is cut between the bilayers).

    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices (h, k, l) of the surface plane in the bulk cell
        min_slab_size: Minimum slab thickness in Angstroms (rounded up to whole layers)
        min_vacuum_size: Vacuum thickness in Angstroms (at least)
        layers: Number of layers, instead of min_slab_size
        center_slab: Centre the slab along z (otherwise its lowest atom is at z = 0)
        primitive: Use the bulk's smallest translation lattice (True) or only the
            lattice of the cell given (False)
        symprec: Tolerance in Angstroms for finding the bulk's lattice translations

    Returns:
        Crystal: The slab, periodic in a and b. Its metadata holds the Miller index,
        the number of layers and d_hkl.

    Examples:
        >>> from matsimpy.builders.surface import generate_slab
        >>> from matsimpy.core import Crystal, Lattice
        >>> cu = Crystal(['Cu'] * 4, [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
        ...              Lattice.cubic(3.61))
        >>> slab = generate_slab(cu, (1, 1, 1), layers=4)
        >>> len(slab), round(float(slab.lattice.a), 4), round(slab.metadata['d_spacing'], 4)
        (4, 2.5527, 2.0842)
        >>> thick = generate_slab(cu, (1, 0, 0), min_slab_size=10, min_vacuum_size=12)
        >>> len(thick), thick.metadata['layers']  # d(100) = a/2, so 6 layers of one atom
        (6, 6)
    """
    hkl = _check_inputs(bulk, miller_index, min_slab_size, min_vacuum_size, layers)
    slab, _ = _build(bulk, hkl, min_slab_size, min_vacuum_size, layers, center_slab, primitive, symprec)
    return slab


def _has_flip_symmetry(slab: Crystal, symprec: float) -> bool:
    """Whether some symmetry operation of the slab maps z to -z (top onto bottom)."""
    numbers = {}
    kinds = [numbers.setdefault((s, repr(sorted(p.items())) if p else ""), len(numbers) + 1)
             for s, p in zip(slab.species, slab.site_properties or [{}] * len(slab))]
    symmetry = spglib.get_symmetry((slab.lattice.matrix, slab.frac_positions, kinds), symprec=symprec)
    if symmetry is None:
        return False
    return any(r[2, 2] == -1 for r in symmetry["rotations"])


@tool
def generate_symmetric_slab(
    bulk: Crystal,
    miller_index: Tuple[int, int, int],
    min_slab_size: Optional[float] = None,
    min_vacuum_size: float = 15.0,
    layers: Optional[int] = None,
    primitive: bool = True,
    symprec: float = 1e-3,
) -> Crystal:
    """
    Cut a stoichiometric slab whose top and bottom surfaces are equivalent by symmetry.

    Tries each cut position between atomic planes (widest gap first) and the
    requested thickness plus up to two extra layers, and returns the first slab
    that has a symmetry operation (inversion, mirror or two-fold axis) mapping
    the top surface onto the bottom one.

    Args:
        bulk: Bulk crystal structure
        miller_index: Miller indices (h, k, l) of the surface plane in the bulk cell
        min_slab_size: Minimum slab thickness in Angstroms
        min_vacuum_size: Vacuum thickness in Angstroms (at least)
        layers: Minimum number of layers, instead of min_slab_size
        primitive: Use the bulk's smallest translation lattice
        symprec: Symmetry tolerance in Angstroms

    Returns:
        Crystal: The symmetric slab

    Raises:
        ValueError: If no stoichiometric cut gives a symmetric slab (polar surfaces
            such as rocksalt or zincblende (111)).

    Examples:
        >>> from matsimpy.builders.surface import generate_symmetric_slab
        >>> from matsimpy.core import Crystal, Lattice
        >>> si = Crystal(['Si'] * 2, [[0, 0, 0], [0.25, 0.25, 0.25]],
        ...              Lattice([[0, 2.715, 2.715], [2.715, 0, 2.715], [2.715, 2.715, 0]]))
        >>> slab = generate_symmetric_slab(si, (1, 1, 1), layers=3)
    """
    hkl = _check_inputs(bulk, miller_index, min_slab_size, min_vacuum_size, layers)
    cut_index, count = 0, 1
    while cut_index < count:
        for extra in range(3):
            slab, count = _build(bulk, hkl, min_slab_size, min_vacuum_size, layers, True, primitive, symprec,
                                 cut_index=cut_index, extra_layers=extra)
            if _has_flip_symmetry(slab, symprec):
                return slab
        cut_index += 1
    raise ValueError(f"No termination of the {tuple(int(x) for x in miller_index)} surface gives a symmetric slab")

