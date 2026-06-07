"""MatterSim machine learning potential calculator.

Restored from v0.4 (commit 845e79e).
Uses M3GNet-based models for energy, force, and stress prediction.
Requires torch + torch_geometric for full functionality.
"""

try:
    from .calculator import Mattersim

    __all__ = ["Mattersim"]
except ImportError:
    __all__ = []
