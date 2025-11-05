"""
AI operations module.

Provides high-level operations that work with any AIInterface:
- generation: Structure generation
- (Future: prediction, analysis, optimization)
"""

from .generation import AIGeneration

__all__ = ['AIGeneration']

