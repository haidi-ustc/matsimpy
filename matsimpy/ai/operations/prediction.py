"""
AI-based property prediction operations.

Provides operations for predicting material properties using AI models.
"""

from typing import Dict, Any, Optional, List
from ..base import AIInterface, AIOperation
from ...core import Crystal, Molecule


class PropertyPrediction(AIOperation):
    """
    AI-based property prediction operation.
    
    Predicts material properties using AI models.
    Works with any AIInterface implementation (MCP, OpenAI, etc.).
    
    Examples:
        >>> from matsimpy.ai import MCPInterface, PropertyPrediction
        >>> 
        >>> mcp = MCPInterface(transport="stdio")
        >>> mcp.connect({"command": "python", "args": ["server.py"]})
        >>> 
        >>> pred = PropertyPrediction(mcp)
        >>> band_gap = pred.predict_band_gap(crystal)
        >>> formation_energy = pred.predict_formation_energy(crystal)
        >>> 
        >>> mcp.disconnect()
    """
    
    def predict_band_gap(self, crystal: Crystal) -> float:
        """
        Predict band gap using AI model.
        
        Args:
            crystal: Crystal structure
        
        Returns:
            Predicted band gap in eV
        """
        structure_data = self._format_structure(crystal)
        
        result = self.interface.call(
            operation="predict_band_gap",
            inputs={"structure": structure_data}
        )
        
        return float(result.get("band_gap", 0.0))
    
    def predict_formation_energy(self, crystal: Crystal) -> float:
        """
        Predict formation energy.
        
        Args:
            crystal: Crystal structure
        
        Returns:
            Predicted formation energy in eV/atom
        """
        structure_data = self._format_structure(crystal)
        
        result = self.interface.call(
            operation="predict_formation_energy",
            inputs={"structure": structure_data}
        )
        
        return float(result.get("formation_energy", 0.0))
    
    def predict_bulk_modulus(self, crystal: Crystal) -> float:
        """
        Predict bulk modulus.
        
        Args:
            crystal: Crystal structure
        
        Returns:
            Predicted bulk modulus in GPa
        """
        structure_data = self._format_structure(crystal)
        
        result = self.interface.call(
            operation="predict_bulk_modulus",
            inputs={"structure": structure_data}
        )
        
        return float(result.get("bulk_modulus", 0.0))
    
    def predict_properties(self, 
                          crystal: Crystal,
                          properties: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Predict multiple properties at once.
        
        Args:
            crystal: Crystal structure
            properties: List of properties to predict.
                       If None, predicts all available properties.
                       Options: 'band_gap', 'formation_energy', 'bulk_modulus', etc.
        
        Returns:
            Dictionary of property names to values
        """
        structure_data = self._format_structure(crystal)
        
        inputs = {"structure": structure_data}
        if properties:
            inputs["properties"] = properties
        
        result = self.interface.call(
            operation="predict_properties",
            inputs=inputs
        )
        
        return result.get("properties", {})
    
    def execute(self, **kwargs) -> Dict[str, float]:
        """
        Execute prediction operation.
        
        Args:
            **kwargs: Should include 'crystal' and optionally 'properties'
        
        Returns:
            Dictionary of predicted properties
        """
        crystal = kwargs.get("crystal")
        if not crystal:
            raise ValueError("Must provide 'crystal' for prediction")
        
        properties = kwargs.get("properties")
        return self.predict_properties(crystal, properties)
    
    def _format_structure(self, structure: Crystal) -> Dict[str, Any]:
        """
        Format structure for AI input.
        
        Args:
            structure: Crystal structure
        
        Returns:
            Dictionary representation
        """
        from ..utils.formatting import format_structure_for_ai
        
        return format_structure_for_ai(structure)


__all__ = ['PropertyPrediction']

