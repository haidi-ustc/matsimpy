# Calculator Module Reorganization Plan

## Current Issues

1. **Flat Structure**: All calculators are in the same directory level
   - `LennardJones` (classical potential)
   - `Mattersim` (ML calculator, but Mattersim is just one framework)
   - Future: VASP, QE, MACE, NequIP, etc. would all be at same level

2. **No Clear Categorization**: Hard to see what type of calculator each is
3. **Limited Extensibility**: Adding new calculators requires modifying root `__init__.py`
4. **No Base Classes for Categories**: Each calculator type has different needs:
   - Classical: Direct computation, no file I/O
   - ML: Model loading, framework-specific
   - DFT: File-based (input/output), execution management

## Proposed Structure

```
matsimpy/calculator/
├── __init__.py              # Main exports (all calculator types)
├── base.py                  # Base Calculator abstract class
│
├── classical/               # Classical/semi-classical potentials
│   ├── __init__.py
│   ├── lennard_jones.py     # LJ potential
│   ├── morse.py             # Morse potential (future)
│   ├── buckingham.py        # Buckingham potential (future)
│   └── base_classical.py    # Base class for classical potentials (optional)
│
├── ml/                      # Machine learning calculators
│   ├── __init__.py
│   ├── base_ml.py           # Base ML calculator class
│   ├── mattersim.py         # Mattersim framework interface
│   ├── mace.py              # MACE-specific calculator (future)
│   ├── nequip.py            # NequIP-specific calculator (future)
│   └── schnet.py            # SchNet-specific calculator (future)
│
├── dft/                     # DFT calculators (file-based)
│   ├── __init__.py
│   ├── base_dft.py          # Base DFT calculator (handles file I/O, execution)
│   ├── vasp.py              # VASP calculator (future)
│   ├── quantum_espresso.py  # Quantum Espresso calculator (future)
│   └── pwscf.py             # PWSCF calculator (future)
│
└── semiempirical/           # Semi-empirical methods (future)
    ├── __init__.py
    ├── base_semiempirical.py
    └── dftb.py              # DFTB calculator (future)
```

## Benefits

1. **Clear Organization**: Calculators grouped by type
2. **Easy Extension**: Add new calculators in appropriate subdirectory
3. **Shared Base Classes**: Common functionality for each category
4. **Better Import Structure**: `from matsimpy.calculator.classical import LennardJones`
5. **Scalable**: Can add new categories without cluttering root

## Implementation Plan

### Phase 1: Reorganize Structure
1. Create subdirectories: `classical/`, `ml/`, `dft/`
2. Move `LennardJones` to `classical/lennard_jones.py`
3. Move `Mattersim` to `ml/mattersim.py`
4. Create base classes for each category

### Phase 2: Base Classes
1. **Base Classical Calculator**: Minimal - just compute energy/forces
2. **Base ML Calculator**: Model loading, input preparation, framework abstraction
3. **Base DFT Calculator**: File I/O, execution management, output parsing

### Phase 3: Update Imports
1. Update `calculator/__init__.py` to export from submodules
2. Maintain backward compatibility (re-export from root)
3. Update tests
4. Update examples

## Detailed Base Class Design

### Base Classical Calculator

```python
class BaseClassical(Calculator):
    """Base class for classical potential calculators."""
    
    def __init__(self, **parameters):
        super().__init__(**parameters)
        # Common parameters for classical potentials
        self.cutoff = parameters.get('cutoff', None)
        self.rc_smooth = parameters.get('rc_smooth', None)
    
    @abstractmethod
    def _compute_pair_energy(self, r, i, j):
        """Compute energy for a pair of atoms."""
        pass
    
    @abstractmethod
    def _compute_pair_forces(self, r, r_vec, i, j):
        """Compute forces for a pair of atoms."""
        pass
```

### Base ML Calculator

```python
class BaseML(Calculator):
    """Base class for machine learning potential calculators."""
    
    def __init__(self, model=None, model_path=None, **parameters):
        super().__init__(model=model, model_path=model_path, **parameters)
        self.model = model
        self.model_path = model_path
        self.device = parameters.get('device', 'cpu')
    
    @abstractmethod
    def _load_model(self):
        """Load ML model from file."""
        pass
    
    @abstractmethod
    def _prepare_input(self, structure):
        """Prepare structure for ML model input."""
        pass
    
    @abstractmethod
    def _run_model(self, model_input):
        """Run ML model inference."""
        pass
```

### Base DFT Calculator

```python
class BaseDFT(Calculator):
    """Base class for DFT calculators (file-based)."""
    
    def __init__(self, directory='./', **parameters):
        super().__init__(directory=directory, **parameters)
        self.directory = Path(directory)
        self.input_files = {}
        self.output_files = {}
    
    @abstractmethod
    def _write_input(self, structure):
        """Write input files for DFT calculation."""
        pass
    
    @abstractmethod
    def _run_calculation(self):
        """Execute DFT calculation."""
        pass
    
    @abstractmethod
    def _read_output(self):
        """Read and parse output files."""
        pass
```

## Import Structure

### Root `__init__.py`

```python
# Main exports - maintain backward compatibility
from .classical import LennardJones
from .ml import Mattersim

# Category imports
from . import classical
from . import ml
from . import dft

__all__ = [
    # Base
    'Calculator',
    
    # Classical
    'LennardJones',
    
    # ML
    'Mattersim',
    
    # Categories
    'classical',
    'ml',
    'dft',
]
```

### Usage Examples

```python
# Option 1: Direct import (backward compatible)
from matsimpy.calculator import LennardJones, Mattersim

# Option 2: Category import
from matsimpy.calculator.classical import LennardJones
from matsimpy.calculator.ml import Mattersim

# Option 3: Category module
from matsimpy.calculator import classical, ml
calc1 = classical.LennardJones(...)
calc2 = ml.Mattersim(...)
```

## Migration Strategy

1. **Backward Compatibility**: Keep old imports working
2. **Gradual Migration**: Update internal code gradually
3. **Deprecation Warning**: (Optional) Warn about old import style
4. **Documentation**: Update all examples and docs

## Testing Strategy

1. Test imports work from both old and new locations
2. Test all calculators still function correctly
3. Test base classes work correctly
4. Test category-specific functionality

## Timeline

- **Phase 1** (Reorganization): 1-2 hours
- **Phase 2** (Base Classes): 2-3 hours  
- **Phase 3** (Updates): 1-2 hours
- **Testing**: 1 hour

**Total**: ~5-8 hours

## Questions for Discussion

1. Should we keep backward compatibility or require migration?
2. Do we need base classes for each category, or is Calculator base enough?
3. Should `dft` calculators be separate, or combined with `code` module?
4. Any other calculator categories to consider?

