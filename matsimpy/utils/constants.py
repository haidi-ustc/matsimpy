"""
Physical constants.

Constants used in materials simulation.
"""

# Physical constants (in SI units, converted for common use)
AVOGADRO = 6.02214076e23  # Avogadro's number
BOLTZMANN = 1.380649e-23  # Boltzmann constant (J/K)
PLANCK = 6.62607015e-34  # Planck constant (J·s)
ELECTRON_CHARGE = 1.602176634e-19  # Elementary charge (C)
BOHR_RADIUS = 5.29177210903e-11  # Bohr radius (m)
RYDBERG = 2.1798723611035e-18  # Rydberg constant (J)

# Conversion factors
ANGSTROM_TO_BOHR = 1.8897259886  # 1 Angstrom = X Bohr
BOHR_TO_ANGSTROM = 1.0 / ANGSTROM_TO_BOHR
EV_TO_JOULE = 1.602176634e-19  # 1 eV = X J
JOULE_TO_EV = 1.0 / EV_TO_JOULE

__all__ = [
    'AVOGADRO', 'BOLTZMANN', 'PLANCK', 'ELECTRON_CHARGE',
    'BOHR_RADIUS', 'RYDBERG',
    'ANGSTROM_TO_BOHR', 'BOHR_TO_ANGSTROM',
    'EV_TO_JOULE', 'JOULE_TO_EV'
]

