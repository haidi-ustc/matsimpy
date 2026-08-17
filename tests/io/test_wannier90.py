import numpy as np
import pytest
from scipy.io import FortranFile

from matsimpy.io import Unk


def test_unk_writes_fortran_records(tmp_path):
    data = np.ones((1, 2, 2, 2), dtype=np.complex128)
    path = tmp_path / "UNK00001.1"

    Unk(1, data).write_file(path)

    assert path.stat().st_size > data.nbytes


def test_unk_writes_collinear_records_in_fortran_order(tmp_path):
    data = np.arange(16, dtype=float).reshape(2, 2, 2, 2) + 1j
    path = tmp_path / "UNK00003.1"

    Unk(3, data).write_file(path)

    with FortranFile(path, mode="r") as file:
        np.testing.assert_array_equal(file.read_ints(np.int32), [2, 2, 2, 3, 2])
        np.testing.assert_array_equal(file.read_record(np.complex128), data[0].flatten("F"))
        np.testing.assert_array_equal(file.read_record(np.complex128), data[1].flatten("F"))


def test_unk_writes_noncollinear_spinor_records_in_band_order(tmp_path):
    data = np.arange(32, dtype=float).reshape(2, 2, 2, 2, 2) + 1j
    path = tmp_path / "UNK00004.NC"

    Unk(4, data).write_file(path)

    with FortranFile(path, mode="r") as file:
        np.testing.assert_array_equal(file.read_ints(np.int32), [2, 2, 2, 4, 2])
        np.testing.assert_array_equal(file.read_record(np.complex128), data[0, 0].flatten("F"))
        np.testing.assert_array_equal(file.read_record(np.complex128), data[0, 1].flatten("F"))
        np.testing.assert_array_equal(file.read_record(np.complex128), data[1, 0].flatten("F"))
        np.testing.assert_array_equal(file.read_record(np.complex128), data[1, 1].flatten("F"))


@pytest.mark.parametrize(
    "shape",
    [
        (2, 2, 2),
        (1, 3, 2, 2, 2),
        (1, 2, 2, 2, 2, 2),
    ],
)
def test_unk_rejects_unsupported_ranks_and_noncollinear_spinor_count(shape):
    with pytest.raises(ValueError, match="shape"):
        Unk(1, np.zeros(shape, dtype=np.complex128))
