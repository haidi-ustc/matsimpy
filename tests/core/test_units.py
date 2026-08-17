from matsimpy.core.units import unitized


def test_unitized_preserves_value_and_exposes_unit():
    @unitized("eV")
    def energy():
        return -1.25

    assert energy() == -1.25
    assert energy.unit == "eV"
