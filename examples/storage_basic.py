"""
MatSimPy Storage Module - Basic Examples

Demonstrates usage of persistent data storage for structures and results.
"""

from matsimpy.storage import DataStorage, MemoryBackend
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator import LennardJones
import tempfile
import shutil
from pathlib import Path

print("=" * 70)
print("MatSimPy Storage Module - Basic Examples")
print("=" * 70)

temp_dir = tempfile.mkdtemp()
storage = None
storage_mem = None

try:
    # ======================================================================
    # 1. Initialize Storage
    # ======================================================================
    print("\n1. Initialize Storage")
    print("-" * 70)

    # Memory store (for testing)
    storage_mem = DataStorage(backend=MemoryBackend())
    print(f"Memory backend: {type(storage_mem.backend).__name__}")

    # To use persistent JSON storage, use MaggmaBackend:
    # from matsimpy.storage import MaggmaBackend
    # storage = DataStorage(backend=MaggmaBackend(store_path="data.json"))

    # ======================================================================
    # 2. Store Crystal Structure
    # ======================================================================
    print("\n2. Store Crystal Structure")
    print("-" * 70)

    from matsimpy.builders.bulk import from_prototype
    crystal = from_prototype('diamond', 'Si', 5.43)
    doc_id = storage_mem.store_data(
        crystal,
        metadata={
            'description': 'Si primitive cell',
            'lattice_param': 5.43,
            'material': 'silicon'
        }
    )
    print(f"Stored crystal with ID: {doc_id}")
    print(f"Crystal formula: {crystal.formula}")

    # ======================================================================
    # 3. Store Calculation Results
    # ======================================================================
    print("\n3. Store Calculation Results")
    print("-" * 70)

    calc = LennardJones(sigma=2.35, epsilon=0.01)
    crystal.calc = calc
    energy = crystal.get_potential_energy()
    forces = crystal.get_forces()

    results = {
        'energy': float(energy),
        'forces': forces.tolist(),
        'calculator': 'LennardJones',
        'parameters': {'sigma': 2.35, 'epsilon': 0.01}
    }

    results_id = storage_mem.store_data(
        results,
        metadata={
            'calculator': 'LJ',
            'structure_id': doc_id,
            'calculation_type': 'energy_force'
        }
    )
    print(f"Stored calculation results with ID: {results_id}")
    print(f"Energy: {energy:.6f} eV")

    # ======================================================================
    # 4. Retrieve Data
    # ======================================================================
    print("\n4. Retrieve Data")
    print("-" * 70)

    # Retrieve crystal (decoded as Crystal object)
    crystal_restored = storage_mem.retrieve_data(doc_id)
    print(f"Restored crystal formula: {crystal_restored.formula}")
    if hasattr(crystal_restored, 'lattice') and crystal_restored.lattice:
        print(f"Restored lattice parameter: {crystal_restored.lattice.a:.2f} A")

    # Retrieve results (plain dict — no MSON metadata)
    retrieved_results = storage_mem.retrieve_data(results_id)
    if isinstance(retrieved_results, dict):
        print(f"Retrieved energy: {retrieved_results.get('energy', 0):.6f} eV")

    # ======================================================================
    # 5. Query Data
    # ======================================================================
    print("\n5. Query Data")
    print("-" * 70)

    lj_results = storage_mem.query({'metadata.calculator': 'LJ'})
    print(f"Found {len(lj_results)} documents with calculator='LJ'")

    si_structures = storage_mem.query({'metadata.material': 'silicon'})
    print(f"Found {len(si_structures)} silicon structures")

    # ======================================================================
    # 6. ID Stability
    # ======================================================================
    print("\n6. ID Stability")
    print("-" * 70)

    id1 = storage_mem.store_data({'test': 'data'})
    id2 = storage_mem.store_data({'test': 'data'})
    print(f"Same content, same ID: {id1 == id2}")
    print(f"ID length (sha256): {len(id1)} chars")

    # ======================================================================
    # 7. Context Manager Usage
    # ======================================================================
    print("\n7. Context Manager Usage")
    print("-" * 70)

    with DataStorage(backend=MemoryBackend()) as storage_ctx:
        doc_id_ctx = storage_ctx.store_data({'test': 'data'})
        retrieved_ctx = storage_ctx.retrieve_data(doc_id_ctx)
        print(f"Stored and retrieved in context: OK")
    # Automatically closed

    # ======================================================================
    # 8. Store Multiple Structures
    # ======================================================================
    print("\n8. Store Multiple Structures")
    print("-" * 70)

    structures = [
        Crystal(['Fe'], [[0, 0, 0]], Lattice.cubic(2.87)),
        Crystal(['Al'], [[0, 0, 0]], Lattice.cubic(4.05)),
        Crystal(['Cu'], [[0, 0, 0]], Lattice.cubic(3.61)),
    ]

    stored_ids = []
    for struct in structures:
        doc_id = storage_mem.store_data(
            struct,
            metadata={'material': struct.formula, 'type': 'metal'}
        )
        stored_ids.append(doc_id)

    print(f"Stored {len(stored_ids)} structures")

    # Query all metals
    metals = storage_mem.query({'metadata.type': 'metal'})
    print(f"Found {len(metals)} metal structures")

finally:
    if storage is not None:
        storage.close()
    if storage_mem is not None:
        storage_mem.close()
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)
    print("\nTemporary storage files cleaned up")

print("\n" + "=" * 70)
print("Storage examples completed!")
print("=" * 70)
