# MatSimPy Documentation Guide

Complete guide for building, maintaining, and contributing to MatSimPy's Sphinx documentation.

## Table of Contents

1. [Documentation Structure](#documentation-structure)
2. [Building Documentation](#building-documentation)
3. [Documentation Configuration](#documentation-configuration)
4. [Writing Documentation](#writing-documentation)
5. [Docstring Standards](#docstring-standards)
6. [Adding New Documentation](#adding-new-documentation)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Documentation Structure

### Directory Layout

```
docs/
├── _build/              # Generated documentation (gitignored)
├── _static/             # Static files (CSS, JS, images)
├── _templates/          # Custom Sphinx templates
├── api_reference/       # API reference documentation
│   ├── index.rst
│   ├── core.rst
│   ├── builders.rst
│   ├── calculator.rst
│   ├── transformation.rst
│   ├── io.rst
│   ├── symmetry.rst
│   ├── config.rst
│   ├── storage.rst
│   └── utils.rst
├── user_guide/          # User guide documentation
│   ├── index.rst
│   ├── core_structures.rst
│   ├── builders.rst
│   ├── transformations.rst
│   ├── calculators.rst
│   ├── io.rst
│   ├── symmetry.rst
│   ├── configuration.rst
│   └── storage.rst
├── conf.py              # Sphinx configuration
├── index.rst            # Main documentation entry point
├── installation.rst      # Installation guide
├── quickstart.rst        # Quick start guide
├── examples.rst          # Examples overview
├── about.rst            # About MatSimPy
├── contributing.rst     # Contributing guidelines
├── changelog.rst        # Changelog
├── Makefile             # Makefile for building docs
└── make.bat             # Windows build script
```

### Documentation Types

1. **User Guide** (`user_guide/`): Conceptual documentation with usage examples
   - Focus on "how to use" rather than API details
   - Include code examples and explanations
   - Link to API reference for detailed documentation

2. **API Reference** (`api_reference/`): Complete API documentation
   - Auto-generated from docstrings using `autodoc`
   - Comprehensive coverage of all classes, methods, and functions
   - Technical details and parameter specifications

3. **Getting Started** (`installation.rst`, `quickstart.rst`): Entry points for new users

4. **Project Information** (`about.rst`, `contributing.rst`, `changelog.rst`): Project metadata

---

## Building Documentation

### Prerequisites

Install Sphinx and the theme:

```bash
pip install sphinx sphinx-rtd-theme
```

Or install all development dependencies:

```bash
pip install -e .[dev]
```

### Building HTML Documentation

**Using Make (Linux/macOS):**

```bash
cd docs
make html
```

**Using sphinx-build directly:**

```bash
cd docs
sphinx-build -b html . _build/html
```

**Using Python:**

```bash
cd docs
python -m sphinx -b html . _build/html
```

### Building Other Formats

```bash
# PDF (requires LaTeX)
make latexpdf

# EPUB
make epub

# Single HTML file
make singlehtml
```

### Viewing Documentation

After building, open `docs/_build/html/index.html` in your browser.

### Clean Build

To remove all generated files and rebuild:

```bash
make clean
make html
```

Or:

```bash
rm -rf docs/_build
make html
```

---

## Documentation Configuration

### Sphinx Configuration (`conf.py`)

Key configuration sections:

#### Project Information

```python
project = 'MatSimPy'
copyright = '2025, haidi wang'
author = 'haidi wang'
release = '0.1.0'
```

#### Extensions

```python
extensions = [
    'sphinx.ext.autodoc',      # Auto-generate docs from docstrings
    'sphinx.ext.autosummary',   # Generate summary tables
    'sphinx.ext.viewcode',      # Link to source code
    'sphinx.ext.napoleon',      # Google/NumPy style docstrings
    'sphinx.ext.intersphinx',   # Link to external docs
    'sphinx.ext.mathjax',       # Math rendering
]
```

#### Theme

```python
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme
```

#### Autodoc Settings

```python
autodoc_default_options = {
    'members': True,              # Include class members
    'member-order': 'bysource',   # Order by source code order
    'special-members': '__init__', # Include special members
    'undoc-members': True,        # Include undocumented members
    'exclude-members': '__weakref__'  # Exclude specific members
}
```

#### Napoleon Settings (Google-style docstrings)

```python
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True
```

#### Intersphinx Mapping

Links to external documentation:

```python
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
}
```

#### Warning Suppression

```python
nitpicky = False
nitpick_ignore = [
    ('py:class', 'AtomSelection'),
    ('py:class', 'Calculator'),
    ('py:obj', 'Calculator'),
]

suppress_warnings = [
    'ref.python',  # Suppress cross-reference ambiguity warnings
]
```

---

## Writing Documentation

### reStructuredText (RST) Syntax

#### Headers

```rst
Level 1 Header
==============

Level 2 Header
--------------

Level 3 Header
~~~~~~~~~~~~~~
```

#### Code Blocks

```rst
.. code-block:: python

    from matsimpy.core import Crystal, Lattice
    
    crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], 
                      Lattice.cubic(5.64))
```

#### Cross-References

```rst
:class:`~matsimpy.core.crystal.Crystal`
:func:`~matsimpy.core.lattice.Lattice.cubic`
:doc:`installation`
:ref:`label-name`
```

#### Lists

```rst
- Item 1
- Item 2
  - Sub-item 2.1
  - Sub-item 2.2
- Item 3

1. Numbered item 1
2. Numbered item 2
3. Numbered item 3
```

#### Admonitions

```rst
.. note::
   This is a note.

.. warning::
   This is a warning.

.. tip::
   This is a tip.

.. important::
   This is important information.
```

#### Tables

```rst
+--------+--------+
| Header | Header |
+========+========+
| Cell   | Cell   |
+--------+--------+
| Cell   | Cell   |
+--------+--------+
```

#### Math

```rst
:math:`E = mc^2`

.. math::
   E = \frac{1}{2}mv^2
```

### User Guide Pages

User guide pages should:

1. **Focus on concepts and usage**, not API details
2. **Include practical examples** with explanations
3. **Link to API reference** for detailed documentation
4. **Use clear, descriptive headings**
5. **Include code examples** that users can copy and run

Example structure:

```rst
Feature Name
============

Brief introduction to the feature.

Basic Usage
-----------

.. code-block:: python

    # Example code here
    pass

Advanced Usage
--------------

More complex examples.

See Also
--------

- :doc:`../api_reference/feature` for complete API documentation
- :doc:`../user_guide/related_feature` for related features
```

### API Reference Pages

API reference pages use `automodule` directives:

```rst
Module Name
===========

.. automodule:: matsimpy.module.name
   :members:
   :undoc-members:
   :no-index:  # Use if module is also imported in __init__.py
```

**Important**: Use `:no-index:` for modules that are imported in parent `__init__.py` files to avoid duplicate object descriptions.

---

## Docstring Standards

### Google-Style Docstrings

MatSimPy uses Google-style docstrings with the following structure:

```python
def function_name(param1: Type, param2: Type) -> ReturnType:
    """
    Brief one-line description.
    
    Longer description if needed. Can span multiple lines and provide
    more context about what the function does, when to use it, etc.
    
    Args:
        param1: Description of param1.
        param2: Description of param2. Can be:
            - Option 1: Description
            - Option 2: Description
    
    Returns:
        Description of return value. Can be:
            - Type 1: Description
            - Type 2: Description
    
    Raises:
        ValueError: When this error occurs.
        TypeError: When this error occurs.
    
    Example:
        >>> from matsimpy.core import Crystal, Lattice
        >>> crystal = Crystal(['Na', 'Cl'], [[0, 0, 0], [0.5, 0.5, 0.5]], 
        ...                   Lattice.cubic(5.64))
        >>> crystal.formula
        'ClNa'
    """
    pass
```

### Class Docstrings

```python
class ClassName:
    """
    Brief one-line description.
    
    Longer description of the class, its purpose, and key features.
    
    Attributes:
        attr1: Description of attr1.
        attr2: Description of attr2.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
    
    Raises:
        ValueError: When this error occurs.
    
    Note:
        Important notes about the class.
    
    Example:
        >>> obj = ClassName(param1, param2)
        >>> obj.method()
    """
    pass
```

### Property Docstrings

```python
@property
def property_name(self) -> Type:
    """
    Brief description of the property.
    
    Returns:
        Description of the return value.
    
    Example:
        >>> obj.property_name
        value
    """
    return self._property
```

### Module Docstrings

```python
"""
Module name and purpose.

This module provides [description of what the module does].

The module includes:
- Feature 1
- Feature 2
- Feature 3

Example:
    >>> from matsimpy.module import Class
    >>> obj = Class()
"""
```

### Type Hints

Always include type hints for better documentation:

```python
from typing import List, Optional, Union, Dict, Tuple
import numpy as np

def function(
    param1: str,
    param2: Optional[int] = None,
    param3: Union[List[float], np.ndarray] = None
) -> Dict[str, float]:
    """Function with type hints."""
    pass
```

### Cross-References in Docstrings

Use fully qualified names to avoid ambiguity:

```python
"""
Returns:
    :obj:`~matsimpy.calculator.base.Calculator` or None: The calculator.
    
See Also:
    :class:`~matsimpy.core.crystal.Crystal`: Related class.
"""
```

---

## Adding New Documentation

### Adding a New User Guide Page

1. **Create the RST file** in `docs/user_guide/`:

```bash
touch docs/user_guide/new_feature.rst
```

2. **Write the content** following user guide standards

3. **Add to `user_guide/index.rst`**:

```rst
.. toctree::
   :maxdepth: 2

   core_structures
   builders
   new_feature  # Add here
   ...
```

### Adding a New API Reference Page

1. **Create the RST file** in `docs/api_reference/`:

```bash
touch docs/api_reference/new_module.rst
```

2. **Add automodule directive**:

```rst
New Module
==========

.. automodule:: matsimpy.new.module
   :members:
   :undoc-members:
   :no-index:  # If imported in __init__.py
```

3. **Add to `api_reference/index.rst`**:

```rst
.. toctree::
   :maxdepth: 2

   core
   builders
   new_module  # Add here
   ...
```

### Adding Documentation to Existing Code

1. **Add module-level docstring** at the top of the file:

```python
"""
Module description.

This module provides...
"""
```

2. **Add class docstrings**:

```python
class MyClass:
    """
    Class description.
    
    Attributes:
        attr: Description.
    """
    pass
```

3. **Add method/function docstrings**:

```python
def my_method(self, param: Type) -> ReturnType:
    """
    Method description.
    
    Args:
        param: Parameter description.
    
    Returns:
        Return value description.
    """
    pass
```

4. **Rebuild documentation**:

```bash
cd docs
make html
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "duplicate object description" Warnings

**Problem**: Objects are documented in multiple places.

**Solution**: 
- Use `:no-index:` on `automodule` directives for modules imported in `__init__.py`
- Remove redundant `automodule` directives from index pages

#### 2. "more than one target found for cross-reference" Warnings

**Problem**: Ambiguous cross-references (e.g., `Calculator` in multiple locations).

**Solution**:
- Use fully qualified names: `:obj:`~matsimpy.calculator.base.Calculator``
- Add to `nitpick_ignore` in `conf.py`
- Use `suppress_warnings = ['ref.python']` in `conf.py`

#### 3. "Bullet list ends without a blank line" Warnings

**Problem**: Missing blank line after bullet lists in docstrings.

**Solution**: Add a blank line after bullet lists:

```python
"""
Returns:
    Type: Description. Can be:
        - Option 1: Description
        - Option 2: Description

    Additional text here.
"""
```

#### 4. "Title underline too short" Warnings

**Problem**: Underline characters don't match title length.

**Solution**: Ensure underlines are at least as long as the title:

```rst
Correct Title
=============  # 13 characters, matches title length
```

#### 5. "Literal block expected" Warnings

**Problem**: Code block syntax error.

**Solution**: Use explicit `.. code-block::` directives:

```rst
.. code-block:: python

    code here
```

#### 6. Import Errors During Build

**Problem**: Sphinx can't import matsimpy modules.

**Solution**: 
- Ensure `sys.path` is set correctly in `conf.py`
- Install matsimpy in development mode: `pip install -e .`
- Check that all dependencies are installed

#### 7. Missing Images or Static Files

**Problem**: Images or CSS files not found.

**Solution**:
- Place files in `docs/_static/`
- Reference with: `.. image:: _static/image.png`
- Ensure `html_static_path = ['_static']` in `conf.py`

---

## Best Practices

### Documentation Writing

1. **Be Clear and Concise**: Write for your audience (users, not just developers)

2. **Use Examples**: Every feature should have at least one example

3. **Keep It Updated**: Update documentation when code changes

4. **Link Appropriately**: Use cross-references to connect related content

5. **Test Examples**: Ensure all code examples work correctly

### Docstring Guidelines

1. **Always Include Type Hints**: Makes documentation more useful

2. **Document All Parameters**: Even optional ones

3. **Include Examples**: Especially for complex functions

4. **Document Exceptions**: List all possible exceptions in `Raises` section

5. **Use Consistent Formatting**: Follow Google style consistently

### File Organization

1. **One Concept Per Page**: Keep pages focused

2. **Logical Grouping**: Group related content together

3. **Clear Navigation**: Use `toctree` effectively

4. **Consistent Naming**: Use clear, descriptive file names

### Maintenance

1. **Regular Reviews**: Review documentation periodically

2. **Version Control**: Track documentation changes in git

3. **Build Regularly**: Build docs locally before committing

4. **Check Warnings**: Fix warnings, don't ignore them

5. **User Feedback**: Incorporate user feedback into documentation

---

## Quick Reference

### Common RST Directives

```rst
.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   page1
   page2

.. automodule:: module.name
   :members:
   :undoc-members:

.. code-block:: python
   
   code here

.. note::
   Note text

.. warning::
   Warning text

.. image:: path/to/image.png
   :alt: Alt text
   :width: 500px
```

### Common Cross-Reference Roles

```rst
:class:`~matsimpy.core.crystal.Crystal`
:func:`~matsimpy.core.lattice.Lattice.cubic`
:meth:`~matsimpy.core.crystal.Crystal.get_potential_energy`
:attr:`~matsimpy.core.crystal.Crystal.volume`
:doc:`installation`
:ref:`label-name`
```

### Common Sphinx Build Commands

```bash
# Build HTML
make html
sphinx-build -b html . _build/html

# Clean and rebuild
make clean html

# Build with warnings as errors
make html SPHINXOPTS="-W"

# Build with keep-going (show all warnings)
make html SPHINXOPTS="-W --keep-going"

# Build PDF (requires LaTeX)
make latexpdf
```

---

## Additional Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Google Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [Napoleon Extension](https://sphinxcontrib-napoleon.readthedocs.io/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)

---

## Summary

This guide covers:

- ✅ Documentation structure and organization
- ✅ Building and viewing documentation
- ✅ Configuration options
- ✅ Writing standards (RST, docstrings)
- ✅ Adding new documentation
- ✅ Troubleshooting common issues
- ✅ Best practices

For questions or improvements to this guide, please open an issue or submit a pull request.

