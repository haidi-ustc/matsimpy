# VASP test fixtures: provenance

Every file here is an unmodified copy of a file from the pymatgen 2026.10.24 test
data (`pymatgen-2026.10.24/test-files/io/vasp/`). Files marked "decompressed" are
stored uncompressed here and are byte-identical to the decompressed source.

Rule: VASP test data must come from those pymatgen test files. Do not write VASP
inputs or outputs by hand, and do not edit these copies.

| file | source (`test-files/io/vasp/...`) |
|---|---|
| INCAR | inputs/INCAR |
| INCAR.lobster | inputs/INCAR.lobster |
| INCAR_2 | inputs/INCAR_2 |
| INCAR_C2 | inputs/INCAR_C2 |
| KPOINTS | inputs/KPOINTS |
| OSZICAR | outputs/OSZICAR |
| OUTCAR | outputs/OUTCAR.gz (decompressed) |
| POSCAR | inputs/POSCAR |
| POSCAR.AlN | inputs/POSCAR.AlN |
| PROCAR.new_format_5.4.4.gz | outputs/PROCAR.new_format_5.4.4.gz |
| PROCAR.simple | outputs/PROCAR.simple |
| vasprun.hse06.xml.gz | outputs/vasprun.hse06.xml.gz |
| vasprun.xml | outputs/vasprun.xml.gz (decompressed) |

The test files contain no PROCAR together with a structure from the same
calculation. `Procar.get_projection_on_elements` only uses the structure's atom
count and species order, so the tests pair PROCAR.new_format_5.4.4.gz (4 ions)
with POSCAR.AlN (4 atoms). The two come from different runs.
