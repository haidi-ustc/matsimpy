import ast
import importlib.util
from pathlib import Path

import matsimpy.electronic_structure as electronic_structure


PACKAGE_DIR = Path(electronic_structure.__file__).resolve().parent


def test_legacy_pymatgen_decoder_is_removed():
    assert not hasattr(electronic_structure, "decode_legacy_pymatgen_dict")
    assert "decode_legacy_pymatgen_dict" not in electronic_structure.__all__
    assert importlib.util.find_spec("matsimpy.electronic_structure.legacy") is None


def test_production_electronic_structure_does_not_import_pymatgen():
    violations = []
    for path in PACKAGE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(name == "pymatgen" or name.startswith("pymatgen.") for name in names):
                violations.append(f"{path.name}:{node.lineno}")
    assert violations == []


def test_electronic_structure_docs_do_not_advertise_legacy_decoder():
    docs = PACKAGE_DIR.parents[1] / "docs" / "api_reference" / "electronic_structure.rst"
    text = docs.read_text(encoding="utf-8")
    assert "decode_legacy_pymatgen_dict" not in text
    assert "Legacy decoding" not in text
