"""Setyawan--Curtarolo high-symmetry reciprocal-space paths.

The Bravais variants, special-point formulae, and path strings are obtained
from ASE 3.29.0's :mod:`ase.lattice` public API.  ASE's implementation is an
independent transcription of Tables 2--19 of Setyawan and Curtarolo,
Comput. Mater. Sci. 49, 299--312 (2010), and is distributed under the
BSD-2-Clause license.  MatSimPy does not copy pymatgen tables or source;
pymatgen 2025.6.14 is used only as an optional black-box parity oracle.

Fractional coordinates use the reciprocal basis of the Setyawan--Curtarolo
standard primitive cell.  As in pymatgen, each edge is sampled independently,
so shared endpoints appear twice at joins.
"""

import math
import re

import numpy as np
from ase.cell import Cell
from ase.dft.kpoints import parse_path_string

from .spacegroup import SpacegroupAnalyzer


G = "\\Gamma"


def _label(label, variant):
    if label == "G":
        return G
    if variant == "BCT2" and label.startswith("S"):
        label = "\\Sigma" + label[1:]
    return re.sub(r"([A-Za-z\\]+)([123])$", r"\1_\2", label)


def _labels_and_paths(lattice):
    """Return public ASE special points and expanded two-point edges."""
    points = {
        _label(label, lattice.variant): tuple(np.asarray(point, float))
        for label, point in lattice.get_special_points().items()
    }
    return points, [
        [_label(label, lattice.variant) for label in branch]
        for branch in parse_path_string(lattice.special_path)
    ]


def _labels_and_segments(lattice):
    points, paths = _labels_and_paths(lattice)
    return points, [edge for branch in paths for edge in zip(branch[:-1], branch[1:])]


def _representative_paths():
    """Concrete, non-aliased examples used for dependency-free invariants."""
    from ase.lattice import (
        BCC, BCT, CUB, FCC, HEX, MCL, MCLC, ORC, ORCC, ORCF, ORCI, RHL, TET,
    )

    lattices = {
        "cP": CUB(3), "cF": FCC(3), "cI": BCC(3),
        "tP": TET(3, 4), "tI": BCT(3, 4),
        "oP": ORC(2, 3, 4), "oF": ORCF(2, 3, 4),
        "oI": ORCI(2, 3, 4), "oC": ORCC(2, 3, 4),
        "hP": HEX(3, 5), "hR": RHL(3, 70),
        "mP": MCL(2, 3, 4, 70), "mC": MCLC(2, 3, 4, 70),
    }
    paths = {key: _labels_and_segments(value) for key, value in lattices.items()}
    # All four SC triclinic variants have the same points and path; signs are
    # fixed by the reciprocal-angle standardization performed by ASE/SC.
    paths["aP"] = (
        {G: (0, 0, 0), "L": (.5, .5, 0), "M": (0, .5, .5),
         "N": (.5, 0, .5), "R": (.5, .5, .5), "X": (.5, 0, 0),
         "Y": (0, .5, 0), "Z": (0, 0, .5)},
        [("X", G), (G, "Y"), ("L", G), (G, "Z"), ("N", G),
         (G, "M"), ("R", G)],
    )
    return paths


PATHS = _representative_paths()


def _bravais(dataset):
    number = int(dataset.number if hasattr(dataset, "number") else dataset["number"])
    symbol = dataset.international if hasattr(dataset, "international") else dataset["international"]
    centering = str(symbol).strip()[0]
    if number >= 195:
        system = "c"
    elif number >= 168:
        system = "h"
    elif number >= 143:
        return "hR" if centering == "R" else "hP"
    elif number >= 75:
        system = "t"
    elif number >= 16:
        system = "o"
    elif number >= 3:
        system = "m"
    else:
        return "aP"
    return system + (centering if centering in "PFIC" else "P")


