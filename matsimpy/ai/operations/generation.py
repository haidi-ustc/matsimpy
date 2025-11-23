"""
AI-based structure generation operations.

Provides operations for generating crystal and molecular structures
using AI models via any AIInterface.
"""

from typing import Dict, Any, Optional, List, Union
from ..base import AIInterface, AIOperation
from ...core import Crystal, Molecule, Lattice


class AIGeneration(AIOperation):
    """
    AI-based structure generation operation.

    Generates crystal and molecular structures using AI models.
    Works with any AIInterface implementation (MCP, OpenAI, etc.).

    Examples:
        >>> from matsimpy.ai import MCPInterface, AIGeneration
        >>>
        >>> # Connect to MCP server
        >>> mcp = MCPInterface(transport="stdio")
        >>> mcp.connect({"command": "python", "args": ["server.py"]})
        >>>
        >>> # Generate structure
        >>> gen = AIGeneration(mcp)
        >>> structure = gen.generate_from_composition("TiO2")
        >>>
        >>> mcp.disconnect()
    """

    def generate_from_composition(
        self, composition: str, constraints: Optional[Dict[str, Any]] = None
    ) -> Crystal:
        """
        Generate crystal structure from chemical composition using AI.

        Args:
            composition: Chemical formula (e.g., "TiO2", "SiC")
            constraints: Optional constraints:
                        - space_group: Space group number
                        - lattice_params: Lattice parameters
                        - density: Target density
                        - etc.

        Returns:
            Generated crystal structure

        Raises:
            RuntimeError: If generation fails
        """
        # Prepare inputs
        inputs = {"composition": composition, "operation": "generate_structure"}

        if constraints:
            inputs["constraints"] = constraints

        # Call AI interface
        result = self.interface.call(operation="generate_structure", inputs=inputs)

        # Parse and create Crystal object
        return self._parse_structure_result(result)

    def generate_from_description(self, description: str) -> Union[Crystal, Molecule]:
        """
        Generate structure from natural language description.

        Args:
            description: Natural language description
                       (e.g., "diamond cubic silicon", "water molecule")

        Returns:
            Generated structure (Crystal or Molecule)
        """
        result = self.interface.call(
            operation="generate_from_text", inputs={"description": description}
        )

        return self._parse_structure_result(result)

    def generate_variants(
        self,
        base_structure: Crystal,
        n_variants: int = 5,
        constraints: Optional[Dict] = None,
    ) -> List[Crystal]:
        """
        Generate variant structures from a base structure.

        Args:
            base_structure: Base crystal structure
            n_variants: Number of variants to generate
            constraints: Optional constraints for variants

        Returns:
            List of variant structures
        """
        # Convert structure to input format
        structure_data = self._format_structure(base_structure)

        inputs = {"base_structure": structure_data, "n_variants": n_variants}

        if constraints:
            inputs["constraints"] = constraints

        result = self.interface.call(operation="generate_variants", inputs=inputs)

        # Parse multiple structures
        structures = result.get("variants", [])
        return [self._parse_structure_result(s) for s in structures]

    def _format_structure(self, structure: Crystal) -> Dict[str, Any]:
        """Format structure for AI input."""
        from ..utils.formatting import format_structure_for_ai

        return format_structure_for_ai(structure)

    def _parse_structure_result(
        self, result: Dict[str, Any]
    ) -> Union[Crystal, Molecule]:
        """
        Parse AI result into Crystal or Molecule object.

        Args:
            result: AI operation result dictionary

        Returns:
            Crystal or Molecule object
        """
        # Use utility function for parsing
        from ..utils.formatting import parse_structure_from_ai

        return parse_structure_from_ai(result)

    def execute(self, **kwargs) -> Union[Crystal, Molecule]:
        """
        Execute generation operation.

        This is a convenience method that calls generate_from_composition
        by default, but can be overridden for custom behavior.

        Args:
            **kwargs: Should include 'composition' or 'description'

        Returns:
            Generated structure
        """
        if "composition" in kwargs:
            return self.generate_from_composition(
                kwargs["composition"], kwargs.get("constraints")
            )
        elif "description" in kwargs:
            return self.generate_from_description(kwargs["description"])
        else:
            raise ValueError(
                "Must provide either 'composition' or 'description' "
                "for generation operation"
            )


__all__ = ["AIGeneration"]
