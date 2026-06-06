# Test Suite Cleanup Review

Date: 2026-06-06

## Scope and evidence

- Current source test inventory: 81 `tests/**/test_*.py` files.
- Current collection size: `python -m pytest --collect-only -q tests` collected 1,449 tests.
- Largest area by count: `tests/core` with 712 collected tests, followed by `tests/io` with 149, `tests/builders` with 138, and `tests/code` with 104.
- This review proposes a cleaned suite layout and old-to-new mapping; it does not remove tests from the repository yet.

## Proposed cleaned suite organization

```text
tests/
  core/
    test_structure_contracts.py        # construction, properties, serialization, immutable return semantics
    test_structure_mutations.py        # add/remove/substitute/sort/wrap shared behavior for Structure/Crystal/Molecule
    test_composition.py                # parser, fractions/mass, serialization, formatting
    test_lattice.py                    # constructors, validation, derived properties, transformations
    test_site.py                       # Site/CrystalSite init, validation, dict roundtrip, property copy isolation
    test_periodic_table.py             # Element lookup and property access
    test_selection.py                  # AtomSelection + functional selection API
  analysis/
    test_graph_functional.py           # graph algorithms and edge cases
    test_graph_oop.py                  # wrapper/factory/caching contract only
  transformation/
    test_geometric.py
    test_atomic.py
    test_lattice.py
    test_composite.py
    test_regressions.py                # focused regressions that would be hard to infer from contract tests
  io/
    test_format_roundtrips.py          # VASP/CIF/XYZ/PDB/MOL/XSF/JSON roundtrips and invalid inputs
    test_converters.py
    test_high_level_io.py
    test_latex.py
  builders/, calculator/, ai/, config/, storage/, symmetry/, ui/
    # keep module-based grouping, but consolidate one-off backward-compatibility/import checks into contract files
```

## Old-to-new cleanup mapping

