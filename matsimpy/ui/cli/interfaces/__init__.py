"""
Interface registry for CLI interfaces.
This module automatically discovers and registers all available interfaces.
"""

import pkgutil
import importlib
from typing import Dict, Callable

# Registry to store all available interfaces
INTERFACE_REGISTRY: Dict[str, Callable] = {}

def discover_interfaces() -> Dict[str, Callable]:
    """
    Automatically discover and register all interfaces in this package.
    
    Returns:
        Dict[str, Callable]: Dictionary mapping interface codes to their main functions
    """
    package = __package__ or "matsimpy.ui.cli.interfaces"
    
    for _, name, _ in pkgutil.iter_modules(__path__):
        try:
            module = importlib.import_module(f"{package}.{name}")
            if hasattr(module, "INTERFACE_CODE") and hasattr(module, "main"):
                INTERFACE_REGISTRY[module.INTERFACE_CODE] = module.main
        except Exception as e:
            print(f"Warning: Failed to load interface {name}: {str(e)}")
    
    return INTERFACE_REGISTRY

def get_interface(code: str) -> Callable:
    """
    Get an interface function by its code.
    
    Args:
        code (str): The interface code (e.g. "[b161]")
        
    Returns:
        Callable: The interface's main function
        
    Raises:
        KeyError: If no interface is found for the given code
    """
    if not INTERFACE_REGISTRY:
        discover_interfaces()
    return INTERFACE_REGISTRY[code]

# Initialize registry on import
discover_interfaces() 