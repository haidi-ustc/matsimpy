Contributing
============

Contributions are welcome! This document provides guidelines for contributing to MatSimPy.

Getting Started
---------------

1. Fork the repository
2. Clone your fork:

   .. code-block:: bash

      git clone https://gitee.com/your-username/MatSimPy.git
      cd MatSimPy

3. Create a branch for your changes:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

4. Install in development mode:

   .. code-block:: bash

      pip install -e .[dev]

5. Make your changes and add tests
6. Run tests:

   .. code-block:: bash

      pytest

7. Commit your changes:

   .. code-block:: bash

      git commit -am "Add feature: your feature description"

8. Push to your fork and create a pull request

Code Style
----------

* Follow PEP 8 style guide
* Use type hints where appropriate
* Write docstrings for all public functions and classes
* Use NumPy/Google style docstrings

Testing
-------

* Write tests for all new features
* Ensure all tests pass: ``pytest``
* Aim for high test coverage
* Use ``@unittest.skipUnless`` for optional dependencies

Documentation
-------------

* Update docstrings for any API changes
* Add examples to the documentation
* Update README.md if needed

Pull Request Process
--------------------

1. Ensure all tests pass
2. Update documentation as needed
3. Add a clear description of your changes
4. Reference any related issues

Thank you for contributing to MatSimPy!