| Old test(s) / file(s) | Action | Reason | Suggested replacement / consolidation |
|---|---:|---|---|
| `tests/core/test_immutability.py::TestNoFreezeMechanism.test_no_frozen_structure_error`, `test_no_freeze_method` | Remove | These assert absence of removed `freeze`/`unfreeze`/`FrozenStructureError` APIs rather than current behavior. They are useful during a migration but become obsolete once the deleted path is gone. | If a public API regression guard is still desired, keep one import-surface contract in `tests/test_packaging_runtime_contracts.py` instead of two behavior tests. |
| `tests/core/test_crystal_helpers.py::TestCrystalCodeDeduplication.test_add_atom_returns_new_object`, `test_remove_atom_returns_new_object`, `test_substitute_returns_new_object`, `test_sort_atoms_returns_new_object` | Remove / consolidate | These duplicate the immutable-return contract already covered more completely in `tests/core/test_immutability.py` for Crystal and Molecule. | Replace with one parametrized `test_mutation_methods_return_new_object_and_leave_original_unchanged` in `tests/core/test_structure_mutations.py`. |
| `tests/core/test_immutability.py::TestImmutabilityCrystal.*returns_new_object` and `TestImmutabilityMolecule.*returns_new_object` | Simplify | Same contract is repeated per method and class with mostly identical setup/assertions. | Parametrize over `(factory, method_call, expected_delta)` and keep method-specific assertions only where behavior differs (`wrap`, `to_crystal`, `make_supercell`). |
| `tests/core/test_lattice_operations.py::TestLatticeInplace.test_apply_strain_always_returns_new`, `test_scale_lattice_always_returns_new` | Remove | These repeat `TestLatticeStrain.test_apply_strain_always_returns_new` and `TestLatticeScaling.test_scale_lattice_always_returns_new`; checking `id()` adds no new contract beyond `is not`. | Keep the earlier semantic tests that also assert original lattice values are unchanged. |
| `tests/core/test_lattice_operations.py::TestLatticeInplace.test_set_volume_always_returns_new`, `test_apply_deformation_always_returns_new` | Simplify | These are pure identity checks separated from the behavior tests, making the file longer without improving failure diagnostics much. | Fold `assert result is not original` into `test_set_volume` and `test_apply_deformation`. |
| `tests/core/test_species_setter.py::test_species_is_tuple` and `tests/core/test_optimizations.py::TestSpeciesImmutability.test_species_is_tuple` | Remove duplicate | Both assert the same tuple contract. | Keep one species immutability/read-only group in `tests/core/test_structure_contracts.py`, with additional cases for setter rejection, copy order, construction validation, and returned-object species tuple. |
| `tests/core/test_optimizations.py::TestSpeciesImmutability.test_species_immutability_after_add/remove` and `tests/core/test_species_setter.py::test_species_immutable_after_substitute` | Simplify | Same invariant across mutation methods: returned object has tuple species and original remains unchanged. | One parametrized species immutability test over `add_atom`, `remove_atom`, and `substitute`. |
| `tests/analysis/test_graph_enhancements.py` happy-path adjacency/distance/edge/coordination/statistics tests and `tests/analysis/test_graph_oop.py::TestMoleculeGraph` / `TestCrystalGraph` happy-path property tests | Consolidate | Functional and OOP tests verify the same graph outputs on the same simple fixtures. The OOP tests should not re-test every algorithm already covered by the functional tests. | Keep algorithm edge cases in `test_graph_functional.py`; in `test_graph_oop.py`, keep factory type selection, cached property identity, wrapper-to-functional equivalence smoke tests, PBC flag handling, and repr. |
| `tests/analysis/test_graph_oop.py::TestGraphMethods.test_shortest_path_same_atom`, `test_shortest_path_invalid_index` and `tests/analysis/test_graph_enhancements.py::TestShortestPath.test_shortest_path_same_atom`, `test_shortest_path_index_validation` | Remove duplicate OOP cases | The same shortest-path edge cases are covered in the functional API; wrapper tests only need to prove delegation once. | Keep functional edge cases; replace OOP edge cases with one `test_shortest_path_delegates_to_functional_result`. |
| `tests/core/test_substitution_common.py`, `tests/transformation/test_transformation.py::TestSubstitution`, and `tests/core/test_core_structure_comprehensive.py::TestStructureSubstitution` | Consolidate | Single/multiple/all substitution, invalid index, and mismatched lengths are repeated across class-method tests, transformation wrapper tests, and broad structure tests. | Keep class-method contract in `tests/core/test_structure_mutations.py`; keep transformation tests only for wrapper delegation and immutable return; keep dict and selection-specific cases in `tests/core/test_substitution_dict_selection.py`. |
| `tests/core/test_core_structure_comprehensive.py::TestStructureProperties.test_formula_property`, `test_composition_property` and `TestStructureMethods.test_formula_property`, `test_composition_property` | Remove duplicate | Same fixture and same assertions are repeated within one file. | Keep property/caching version once in `tests/core/test_structure_contracts.py`; remove method-section duplicates. |
| `tests/core/test_core_structure_comprehensive.py::test_symbol_set_matches_vasp_format` and `test_symbol_set_affects_vasp_output_after_sort` | Move / simplify | These are IO integration assertions embedded in a core structure file. | Move to `tests/io/test_io_vasp.py` as one parametrized VASP species-order test; keep core-only `symbol_set` ordering tests in core. |
| `tests/core/test_composition_cache_and_errors.py::TestCompositionBackwardCompatibility.*` | Remove duplicate | `basic_composition_still_works`, `complex_formula_still_works`, `mass_calculation_still_works`, and `serialization_still_works` duplicate comprehensive composition tests. | Keep direct tests in `tests/core/test_composition.py`; reserve backward-compatibility labels for compatibility with deprecated public APIs only. |
| `tests/core/test_composition_cache_and_errors.py::TestCompositionCodeDeduplication.*` and `TestCompositionTypeHints.*` | Remove or demote | Tests assert implementation structure/type annotations rather than user-visible behavior; they are fragile cleanup-era tests. | Keep output behavior in HTML/LaTeX tests; rely on static type tooling for annotations if desired. |
| `tests/core/test_composition_cache_and_errors.py::test_invalid_characters_raise_error`, `test_invalid_characters_with_spaces`, `test_invalid_characters_special` | Simplify | Three tests cover the same invalid-character parser branch. | One parametrized invalid-formula test with cases: `H2O@#$`, `H2 O`, `Fe*2`, `Si-O2`, `C+H4`. |
| `tests/core/test_lattice_comprehensive.py` constructor/property tests and `tests/core/test_lattice_convenient_constructors.py` scalar/list constructor tests | Consolidate | Cubic/orthorhombic constructor behavior and traditional 3x3 behavior are split across files and partially repeated. | One `tests/core/test_lattice.py` with parametrized constructors: scalar cubic, `[a,b,c]`, 3x3 matrix, class constructors, and invalid inputs. |
| `tests/io/test_io_latex.py::TestCrystalsToLatexTable.test_table_has_caption`, `test_table_has_label`, `test_table_includes_formulas`, `test_table_includes_lattice_params`, `test_custom_columns`, `test_volume_column` | Simplify | These repeatedly construct the same table and assert one token at a time. | One table-content test per output type using expected token sets, plus one parametrized custom-column test. |
| `tests/io/test_io_latex.py::TestMoleculesToLatexTable.test_basic_table_generation`, `test_table_includes_formulas`, `test_table_with_mass_column` | Simplify | Same output template checks as crystal table tests. | Parametrize over `(renderer, fixtures, expected_tokens, custom_columns)`. |
| `tests/code/test_add_atoms_multiple.py::test_add_atom_rejects_mismatched_batch_lengths` and `test_add_atom_rejects_non_3d_coordinates` | Simplify | They share identical harness and warning suppression; only invalid inputs differ. | One parametrized `test_add_atom_rejects_invalid_batch_inputs` with an `expected_message` column, unless separate failure categories are needed for diagnostics. |
| `tests/code/test_add_atoms_multiple.py::test_formula_updated_after_adding_multiple`, `test_composition_updated_after_adding_multiple` | Simplify | Both assert cache-derived metadata updates after the same operation. | One test that asserts species, formula, and composition on the returned object after a multi-add. |
| `tests/ui/test_ui_imports.py` and `tests/ui/test_ui_interfaces.py::TestInterfaceIntegration.test_interface_imports` | Consolidate | Import-surface checks are scattered and can become noisy. | One `tests/ui/test_import_contracts.py` parametrized over import targets, with behavior tests kept in `test_ui_interfaces.py`. |