class HighSymmKpath:
    """Setyawan--Curtarolo path for a standardized structure."""

    def __init__(self, structure, symprec=0.01, angle_tolerance=5.0):
        self.structure = structure
        self.analyzer = SpacegroupAnalyzer(structure, symprec, angle_tolerance)
        self.bravais = _bravais(self.analyzer._dataset())
        conventional = self.analyzer.get_conventional_standard_structure()
        primitive = self.analyzer.get_primitive_standard_structure()
        # ASE canonicalizes metric ordering and selects all SC subvariants
        # (BCT1/2, ORCF1/2/3, RHL1/2, MCLC1--5, TRI1a--2b).
        self._lattice = self._sc_lattice(conventional, primitive, max(float(symprec), 1e-7))
        points, paths = _labels_and_paths(self._lattice)
        # F_3 is symmetry-equivalent bookkeeping in ASE's MCLC point set and
        # is not part of the SC path dictionary exposed by pymatgen 2025.6.14.
        if self.bravais == "mC":
            points.pop("F_3", None)
        self.kpath = {
            "kpoints": points,
            "path": paths,
            "bravais": self.bravais,
            "variant": self._lattice.variant,
        }
        if self.bravais == "aP":
            self._reciprocal = 2 * np.pi * np.linalg.inv(primitive.lattice.matrix).T
        else:
            self._reciprocal = 2 * np.pi * np.asarray(self._lattice.tocell().reciprocal())

    def _sc_lattice(self, conventional, primitive, eps):
        from ase.lattice import BCC, BCT, CUB, FCC, HEX, MCL, MCLC, ORC, ORCC, ORCF, ORCI, RHL, TET

        abc = np.asarray(
            [conventional.lattice.a, conventional.lattice.b, conventional.lattice.c], float
        )
        key = self.bravais
        if key == "cP": return CUB(float(np.mean(abc)))
        if key == "cF": return FCC(float(np.mean(abc)))
        if key == "cI": return BCC(float(np.mean(abc)))
        if key == "tP": return TET(float(np.mean(abc[:2])), float(abc[2]))
        if key == "tI": return BCT(float(np.mean(abc[:2])), float(abc[2]))
        if key in {"oP", "oF", "oI"}:
            a, b, c = sorted(abc)
            return {"oP": ORC, "oF": ORCF, "oI": ORCI}[key](a, b, c)
        if key == "oC":
            a, b = sorted(abc[:2])
            return ORCC(a, b, float(abc[2]))
        if key == "hP": return HEX(float(np.mean(abc[:2])), float(abc[2]))
        if key == "hR":
            p = primitive.lattice
            return RHL(
                float(np.mean([p.a, p.b, p.c])),
                float(np.mean([p.alpha, p.beta, p.gamma])),
            )
        if key in {"mP", "mC"}:
            # spglib uses the conventional unique-b (beta obtuse) setting;
            # SC/ASE uses the equivalent unique-a setting with alpha acute.
            beta = float(conventional.lattice.beta)
            a, b, c = float(abc[1]), float(abc[0]), float(abc[2])
            alpha = min(beta, 180.0 - beta)
            if b > c:
                b, c = c, b
            return (MCL if key == "mP" else MCLC)(a, b, c, alpha)
        return Cell(primitive.lattice.matrix).get_bravais_lattice(eps=eps)

    def get_kpoints(self, line_density=20, coords_are_cartesian=False):
        if line_density <= 0:
            raise ValueError("line_density must be positive")
        coordinates, labels = [], []
        for branch in self.kpath["path"]:
            for start_label, end_label in zip(branch[:-1], branch[1:]):
                start = np.asarray(self.kpath["kpoints"][start_label], float)
                end = np.asarray(self.kpath["kpoints"][end_label], float)
                start_cart = start @ self._reciprocal
                end_cart = end @ self._reciprocal
                intervals = int(math.ceil(np.linalg.norm(end_cart - start_cart) * line_density))
                if intervals == 0:
                    continue
                segment = np.linspace(start, end, intervals + 1)
                coordinates.extend(segment.tolist())
                labels.extend([start_label] + [""] * (intervals - 1) + [end_label])
        result = np.asarray(coordinates)
        if coords_are_cartesian:
            result = result @ self._reciprocal
        return result, labels
