"""2D sheets: reading a layer's in-plane lattice and tiling it into integer supercells.

Shared by the nanotube and twisted-layer builders.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...core import Crystal

_TOL = 1e-8


@dataclass(frozen=True)
class Sheet:
    """The in-plane description of a layer.

    Attributes:
        lattice: 2x2 array whose columns are the in-plane lattice vectors a1, a2 (Angstrom).
        frac: (N, 2) in-plane fractional coordinates of the atoms in that basis.
        height: (N,) Cartesian z of the atoms (the out-of-plane coordinate).
        species: The N species.
        site_properties: Per-atom property dicts, or None.
    """

    lattice: np.ndarray
    frac: np.ndarray
    height: np.ndarray
    species: tuple
    site_properties: tuple | None

    @property
    def area(self) -> float:
        return abs(float(np.linalg.det(self.lattice)))


def sheet_from_layer(layer: Crystal, name: str = "layer") -> Sheet:
    """Describe ``layer`` as a 2D sheet.

    The layer's a and b vectors must lie in the xy-plane (as in a slab from
    ``generate_slab`` or any 2D cell with c along z). The c vector only holds the
    vacuum and is ignored.
    """
    if not isinstance(layer, Crystal):
        raise TypeError(f"{name} must be a Crystal")
    if len(layer) == 0:
        raise ValueError(f"{name} has no atoms")
    matrix = layer.lattice.matrix
    a, b, c = matrix
    if abs(a[2]) > 1e-6 * np.linalg.norm(a) or abs(b[2]) > 1e-6 * np.linalg.norm(b):
        raise ValueError(
            f"{name}'s a and b vectors must lie in the xy-plane, with c out of it "
            "(build the layer with generate_slab, or rotate it so the sheet normal is z)"
        )
    if c[2] <= 0:
        raise ValueError(f"{name}'s c vector must point along +z")
    lattice = np.column_stack([a[:2], b[:2]])
    if abs(np.linalg.det(lattice)) < 1e-8:
        raise ValueError(f"{name}'s a and b vectors are parallel")
    cart = layer.cart_positions
    frac = np.linalg.solve(lattice, cart[:, :2].T).T
    properties = layer.site_properties or None
    return Sheet(lattice, frac, cart[:, 2].copy(), tuple(layer.species), properties)


def tile(sheet: Sheet, supercell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Atoms of the supercell spanned by ``sheet.lattice @ supercell``.

    Args:
        sheet: The sheet to tile.
        supercell: 2x2 integer matrix; its columns are the supercell vectors in the
            sheet's lattice basis.

    Returns:
        ``(atom_index, frac)``: for every atom of the supercell, the index of the sheet
        atom it copies, and its fractional coordinates in the supercell basis, in [0, 1).
    """
    supercell = np.asarray(supercell)
    determinant = int(round(np.linalg.det(supercell)))
    if determinant == 0:
        raise ValueError("supercell vectors are parallel")
    inverse = np.linalg.inv(supercell)
    corners = np.array([[0, 0], supercell[:, 0], supercell[:, 1], supercell[:, 0] + supercell[:, 1]])
    low, high = corners.min(axis=0) - 1, corners.max(axis=0) + 1
    grid = np.stack(np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1),
                                indexing="ij"), axis=-1).reshape(-1, 2)
    # the lattice points in the half-open supercell are the cell origins
    q = np.round(grid @ inverse.T, 9)
    origins = q[np.all((q >= 0) & (q < 1), axis=1)]
    if len(origins) != abs(determinant):
        raise RuntimeError(f"found {len(origins)} cells in a supercell of {abs(determinant)}")  # pragma: no cover
    atoms = sheet.frac @ inverse.T
    frac = (origins[:, None, :] + atoms[None, :, :]) % 1.0
    frac[np.isclose(frac, 1.0, atol=_TOL)] = 0.0
    index = np.tile(np.arange(len(sheet.species)), len(origins))
    return index, frac.reshape(-1, 2)


def reduce_basis(vectors: np.ndarray, coefficients: list[np.ndarray]) -> tuple[np.ndarray, list[np.ndarray]]:
    """Lagrange-reduce a 2D basis (columns of ``vectors``) and make it right-handed.

    The same unimodular change is applied to each integer matrix in ``coefficients``
    (whose columns give the basis vectors in some lattice), so they stay consistent.
    """
    s = np.array(vectors, dtype=float)
    cs = [np.array(c, dtype=int) for c in coefficients]

    def apply(transform):
        nonlocal s, cs
        s = s @ transform
        cs = [c @ transform for c in cs]

    while True:
        if np.linalg.norm(s[:, 1]) < np.linalg.norm(s[:, 0]) - 1e-12:
            apply(np.array([[0, 1], [1, 0]]))
        mu = int(round(float(s[:, 0] @ s[:, 1]) / float(s[:, 0] @ s[:, 0])))
        if mu == 0:
            break
        apply(np.array([[1, -mu], [0, 1]]))
    if np.linalg.det(s) < 0:
        apply(np.array([[1, 0], [0, -1]]))
    return s, cs
