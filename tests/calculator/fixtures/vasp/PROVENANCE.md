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
| POSCAR | inputs/POSCAR (VASP 4 format: no symbol line) |
| POSCAR.AlN | inputs/POSCAR.AlN |
| PROCAR.new_format_5.4.4.gz | outputs/PROCAR.new_format_5.4.4.gz |
| PROCAR.simple | outputs/PROCAR.simple |
| vasprun.hse06.xml.gz | outputs/vasprun.hse06.xml.gz |
| vasprun.xml | outputs/vasprun.xml.gz (decompressed) |
| CONTCAR_Li2O | outputs/CONTCAR_Li2O |
| FePO4.vasp | inputs/FePO4.vasp |
| POSCAR_fcc | inputs/POSCAR_fcc |
| nmr/cs/basic/hydromagnesite/POSCAR | fixtures/nmr/cs/basic/hydromagnesite/POSCAR |
| POSCAR_C2 | inputs/POSCAR_C2 |
| CONTCAR.MD | outputs/CONTCAR.MD (MD run: velocity and predictor-corrector blocks) |
| CONTCAR.MD.npt | outputs/CONTCAR.MD.npt (NPT MD run: lattice-velocity block, then velocities) |
| lobster_env/POSCAR.gz | `test-files/analysis/lobster_env/POSCAR.gz` (gzip-compressed POSCAR) |
| POSCAR_symbols_natoms_multilines | inputs/POSCAR_symbols_natoms_multilines |
| KPOINTS_auto, KPOINTS_gamma, KPOINTS_band, KPOINTS_cartesian, KPOINTS_explicit, KPOINTS_explicit_tet | inputs/ (same names) |
| CHGCAR.nospin.gz, CHGCAR.spin.gz, CHGCAR.NiO_SOC.gz | outputs/ (same names) |
| LOCPOT.gz, ELFCAR.gz | outputs/ (same names) |
| XDATCAR_5 | outputs/XDATCAR_5 |
| vasprun.charged.xml.gz, vasprun.split.charged.xml.gz | outputs/ (same names) |
| POSCAR_Li2O, POSCAR_MnO, POSCAR_bcc, POSCAR_Al12O18 | inputs/ (same names) |
| fake_potcars/POTCAR.gz | inputs/fake_potcars/POTCAR.gz |
| fake_potcars/POT_GGA_PAW_PBE_54/POTCAR.{Fe,Fe_pv,P,O}.gz | inputs/fake_potcars/POT_GGA_PAW_PBE_54/ (same names) |

The test files contain no PROCAR together with a structure from the same
calculation. `Procar.get_projection_on_elements` only uses the structure's atom
count and species order, so the tests pair PROCAR.new_format_5.4.4.gz (4 ions)
with POSCAR.AlN (4 atoms). The two come from different runs.

POTCARs are copyrighted, so real POTCARs and POTCAR-derived reference statistics
are never used. POTCAR tests use only pymatgen's placeholder POTCARs
(`fake_potcars`, TITEL lines marked `; FAKE`).

No test file has selective dynamics. Tests for it set the flags through the
`Poscar` API on a real structure (POSCAR.AlN), write the file with the library
and parse it back; no POSCAR text is written by hand.

The test files contain no POTCARs for the charged runs, and the real POTCARs in
`inputs/POTCAR_*.gz` are not used. The charge test gives each placeholder POTCAR
only the element and valence that the run records in its own `atomtypes` table.
