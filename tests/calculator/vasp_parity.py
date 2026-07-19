import numpy as np


def neutral_structure(structure):
    return {
        "lattice": np.asarray(structure.lattice.matrix, dtype=float),
        "species": [str(site.specie) for site in structure],
        "frac_coords": np.asarray(structure.frac_coords, dtype=float),
    }


def neutral_array_map(values):
    return {int(key): np.asarray(value) for key, value in values.items()}
