"""
AI-assisted analysis operations.

Provides operations for AI-assisted structure analysis and insights.
"""

from typing import Dict, Any, Optional, List
from ..base import AIInterface, AIOperation
from ...core import Crystal, Molecule


class AIAnalysis(AIOperation):
    """
    AI-assisted analysis operation.
    
    Provides AI-powered analysis and insights for structures.
    Works with any AIInterface implementation.
    
    Examples:
        >>> from matsimpy.ai import MCPInterface, AIAnalysis
        >>> 
        >>> mcp = MCPInterface(transport="stdio")
        >>> mcp.connect({"command": "python", "args": ["server.py"]})
        >>> 
        >>> analysis = AIAnalysis(mcp)
        >>> insights = analysis.analyze_structure(crystal)
        >>> suggestions = analysis.suggest_improvements(crystal)
        >>> 
        >>> mcp.disconnect()
    """
    
    def analyze_structure(self, 
                         structure: Crystal,
                         analysis_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze structure using AI.
        
        Args:
            structure: Crystal or Molecule structure
            analysis_type: Type of analysis ('stability', 'symmetry', 'properties', etc.)
                          If None, performs comprehensive analysis
        
        Returns:
            Analysis results dictionary
        """
        structure_data = self._format_structure(structure)
        
        inputs = {"structure": structure_data}
        if analysis_type:
            inputs["analysis_type"] = analysis_type
        
        result = self.interface.call(
            operation="analyze_structure",
            inputs=inputs
        )
        
        return result.get("analysis", {})
    
    def suggest_improvements(self, 
                            structure: Crystal,
                            target_property: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Suggest structure improvements using AI.
        
        Args:
            structure: Crystal structure
            target_property: Target property to optimize ('stability', 'band_gap', etc.)
        
        Returns:
            List of suggested modifications
        """
        structure_data = self._format_structure(structure)
        
        inputs = {"structure": structure_data}
        if target_property:
            inputs["target_property"] = target_property
        
        result = self.interface.call(
            operation="suggest_improvements",
            inputs=inputs
        )
        
        return result.get("suggestions", [])
    
    def compare_structures(self, 
                          structures: List[Crystal],
                          comparison_type: str = "properties") -> Dict[str, Any]:
        """
        Compare multiple structures using AI.
        
        Args:
            structures: List of crystal structures
            comparison_type: Type of comparison ('properties', 'stability', 'similarity')
        
        Returns:
            Comparison results
        """
        structures_data = [self._format_structure(s) for s in structures]
        
        result = self.interface.call(
            operation="compare_structures",
            inputs={
                "structures": structures_data,
                "comparison_type": comparison_type
            }
        )
        
        return result.get("comparison", {})
    
    def validate_structure(self, structure: Crystal) -> Dict[str, Any]:
        """
        Validate structure using AI.
        
        Checks for common issues, inconsistencies, or problems.
        
        Args:
            structure: Crystal structure
        
        Returns:
            Validation results with issues and recommendations
        """
        structure_data = self._format_structure(structure)
        
        result = self.interface.call(
            operation="validate_structure",
            inputs={"structure": structure_data}
        )
        
        return result.get("validation", {})
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute analysis operation.
        
        Args:
            **kwargs: Should include 'structure' and optionally 'analysis_type'
        
        Returns:
            Analysis results
        """
        structure = kwargs.get("structure")
        if not structure:
            raise ValueError("Must provide 'structure' for analysis")
        
        analysis_type = kwargs.get("analysis_type")
        return self.analyze_structure(structure, analysis_type)
    
    def _format_structure(self, structure: Crystal) -> Dict[str, Any]:
        """Format structure for AI input."""
        from ..utils.formatting import format_structure_for_ai
        
        return format_structure_for_ai(structure)


__all__ = ['AIAnalysis']

