import numpy as np
import pytest

from matsimpy.io.wannier import Unk


@pytest.mark.parametrize("data", [np.zeros((2, 2, 2)), np.zeros((1, 3, 2, 2, 2))])
def test_unk_rejects_invalid_shapes(data):
    with pytest.raises(ValueError, match="shape"):
        Unk(1, data)
