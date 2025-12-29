# Calculator Module Development Plan

## Overview

This document outlines the plan for developing a calculator module for MatSimPy, inspired by ASE's calculator interface but adapted for MatSimPy's architecture.

## Design Goals

1. **ASE-Inspired but Not Copied**: Learn from ASE's design patterns but adapt to MatSimPy's structure
2. **Clean Interface**: Calculator objects attach to Crystal/Molecule structures
3. **Extensible**: Easy to add new calculator types (VASP, Quantum Espresso, etc.)
4. **Flexible**: Support both file-based and direct execution
5. **Results Storage**: Store calculation results in calculator objects
6. **Parameter Management**: Easy parameter setting and validation

## Architecture

### Base Calculator Class

```python
class Calculator(ABC):
    """Base class for all calculators."""
    
    def __init__(self, **parameters):
        self.parameters = {}
        self.results = {}
        self.structure = None
        
    def set_parameters(self, **kwargs):
        """Set calculation parameters."""
        
    def calculate(self, structure):
        """Run calculation and store results."""
        
    @abstractmethod
    def _write_input(self, structure):
        """Write input file (for file-based calculators)."""
        
    @abstractmethod
    def _read_output(self):
        """Read output file (for file-based calculators)."""
        
    @abstractmethod
    def _run_calculation(self):
        """Execute the calculation."""
```

### Calculator Types

1. **File-Based Calculators** (VASP, Quantum Espresso)
   - Write input files
   - Execute external program
   - Read output files
   - Store results

2. **Direct Calculators** (Python-based, future)
   - Execute calculation directly
   - No file I/O needed

## Proposed Structure

```
matsimpy/calculator/
├── __init__.py           # Main exports
├── base.py               # Base Calculator class
├── vasp.py               # VASP calculator
├── quantum_espresso.py   # Quantum Espresso calculator
└── results.py            # Results storage classes
```

## Features to Implement

### Phase 1: Base Framework
- [ ] Base `Calculator` abstract class
- [ ] Calculator attachment to Crystal/Molecule
- [ ] Parameter management system
- [ ] Results storage structure
- [ ] Basic calculator interface

### Phase 2: VASP Calculator
- [ ] VASP calculator class
- [ ] Input file generation (POSCAR, INCAR, KPOINTS)
- [ ] Output file parsing (OUTCAR, CONTCAR)
- [ ] Energy extraction
- [ ] Forces extraction
- [ ] Stress extraction

### Phase 3: Quantum Espresso Calculator
- [ ] QE calculator class
- [ ] Input file generation (PW input)
- [ ] Output file parsing
- [ ] Energy and forces extraction

### Phase 4: Integration
- [ ] Integration with Crystal/Molecule classes
- [ ] Calculator property on structures
- [ ] Convenience methods (get_potential_energy(), get_forces(), etc.)

## API Design

### Basic Usage

```python
from matsimpy import Crystal, Lattice
from matsimpy.calculator import VASP

# Create structure
crystal = Crystal(['Si'], [[0,0,0]], Lattice.cubic(5.43))

# Create and attach calculator
calc = VASP(
    xc='PBE',
    kpts=(4, 4, 4),
    encut=400,
    directory='./calc'
)
crystal.calc = calc

# Run calculation
crystal.calc.calculate()

# Access results
energy = crystal.calc.results['energy']
forces = crystal.calc.results['forces']
```

### Parameter Management

```python
# Set parameters
calc.set_parameters(xc='PBE', encut=500)

# Get parameters
params = calc.get_parameters()

# Update specific parameters
calc.update_parameters(encut=600)
```

### Results Access

```python
# Direct access
energy = calc.results['energy']

# Convenience methods
energy = calc.get_potential_energy()
forces = calc.get_forces()
stress = calc.get_stress()
```

## File Structure

### Calculator Base (`base.py`)

```python
class Calculator:
    - __init__(**parameters)
    - set_parameters(**kwargs)
    - get_parameters()
    - calculate(structure)
    - _write_input(structure)
    - _read_output()
    - _run_calculation()
    - get_potential_energy()
    - get_forces()
    - get_stress()
```

### VASP Calculator (`vasp.py`)

```python
class VASP(Calculator):
    - __init__(**parameters)
    - _write_input(structure)  # Write POSCAR, INCAR, KPOINTS
    - _read_output()            # Read OUTCAR, CONTCAR
    - _run_calculation()        # Execute vasp
    - _parse_energy()
    - _parse_forces()
    - _parse_stress()
```

### Quantum Espresso Calculator (`quantum_espresso.py`)

```python
class QuantumEspresso(Calculator):
    - __init__(**parameters)
    - _write_input(structure)  # Write PW input
    - _read_output()            # Read output
    - _run_calculation()        # Execute pw.x
```

## Integration with Core Classes

### Crystal/Molecule Extensions

```python
# In crystal.py and molecule.py
@property
def calc(self):
    """Get attached calculator."""
    return self._calculator

@calc.setter
def calc(self, calculator):
    """Attach calculator."""
    self._calculator = calculator

def get_potential_energy(self):
    """Get potential energy from calculator."""
    if self.calc is None:
        raise ValueError("No calculator attached")
    if 'energy' not in self.calc.results:
        self.calc.calculate(self)
    return self.calc.results['energy']
```

## Testing Plan

1. **Base Calculator Tests**
   - Parameter management
   - Results storage
   - Calculator attachment

2. **VASP Calculator Tests**
   - Input file generation
   - Output parsing (mock files)
   - Parameter validation

3. **Integration Tests**
   - Calculator attachment to structures
   - Results access
   - Error handling

## Implementation Steps (Revised - Phase 1)

**Priority: Start with LJ and Mattersim calculators**

1. **Create base calculator framework**
   - Base class with abstract methods
   - Parameter management
   - Results storage
   - Tests

2. **Implement Lennard-Jones (LJ) calculator**
   - Pure Python implementation
   - Energy and forces calculation
   - Neighbor list for efficiency
   - Parameter customization (sigma, epsilon, cutoff)
   - Tests

3. **Implement Mattersim (ML) calculator**
   - Machine learning potential interface
   - Model loading and prediction
   - Energy and forces from ML models
   - Support for various ML frameworks
   - Tests

4. **Integrate with Crystal/Molecule**
   - Add calculator property
   - Add convenience methods
   - Tests

5. **Documentation and examples**
   - Usage examples
   - API documentation
   - Calculator setup guide

**Future Phases:**
- Phase 2: VASP calculator (file-based)
- Phase 3: Quantum Espresso calculator (file-based)

## Questions for Discussion

1. Should calculators be separate objects or integrated into structures?
   - **Proposed**: Separate objects that attach to structures (ASE-style)

2. How should calculation execution work?
   - **Proposed**: File-based for external codes, with option for direct execution

3. Should we support calculator chaining or composition?
   - **Proposed**: Not in initial version, but design for extensibility

4. How to handle calculation failures?
   - **Proposed**: Raise exceptions with clear error messages

## Dependencies

- Existing: `matsimpy.core`, `matsimpy.io`
- New: None (uses existing modules)

## Timeline

- **Phase 1** (Base Framework): 1-2 days
- **Phase 2** (VASP Calculator): 2-3 days
- **Phase 3** (QE Calculator): 1-2 days
- **Phase 4** (Integration): 1 day
- **Testing**: Ongoing throughout

**Total Estimated Time**: 5-8 days

