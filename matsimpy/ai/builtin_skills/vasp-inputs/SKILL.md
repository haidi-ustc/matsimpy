---
name: vasp-inputs
description: Prepare VASP input files (INCAR, KPOINTS, POSCAR) for relaxations, static runs, DOS or band structures of a crystal. Use when the user asks for VASP inputs or a VASP calculation setup.
allowed-tools: write_vasp_input get_symmetry_info
---

# VASP inputs

1. Get the crystal (a structure_ref from an earlier tool, or read_structure).
2. Choose the Materials Project input set for the task (`incar-presets.md`, read it
   with read_skill_resource): `MPRelaxSet` for a relaxation, `MPStaticSet` for a
   single point. The set already holds ENCUT, smearing, spin, MAGMOM and +U.
3. Pass only the tags the user asks for as `incar` overrides; do not repeat the set's.
4. k-points: if the user gives a k-point density, turn it into a mesh with
   `kpoint_mesh`; if they give a mesh, use it; otherwise leave `kpoints` out and the
   set's density is used.
5. Write the files with `write_vasp_input` (structure, directory, input_set, incar,
   kpoints). Use one directory per calculation, e.g. `relax`, `static`. Report the
   INCAR and KPOINTS it returns.
6. Tell the user that no POTCAR was written: POTCAR.spec lists the POTCARs to take
   from their own licensed VASP pseudopotentials.

Do not run VASP.
