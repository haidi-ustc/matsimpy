# Repository Guidelines

## Project Structure & Module Organization

MatSimPy is a Python package under `matsimpy/`. Core domain objects live in `matsimpy/core/`; builders, transformations, analysis, I/O, calculators, storage, symmetry, and AI tooling have matching subpackages. Keep dependency direction intact: core must not import higher-level modules; builders may use transformations; optional integrations should use lazy imports.

Tests mirror the package in `tests/`. Registry-wide behavior belongs in `tests/contracts/`, cross-module workflows in `tests/integration/`, and focused regressions in the relevant domain directory. Examples and their runner are under `examples/`.

## Build, Test, and Development Commands

```bash
pip install -e '.[dev]'          # editable install with pytest tooling
pytest                           # run the current environment's full suite
pytest tests/contracts/ -q       # run registry contract tests
pytest tests/core/test_lattice_comprehensive.py -v
tox run -- -q                    # run Python 3.10, 3.12, and 3.13 matrices
pytest --cov=matsimpy --cov-report=html
```

Install feature extras when needed, for example `.[dev,builders]` or `.[dev,parity]`. The `parity` extra intentionally pins the pymatgen oracle.

## Coding Style & Naming Conventions

Use four-space indentation, type hints for public APIs, and concise docstrings. Follow standard Python naming: `snake_case` functions and modules, `PascalCase` classes, and uppercase constants. Preserve the immutable-return contract: structure mutations and transformations return new objects. Public `Structure.positions` are Cartesian; `Crystal` stores fractional coordinates internally. Avoid broad exception catches and hidden optional-dependency fallbacks.

## Testing Guidelines

Pytest discovers `test_*.py`, `Test*`, and `test_*`. Add a regression test before fixing a bug, then run the focused test and the affected contract suite. Registered builders, transformations, and formats must have valid schemas and executable contract fixtures; do not convert unexpected callable errors into skips. Mark genuinely optional tests with the markers declared in `pyproject.toml`.

## Commit & Pull Request Guidelines

History uses short, imperative subjects, often with a conventional prefix: `fix:`, `test:`, `docs:`, or `refactor:`. Keep commits focused and avoid mixing unrelated workspace changes. Pull requests should explain the problem and solution, list verification commands and results, link relevant issues, and call out API, schema, dependency, or compatibility changes. Include screenshots only for user-visible UI changes.

## Agent-Specific Instructions

Read `CLAUDE.md` for detailed architecture and domain invariants. Preserve existing user changes, inspect the diff before editing, use targeted tests during development, and run `git diff --check` before completion. Always store Superpowers plans and specifications under the repository-root `superpowers/` directory, never under `docs/`. Keep `superpowers/` ignored and do not commit it.
