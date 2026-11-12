"""Packaged VASP data files are loaded strictly.

In 0.9.0 a missing or broken file was replaced by ``{}``: a misspelled
input-set name gave a set without INCAR defaults, and POTCAR_STATS_PATH pointed
at a file that does not exist, so POTCAR validation silently had no reference data.
"""

import os

import pytest

from matsimpy.calculator.vasp import inputs, sets
from matsimpy.calculator.vasp._resources import load_resource
from matsimpy.exceptions import FormatError

VASP_DIR = os.path.dirname(inputs.__file__)


def test_load_resource_reads_yaml_and_returns_a_fresh_dict(tmp_path):
    path = tmp_path / "x.yaml"
    path.write_text("A: 1\nB: [1, 2]\n")
    first = load_resource(path)
    assert first == {"A": 1, "B": [1, 2]}
    first["A"] = 99
    assert load_resource(path)["A"] == 1


def test_load_resource_missing_file_raises_with_path(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError, match="nope.json"):
        load_resource(missing)


def test_load_resource_unparseable_file_raises_format_error(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("A: [1, 2\n")
    with pytest.raises(FormatError, match="broken.yaml"):
        load_resource(path)


def test_load_resource_non_mapping_raises_format_error(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2]")
    with pytest.raises(FormatError, match="must contain a mapping"):
        load_resource(path)


def test_misspelled_input_set_config_raises():
    with pytest.raises(FileNotFoundError, match="MPRelaxSett.yaml"):
        sets._load_yaml_config("MPRelaxSett")


def test_input_set_config_inherits_parent():
    config = sets._load_yaml_config("MPRelaxSet")
    assert config["INCAR"]  # defaults present, not an empty set
    assert {"KPOINTS", "POTCAR", "POTCAR_FUNCTIONAL"} <= set(config)


def test_potcar_stats_path_points_to_a_packaged_file():
    assert os.path.isfile(inputs.POTCAR_STATS_PATH)
    assert os.path.dirname(inputs.POTCAR_STATS_PATH) == VASP_DIR


@pytest.mark.parametrize(
    "name",
    sorted(f for f in os.listdir(VASP_DIR) if f.endswith((".json", ".yaml"))),
)
def test_every_packaged_resource_loads(name):
    assert isinstance(load_resource(os.path.join(VASP_DIR, name)), dict)


@pytest.mark.filterwarnings("ignore:missing .* POTCAR directory")
def test_append_requires_existing_summary_stats(tmp_path):
    with pytest.raises(FileNotFoundError):
        inputs._gen_potcar_summary_stats(
            append=True,
            vasp_psp_dir=str(tmp_path),
            summary_stats_filename=str(tmp_path / "missing.json"),
        )
