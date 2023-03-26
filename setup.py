from setuptools import setup, find_packages

setup(
    name="MatSimPy",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "scipy",
        "monty"
    ],
    package_data={
        "matsimpy.core": ["periodic_table.json"],
        "tests": ["POSCAR-cart.vasp","POSCAR-frac.vasp"]
    },
    extras_require={
        "dev": [
            "pytest"
        ]
    },
    author="haidi wang",
    author_email="haidi@hfut.edu.cn",
    description="A package for materials simulation and analysis",
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
)

