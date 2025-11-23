"""
AI operations module.

Provides high-level operations that work with any AIInterface:
- generation: Structure generation
- prediction: Property prediction
- analysis: AI-assisted analysis
- optimization: Structure optimization
"""

from .generation import AIGeneration
from .prediction import PropertyPrediction
from .analysis import AIAnalysis
from .optimization import AIOptimization

__all__ = [
    "AIGeneration",
    "PropertyPrediction",
    "AIAnalysis",
    "AIOptimization",
]
