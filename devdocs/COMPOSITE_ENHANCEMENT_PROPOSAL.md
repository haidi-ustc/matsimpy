# Composite Transformation Module Enhancement Proposal

## Overview

Enhance the `composite.py` module to support high-throughput structure generation and transformation pipelines. This is critical for:
- Generating large datasets for ML training
- Parameter sweeps (strain, doping, defects)
- Combinatorial material discovery
- Batch processing for DFT/MD simulations

## Current State

The current `composite.py` only provides:
- `chain()`: Simple sequential transformation chaining
- `apply_transformations()`: Convenience wrapper

**Limitations:**
- No batch processing
- No parameter sweeps
- No parallelization
- No workflow management
- No progress tracking
- No error recovery

## Proposed Enhancements

### 1. TransformationPipeline Class

A reusable pipeline that can be defined once and applied to multiple structures.

```python
from matsimpy.transformation.composite import TransformationPipeline
from matsimpy.transformation import translate, rotate, apply_strain, make_supercell

# Define pipeline
pipeline = TransformationPipeline("strain_study")
pipeline.add_step(translate, displacement=[0, 0, 0])
pipeline.add_step(make_supercell, scaling_matrix=[2, 2, 2])
pipeline.add_step(apply_strain, strain_matrix=[[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])

# Apply to structure
result = pipeline.apply(crystal)

# Apply to multiple structures
results = pipeline.apply_batch([crystal1, crystal2, crystal3])
```

**Features:**
- Named pipelines for reuse
- Step-by-step execution with logging
- Validation of intermediate results
- Error handling and recovery
- Serialization (save/load pipelines)

### 2. Parameter Sweep Generator

Generate structures with varying parameters.

```python
from matsimpy.transformation.composite import ParameterSweep

# Define parameter ranges
sweep = ParameterSweep(
    base_structure=crystal,
    transformations={
        'strain': {
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],  # 0%
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],  # 1%
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],  # 2%
                ]
            }
        },
        'supercell': {
            'func': make_supercell,
            'params': {
                'scaling_matrix': [[2,2,2], [3,3,3], [4,4,4]]
            }
        }
    },
    mode='cartesian'  # or 'zip' for parallel iteration
)

# Generate all combinations
structures = list(sweep.generate())

# Or iterate lazily
for struct, metadata in sweep:
    print(f"Strain: {metadata['strain']}, Supercell: {metadata['supercell']}")
    run_calculation(struct)
```

**Modes:**
- `cartesian`: All combinations (3 strains × 3 supercells = 9 structures)
- `zip`: Parallel iteration (3 structures, one from each)
- `custom`: User-defined combination logic

### 3. Batch Processor

Process multiple structures efficiently with parallelization.

```python
from matsimpy.transformation.composite import BatchProcessor

# Define transformation sequence
transformations = [
    lambda s: make_supercell(s, [2, 2, 2]),
    lambda s: apply_strain(s, [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]]),
    lambda s: substitute(s, [0], ['Al'])
]

# Process batch
processor = BatchProcessor(
    transformations=transformations,
    n_workers=4,  # Parallel processing
    progress=True,  # Show progress bar
    error_handling='skip'  # or 'raise', 'log'
)

results = processor.process([crystal1, crystal2, ..., crystal1000])

# Results include metadata
for result in results:
    if result.success:
        print(f"Success: {result.structure.formula}")
    else:
        print(f"Failed: {result.error}")
```

**Features:**
- Parallel processing with multiprocessing/threading
- Progress tracking (tqdm integration)
- Error handling strategies
- Memory-efficient streaming
- Result metadata (success, error, timing)

### 4. Combinatorial Generator

Generate all combinations of transformations and parameters.

