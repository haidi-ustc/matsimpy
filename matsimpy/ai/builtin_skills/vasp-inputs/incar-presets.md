# Input sets

`write_vasp_input` starts from a Materials Project input set. Its INCAR holds the
tested defaults (ENCUT 520 eV, PREC Accurate, spin polarization with MAGMOM, +U for
transition-metal oxides and fluorides, LASPH); pass only the changes the user asks for.

| Task | input_set | Notes |
|---|---|---|
| Relax positions and cell | `MPRelaxSet` | ISIF = 3, IBRION = 2, NSW = 99, ionic stop by EDIFF |
| Relax positions only (slabs, fixed cell) | `MPRelaxSet` | override `{"ISIF": 2}` |
| Single point, charge density, DOS | `MPStaticSet` | NSW = 0, tetrahedron smearing (ISMEAR = -5), LORBIT = 11 |
| r2SCAN meta-GGA | `MPScanRelaxSet`, `MPScanStaticSet` | |
| HSE06 hybrid | `MPHSERelaxSet` | expensive |

Common overrides:
- Both sets use tetrahedron smearing (ISMEAR = -5, SIGMA = 0.05). For metals the user
  may want Methfessel-Paxton: `{"ISMEAR": 1, "SIGMA": 0.2}`; for molecules or very few
  k-points, Gaussian: `{"ISMEAR": 0, "SIGMA": 0.05}`.
- A force criterion: `{"EDIFFG": -0.02}`.
- Non-magnetic calculation: `{"ISPIN": 1, "MAGMOM": null}`.
- Converged production values: raise `ENCUT` and use a denser k-point mesh.
