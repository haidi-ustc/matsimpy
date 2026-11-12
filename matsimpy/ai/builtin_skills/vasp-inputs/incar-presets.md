# INCAR presets

Starting points only; converge ENCUT and the k-point mesh for production work.

## Common to all
- `PREC = Accurate`, `ENCUT = 520` (or 1.3 x the largest ENMAX of the POTCARs)
- `EDIFF = 1E-6`, `LREAL = Auto` for cells with more than about 20 atoms
- Spin polarized (magnetic elements such as Fe, Co, Ni, Mn): `ISPIN = 2`, `MAGMOM` per atom

## Smearing
- Metals: `ISMEAR = 1`, `SIGMA = 0.2`
- Semiconductors and insulators: `ISMEAR = 0`, `SIGMA = 0.05`
- Unknown: `ISMEAR = 0`, `SIGMA = 0.05` is safe for both

## Relaxation (positions and cell)
`IBRION = 2`, `ISIF = 3`, `NSW = 100`, `EDIFFG = -0.02`

## Relaxation (positions only, e.g. slabs or fixed cell)
`IBRION = 2`, `ISIF = 2`, `NSW = 100`, `EDIFFG = -0.02`

## Static (single point)
`IBRION = -1`, `NSW = 0`, `LCHARG = .TRUE.`

## Density of states (after a static run)
`ICHARG = 11`, `ISMEAR = -5`, `LORBIT = 11`, `NEDOS = 3001`, denser k-point mesh

## Band structure (after a static run)
`ICHARG = 11`, `LORBIT = 11`, line-mode KPOINTS along a high-symmetry path