```python
from matsimpy.transformation.composite import CombinatorialGenerator

generator = CombinatorialGenerator(
    base_structure=crystal,
    transformations=[
        {
            'name': 'strain',
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
                ]
            }
        },
        {
            'name': 'doping',
            'func': substitute,
            'params': {
                'indices': [[0], [1], [0, 1]],
                'new_species': [['Al'], ['Ga']]
            }
        }
    ]
)

# Generate all combinations: 2 strains × 3 indices × 2 species = 12 structures
for struct, params in generator:
    print(f"Strain: {params['strain']}, Doping: {params['doping']}")
```

### 5. Conditional Transformations

Apply transformations based on conditions.

```python
from matsimpy.transformation.composite import ConditionalPipeline

pipeline = ConditionalPipeline()
pipeline.add_if(
    condition=lambda s: len(s) < 100,
    transform=lambda s: make_supercell(s, [2, 2, 2]),
    name='expand_small'
)
pipeline.add_if(
    condition=lambda s: s.composition.get('Si', 0) > 0,
    transform=lambda s: substitute(s, [0], ['Ge']),
    name='substitute_si'
)
pipeline.add_always(
    transform=lambda s: translate(s, [0, 0, 0]),
    name='center'
)

result = pipeline.apply(crystal)
```

### 6. Workflow Builder (Fluent Interface)

Chain transformations with a fluent interface.

```python
from matsimpy.transformation.composite import Workflow

result = (Workflow(crystal)
    .translate([1, 1, 1])
    .rotate(90, [0, 0, 1])
    .make_supercell([2, 2, 2])
    .apply_strain([[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])
    .substitute([0], ['Al'])
    .execute()
)
```

### 7. High-Throughput Structure Generator

Complete solution for generating large datasets.

```python
from matsimpy.transformation.composite import HighThroughputGenerator
from matsimpy.builders.bulk import from_prototype

# Define generation strategy
generator = HighThroughputGenerator(
    base_structures=[
        from_prototype('diamond', 'Si', 5.43),
        from_prototype('fcc', 'Al', 4.05),
        from_prototype('bcc', 'Fe', 2.87),
    ],
    transformations={
        'strain': {
            'func': apply_strain,
            'values': [
                [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
                [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
            ]
        },
        'supercell': {
            'func': make_supercell,
            'values': [[2,2,2], [3,3,3]]
        }
    },
    output_dir='./generated_structures',
    save_format='vasp',  # or 'xyz', 'json'
    parallel=True,
    n_workers=8
)

# Generate all structures
generator.generate_all()

# Or process lazily
for struct, metadata in generator:
    # Run calculation
    energy = run_dft(struct)
    # Save result
    generator.save_result(struct, metadata, {'energy': energy})
```

## Implementation Structure

```
matsimpy/transformation/composite/
├── __init__.py              # Main exports
├── pipeline.py              # TransformationPipeline class
├── sweep.py                 # ParameterSweep class
├── batch.py                 # BatchProcessor class
├── combinatorial.py         # CombinatorialGenerator class
├── conditional.py           # ConditionalPipeline class
├── workflow.py              # Workflow builder (fluent interface)
├── htp.py                   # HighThroughputGenerator class
├── utils.py                 # Helper functions (parallel, progress, etc.)
└── serialization.py         # Save/load pipelines
```

## Detailed API Design

### TransformationPipeline

```python
class TransformationPipeline:
    """
    Reusable transformation pipeline for applying multiple transformations.
    
    Examples:
        >>> pipeline = TransformationPipeline("my_pipeline")
        >>> pipeline.add_step(translate, displacement=[1, 1, 1])
        >>> pipeline.add_step(rotate, angle=90, axis=[0, 0, 1])
        >>> result = pipeline.apply(crystal)
    """
    
    def __init__(self, name: str = "pipeline"):
        self.name = name
        self.steps = []
        self.metadata = {}
    
    def add_step(self, func: Callable, **kwargs):
        """Add a transformation step."""
        self.steps.append({'func': func, 'kwargs': kwargs})
        return self
    
    def apply(self, structure, inplace: bool = False):
        """Apply pipeline to a single structure."""
        result = structure
        for step in self.steps:
            result = step['func'](result, **step['kwargs'], inplace=inplace)
            inplace = False  # Only first step can be inplace
        return result
    
    def apply_batch(self, structures, parallel: bool = False, n_workers: int = 4):
        """Apply pipeline to multiple structures."""
        ...
    
    def save(self, path: str):
        """Save pipeline to file."""
        ...
    
    @classmethod
    def load(cls, path: str):
        """Load pipeline from file."""
        ...
```

