"""
AI-guided structure optimization operations.

Provides operations for optimizing structures using AI guidance.
"""

from typing import Dict, Any, Optional, List
from ..base import AIInterface, AIOperation
from ...core import Crystal


class AIOptimization(AIOperation):
    """
    AI-guided structure optimization operation.

    Optimizes structures toward target properties using AI guidance.
    Works with any AIInterface implementation.

    Examples:
        >>> from matsimpy.ai import MCPInterface, AIOptimization
        >>>
        >>> mcp = MCPInterface(transport="stdio")
        >>> mcp.connect({"command": "python", "args": ["server.py"]})
        >>>
        >>> opt = AIOptimization(mcp)
        >>> optimized = opt.optimize_for_property(crystal, "band_gap", target=2.0)
        >>>
        >>> mcp.disconnect()
    """

    def optimize_for_property(
        self,
        crystal: Crystal,
        property_name: str,
        target_value: Optional[float] = None,
        maximize: bool = True,
        max_iterations: int = 10,
    ) -> Crystal:
        """
        Optimize structure for a specific property.

        Args:
            crystal: Initial crystal structure
            property_name: Property to optimize ('band_gap', 'formation_energy', etc.)
            target_value: Target value for the property (if None, maximize/minimize)
            maximize: If True, maximize property; if False, minimize
            max_iterations: Maximum optimization iterations

        Returns:
            Optimized crystal structure
        """
        structure_data = self._format_structure(crystal)

        inputs = {
            "structure": structure_data,
            "property_name": property_name,
            "maximize": maximize,
            "max_iterations": max_iterations,
        }

        if target_value is not None:
            inputs["target_value"] = target_value

        result = self.interface.call(operation="optimize_for_property", inputs=inputs)

        return self._parse_structure_result(result)

    def optimize_stability(self, crystal: Crystal, max_iterations: int = 10) -> Crystal:
        """
        Optimize structure for stability (minimize formation energy).

        Args:
            crystal: Initial crystal structure
            max_iterations: Maximum optimization iterations

        Returns:
            Optimized crystal structure
        """
        return self.optimize_for_property(
            crystal, "formation_energy", maximize=False, max_iterations=max_iterations
        )

    def optimize_lattice_parameters(
        self,
        crystal: Crystal,
        target_density: Optional[float] = None,
        constraints: Optional[Dict] = None,
    ) -> Crystal:
        """
        Optimize lattice parameters.

        Args:
            crystal: Initial crystal structure
            target_density: Target density in g/cm³
            constraints: Optional constraints (space group, symmetry, etc.)

        Returns:
            Crystal with optimized lattice parameters
        """
        structure_data = self._format_structure(crystal)

        inputs = {"structure": structure_data}
        if target_density:
            inputs["target_density"] = target_density
        if constraints:
            inputs["constraints"] = constraints

        result = self.interface.call(
            operation="optimize_lattice_parameters", inputs=inputs
        )

        return self._parse_structure_result(result)

    def execute(self, **kwargs) -> Crystal:
        """
        Execute optimization operation.

        Args:
            **kwargs: Should include 'crystal' and optimization parameters

        Returns:
            Optimized crystal structure
        """
        crystal = kwargs.get("crystal")
        if not crystal:
            raise ValueError("Must provide 'crystal' for optimization")

        property_name = kwargs.get("property_name", "formation_energy")
        target_value = kwargs.get("target_value")
        maximize = kwargs.get("maximize", False)
        max_iterations = kwargs.get("max_iterations", 10)

        return self.optimize_for_property(
            crystal, property_name, target_value, maximize, max_iterations
        )

    def _format_structure(self, structure: Crystal) -> Dict[str, Any]:
        """Format structure for AI input."""
        from ..utils.formatting import format_structure_for_ai

        return format_structure_for_ai(structure)

    def _parse_structure_result(self, result: Dict[str, Any]) -> Crystal:
        """Parse AI result into Crystal object."""
        from ..utils.formatting import parse_structure_from_ai

        return parse_structure_from_ai(result)


__all__ = ["AIOptimization"]
