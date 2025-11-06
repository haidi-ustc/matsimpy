# Data Storage Module Implementation Plan

## Overview

Implement a persistent data storage module using maggma for storing computation results, structures, and workflows.

## Design Goals

1. **Graceful Integration**: Work seamlessly with existing MatSimPy classes
2. **Flexible Storage**: Support both memory and file-based storage
3. **Config Integration**: Use config system for default paths
4. **MSONable Support**: Store Crystal, Molecule, and other MSONable objects
5. **Optional Dependency**: Handle maggma as optional dependency gracefully

## Proposed Structure

```
matsimpy/storage/
├── __init__.py           # Main exports
├── base.py               # Base storage class (optional fallback)
├── maggma_store.py       # Maggma-based storage implementation
└── utils.py              # Helper functions
```

## Implementation Details

### Features

1. **Storage Types**:
   - MemoryStore: For testing and temporary data
   - JSONStore: Persistent file-based storage
   - Configurable via config system

2. **Integration Points**:
   - Config system: Default storage path
   - Calculators: Store calculation results
   - Core classes: Store structures
   - Workflows: Store workflow data

3. **Error Handling**:
   - Graceful fallback if maggma not available
   - Clear error messages
   - Optional dependency warnings

## Usage Examples

```python
from matsimpy.storage import DataStorage
from matsimpy import Crystal, Lattice

# Initialize storage (uses config default path)
storage = DataStorage()

# Store a crystal structure
crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))
doc_id = storage.store_data(crystal)

# Store calculation results
results = {'energy': -10.5, 'forces': [[0,0,0]]}
storage.store_data(results, metadata={'calculator': 'LJ'})

# Retrieve data
crystal_dict = storage.retrieve_data(doc_id)
crystal = Crystal.from_dict(crystal_dict)

# Query data
results = storage.retrieve_data(query={'metadata.calculator': 'LJ'})
```

## Dependencies

- **maggma**: Optional dependency (add to extras_require)
- **monty**: Already in dependencies (for MSONable)

## Integration with Config

```yaml
# ~/.matsimpy/config.yaml
storage:
  default_path: "~/.matsimpy/storage/data.json"
  default_store_type: "json"  # or "memory"
  auto_save: true
```

## Error Handling

If maggma is not available:
- Provide clear error message
- Optionally provide fallback implementation
- Suggest installation: `pip install matsimpy[storage]`

