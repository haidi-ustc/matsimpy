from pathlib import Path
from monty.serialization import loadfn, dumpfn

fpdt = str(Path(__file__).absolute().parent / "periodic_table.json")
_pdt = loadfn(fpdt)
ELEMENTS = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', \
         'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag',\
         'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb',\
         'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', \
         'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr']

class Element:

    def __init__(self, symbol: str):
        assert symbol in ELEMENTS, f"{symbol} not found in periodic table"
        self.symbol = symbol
        self._data = _pdt[symbol]

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return f"Element : {self.symbol}"

    @classmethod
    def from_Z(cls, Z):
        assert Z > 0 and Z <= len(ELEMENTS), f"Z must be between 1 and {len(ELEMENTS)}"
        return cls(ELEMENTS[Z-1])

    @property
    def atomic_no(self):
        return self._data['atomic_no']

    @property
    def name(self):
        return self._data['name']

    @property
    def X(self):
        return self._data['X']


    @property
    def radius(self):
        return self._data['radius']

    @property
    def calculated_radius(self):
        return self._data['calculated_radius']

    @property
    def shannon_radii(self):
        return self._data["Shannon radii"]

    @property
    def superconduction_temperature(self):
        return self._data["Superconduction temperature"]

    @property
    def thermal_conductivity(self):
        return self._data["Thermal conductivity"]

    @property
    def van_der_waals_radius(self):
        return self._data["Van der waals radius"]

    @property
    def velocity_of_sound(self):
        return self._data["Velocity of sound"]

    @property
    def vickers_hardness(self):
        return self._data["Vickers hardness"]

    @property
    def x(self):
        return self._data["X"]

    @property
    def youngs_modulus(self):
        return self._data["Youngs modulus"]

    @property
    def metallic_radius(self):
        return self._data["Metallic radius"]

    @property
    def iupac_ordering(self):
        return self._data["iupac_ordering"]

    @property
    def iupac_ordering(self):
        return self._data["IUPAC ordering"]

    @property
    def atomic_mass(self):
        return self._data["Atomic mass"]


    @property
    def atomic_orbitals(self):
        return self._data["Atomic orbitals"]

    @property
    def atomic_radius(self):
        return self._data["Atomic radius"]

    @property
    def atomic_radius_calculated(self):
        return self._data["Atomic radius calculated"]

    @property
    def boiling_point(self):
        return self._data["Boiling point"]

    @property
    def brinell_hardness(self):
        return self._data["Brinell hardness"]

    @property
    def bulk_modulus(self):
        return self._data["Bulk modulus"]

    @property
    def coefficient_of_linear_thermal_expansion(self):
        return self._data["Coefficient of linear thermal expansion"]

    @property
    def common_oxidation_states(self):
        return self._data["Common oxidation states"]

    @property
    def critical_temperature(self):
        return self._data["Critical temperature"]

    @property
    def density_of_solid(self):
        return self._data["Density of solid"]

    @property
    def electrical_resistivity(self):
        return self._data["Electrical resistivity"]

    @property
    def electronic_structure(self):
        return self._data["Electronic structure"]

    @property
    def ionic_radii(self):
        return self._data["Ionic radii"]

    @property
    def liquid_range(self):
        return self._data["Liquid range"]

    @property
    def melting_point(self):
        return self._data["Melting point"]

    @property
    def mendeleev_no(self):
        return self._data["Mendeleev no"]

    @property
    def mineral_hardness(self):
        return self._data["Mineral hardness"]

    @property
    def molar_volume(self):
        return self._data["Molar volume"]

    @property
    def name(self):
        return self._data["Name"]

    @property
    def oxidation_states(self):
        return self._data["Oxidation states"]

    @property
    def poissons_ratio(self):
        return self._data["Poissons ratio"]

    @property
    def reflectivity(self):
        return self._data["Reflectivity"]

    @property
    def refractive_index(self):
        return self._data["Refractive index"]

    @property
    def rigidity_modulus(self):
        return self._data["Rigidity modulus"]

if __name__ == '__main__':
    h=Element('H')
    print(h)
    he=Element.from_Z(2)
    print(he)

    
