"""
MatSimPy Storage Module - Basic Examples

Demonstrates usage of persistent data storage for structures and results.
"""

from matsimpy.storage import DataStorage
from matsimpy import Crystal, Molecule, Lattice
from matsimpy.calculator import LennardJones
import tempfile
import shutil
from pathlib import Path

print("=" * 70)
print("MatSimPy Storage Module - Basic Examples")
print("=" * 70)

# Create temporary directory for testing
temp_dir = tempfile.mkdtemp()
store_path = Path(temp_dir) / 'test_storage.json'

try:
    # ======================================================================
    # 1. Initialize Storage
    # ======================================================================
    print("\n1. Initialize Storage")
    print("-" * 70)
    
    # Memory store (for testing)
    storage_mem = DataStorage(use_memory_store=True)
    print(f"Memory store type: {storage_mem.store_type}")
    
    # JSON file store
    storage = DataStorage(store_path=str(store_path))
    print(f"JSON store type: {storage.store_type}")
    print(f"Storage path: {storage.store_path}")
    
    # ======================================================================
    # 2. Store Crystal Structure
    # ======================================================================
    print("\n2. Store Crystal Structure")
    print("-" * 70)
    
    crystal = Crystal(['Si'], [[0, 0, 0]], Lattice.cubic(5.43))
    doc_id = storage.store_data(
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
    
    # Perform calculation
    calc = LennardJones(sigma=2.35, epsilon=0.01)  # Approximate Si parameters
    crystal.calc = calc
    energy = crystal.get_potential_energy()
    forces = crystal.get_forces()
    
    # Store results with metadata
    results = {
        'energy': float(energy),
        'forces': forces.tolist(),
        'calculator': 'LennardJones',
        'parameters': {'sigma': 2.35, 'epsilon': 0.01}
    }
    
    results_id = storage.store_data(
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
    
    # Retrieve crystal
    retrieved_crystal_dict = storage.retrieve_data(doc_id)
    print(f"Retrieved document keys: {list(retrieved_crystal_dict.keys())[:5]}...")
    
    # Restore crystal from dict
    crystal_restored = Crystal.from_dict(retrieved_crystal_dict)
    print(f"Restored crystal formula: {crystal_restored.formula}")
    print(f"Restored lattice parameter: {crystal_restored.lattice.a:.2f} Å")
    
    # Retrieve results
    retrieved_results = storage.retrieve_data(results_id)
    print(f"Retrieved energy: {retrieved_results['energy']:.6f} eV")
    print(f"Calculator: {retrieved_results.get('calculator', 'N/A')}")
    
    # ======================================================================
    # 5. Query Data
    # ======================================================================
    print("\n5. Query Data")
    print("-" * 70)
    
    # Query all LJ calculations
    lj_results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
    print(f"Found {len(lj_results)} documents with calculator='LJ'")
    
    # Query by material
    si_structures = storage.retrieve_data(query={'metadata.material': 'silicon'})
    print(f"Found {len(si_structures)} silicon structures")
    
    # ======================================================================
    # 6. Count and Manage Documents
    # ======================================================================
    print("\n6. Count and Manage Documents")
    print("-" * 70)
    
    total_count = storage.count_documents()
    print(f"Total documents in store: {total_count}")
    
    lj_count = storage.count_documents(query={'metadata.calculator': 'LJ'})
    print(f"LJ calculation results: {lj_count}")
    
    # ======================================================================
    # 7. Context Manager Usage
    # ======================================================================
    print("\n7. Context Manager Usage")
    print("-" * 70)
    
    with DataStorage(use_memory_store=True) as storage_ctx:
        doc_id_ctx = storage_ctx.store_data({'test': 'data'})
        retrieved_ctx = storage_ctx.retrieve_data(doc_id_ctx)
        print(f"Stored and retrieved in context: {retrieved_ctx.get('test')}")
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
        doc_id = storage.store_data(
            struct,
            metadata={'material': struct.formula, 'type': 'metal'}
        )
        stored_ids.append(doc_id)
    
    print(f"Stored {len(stored_ids)} structures")
    print(f"Total documents now: {storage.count_documents()}")
    
    # Query all metals
    metals = storage.retrieve_data(query={'metadata.type': 'metal'})
    print(f"Found {len(metals)} metal structures")
    
finally:
    # Cleanup
    storage.close()
    storage_mem.close()
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)
    print("\nTemporary storage files cleaned up")

print("\n" + "=" * 70)
print("Storage examples completed!")
print("=" * 70)

