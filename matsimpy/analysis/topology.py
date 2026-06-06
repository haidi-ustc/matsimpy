"""Connectivity topology analysis — thin wrapper over graph.py."""

import numpy as np
from typing import Optional, Union, List
from ..core import Crystal, Molecule
from .graph import MoleculeGraph, CrystalGraph


class TopologyAnalyzer:
    """Structural topology analysis — connectivity, rings, paths.

    Thin wrapper over graph.py for discoverability. Delegates to
    MoleculeGraph or CrystalGraph internally.

    Usage::

        >>> analyzer = TopologyAnalyzer(molecule, cutoff=1.6)
        >>> analyzer.is_connected()
        >>> rings = analyzer.get_rings(max_size=6)
    """

    def __init__(self, structure: Union[Crystal, Molecule], cutoff: float = 2.0,
                 use_pbc: bool = False):
        self.structure = structure
        self._cutoff = cutoff
        self._use_pbc = use_pbc
        self._graph = None

    def _get_graph(self):
        """Lazy-build the appropriate graph object."""
        if self._graph is None:
            if isinstance(self.structure, Crystal):
                self._graph = CrystalGraph(
                    self.structure, cutoff=self._cutoff, use_pbc=self._use_pbc
                )
            else:
                self._graph = MoleculeGraph(self.structure, cutoff=self._cutoff)
        return self._graph

    def is_connected(self) -> bool:
        """True if the structure forms one connected component."""
        return self._get_graph().is_connected

    def connected_components(self) -> List[List[int]]:
        """Atoms grouped by connected component."""
        return self._get_graph().connected_components

    def get_rings(self, max_size: int = 6) -> List[List[int]]:
        """Find all rings up to max_size atoms."""
        return self._get_graph().find_rings(max_size=max_size)

    def shortest_path(self, source: int, target: int) -> Optional[List[int]]:
        """Shortest atom-index path between source and target."""
        return self._get_graph().shortest_path(source, target)

    def coordination_numbers(self) -> dict:
        """Coordination number for each atom."""
        return self._get_graph().coordination_numbers

    def adjacency_matrix(self) -> np.ndarray:
        """N×N adjacency matrix."""
        return self._get_graph().adjacency_matrix


__all__ = ["TopologyAnalyzer"]
