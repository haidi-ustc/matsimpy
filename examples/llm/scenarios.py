"""Declarative live-LLM example corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


Validator = Callable[[dict], list[str]]


def _valid(evidence: dict) -> list[str]:
    return []


def _saved(extension: str, atoms: int | None = None) -> Validator:
    def validate(evidence: dict) -> list[str]:
        errors = []
        artifacts = evidence.get("artifacts", [])
        matching = [item for item in artifacts if item["path"].endswith(extension)]
        if not matching:
            errors.append(f"missing {extension} artifact")
        if atoms is not None and matching and matching[0].get("num_atoms") != atoms:
            errors.append(f"expected {atoms} atoms, got {matching[0].get('num_atoms')}")
        return errors
    return validate


def _result_field(tool: str, field: str, expected=None) -> Validator:
    def validate(evidence: dict) -> list[str]:
        calls = [call for call in evidence["tool_calls"] if call["name"] == tool]
        if not calls:
            return [f"missing {tool} result"]
        value = calls[-1]["result"].get(field)
        if expected is not None and value != expected:
            return [f"{tool}.{field}: expected {expected!r}, got {value!r}"]
        return []
    return validate


def _one_of_tools(*names: str) -> Validator:
    def validate(evidence: dict) -> list[str]:
        used = {call["name"] for call in evidence["tool_calls"]}
        return [] if used.intersection(names) else [f"expected one of tools: {list(names)}"]
    return validate


def _all(*validators: Validator) -> Validator:
    def validate(evidence: dict) -> list[str]:
        return [error for validator in validators for error in validator(evidence)]
    return validate


@dataclass(frozen=True)
class Scenario:
    id: str
    slug: str
    name: str
    tier: str
    prompts: tuple[str, ...]
    required_tools: frozenset[str]
    validate: Validator = _valid
    scientific_context: str = ""


SCENARIOS = [
    Scenario("01", "water_xyz", "Water molecule to XYZ", "pipeline", (
        "Create a water molecule with Cartesian positions O=(0,0,0), H=(0.96,0,0), H=(-0.24,0.93,0), then save water.xyz",
    ), frozenset({"create_molecule", "write_structure"}), _saved(".xyz", 3)),
    Scenario("02", "explicit_crystal", "Explicit fractional crystal", "single", (
        "Create a periodic cubic crystal with species Li and F at fractional coordinates [0,0,0] and [0.5,0.5,0.5], a=4.02 A. Do not infer or name a prototype; report only the supplied geometry.",
    ), frozenset({"create_crystal"}), _valid,
        "The low-level constructor establishes only the supplied simple-cubic lattice and coordinates. "
        "It does not establish a named prototype; these positions must not be called rocksalt."),
    Scenario("03", "fcc_copper", "FCC copper to CIF", "pipeline", (
        "Build fcc copper with lattice constant 3.61 A and save fcc_cu.cif",
    ), frozenset({"from_prototype", "write_structure"}), _saved(".cif", 1),
        "The builder uses 3.61 A as the conventional FCC prototype parameter and returns a one-atom "
        "primitive rhombohedral cell with vector length 3.61/sqrt(2)."),
    Scenario("04", "racksalt_nacl", "Misspelled rocksalt NaCl", "pipeline", (
        "Build racksalt sodium chloride with lattice constant 5.64 A and save nacl.cif",
    ), frozenset({"from_prototype", "write_structure"}), _saved(".cif", 2),
        "The builder uses 5.64 A as the conventional rocksalt prototype parameter and returns a two-atom "
        "primitive rhombohedral cell with vector length 5.64/sqrt(2) and 60 degree angles."),
    Scenario("05", "wurtzite_gan", "Wurtzite GaN", "pipeline", (
        "Build wurtzite GaN with lattice constants a=3.19 A and c=5.19 A, then save gan.cif",
    ), frozenset({"from_prototype", "write_structure"}), _saved(".cif", 2)),
    Scenario("06", "random_sio2", "Random SiO2 with PyXtal", "pipeline", (
        "Generate a random SiO2 crystal in space group 1 with 1 Si and 2 O atoms, then save random_sio2.cif",
    ), frozenset({"random_crystal", "write_structure"}), _saved(".cif", 3)),
    Scenario("07", "translate_copper", "Build and translate copper", "pipeline", (
        "Build fcc Cu with a=3.61 A, translate it by [0.1,0,0] A, and save translated.cif",
    ), frozenset({"from_prototype", "translate", "write_structure"}), _saved(".cif", 1)),
    Scenario("08", "strain_silicon", "Build and strain silicon", "pipeline", (
        "Build diamond silicon with a=5.43 A, apply 1 percent isotropic strain, and save strained_si.cif",
    ), frozenset({"from_prototype", "write_structure"}), _all(
        _one_of_tools("apply_strain", "scale_lattice", "apply_deformation"),
        _saved(".cif", 2),
    )),
    Scenario("09", "supercell_vacancy", "Supercell vacancy pipeline", "pipeline", (
        "Build fcc Cu with a=3.61 A, make a 2x2x2 supercell, create one vacancy at site 0, and save cu_vacancy.cif",
    ), frozenset({"from_prototype", "make_supercell", "create_vacancy", "write_structure"}), _saved(".cif", 7)),
    Scenario("10", "water_bonds", "Read and analyze water bonds", "single", (
        "Create water with O at [0,0,0] and H at [0.96,0,0] and [-0.24,0.93,0], save water.xyz, then analyze its bonds with cutoff 1.2 A",
    ), frozenset({"create_molecule", "write_structure", "analyze_bonds"}), _result_field("analyze_bonds", "num_bonds", 2)),
    Scenario("11", "argon_lj", "Argon dimer Lennard-Jones", "pipeline", (
        "Create an argon dimer at Cartesian coordinates [0,0,0] and [4,0,0], then calculate Lennard-Jones energy and forces",
    ), frozenset({"create_molecule", "calculate_lennard_jones"}), _result_field("calculate_lennard_jones", "energy")),
    Scenario("12", "silicon_symmetry", "Silicon symmetry", "pipeline", (
        "Build diamond silicon with a=5.43 A and analyze its symmetry",
    ), frozenset({"from_prototype", "analyze_symmetry"})),
    Scenario("13", "store_retrieve", "Save, store, and retrieve", "pipeline", (
        "Build fcc aluminum with a=4.05 A, save aluminum.cif, store it with metadata project=demo, then retrieve it",
    ), frozenset({"from_prototype", "write_structure", "store_structure", "retrieve_structure"})),
    Scenario("14", "multiturn_nacl", "Multi-turn NaCl workflow", "multiturn", (
        "Build rocksalt NaCl with lattice constant 5.64 A",
        "Now make a 2x1x1 supercell and save it as nacl_supercell.cif",
    ), frozenset({"from_prototype", "make_supercell", "write_structure"}), _saved(".cif", 4)),
    Scenario("15", "error_recovery", "Invalid prototype recovery", "recovery", (
        "Try to build prototype unobtainium for Cu; if MatSimPy rejects it, recover by building fcc Cu with a=3.61 A and save recovered.cif",
    ), frozenset({"from_prototype", "write_structure"}), _saved(".cif", 1)),
]


def get_scenario(identifier: str) -> Scenario:
    for scenario in SCENARIOS:
        if identifier in {scenario.id, scenario.slug, f"{scenario.id}_{scenario.slug}"}:
            return scenario
    raise KeyError(identifier)


__all__ = ["Scenario", "SCENARIOS", "get_scenario"]
