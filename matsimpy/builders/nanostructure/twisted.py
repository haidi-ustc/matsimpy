"""
Twisted bilayers and multilayers in commensurate supercells.

Each layer k is rotated by an angle theta_k about the z axis. The builders look for a
supercell S whose vectors are lattice vectors of the bottom layer and, to within
``max_strain``, of every rotated layer (a coincidence-site lattice). The bottom layer
is kept exact; the other layers are strained by at most ``max_strain`` so that they
fit S. The angles that are actually realized, and the strain, are reported in the
structure's metadata.

Hexagonal and square lattices have exactly commensurate angles, indexed by a pair of
integers (n, m): the rotation takes the lattice vector m*a1 + n*a2 to n*a1 + m*a2.
For a hexagonal lattice cos(theta) = (n^2 + 4nm + m^2) / (2 (n^2 + nm + m^2)), so
(1, 2) gives 21.79 degrees and (31, 32) the magic angle 1.05 degrees of graphene.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

import numpy as np

from matsimpy.utils.tooling import tool

from ...core import Crystal, Lattice
from ._sheet import Sheet, reduce_basis, sheet_from_layer, tile

__all__ = [
    "build_twisted_bilayer",
    "build_twisted_multilayer",
    "build_magic_angle_twisted",
    "commensurate_twist_angles",
]

_SIN60 = np.sqrt(3.0) / 2


def _rotation(degrees: float) -> np.ndarray:
    t = np.radians(degrees)
    return np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])


def _lattice_points(lattice: np.ndarray, radius: float) -> np.ndarray:
    """Integer coordinates of the non-zero lattice vectors no longer than ``radius``."""
    bounds = np.ceil(radius * np.linalg.norm(np.linalg.inv(lattice), axis=1)).astype(int)
    i, j = np.meshgrid(np.arange(-bounds[0], bounds[0] + 1), np.arange(-bounds[1], bounds[1] + 1),
                       indexing="ij")
    points = np.column_stack([i.ravel(), j.ravel()])
    lengths = np.linalg.norm(points @ lattice.T, axis=1)
    keep = (lengths <= radius * (1 + 1e-9)) & (lengths > 0)
    return points[keep]


def _search_radius(sheets: Sequence[Sheet], max_atoms: int) -> float:
    """Longest supercell vector worth trying for supercells of at most ``max_atoms`` atoms."""
    atoms_per_area = sum(len(s.species) / s.area for s in sheets)
    max_area = max_atoms / atoms_per_area
    return float(np.sqrt(max_area / _SIN60)) * 1.05


def _coincidence_supercell(sheets: Sequence[Sheet], angles: Sequence[float], max_strain: float,
                           max_atoms: int, angle_tolerance: float):
    """Integer supercell matrices (columns = supercell vectors) of every layer, or None."""
    bottom = sheets[0].lattice
    radius = _search_radius(sheets, max_atoms)
    points = _lattice_points(bottom, radius)
    if len(points) == 0:
        return None
    vectors = points @ bottom.T
    lengths = np.linalg.norm(vectors, axis=1)
    ok = np.ones(len(points), dtype=bool)
    images = []
    for sheet, angle in zip(sheets[1:], angles[1:]):
        rotated = _rotation(angle) @ sheet.lattice
        coords = np.rint(np.linalg.solve(rotated, vectors.T).T).astype(int)
        error = np.linalg.norm(coords @ rotated.T - vectors, axis=1) / lengths
        ok &= error <= max_strain
        images.append(coords)
    candidates = np.flatnonzero(ok)
    if len(candidates) == 0:
        return None
    # shortest coincident vector, then the one spanning the smallest area with it
    order = candidates[np.lexsort((np.arctan2(vectors[candidates, 1], vectors[candidates, 0]),
                                   np.round(lengths[candidates], 8)))]
    first = order[0]
    cross = np.abs(vectors[first, 0] * vectors[candidates, 1] - vectors[first, 1] * vectors[candidates, 0])
    independent = cross > 1e-6 * lengths[first] * lengths[candidates]
    if not independent.any():
        return None
    pool = candidates[independent]
    area = cross[independent]
    rotated = [_rotation(angle) @ sheet.lattice for sheet, angle in zip(sheets[1:], angles[1:])]
    for second in pool[np.lexsort((np.round(lengths[pool], 8), np.round(area, 6)))][:5000]:
        pair = [first, second]
        target = vectors[pair].T
        # the pair must fit every layer as a whole, not only vector by vector
        if all(_fits(target @ np.linalg.inv(lat @ coords[pair].T), max_strain, angle_tolerance)
               for lat, coords in zip(rotated, images)):
            break
    else:
        return None
    matrices = [points[pair].T] + [coords[pair].T for coords in images]
    _, matrices = reduce_basis(vectors[pair].T, matrices)
    count = sum(abs(int(round(np.linalg.det(mat)))) * len(s.species) for mat, s in zip(matrices, sheets))
    if count > max_atoms:
        return None
    return matrices


def _polar(deformation: np.ndarray):
    """(rotation angle in degrees, largest principal strain) of a 2x2 deformation."""
    u, sigma, vt = np.linalg.svd(deformation)
    rotation = u @ vt
    angle = float(np.degrees(np.arctan2(rotation[1, 0], rotation[0, 0])))
    return angle, float(np.max(np.abs(sigma - 1)))


def _fits(deformation: np.ndarray, max_strain: float, angle_tolerance: float) -> bool:
    """Whether a deformation strains by at most max_strain and rotates by at most angle_tolerance degrees."""
    angle, strain = _polar(deformation)
    return strain <= max_strain and abs(angle) <= angle_tolerance


def _check_number(value, name: str, positive: bool = True):
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} must be a number, got {value!r}")
    if not np.isfinite(value) or (positive and value <= 0) or (not positive and value < 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'non-negative'}, got {value}")


def _stack(layers: Sequence[Crystal], angles: Sequence[float], layer_spacing: float, vacuum: float,
           max_strain: float, max_atoms: int, angle_tolerance: float) -> Crystal:
    _check_number(layer_spacing, "layer_spacing")
    _check_number(vacuum, "vacuum", positive=False)
    _check_number(max_strain, "max_strain", positive=False)
    _check_number(angle_tolerance, "angle_tolerance", positive=False)
    if isinstance(max_atoms, bool) or not isinstance(max_atoms, (int, np.integer)) or max_atoms < 1:
        raise ValueError(f"max_atoms must be a positive integer, got {max_atoms}")
    sheets = [sheet_from_layer(layer, f"layer {k}") for k, layer in enumerate(layers)]
    angles = [float(a) for a in angles]
    for angle in angles:
        if not np.isfinite(angle):
            raise ValueError(f"twist angles must be finite, got {angle}")

    matrices = _coincidence_supercell(sheets, angles, max_strain, max_atoms, angle_tolerance)
    if matrices is None:
        hint = ""
        if len(sheets) == 2 and np.allclose(sheets[0].lattice, sheets[1].lattice):
            near = commensurate_twist_angles(layers[0], max_atoms=max_atoms)
            relative = angles[1] - angles[0]
            near = sorted(near, key=lambda item: abs(item["angle"] - abs(relative) % 360))[:5]
            if near:
                listed = ", ".join(f"{item['angle']:.4f} ({item['atoms']} atoms)" for item in near)
                hint = f" Nearby commensurate angles: {listed}."
        raise ValueError(
            f"No supercell with at most {max_atoms} atoms fits twist angles {angles} within "
            f"max_strain={max_strain} and angle_tolerance={angle_tolerance}. Raise max_atoms, "
            "max_strain or angle_tolerance, or use a commensurate angle."
            + hint
        )

    supercell = sheets[0].lattice @ matrices[0]
    realized, strains = [], []
    for sheet, angle, matrix in zip(sheets, angles, matrices):
        natural = sheet.lattice @ matrix  # the layer's own supercell, before rotation
        rotation, strain = _polar(supercell @ np.linalg.inv(natural))
        realized.append(rotation)
        strains.append(strain)

    species, positions, properties = [], [], []
    z = 0.0
    for k, (sheet, matrix) in enumerate(zip(sheets, matrices)):
        index, frac = tile(sheet, matrix)
        heights = sheet.height[index] - sheet.height.min()
        xy = frac @ supercell.T
        positions.append(np.column_stack([xy, z + heights]))
        species.extend(sheet.species[i] for i in index)
        for i in index:
            props = dict(sheet.site_properties[i]) if sheet.site_properties else {}
            props["layer"] = k
            properties.append(props)
        z += float(np.ptp(sheet.height)) + layer_spacing
    positions = np.concatenate(positions)
    thickness = float(np.ptp(positions[:, 2]))
    positions[:, 2] += vacuum / 2
    height = thickness + vacuum
    if height <= 0:
        raise ValueError("vacuum must be positive for a stack of flat layers")
    lattice = Lattice([[supercell[0, 0], supercell[1, 0], 0.0],
                       [supercell[0, 1], supercell[1, 1], 0.0],
                       [0.0, 0.0, height]])
    return Crystal(
        species, positions.tolist(), lattice, coords_are_cartesian=True, pbc=(True, True, False),
        site_properties=properties,
        metadata={
            "twist_angles": [round(a, 10) + 0.0 for a in realized],
            "requested_twist_angles": angles,
            "strain": strains,
            "supercell_matrices": [matrix.tolist() for matrix in matrices],
        },
    )


@tool
def build_twisted_bilayer(
    layer: Crystal,
    twist_angle: float,
    layer_spacing: float = 3.35,
    top_layer: Optional[Crystal] = None,
    vacuum: float = 15.0,
    max_strain: float = 1e-4,
    angle_tolerance: float = 0.01,
    max_atoms: int = 20000,
) -> Crystal:
    """
    Stack two layers with a relative twist in a commensurate (periodic) supercell.

    The top layer is rotated by ``twist_angle`` about the z axis through the cell
    origin. The supercell is spanned by the shortest vector of the bottom lattice
    that is also, to within ``max_strain``, a vector of the rotated top lattice,
    and the partner vector giving the smallest area; the bottom layer is exact
    and the top layer is strained (and rotated by up to ``angle_tolerance``) to fit. Angles that are not commensurate
    need very large supercells, so use ``commensurate_twist_angles`` or
    ``build_magic_angle_twisted`` to pick one, or allow some strain.

    Args:
        layer: The bottom layer: a crystal whose a and b vectors lie in the xy-plane
            (e.g. graphene with c along z, or a slab from generate_slab).
        twist_angle: Rotation of the top layer in degrees (counter-clockwise).
        layer_spacing: Vertical gap in Angstroms between the highest atom of the
            bottom layer and the lowest atom of the top layer.
        top_layer: A different top layer for a heterobilayer (default: same as layer).
            Lattice mismatch must fit within max_strain.
        vacuum: Vacuum along z in Angstroms.
        max_strain: Largest strain allowed in the top layer.
        angle_tolerance: Largest difference in degrees between the requested and
            the realized twist.
        max_atoms: Largest supercell (total atoms) to consider.

    Returns:
        Crystal: The bilayer, periodic in-plane only. Its metadata holds the realized
        ``twist_angles`` (degrees, per layer), ``strain`` per layer and the
        ``supercell_matrices`` (columns = supercell vectors in each layer's basis).
        Every atom has a ``layer`` site property (0 = bottom).

    Examples:
        >>> from matsimpy.builders.nanostructure import build_twisted_bilayer
        >>> from matsimpy.core import Crystal, Lattice
        >>> graphene = Crystal(['C', 'C'], [[0, 0, 0.5], [1/3, 2/3, 0.5]],
        ...                    Lattice.hexagonal(2.46, 15.0))
        >>> tblg = build_twisted_bilayer(graphene, 21.786789)
        >>> len(tblg)
        28
    """
    return _stack([layer, top_layer if top_layer is not None else layer], [0.0, twist_angle],
                  layer_spacing, vacuum, max_strain, max_atoms, angle_tolerance)


@tool
def build_twisted_multilayer(
    layer: Crystal,
    num_layers: int,
    twist_angles: Union[float, List[float]],
    layer_spacing: float = 3.35,
    vacuum: float = 15.0,
    max_strain: float = 1e-4,
    angle_tolerance: float = 0.01,
    max_atoms: int = 20000,
) -> Crystal:
    """
    Stack copies of a layer, each twisted relative to the one below it.

    Args:
        layer: The layer: a crystal whose a and b vectors lie in the xy-plane.
        num_layers: Number of layers (at least 2).
        twist_angles: Twist in degrees of each layer relative to the layer below:
            one number (the same twist each time, so layer k is at k*angle) or a
            list of num_layers - 1 numbers. Use [theta, -theta] for alternating
            twisted trilayer graphene.
        layer_spacing: Vertical gap in Angstroms between neighbouring layers.
        vacuum: Vacuum along z in Angstroms.
        max_strain: Largest strain allowed in any layer above the bottom one.
        angle_tolerance: Largest difference in degrees between a requested and
            a realized twist.
        max_atoms: Largest supercell (total atoms) to consider.

    Returns:
        Crystal: The multilayer in a common supercell; metadata as in
        build_twisted_bilayer, with absolute angles per layer.

    Examples:
        >>> from matsimpy.builders.nanostructure import build_twisted_multilayer
        >>> from matsimpy.core import Crystal, Lattice
        >>> graphene = Crystal(['C', 'C'], [[0, 0, 0.5], [1/3, 2/3, 0.5]],
        ...                    Lattice.hexagonal(2.46, 15.0))
        >>> trilayer = build_twisted_multilayer(graphene, 3, [21.786789, -21.786789])
        >>> len(trilayer)
        42
    """
    if isinstance(num_layers, bool) or not isinstance(num_layers, (int, np.integer)) or num_layers < 2:
        raise ValueError(f"num_layers must be an integer of at least 2, got {num_layers}")
    if np.ndim(twist_angles) == 0:
        relative = [float(twist_angles)] * (num_layers - 1)
    else:
        relative = [float(angle) for angle in twist_angles]
        if len(relative) != num_layers - 1:
            raise ValueError(
                f"Number of twist angles ({len(relative)}) must be num_layers - 1 ({num_layers - 1})"
            )
    absolute = [0.0] + list(np.cumsum(relative))
    return _stack([layer] * num_layers, absolute, layer_spacing, vacuum, max_strain, max_atoms,
                  angle_tolerance)


def _commensurate_angle(lattice: np.ndarray, n: int, m: int) -> float:
    """Angle in degrees of the rotation taking m*a1 + n*a2 to n*a1 + m*a2."""
    u = lattice @ np.array([m, n], dtype=float)
    v = lattice @ np.array([n, m], dtype=float)
    return float(np.degrees(np.arctan2(u[0] * v[1] - u[1] * v[0], u @ v)))


@tool
def build_magic_angle_twisted(
    layer: Crystal,
    n: int,
    m: int,
    layer_spacing: float = 3.35,
    vacuum: float = 15.0,
    max_atoms: int = 50000,
) -> Crystal:
    """
    Twisted bilayer at the exactly commensurate angle indexed by (n, m).

    The top layer is rotated by the angle that takes m*a1 + n*a2 to n*a1 + m*a2, so
    the supercell is exact (no strain). This needs a lattice with |a1| = |a2|:
    hexagonal (graphene, h-BN, TMDs) or square. For graphene, (31, 32) gives
    1.05 degrees, the first magic angle, with 11908 atoms; (1, 2) gives 21.79 degrees.

    Args:
        layer: The layer, with a and b in the xy-plane and |a| = |b|.
        n: First index (positive).
        m: Second index (positive, different from n).
        layer_spacing: Vertical gap in Angstroms between the layers.
        vacuum: Vacuum along z in Angstroms.
        max_atoms: Refuse supercells with more atoms than this.

    Returns:
        Crystal: The twisted bilayer; metadata as in build_twisted_bilayer.

    Examples:
        >>> from matsimpy.builders.nanostructure import build_magic_angle_twisted
        >>> from matsimpy.core import Crystal, Lattice
        >>> graphene = Crystal(['C', 'C'], [[0, 0, 0.5], [1/3, 2/3, 0.5]],
        ...                    Lattice.hexagonal(2.46, 15.0))
        >>> tblg = build_magic_angle_twisted(graphene, 1, 2)
        >>> round(tblg.metadata['twist_angles'][1], 2)
        21.79
    """
    for name, value in (("n", n), ("m", m)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer, got {value!r}")
    if n == m:
        raise ValueError("Equal indices give no twist; choose n != m")
    sheet = sheet_from_layer(layer)
    a1, a2 = np.linalg.norm(sheet.lattice, axis=0)
    if not np.isclose(a1, a2, rtol=1e-6):
        raise ValueError(
            f"Commensurate (n, m) angles need |a| = |b| (hexagonal or square), got {a1:.6g} and {a2:.6g}; "
            "use build_twisted_bilayer with commensurate_twist_angles instead"
        )
    basis = sheet.lattice
    if basis[:, 0] @ basis[:, 1] < -1e-9 * a1 * a2:
        # a 120-degree hexagonal basis: index the angles in the 60-degree one
        basis = np.column_stack([basis[:, 0], basis[:, 0] + basis[:, 1]])
    angle = _commensurate_angle(basis, int(n), int(m))
    return _stack([layer, layer], [0.0, angle], layer_spacing, vacuum, 1e-8, max_atoms, 1e-6)


@tool
def commensurate_twist_angles(
    layer: Crystal,
    max_atoms: int = 2000,
    max_angle: float = 60.0,
) -> List[dict]:
    """
    List the exactly commensurate twist angles of a homobilayer.

    An angle is commensurate when the rotated layer shares a supercell with the
    unrotated one without strain. Use the angles with build_twisted_bilayer.

    Args:
        layer: The layer, with a and b in the xy-plane.
        max_atoms: Largest bilayer supercell (total atoms) to list.
        max_angle: Largest angle in degrees to list.

    Returns:
        A list of {"angle": degrees, "atoms": atoms in the bilayer supercell},
        sorted by angle.

    Examples:
        >>> from matsimpy.builders.nanostructure import commensurate_twist_angles
        >>> from matsimpy.core import Crystal, Lattice
        >>> graphene = Crystal(['C', 'C'], [[0, 0, 0.5], [1/3, 2/3, 0.5]],
        ...                    Lattice.hexagonal(2.46, 15.0))
        >>> [(round(item['angle'], 2), item['atoms']) for item in commensurate_twist_angles(graphene, 100)]
        [(13.17, 76), (21.79, 28), (27.8, 52), (32.2, 52), (38.21, 28), (46.83, 76)]
    """
    _check_number(max_angle, "max_angle")
    if isinstance(max_atoms, bool) or not isinstance(max_atoms, (int, np.integer)) or max_atoms < 1:
        raise ValueError(f"max_atoms must be a positive integer, got {max_atoms}")
    sheet = sheet_from_layer(layer)
    radius = _search_radius([sheet, sheet], max_atoms)
    points = _lattice_points(sheet.lattice, radius)
    vectors = points @ sheet.lattice.T
    lengths = np.linalg.norm(vectors, axis=1)
    shell = np.unique(np.round(lengths**2, 6), return_inverse=True)[1]
    polar = np.degrees(np.arctan2(vectors[:, 1], vectors[:, 0]))
    # a rotation by theta is commensurate when it maps lattice vectors u onto lattice
    # vectors w; collect, for every theta, the vectors w it hits (equal-length pairs)
    order = np.argsort(shell, kind="stable")
    bounds = np.flatnonzero(np.diff(shell[order])) + 1
    hits, thetas = [], []
    for group in np.split(order, bounds):
        if len(group) < 2:
            continue
        theta = np.mod(polar[group][None, :] - polar[group][:, None], 360.0)
        keep = (theta > 1e-6) & (theta <= max_angle + 1e-9)
        hits.append(np.broadcast_to(group[None, :], theta.shape)[keep])
        thetas.append(theta[keep])
    if not hits:
        return []
    hits, thetas = np.concatenate(hits), np.round(np.concatenate(thetas), 6)
    order = np.argsort(thetas, kind="stable")
    hits, thetas = hits[order], thetas[order]
    bounds = np.flatnonzero(np.diff(thetas)) + 1
    result = []
    for group, theta in zip(np.split(hits, bounds), thetas[np.r_[0, bounds]]):
        first = group[np.argmin(lengths[group])]
        cross = np.abs(vectors[first, 0] * vectors[group, 1] - vectors[first, 1] * vectors[group, 0])
        independent = cross > 1e-6 * lengths[first] * lengths[group]
        if not independent.any():
            continue
        cells = int(round(cross[independent].min() / sheet.area))
        count = 2 * cells * len(sheet.species)
        if cells == 1 or count > max_atoms:
            continue  # cells == 1: the rotation is a symmetry of the lattice, not a twist
        result.append({"angle": float(theta), "atoms": count})
    return result