### ParameterSweep

```python
class ParameterSweep:
    """
    Generate structures with varying parameters.
    
    Examples:
        >>> sweep = ParameterSweep(
        ...     base_structure=crystal,
        ...     transformations={
        ...         'strain': {
        ...             'func': apply_strain,
        ...             'params': {'strain_matrix': [...]}
        ...         }
        ...     },
        ...     mode='cartesian'
        ... )
        >>> for struct, params in sweep:
        ...     process(struct)
    """
    
    def __init__(
        self,
        base_structure: Union[Crystal, Molecule],
        transformations: Dict[str, Dict],
        mode: str = 'cartesian'  # 'cartesian', 'zip', 'custom'
    ):
        ...
    
    def generate(self):
        """Generate all combinations."""
        ...
    
    def __iter__(self):
        """Iterate over generated structures."""
        ...
    
    def __len__(self):
        """Number of structures to generate."""
        ...
```

### BatchProcessor

```python
class BatchProcessor:
    """
    Process multiple structures with transformations in parallel.
    
    Examples:
        >>> processor = BatchProcessor(
        ...     transformations=[...],
        ...     n_workers=4,
        ...     progress=True
        ... )
        >>> results = processor.process(structures)
    """
    
    def __init__(
        self,
        transformations: List[Callable],
        n_workers: int = 4,
        progress: bool = True,
        error_handling: str = 'skip'  # 'skip', 'raise', 'log'
    ):
        ...
    
    def process(self, structures: List[Union[Crystal, Molecule]]):
        """Process batch of structures."""
        ...
    
    def process_stream(self, structures):
        """Process structures lazily (generator)."""
        ...
```

### HighThroughputGenerator

```python
class HighThroughputGenerator:
    """
    Complete solution for high-throughput structure generation.
    
    Examples:
        >>> generator = HighThroughputGenerator(
        ...     base_structures=[...],
        ...     transformations={...},
        ...     output_dir='./structures',
        ...     parallel=True
        ... )
        >>> generator.generate_all()
    """
    
    def __init__(
        self,
        base_structures: List[Union[Crystal, Molecule]],
        transformations: Dict[str, Dict],
        output_dir: str = './generated',
        save_format: str = 'vasp',
        parallel: bool = True,
        n_workers: int = 8,
        progress: bool = True
    ):
        ...
    
    def generate_all(self):
        """Generate all structures and save to disk."""
        ...
    
    def __iter__(self):
        """Iterate over generated structures."""
        ...
    
    def save_result(self, structure, metadata, results):
        """Save structure with calculation results."""
        ...
```

## Usage Examples

### Example 1: Strain Study

```python
from matsimpy.transformation.composite import ParameterSweep
from matsimpy.transformation import apply_strain, make_supercell
from matsimpy.builders.bulk import from_prototype

# Base structure
crystal = from_prototype('diamond', 'Si', 5.43)

# Generate strained structures
sweep = ParameterSweep(
    base_structure=crystal,
    transformations={
        'supercell': {
            'func': make_supercell,
            'params': {'scaling_matrix': [[2,2,2], [3,3,3]]}
        },
        'strain': {
            'func': apply_strain,
            'params': {
                'strain_matrix': [
                    [[0.00, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
                    [[0.02, 0, 0], [0, 0, 0], [0, 0, 0]],
                ]
            }
        }
    },
    mode='cartesian'
)

# Generate 2 × 3 = 6 structures
for struct, params in sweep:
    print(f"Supercell: {params['supercell']}, Strain: {params['strain']}")
    energy = run_dft(struct)
    print(f"Energy: {energy} eV")
```

