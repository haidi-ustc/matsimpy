"""Package layering contract (0.9.0): lower layers never import higher layers.

Every import is checked, including imports inside functions (the lazy-import
trick that hid core -> io/symmetry/transformation dependencies in 0.8.x).
Imports inside ``if TYPE_CHECKING:`` blocks are ignored (no runtime effect).
"""

import ast
from pathlib import Path

import matsimpy

ROOT = Path(matsimpy.__file__).resolve().parent

LAYER = {
    "utils": 0, "constants": 0, "exceptions": 0,
    "core": 1,
    "analysis": 2, "symmetry": 2, "io": 2, "electronic_structure": 2, "config": 2,
    "transformation": 3, "builders": 3, "storage": 3,
    "calculator": 4,
    "ai": 5, "plugins": 5, "__init__": 5,
}
# Same-layer imports that are allowed (no cycles between these pairs).
SAME_LAYER_OK = {
    ("io", "electronic_structure"), ("symmetry", "analysis"), ("analysis", "symmetry"),
    ("builders", "transformation"), ("builders", "storage"),
    ("__init__", "plugins"),
}


def _package_of(path: Path) -> str:
    rel = path.relative_to(ROOT).parts
    return rel[0] if len(rel) > 1 else rel[0][:-3]


def _imported_packages(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            skip.update(id(n) for n in ast.walk(node))
    for node in ast.walk(tree):
        if id(node) in skip:
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module and node.module.startswith("matsimpy."):
                    yield node.lineno, node.module.split(".")[1]
            else:
                pkg_parts = list(path.relative_to(ROOT).parts[:-1])
                base = pkg_parts[: len(pkg_parts) - (node.level - 1)] if node.level > 1 else pkg_parts
                target = base + (node.module.split(".") if node.module else [])
                if target:
                    yield node.lineno, target[0]
                elif node.module is None:  # "from .. import x" at top level
                    for alias in node.names:
                        yield node.lineno, alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("matsimpy."):
                    yield node.lineno, alias.name.split(".")[1]


def test_no_upward_imports():
    violations = []
    for path in ROOT.rglob("*.py"):
        src = _package_of(path)
        if src not in LAYER:
            continue
        for lineno, dst in _imported_packages(path):
            if dst not in LAYER or dst == src:
                continue
            if LAYER[dst] > LAYER[src] or (LAYER[dst] == LAYER[src] and (src, dst) not in SAME_LAYER_OK):
                violations.append(f"{path.relative_to(ROOT)}:{lineno} {src}(L{LAYER[src]}) -> {dst}(L{LAYER[dst]})")
    assert not violations, "layering violations:\n" + "\n".join(sorted(violations))


def test_every_subpackage_has_a_layer():
    pkgs = {p.name for p in ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    assert pkgs <= set(LAYER), f"assign a layer to: {sorted(pkgs - set(LAYER))}"
