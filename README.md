# MatSimPy

MatSimPy (Materials Simulation in Python) is a Python package that used for molecular and materials simulation.

## Installation

You can install MatSimPy using pip:

```
pip install MatSimPy
```


## Usage

### Structure

The `Structure` class is used to represent crystal and molecular structures. It takes in the species, positions, and lattice vectors as input. 

```python
from matsimpy import Structure, Lattice

species = ['C', 'C', 'O', 'O']
positions = [[0, 0, 0], [1.4, 1.4, 1.4], [1, 1, 1], [-1, -1, -1]]
lattice = Lattice([[10,0,0],[0,10,0],[0,0,10]])
structure = Structure(species, positions, lattice)
```

You can add and remove atoms from the structure:

```python
structure.add_atom('N', [0.5, 0.5, 0.5])
structure.remove_atom(0)
```

### Molecule
The Molecule class is a subclass of Structure that is used to represent molecules without a lattice. It takes in the species and positions as input.

```python
from matsimpy import Molecule

species = ['C', 'C', 'O', 'O']
positions = [[0, 0, 0], [1.4, 1.4, 1.4], [1, 1, 1], [-1, -1, -1]]
molecule = Molecule(species, positions)
```

You can get the center of mass of the molecule:
```python
print(molecule.get_center_of_mass())
```
