---
name: vasp-inputs
description: Prepare VASP input files (INCAR, KPOINTS, POSCAR) for relaxations, static runs, DOS or band structures of a crystal. Use when the user asks for VASP inputs or a VASP calculation setup.
allowed-tools: write_vasp_input get_symmetry_info
---

# VASP inputs

1. Get the crystal (a structure_ref from an earlier tool, or read_structure).
2. Choose the task and its INCAR tags from `incar-presets.md` (read it with
   read_skill_resource). Use the user's values where given; say which tags you chose.
3. Choose the k-point mesh with `kpoint_mesh`. Use a k-point density of 1000
   per reciprocal atom for relaxations and 3000 or more for DOS, unless the user
   gives a mesh.
4. Write the files with `write_vasp_input` (structure, directory, incar, kpoints).
   Use one directory per calculation, e.g. `relax`, `static`.
5. Tell the user that no POTCAR was written: they must add POTCARs from their
   own licensed VASP pseudopotentials, in the element order of the POSCAR.

Do not run VASP.
