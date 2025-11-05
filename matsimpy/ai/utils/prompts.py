"""
Prompt templates for AI operations.

Provides pre-formatted prompt templates for various AI operations.
"""

from typing import Dict, Any, Optional


def get_generation_prompt(composition: str, 
                         constraints: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate prompt for structure generation.
    
    Args:
        composition: Chemical formula
        constraints: Optional constraints
    
    Returns:
        Formatted prompt string
    """
    prompt = f"Generate a crystal structure for {composition}."
    
    if constraints:
        if "space_group" in constraints:
            prompt += f" Space group: {constraints['space_group']}."
        if "lattice_params" in constraints:
            prompt += f" Lattice parameters: {constraints['lattice_params']}."
        if "density" in constraints:
            prompt += f" Target density: {constraints['density']} g/cm³."
    
    prompt += " Return the structure in JSON format with species, positions, and lattice vectors."
    
    return prompt


def get_prediction_prompt(property_name: str, structure_info: str) -> str:
    """
    Generate prompt for property prediction.
    
    Args:
        property_name: Name of property to predict
        structure_info: Structure information (formula, composition, etc.)
    
    Returns:
        Formatted prompt string
    """
    return (
        f"Predict the {property_name} for the following structure: {structure_info}. "
        f"Return the value in appropriate units."
    )


def get_analysis_prompt(analysis_type: str, structure_info: str) -> str:
    """
    Generate prompt for structure analysis.
    
    Args:
        analysis_type: Type of analysis
        structure_info: Structure information
    
    Returns:
        Formatted prompt string
    """
    prompts = {
        "stability": f"Analyze the stability of: {structure_info}. Assess formation energy, phase stability, and potential issues.",
        "symmetry": f"Analyze the symmetry of: {structure_info}. Identify space group, point group, and symmetry operations.",
        "properties": f"Comprehensively analyze the properties of: {structure_info}. Include electronic, mechanical, and thermal properties.",
        "defects": f"Analyze potential defects in: {structure_info}. Identify common defect types and their energies.",
    }
    
    return prompts.get(analysis_type, f"Analyze the structure: {structure_info}.")


def get_optimization_prompt(property_name: str,
                           target_value: Optional[float] = None,
                           maximize: bool = True) -> str:
    """
    Generate prompt for structure optimization.
    
    Args:
        property_name: Property to optimize
        target_value: Target value (if specified)
        maximize: Whether to maximize or minimize
    
    Returns:
        Formatted prompt string
    """
    direction = "maximize" if maximize else "minimize"
    
    if target_value:
        prompt = (
            f"Optimize the structure to achieve {property_name} = {target_value}."
        )
    else:
        prompt = (
            f"Optimize the structure to {direction} {property_name}."
        )
    
    prompt += " Suggest modifications to lattice parameters, atomic positions, or composition."
    
    return prompt


def get_validation_prompt(structure_info: str) -> str:
    """
    Generate prompt for structure validation.
    
    Args:
        structure_info: Structure information
    
    Returns:
        Formatted prompt string
    """
    return (
        f"Validate the structure: {structure_info}. "
        "Check for common issues like: unreasonably short bonds, "
        "incorrect coordination numbers, symmetry inconsistencies, "
        "or physically unrealistic parameters. Return validation results."
    )


__all__ = [
    'get_generation_prompt',
    'get_prediction_prompt',
    'get_analysis_prompt',
    'get_optimization_prompt',
    'get_validation_prompt',
]