## Tests to keep as focused regressions

These are not cleanup targets because they encode specific failures or externally meaningful contracts:

- `tests/test_packaging_runtime_contracts.py` optional-dependency and removed-entrypoint import checks.
- `tests/transformation/test_transformation_regressions.py` site-property preservation, RNG isolation, serialization, and lazy/parallel processor regressions.
- Graph PBC distance tests: `test_crystal_distance_matrix_not_limited_to_20_angstrom`, `test_crystal_distance_matrix_uses_nearest_periodic_image`, and OOP `test_distance_matrix_not_limited_by_neighbor_cutoff`.
- IO parser edge cases such as VASP selective dynamics, CIF multiline/cartesian parsing, MOL fixed-width elements, and XYZ multiframe final-frame handling.
- Storage contract tests without real `maggma`, because they validate optional dependency behavior.

## Coverage gaps to watch after cleanup

| Area | Gap / risk | Suggested coverage |
|---|---|---|
| `matsimpy/analysis/bonding.py`, `analysis/structure.py`, `analysis/topology.py` | These modules appear to be TODO/stub-like and have no direct behavior tests beyond graph analysis. | Add explicit contract tests once implemented, or mark as intentionally unimplemented with import/no-op tests if public. |
| DFT/code backends (`matsimpy/code/pwdft.py`, `quantum_espresso.py`, `vasp.py`, `calculator/dft/base_dft.py`) | Current tests emphasize transformations/core/IO; backend write/parse TODO paths have limited or no executable coverage. | Add lightweight parser/writer contract tests for supported behavior and explicit `NotImplementedError` tests for unsupported TODO paths. |
| UI session/menu surfaces (`matsimpy/ui/cli/session.py`, `menu2interface.py`, materials project interface, maintenance tools) | Import tests cover some UI modules, but interactive routing/session behavior is mostly untested. | Add non-interactive smoke tests around menu-to-interface registration and parameter/session state transitions. |
| Optional dependency boundaries | Existing packaging tests cover several optional deps; cleanup should not delete these as “import only” tests. | Keep one dedicated optional-dependency contract file with subprocess isolation. |
| Cross-format IO invariants | Many format files test roundtrips individually; cleanup may over-consolidate and lose format-specific parser bugs. | Keep one generic roundtrip parametrization plus separate edge-case tests for format-specific syntax. |
| Mutation methods with site properties | Several regression tests cover site properties; if duplicate mutation tests are removed, property preservation must remain explicit. | Keep site-property tests in mutation/regression files, especially add/remove/sort/supercell/substitution cases. |

## Expected cleaned-suite effect

A conservative cleanup should remove or consolidate roughly 80-130 tests without reducing behavioral coverage, primarily by:

1. replacing duplicated immutable-return and species tuple checks with parametrized contract tests;
2. separating functional algorithm tests from OOP wrapper tests in graph coverage;
3. moving IO integration assertions out of core structure tests;
4. deleting migration-era tests for removed freeze APIs and code-dedup/type-hint implementation details;
5. collapsing repeated single-token LaTeX/output checks into table-driven tests.

Recommended stop condition for implementation: after the cleanup, `python -m pytest --collect-only -q tests` should still collect the renamed/parametrized suite cleanly, and a full `python -m pytest tests` run should pass with no lost coverage for the focused regressions listed above.
