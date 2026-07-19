import numpy as np
import pytest
from scipy.io import FortranFile

from matsimpy.io.wannier import Unk


def test_unk_writes_collinear_fortran_records(tmp_path):
    data = np.arange(16).reshape(2, 2, 2, 2).astype(np.complex128) * (1 + 1j)
    path = tmp_path / "UNK00001.1"
    Unk(3, data).write_file(path)
    with FortranFile(path, "r") as stream:
        np.testing.assert_array_equal(stream.read_ints(np.int32), [2, 2, 2, 3, 2])
        for band in data:
            np.testing.assert_array_equal(stream.read_record(np.complex128), band.ravel(order="F"))


def test_unk_writes_noncollinear_spinors_as_separate_records(tmp_path):
    data = np.arange(16).reshape(1, 2, 2, 2, 2).astype(np.complex128)
    path = tmp_path / "UNK00001.NC"
    Unk(1, data).write_file(path)
    with FortranFile(path, "r") as stream:
        np.testing.assert_array_equal(stream.read_ints(np.int32), [2, 2, 2, 1, 1])
        for spinor in data[0]:
            np.testing.assert_array_equal(stream.read_record(np.complex128), spinor.ravel(order="F"))


@pytest.mark.parametrize("data", [np.zeros((2, 2, 2)), np.zeros((1, 3, 2, 2, 2))])
def test_unk_rejects_invalid_shapes(data):
    with pytest.raises(ValueError, match="shape"):
        Unk(1, data)
