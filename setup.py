from setuptools import setup, find_packages
import os

# Read README for long description
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        long_description = f.read()

setup(
    name="MatSimPy",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "scipy",
        "monty",
        "tabulate"
    ],
    package_data={
        "matsimpy.core": ["periodic_table.json"],
        "matsimpy.ui.cli": ["matsimpy_menu.json"],
        "tests": ["POSCAR-cart.vasp","POSCAR-frac.vasp"]
    },
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov"
        ],
        "storage": [
            "maggma"
        ],
        "all": [
            "pytest",
            "pytest-cov",
            "maggma"
        ]
    },
    author="haidi wang",
    author_email="haidi@hfut.edu.cn",
    description="A package for materials simulation and analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitee.com/haidi-hfut/MatSimPy",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={
        "console_scripts": [
            "matsimpy=matsimpy.ui.cli.__main__:main",
        ],
    },
    python_requires=">=3.6",
)

