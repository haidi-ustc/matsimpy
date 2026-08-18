from pathlib import Path

import pytest

from matsimpy.exceptions import FormatError


def test_load_vasp_resource_reads_json_mapping(tmp_path):
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    resource = tmp_path / "resource.json"
    resource.write_text('{"alpha": 1}', encoding="utf-8")

    assert load_vasp_resource(resource) == {"alpha": 1}


def test_load_vasp_resource_reads_yaml_mapping(tmp_path):
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    resource = tmp_path / "resource.yaml"
    resource.write_text("alpha: 1\n", encoding="utf-8")

    assert load_vasp_resource(resource) == {"alpha": 1}


def test_required_resource_failure_has_context(tmp_path):
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    missing = tmp_path / "missing.yaml"
    with pytest.raises(FormatError, match="missing.yaml") as exc:
        load_vasp_resource(missing)

    assert isinstance(exc.value.__cause__, FileNotFoundError)


def test_malformed_required_resource_has_context_and_cause(tmp_path):
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    malformed = tmp_path / "bad.json"
    malformed.write_text("{", encoding="utf-8")

    with pytest.raises(FormatError, match="bad.json") as exc:
        load_vasp_resource(malformed)

    assert exc.value.__cause__ is not None


def test_optional_resource_allows_only_absence(tmp_path):
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    assert load_vasp_resource(tmp_path / "missing.json", required=False) == {}

    malformed = tmp_path / "bad.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(FormatError) as exc:
        load_vasp_resource(malformed, required=False)

    assert isinstance(exc.value.__cause__, Exception)


def test_vasp_packaged_resources_load_as_mappings():
    from matsimpy.calculator.vasp._resources import load_vasp_resource

    resource_dir = Path(__file__).resolve().parents[2] / "matsimpy" / "calculator" / "vasp"

    for resource_name in (
        "vasp_potcar_pymatgen_hashes.json",
        "vasp_potcar_file_hashes.json",
        "vasp_potcar_stats.json",
        "MITRelaxSet.yaml",
        "MPRelaxSet.yaml",
        "vdW_parameters.yaml",
    ):
        assert isinstance(load_vasp_resource(resource_dir / resource_name), dict)


def test_vasp_inputs_and_sets_do_not_expose_masking_loaders():
    from matsimpy.calculator.vasp import inputs, sets

    assert not hasattr(inputs, "_safe_loadfn")
    assert not hasattr(sets, "_safe_loadfn")
    assert inputs.POTCAR_STATS_PATH.endswith("vasp_potcar_stats.json")
    assert isinstance(inputs.PotcarSingle._potcar_summary_stats, dict)
    assert isinstance(sets.MITRelaxSet.CONFIG, dict)


def test_append_summary_stats_requires_default_packaged_resource(tmp_path, monkeypatch):
    from matsimpy.calculator.vasp import inputs

    calls = []

    def record_load(path, *, required=True):
        calls.append((path, required))
        return {}

    monkeypatch.setattr(inputs, "load_vasp_resource", record_load)
    monkeypatch.setattr(inputs, "dumpfn", lambda *args, **kwargs: None)
    monkeypatch.setattr(inputs.PotcarSingle, "functional_dir", {})

    inputs._gen_potcar_summary_stats(append=True, vasp_psp_dir=str(tmp_path))

    assert calls == [(inputs.POTCAR_STATS_PATH, True)]


def test_append_summary_stats_requires_explicit_packaged_resource(tmp_path, monkeypatch):
    from matsimpy.calculator.vasp import inputs

    calls = []

    def record_load(path, *, required=True):
        calls.append((path, required))
        return {}

    monkeypatch.setattr(inputs, "load_vasp_resource", record_load)
    monkeypatch.setattr(inputs, "dumpfn", lambda *args, **kwargs: None)
    monkeypatch.setattr(inputs.PotcarSingle, "functional_dir", {})

    inputs._gen_potcar_summary_stats(
        append=True,
        vasp_psp_dir=str(tmp_path),
        summary_stats_filename=inputs.POTCAR_STATS_PATH,
    )

    assert calls == [(inputs.POTCAR_STATS_PATH, True)]


def test_append_summary_stats_allows_missing_explicit_target(tmp_path, monkeypatch):
    from matsimpy.calculator.vasp import inputs

    append_target = tmp_path / "generated_stats.json"
    calls = []

    def record_load(path, *, required=True):
        calls.append((path, required))
        return {}

    monkeypatch.setattr(inputs, "load_vasp_resource", record_load)
    monkeypatch.setattr(inputs, "dumpfn", lambda *args, **kwargs: None)
    monkeypatch.setattr(inputs.PotcarSingle, "functional_dir", {})

    inputs._gen_potcar_summary_stats(
        append=True,
        vasp_psp_dir=str(tmp_path),
        summary_stats_filename=str(append_target),
    )

    assert calls == [(str(append_target), False)]
