"""Native Wannier90 file containers."""

from __future__ import annotations

from numbers import Integral
from os import PathLike
from typing import Any

import numpy as np
from scipy.io import FortranFile


class Unk:
    """Container for Wannier90 UNK wavefunction grid data."""

    def __init__(self, ik: int, data: Any) -> None:
        if isinstance(ik, bool) or not isinstance(ik, Integral) or ik <= 0:
            raise ValueError("UNK kpoint index must be a positive integer")
        self.ik = int(ik)
        self.data = data

    @property
    def data(self) -> np.ndarray:
        return self._data

    @data.setter
    def data(self, value: Any) -> None:
        raw = np.asarray(value)
        if not np.iscomplexobj(raw):
            raise TypeError("UNK data must be complex before casting")

        data = np.array(value, dtype=np.complex128)
        if data.ndim not in (4, 5):
            raise ValueError(
                "invalid data shape, must be (nbands, ngx, ngy, ngz) "
                "or (nbands, 2, ngx, ngy, ngz)"
            )
        if data.ndim == 5 and data.shape[1] != 2:
            raise ValueError("invalid noncollinear data shape, expected spinor count 2")
        if any(dim <= 0 for dim in data.shape):
            raise ValueError("UNK data band and grid extents must be positive")

        self._data = data
        self.is_noncollinear = data.ndim == 5
        self.nbnd = data.shape[0]
        self.ng = tuple(int(dim) for dim in data.shape[-3:])

    def write_file(self, filename: str | PathLike[str]) -> None:
        with FortranFile(filename, mode="w") as file:
            file.write_record(np.array([*self.ng, self.ik, self.nbnd], dtype=np.int32))
            for ib in range(self.nbnd):
                if self.is_noncollinear:
                    file.write_record(self.data[ib, 0].flatten("F"))
                    file.write_record(self.data[ib, 1].flatten("F"))
                else:
                    file.write_record(self.data[ib].flatten("F"))
