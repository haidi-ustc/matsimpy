# 15_error_recovery — run 3

## Requests

- Try to build prototype unobtainium for Cu; if MatSimPy rejects it, recover by building fcc Cu with a=3.61 A and save recovered.cif

## Tool trace

- `from_prototype` — failure — args: `{"lattice_constant": 3.61, "prototype": "unobtainium", "species": "Cu"}`
- `from_prototype` — success — args: `{"lattice_constant": 3.61, "prototype": "fcc", "species": "Cu"}`
- `write_structure` — success — args: `{"path": "recovered.cif", "structure": {"structure_ref": "structure:1"}}`

## Artifacts

- `recovered.cif` (424 bytes, formula=Cu, atoms=1)
- `state.db-shm` (32768 bytes, formula=n/a, atoms=n/a)
- `state.db-wal` (193672 bytes, formula=n/a, atoms=n/a)

## Final assistant output

Done. Here's what happened:

| Step | Action | Result |
|------|--------|--------|
| 1 | `from_prototype("unobtainium", "Cu", 3.61)` | ❌ Rejected — unknown prototype |
| 2 | `from_prototype("fcc", "Cu", 3.61)` | ✅ FCC Cu primitive cell created |
| 3 | `write_structure` → `recovered.cif` | ✅ Saved |

The recovered structure is the **primitive FCC cell** of copper: 1 atom, lattice vectors of 2.553 Å with angles α = β = γ = 60° (the conventional 3.61 Å cubic parameter corresponds to the primitive rhombohedral representation, where a_primitive = a_conv / √2 ≈ 2.553 Å). The CIF file is written to `recovered.cif`.

## Deterministic validation

- Pass: True
- Errors: []

## LLM judge

- Pass: True
- Score: 100
- Analysis: The workflow correctly attempted to create 'unobtainium' prototype, received a deterministic error (unknown prototype), then fell back to building fcc Cu with a conventional lattice constant of 3.61 Å. The from_prototype tool produced a valid primitive fcc cell (a=2.553 Å, α=β=γ=60°), which corresponds to a_conv/√2. The structure was saved as recovered.cif. No unsupported claims or deterministic errors are present; the recovery adheres exactly to the request.
