# Known Issues

## MatterSim ML Calculator Stress Output

- **Label:** `BUG-mattersim-calculator-stress`
- **Status:** Open
- **Description:** The current MatSimPy `Mattersim` calculator produces stress tensors that deviate significantly from the ASE + MatterSim reference implementation. Energies are consistent, but the first principal stress differs by roughly −1.7 eV/Å³ (≈ −278 GPa), indicating a remaining unit-handling issue in the calculator pipeline.
- **Impact:** Post-processing workflows (e.g., elastic property evaluation) that depend on accurately scaled stresses will yield incorrect results.
- **Workaround:** Use the ASE `MatterSimCalculator` directly for any task requiring reliable stress tensors until this bug is resolved.

