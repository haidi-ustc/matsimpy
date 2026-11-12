---
name: cubic-supercell
description: Build a near-cubic supercell of a crystal with at least a given number of atoms, e.g. for defect or molecular-dynamics cells. Use when the user asks for a "cubic", "isotropic" or "N-atom" supercell.
---

# Near-cubic supercells

1. Get the crystal (a structure_ref from an earlier tool, or read_structure).
2. Call `cubic_supercell_matrix` with the crystal and the minimum number of atoms.
   It returns a diagonal scaling matrix whose cell lengths are as equal as possible.
3. Build the supercell with `make_supercell` using that matrix.
4. Report the number of atoms and the cell lengths a, b, c.