### Example 2: Defect Study

```python
from matsimpy.transformation.composite import CombinatorialGenerator
from matsimpy.transformation import substitute
from matsimpy.builders.defects import create_vacancy, create_interstitial

crystal = from_prototype('diamond', 'Si', 5.43)

# Generate all defect combinations
generator = CombinatorialGenerator(
    base_structure=crystal,
    transformations=[
        {
            'name': 'vacancy',
            'func': create_vacancy,
            'params': {
                'indices': [[0], [1], [0, 1]]
            }
        },
        {
            'name': 'substitution',
            'func': substitute,
            'params': {
                'indices': [[0], [1]],
                'new_species': [['Ge'], ['C']]
            }
        }
    ]
)

# Generate all combinations
for struct, params in generator:
    print(f"Vacancy: {params['vacancy']}, Substitution: {params['substitution']}")
    run_calculation(struct)
```

### Example 3: High-Throughput Dataset Generation

```python
from matsimpy.transformation.composite import HighThroughputGenerator

# Generate 1000s of structures
generator = HighThroughputGenerator(
    base_structures=[
        from_prototype('diamond', 'Si', 5.43),
        from_prototype('fcc', 'Al', 4.05),
    ],
    transformations={
        'strain': {
            'func': apply_strain,
            'values': [strain_0, strain_1, ..., strain_10]
        },
        'doping': {
            'func': substitute,
            'values': [doping_config_1, doping_config_2, ...]
        }
    },
    output_dir='./ml_training_data',
    save_format='json',
    parallel=True,
    n_workers=16
)

# Generate and save all
generator.generate_all()

# Or process with calculations
for struct, metadata in generator:
    energy = run_dft(struct)
    forces = run_dft_forces(struct)
    generator.save_result(struct, metadata, {
        'energy': energy,
        'forces': forces
    })
```

## Implementation Priority

### Phase 1: Core Components (Essential)
1. **TransformationPipeline** - Reusable pipelines
2. **ParameterSweep** - Parameter variation
3. **BatchProcessor** - Parallel batch processing

### Phase 2: Advanced Features
4. **CombinatorialGenerator** - All combinations
5. **ConditionalPipeline** - Conditional transformations
6. **Workflow Builder** - Fluent interface

### Phase 3: High-Throughput Tools
7. **HighThroughputGenerator** - Complete solution
8. **Serialization** - Save/load pipelines
9. **Progress Tracking** - Enhanced progress bars

## Dependencies

- **multiprocessing/threading**: Parallel processing
- **tqdm**: Progress bars
- **joblib**: Advanced parallel processing (optional)
- **dask**: Distributed processing (optional, for very large batches)

## Testing Strategy

1. **Unit Tests**: Each class independently
2. **Integration Tests**: Full workflows
3. **Performance Tests**: Benchmark parallel processing
4. **Memory Tests**: Large batch processing

## Backward Compatibility

- Keep existing `chain()` and `apply_transformations()` functions
- New classes are additive, don't break existing code
- Provide migration examples for users

## File Size Estimate

- `pipeline.py`: ~200 lines
- `sweep.py`: ~250 lines
- `batch.py`: ~300 lines
- `combinatorial.py`: ~200 lines
- `conditional.py`: ~150 lines
- `workflow.py`: ~200 lines
- `htp.py`: ~400 lines
- `utils.py`: ~150 lines
- `serialization.py`: ~100 lines

**Total**: ~1950 lines

## Benefits

1. **Productivity**: Generate 1000s of structures with few lines of code
2. **Reproducibility**: Save/load pipelines for reproducibility
3. **Efficiency**: Parallel processing for speed
4. **Flexibility**: Multiple patterns (sweeps, combinations, conditionals)
5. **Integration**: Works with existing transformation functions
6. **Scalability**: Handle large datasets efficiently

