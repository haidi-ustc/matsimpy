"""Wannier90 binary file support."""

from __future__ import annotations

import numpy as np
from scipy.io import FortranFile


class Unk:
    """Cell-periodic wavefunctions for one k-point in Wannier90 UNK format."""

    def __init__(self, ik, data):
        array = np.asarray(data)
        valid = array.ndim == 4 or (array.ndim == 5 and array.shape[1] == 2)
        if not valid:
            raise ValueError("UNK data must have shape (nbands, nx, ny, nz) or (nbands, 2, nx, ny, nz)")
        self.ik = int(ik)
        self.data = np.asarray(array, dtype=np.complex128)

    @property
    def is_noncollinear(self):
        return self.data.ndim == 5

    def write_file(self, filename):
        grid = self.data.shape[-3:]
        nbands = self.data.shape[0]
        with FortranFile(filename, "w") as stream:
            stream.write_record(np.asarray((*grid, self.ik, nbands), dtype=np.int32))
            for band in self.data:
                components = band if self.is_noncollinear else (band,)
                for component in components:
                    stream.write_record(np.asarray(component, dtype=np.complex128).ravel(order="F"))
