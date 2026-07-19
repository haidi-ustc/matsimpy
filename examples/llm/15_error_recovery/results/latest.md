# 15_error_recovery — run 3

## Requests

- Try to build prototype unobtainium for Cu; if MatSimPy rejects it, recover by building fcc Cu with a=3.61 A and save recovered.cif

## Tool trace

- `from_prototype` — failure — args: `{"lattice_constant": 3.61, "prototype": "unobtainium", "species": "Cu"}`
- `from_prototype` — success — args: `{"lattice_constant": 3.61, "prototype": "fcc", "species": "Cu"}`
- `write_structure` — success — args: `{"path": "recovered.cif", "structure": {"formula": "Cu", "num_atoms": 1, "structure_ref": "structure:1"}}`

## Artifacts

- `recovered.cif` (424 bytes, formula=Cu, atoms=1)
- `state.db-shm` (32768 bytes, formula=n/a, atoms=n/a)
- `state.db-wal` (127752 bytes, formula=n/a, atoms=n/a)

## Final assistant output

Here's a summary of what happened:

1. **`unobtainium` prototype rejected** — MatSimPy raised `ValueError: Unknown prototype 'unobtainium'`. The available prototypes are: `fcc`, `bcc`, `diamond`, `zincblende`, `rocksalt`, `wurtzite`, `perovskite`, `hcp`, and `sc`.

2. **Recovery successful** — Built fcc Cu with `a = 3.61 Å` and saved it as **`recovered.cif`** (1 atom in the primitive cell, space group Fm$\bar{3}$m).

## Deterministic validation

- Pass: True
- Errors: []

## LLM judge

- Pass: True
- Score: 85
- Analysis: The workflow correctly attempted to build 'unobtainium' prototype, failed as expected, recovered by building fcc Cu with lattice_constant=3.61 (interpreted as conventional cell, primitive cell lengths ~2.55 Å and angles 60° consistent with fcc), and saved the structure as 'recovered.cif'. No deterministic errors occurred. However, the final output states 'space group Fm\bar{3}m' which is not evidenced by the supplied tool results (neither from_prototype nor write_structure provided space group information).
