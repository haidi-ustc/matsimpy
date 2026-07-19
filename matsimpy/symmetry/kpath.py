"""Deterministic high-symmetry reciprocal-space paths.

The special-point coordinates follow the conventional crystallographic labels
used by Setyawan and Curtarolo, Comput. Mater. Sci. 49, 299 (2010), for the
metric-independent cases.  Metric-dependent variants use conservative paths
through their universally defined special points rather than copied code tables.
"""

import math

import numpy as np

from .spacegroup import SpacegroupAnalyzer


G = "\\Gamma"

# Coordinates are fractional in the reciprocal basis.  Separate segments avoid
# drawing lines between disconnected branches of a published path.
PATHS = {
    "cP": ({G:(0,0,0), "X":(0,.5,0), "M":(.5,.5,0), "R":(.5,.5,.5)},
           [(G,"X"),("X","M"),("M",G),(G,"R"),("R","X"),("M","R")]),
    "cF": ({G:(0,0,0), "X":(0,.5,.5), "W":(.25,.75,.5), "K":(.375,.75,.375), "L":(.5,.5,.5), "U":(.625,.625,.25)},
           [(G,"X"),("X","W"),("W","K"),("K",G),(G,"L"),("L","U"),("U","W"),("W","L"),("L","K"),("U","X")]),
    "cI": ({G:(0,0,0), "H":(.5,-.5,.5), "N":(0,0,.5), "P":(.25,.25,.25)},
           [(G,"H"),("H","N"),("N",G),(G,"P"),("P","H"),("P","N")]),
    "tP": ({G:(0,0,0), "X":(0,.5,0), "M":(.5,.5,0), "Z":(0,0,.5), "R":(0,.5,.5), "A":(.5,.5,.5)},
           [(G,"X"),("X","M"),("M",G),(G,"Z"),("Z","R"),("R","A"),("A","Z"),("X","R"),("M","A")]),
    "oP": ({G:(0,0,0), "X":(.5,0,0), "Y":(0,.5,0), "Z":(0,0,.5), "S":(.5,.5,0), "R":(.5,.5,.5), "T":(0,.5,.5), "U":(.5,0,.5)},
           [(G,"X"),("X","S"),("S","Y"),("Y",G),(G,"Z"),("Z","U"),("U","R"),("R","T"),("T","Z"),("Y","T"),("U","X"),("S","R")]),
    "hP": ({G:(0,0,0), "M":(.5,0,0), "K":(1/3,1/3,0), "A":(0,0,.5), "L":(.5,0,.5), "H":(1/3,1/3,.5)},
           [(G,"M"),("M","K"),("K",G),(G,"A"),("A","L"),("L","H"),("H","A"),("L","M"),("K","H")]),
    "hR": ({G:(0,0,0), "L":(.5,0,0), "B":(.5,-.5,.5), "Z":(.5,.5,.5), "F":(.5,.5,0)},
           [(G,"L"),("L","B"),("B",G),(G,"Z"),("Z","F"),("F",G)]),
    "mP": ({G:(0,0,0), "A":(.5,.5,0), "C":(0,.5,.5), "D":(.5,0,.5), "E":(.5,.5,.5), "Y":(0,.5,0), "Z":(0,0,.5)},
           [(G,"Y"),("Y","A"),("A",G),(G,"Z"),("Z","D"),("D","E"),("E","C"),("C","Y")]),
    "aP": ({G:(0,0,0), "X":(.5,0,0), "Y":(0,.5,0), "Z":(0,0,.5), "L":(.5,.5,0), "M":(.5,0,.5), "N":(0,.5,.5), "R":(.5,.5,.5)},
           [(G,"X"),("Y",G),(G,"Z"),("R",G),(G,"N"),("M","X"),("Y","L"),("Z","M")]),
}

# Centered orthorhombic/monoclinic and body-centered tetragonal paths retain
# deterministic conventional-cell corner/face paths when metric parameters vary.
PATHS["tI"] = PATHS["tP"]
for _key in ("oF", "oI", "oC"):
    PATHS[_key] = PATHS["oP"]
PATHS["mC"] = PATHS["mP"]


def _bravais(dataset):
    number = int(dataset.number if hasattr(dataset, "number") else dataset["number"])
    symbol = dataset.international if hasattr(dataset, "international") else dataset["international"]
    centering = str(symbol).strip()[0]
    if number >= 195: system = "c"
    elif number >= 168: system = "h"
    elif number >= 143: return "hR" if centering == "R" else "hP"
    elif number >= 75: system = "t"
    elif number >= 16: system = "o"
    elif number >= 3: system = "m"
    else: return "aP"
    return system + (centering if centering in "PFIC" else "P")


class HighSymmKpath:
    def __init__(self, structure, symprec=0.01, angle_tolerance=5.0):
        self.structure = structure
        self.analyzer = SpacegroupAnalyzer(structure, symprec, angle_tolerance)

    def get_kpoints(self, line_density=20, coords_are_cartesian=False):
        if line_density <= 0:
            raise ValueError("line_density must be positive")
        conventional = self.analyzer.get_conventional_standard_structure()
        key = _bravais(self.analyzer._dataset())
        points, segments = PATHS[key]
        reciprocal = 2 * np.pi * np.linalg.inv(conventional.lattice.matrix).T
        coordinates, labels = [], []
        for start_label, end_label in segments:
            start = np.asarray(points[start_label], float)
            end = np.asarray(points[end_label], float)
            distance = np.linalg.norm((end - start) @ reciprocal)
            count = max(2, int(math.ceil(line_density * distance)))
            segment = np.linspace(start, end, count)
            segment_labels = [start_label] + [""] * (count - 2) + [end_label]
            if coords_are_cartesian:
                segment = segment @ reciprocal
            coordinates.extend(segment.tolist())
            labels.extend(segment_labels)
        return np.asarray(coordinates), labels
