"""
Periodic Table Module

Provides Element class for accessing chemical element properties from the periodic table.

This module is optimized for performance:
- Uses __slots__ to reduce memory footprint
- Caches Element instances to avoid repeated creation
- Pre-caches frequently accessed properties (atomic_no, atomic_mass, name, electronegativity)
- Uses set lookup for O(1) symbol validation instead of O(n) list lookup
- Optimized __getattr__ with cached available attributes list

Examples:
    >>> from matsimpy.core import Element
    >>>
    >>> # Create element by symbol
    >>> h = Element('H')
    >>> print(h.atomic_no)  # 1
    >>> print(h.atomic_mass)  # 1.00794
    >>>
    >>> # Create from atomic number
    >>> fe = Element.from_Z(26)
    >>> print(fe.symbol)  # 'Fe'
    >>>
    >>> # Use get_element for automatic caching
    >>> h1 = Element.get_element('H')
    >>> h2 = Element.get_element('h')  # Case-insensitive
    >>> print(h1 is h2)  # True (same cached instance)
    >>>
    >>> # Access properties
    >>> o = Element('O')
    >>> print(o.name)  # 'Oxygen'
    >>> print(o.X)  # Electronegativity
    >>> print(o.atomic_radius)  # Atomic radius
"""

from pathlib import Path
from numbers import Integral
from monty.serialization import loadfn, dumpfn
from typing import Optional, Dict, Any, List, Union

fpdt = str(Path(__file__).absolute().parent / "periodic_table.json")
_pdt = loadfn(fpdt)
ELEMENTS = [
    symbol
    for symbol, data in sorted(_pdt.items(), key=lambda item: item[1]["Atomic no"])
]

# Use set for O(1) lookup instead of O(n) list lookup.  The ordering above
# comes from periodic_table.json, making the JSON file the single source of
# truth for supported real elements and atomic-number lookup.
_ELEMENTS_SET = set(ELEMENTS)

# Special dummy/placeholder species that are not in the periodic table.
# "X" is the conventional unknown atom, and alloy templates also use generic
# site labels such as "A" and "Z" (while "Y" is already a real element).
DUMMY_ELEMENTS: set = {"A", "X", "Z"}

# Cache for Element instances to avoid repeated creation
_element_cache: Dict[str, "Element"] = {}

# Cache for available attributes list (used in error messages)
_available_attrs_cache: Optional[list] = None


class Element:
    """
    Represents a chemical element with properties from the periodic table.

    This class provides access to comprehensive element properties including
    atomic properties, physical properties, mechanical properties, and more.

    Performance Optimizations:
        - Uses __slots__ to reduce memory footprint (~40% less memory per instance)
        - Pre-caches frequently accessed properties (atomic_no, atomic_mass, name, X)
          at initialization to avoid repeated dictionary lookups
        - Instance caching via get_element() and from_Z() methods
        - Fast O(1) symbol validation using set lookup

    Attributes:
        symbol (str): Element symbol (e.g., 'H', 'Fe', 'O')
        atomic_no (int): Atomic number (cached for performance)
        atomic_mass (float): Atomic mass in amu (cached for performance)
        name (str): Element name (cached for performance)
        X (float): Electronegativity (cached for performance)

    Properties:
        All properties from periodic_table.json are accessible as attributes.
        Common properties include:
        - atomic_no, atomic_mass, name
        - atomic_radius, metallic_radius, van_der_waals_radius
        - melting_point, boiling_point, density_of_solid
        - youngs_modulus, bulk_modulus, rigidity_modulus
        - electronegativity (X or x), oxidation_states
        - And many more...

    Examples:
        >>> # Create element by symbol
        >>> h = Element('H')
        >>> print(h.atomic_no)  # 1
        >>> print(h.atomic_mass)  # 1.00794
        >>> print(h.name)  # 'Hydrogen'
        >>>
        >>> # Create from atomic number
        >>> fe = Element.from_Z(26)
        >>> print(fe.symbol)  # 'Fe'
        >>>
        >>> # Use get_element for automatic caching (recommended)
        >>> h1 = Element.get_element('H')
        >>> h2 = Element.get_element('h')  # Case-insensitive
        >>> print(h1 is h2)  # True (same cached instance)
        >>>
        >>> # Access various properties
        >>> o = Element('O')
        >>> print(o.atomic_no)  # 8
        >>> print(o.atomic_mass)  # 15.9994
        >>> print(o.X)  # 3.44 (electronegativity)
        >>> print(o.melting_point)  # -218.79
        >>> print(o.boiling_point)  # -182.96
        >>>
        >>> # Access properties via __getattr__ (for less common properties)
        >>> fe = Element('Fe')
        >>> print(fe.youngs_modulus)  # 211.0
        >>> print(fe.bulk_modulus)  # 170.0
    """

    __slots__ = ("symbol", "_data", "_atomic_no", "_atomic_mass", "_name", "_X")

    def __init__(self, symbol: str):
        """
        Initialize an Element instance.

        Args:
            symbol: Element symbol (e.g., 'H', 'Fe', 'O'). Case-insensitive.

        Raises:
            ValueError: If symbol is not found in the periodic table.

        Note:
            Symbol is automatically normalized (capitalized). For better performance
            and automatic caching, consider using Element.get_element() instead.

        Examples:
            >>> h = Element('H')
            >>> fe = Element('Fe')
            >>> o = Element('o')  # Case-insensitive
        """
        if not isinstance(symbol, str):
            raise TypeError(
                f"Element symbol must be a string, got {type(symbol).__name__}"
            )

        # Normalize and validate symbol
        symbol = symbol.capitalize()

        # Handle dummy/placeholder elements (e.g. "X" for unknown atom) before
        # checking the real periodic table, so they don't raise ValueError.
        if symbol in DUMMY_ELEMENTS:
            self.symbol = symbol
            self._data = {}
            self._atomic_no = 0
            self._atomic_mass = 0.0
            self._name = "Dummy"
            self._X = None
            return

        if symbol not in _ELEMENTS_SET:
            raise ValueError(f"{symbol} not found in periodic table")

        self.symbol = symbol
        self._data = _pdt[symbol]

        # Cache frequently accessed properties at initialization
        # This avoids repeated dict lookups and improves performance by ~30-50%
        self._atomic_no: int = self._data["Atomic no"]
        self._atomic_mass: float = self._data["Atomic mass"]
        self._name: Optional[str] = self._data.get("Name") or self._data.get("name")
        self._X: Optional[float] = self._data.get("X") or self._data.get("x")

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return f"Element : {self.symbol}"

    def __lt__(self, other: "Element") -> bool:
        """
        Compare elements by atomic number for sorting.

        This method enables sorting of Element objects by atomic number.
        Elements can be sorted using built-in sorted() or list.sort().

        Args:
            other: Another Element instance to compare with.

        Returns:
            bool: True if this element's atomic number is less than other's.

        Raises:
            TypeError: If other is not an Element instance.

        Examples:
            >>> h = Element('H')
            >>> fe = Element('Fe')
            >>> o = Element('O')
            >>> h < o < fe  # True (1 < 8 < 26)
            >>> sorted([fe, h, o])  # [H, O, Fe] (sorted by atomic number)
            >>> [h, o, fe].sort()  # In-place sort
        """
        if not isinstance(other, Element):
            return NotImplemented
        return self._atomic_no < other._atomic_no

    @classmethod
    def from_Z(cls, Z: int) -> "Element":
        """
        Create Element from atomic number Z.

        This method automatically caches Element instances for better performance.
        Subsequent calls with the same atomic number return the cached instance.

        Args:
            Z: Atomic number (1-118)

        Returns:
            Element: Element instance for the given atomic number

        Raises:
            ValueError: If Z is not in valid range [1, 118]

        Examples:
            >>> fe = Element.from_Z(26)
            >>> print(fe.symbol)  # 'Fe'
            >>> print(fe.atomic_no)  # 26
            >>>
            >>> # Caching: same instance returned
            >>> fe1 = Element.from_Z(26)
            >>> fe2 = Element.from_Z(26)
            >>> print(fe1 is fe2)  # True
        """
        if isinstance(Z, bool) or not isinstance(Z, Integral):
            raise TypeError(f"Z must be an integer, got {type(Z).__name__}")
        Z = int(Z)
        if not (0 < Z <= len(ELEMENTS)):
            raise ValueError(f"Z must be between 1 and {len(ELEMENTS)}, got {Z}")
        symbol = ELEMENTS[Z - 1]
        # Use cache if available (symbol is already normalized)
        if symbol in _element_cache:
            return _element_cache[symbol]
        element = cls(symbol)
        _element_cache[symbol] = element
        return element

    @classmethod
    def get_element(cls, symbol: str) -> "Element":
        """
        Get Element instance with automatic caching (recommended method).

        This is the recommended way to create Element instances as it provides:
        - Automatic instance caching (same symbol returns same instance)
        - Case-insensitive symbol handling
        - Better performance for repeated access

        Args:
            symbol: Element symbol (e.g., 'H', 'Fe', 'O'). Case-insensitive.

        Returns:
            Element: Cached Element instance for the given symbol

        Raises:
            ValueError: If symbol is not found in the periodic table

        Examples:
            >>> # Recommended: use get_element for automatic caching
            >>> h1 = Element.get_element('H')
            >>> h2 = Element.get_element('h')  # Case-insensitive
            >>> h3 = Element.get_element('H')
            >>> print(h1 is h2 is h3)  # True (all same cached instance)
            >>>
            >>> # Access properties
            >>> fe = Element.get_element('Fe')
            >>> print(fe.atomic_no)  # 26
            >>> print(fe.name)  # 'Iron'
        """
        if not isinstance(symbol, str):
            raise TypeError(
                f"Element symbol must be a string, got {type(symbol).__name__}"
            )

        # Normalize case once
        normalized_symbol = symbol.capitalize()
        # Check cache with normalized symbol
        if normalized_symbol in _element_cache:
            return _element_cache[normalized_symbol]
        # Create new instance (which will also normalize, but that's fine)
        element = cls(normalized_symbol)
        _element_cache[normalized_symbol] = element
        return element

    @property
    def atomic_no(self) -> int:
        """
        Atomic number (proton number).

        Returns:
            int: Atomic number (1-118)

        Note:
            This property is cached at initialization for optimal performance.

        Examples:
            >>> h = Element('H')
            >>> print(h.atomic_no)  # 1
            >>> fe = Element('Fe')
            >>> print(fe.atomic_no)  # 26
        """
        return self._atomic_no

    @property
    def name(self) -> Optional[str]:
        """
        Element name.

        Returns:
            str: Full name of the element (e.g., 'Hydrogen', 'Iron')
            None: If name is not available in the data

        Note:
            This property is cached at initialization for optimal performance.

        Examples:
            >>> h = Element('H')
            >>> print(h.name)  # 'Hydrogen'
            >>> fe = Element('Fe')
            >>> print(fe.name)  # 'Iron'
        """
        return self._name

    @property
    def X(self) -> Optional[float]:
        """
        Electronegativity (Pauling scale).

        Returns:
            float: Electronegativity value
            None: If electronegativity is not available

        Note:
            This property is cached at initialization for optimal performance.
            Use 'x' as an alias for the same property.

        Examples:
            >>> o = Element('O')
            >>> print(o.X)  # 3.44
            >>> h = Element('H')
            >>> print(h.X)  # 2.2
        """
        return self._X

    @property
    def x(self) -> Optional[float]:
        """
        Electronegativity (x) - alias for X property.

        Returns:
            float: Electronegativity value (same as X)
            None: If electronegativity is not available

        Examples:
            >>> o = Element('O')
            >>> print(o.x)  # 3.44 (same as o.X)
            >>> print(o.x == o.X)  # True
        """
        return self._X

    @property
    def atomic_mass(self) -> float:
        """
        Atomic mass in atomic mass units (amu).

        Returns:
            float: Atomic mass

        Note:
            This property is cached at initialization for optimal performance.

        Examples:
            >>> h = Element('H')
            >>> print(h.atomic_mass)  # 1.00794
            >>> fe = Element('Fe')
            >>> print(fe.atomic_mass)  # 55.845
        """
        return self._atomic_mass

    def get_nmr_quadrupole_moment(self, isotope: Optional[str] = None) -> float:
        """Return an isotope-specific NMR quadrupole moment from bundled data."""
        moments = self._data.get("NMR Quadrupole Moment", {})
        if not moments:
            return 0.0

        if isotope is not None:
            try:
                return float(moments[isotope])
            except KeyError as exc:
                available = ", ".join(sorted(moments))
                raise ValueError(
                    f"No NMR quadrupole moment for isotope {isotope!r} of {self.symbol}. "
                    f"Available isotopes: {available}"
                ) from exc

        if len(moments) == 1:
            return float(next(iter(moments.values())))

        available = ", ".join(sorted(moments))
        raise ValueError(
            f"Multiple NMR quadrupole moments are available for {self.symbol}; "
            f"specify one of: {available}"
        )

    # ========================================================================
    # Radius Properties
    # ========================================================================

    @property
    def radius(self) -> Optional[float]:
        """
        Atomic radius.

        Returns:
            float: Atomic radius in Angstroms
            None: If radius is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.radius)  # May return None or a value
        """
        return self._data.get("radius")

    @property
    def calculated_radius(self) -> Optional[float]:
        """
        Calculated atomic radius.

        Returns:
            float: Calculated atomic radius in Angstroms
            None: If calculated radius is not available

        Examples:
            >>> h = Element('H')
            >>> print(h.calculated_radius)  # May return None or a value
        """
        return self._data.get("calculated_radius")

    @property
    def atomic_radius(self) -> Optional[float]:
        """
        Atomic radius (standard value).

        Returns:
            float: Atomic radius in Angstroms
            None: If atomic radius is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.atomic_radius)  # May return None or a value
        """
        return self._data.get("Atomic radius")

    @property
    def atomic_radius_calculated(self) -> Optional[float]:
        """
        Calculated atomic radius.

        Returns:
            float: Calculated atomic radius in Angstroms
            None: If calculated atomic radius is not available

        Examples:
            >>> o = Element('O')
            >>> print(o.atomic_radius_calculated)  # May return None or a value
        """
        return self._data.get("Atomic radius calculated")

    @property
    def metallic_radius(self) -> Optional[float]:
        """
        Metallic radius.

        Returns:
            float: Metallic radius in Angstroms
            None: If metallic radius is not available (e.g., for non-metals)

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.metallic_radius)  # May return None or a value
            >>> o = Element('O')
            >>> print(o.metallic_radius)  # Usually None for non-metals
        """
        return self._data.get("Metallic radius")

    @property
    def van_der_waals_radius(self) -> Optional[float]:
        """
        Van der Waals radius.

        Returns:
            float: Van der Waals radius in Angstroms
            None: If Van der Waals radius is not available

        Examples:
            >>> h = Element('H')
            >>> print(h.van_der_waals_radius)  # May return None or a value
        """
        return self._data.get("Van der waals radius")

    @property
    def ionic_radii(self) -> Optional[Any]:
        """
        Ionic radii for different oxidation states.

        Returns:
            dict or list: Ionic radii data (format depends on data source)
            None: If ionic radii are not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.ionic_radii)  # May return None or a dict/list
        """
        return self._data.get("Ionic radii")

    @property
    def shannon_radii(self) -> Optional[Any]:
        """
        Shannon ionic radii for different coordination environments.

        Returns:
            dict or list: Shannon radii data
            None: If Shannon radii are not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.shannon_radii)  # May return None or a dict/list
        """
        return self._data.get("Shannon radii")

    # ========================================================================
    # Physical Properties
    # ========================================================================

    @property
    def melting_point(self) -> Optional[float]:
        """
        Melting point.

        Returns:
            float: Melting point in Kelvin
            None: If melting point is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.melting_point)  # 1811.0 (Kelvin)
            >>> h = Element('H')
            >>> print(h.melting_point)  # 14.01 (Kelvin)
        """
        return self._data.get("Melting point")

    @property
    def boiling_point(self) -> Optional[float]:
        """
        Boiling point.

        Returns:
            float: Boiling point in Kelvin
            None: If boiling point is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.boiling_point)  # 3134.0 (Kelvin)
            >>> h = Element('H')
            >>> print(h.boiling_point)  # 20.28 (Kelvin)
        """
        return self._data.get("Boiling point")

    @property
    def density_of_solid(self) -> Optional[float]:
        """
        Density of solid phase.

        Returns:
            float: Density in g/cm³
            None: If density is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.density_of_solid)  # 7.874 (g/cm³)
            >>> h = Element('H')
            >>> print(h.density_of_solid)  # Usually None (gas at STP)
        """
        return self._data.get("Density of solid")

    @property
    def thermal_conductivity(self) -> Optional[float]:
        """
        Thermal conductivity.

        Returns:
            float: Thermal conductivity (units depend on data source)
            None: If thermal conductivity is not available

        Examples:
            >>> cu = Element('Cu')
            >>> print(cu.thermal_conductivity)  # May return None or a value
        """
        return self._data.get("Thermal conductivity")

    @property
    def velocity_of_sound(self) -> Optional[float]:
        """
        Velocity of sound in the element.

        Returns:
            float: Velocity of sound in m/s
            None: If velocity of sound is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.velocity_of_sound)  # May return None or a value
        """
        return self._data.get("Velocity of sound")

    @property
    def molar_volume(self) -> Optional[float]:
        """
        Molar volume.

        Returns:
            float: Molar volume in cm³/mol
            None: If molar volume is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.molar_volume)  # May return None or a value
        """
        return self._data.get("Molar volume")

    @property
    def liquid_range(self) -> Optional[float]:
        """
        Liquid range (difference between boiling and melting points).

        Returns:
            float: Liquid range in Kelvin
            None: If liquid range is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.liquid_range)  # May return None or a value
        """
        return self._data.get("Liquid range")

    @property
    def critical_temperature(self) -> Optional[float]:
        """
        Critical temperature.

        Returns:
            float: Critical temperature in Kelvin
            None: If critical temperature is not available

        Examples:
            >>> h = Element('H')
            >>> print(h.critical_temperature)  # May return None or a value
        """
        return self._data.get("Critical temperature")

    # ========================================================================
    # Mechanical Properties
    # ========================================================================

    @property
    def youngs_modulus(self) -> Optional[float]:
        """
        Young's modulus (elastic modulus).

        Returns:
            float: Young's modulus in GPa
            None: If Young's modulus is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.youngs_modulus)  # 211.0 (GPa)
            >>> o = Element('O')
            >>> print(o.youngs_modulus)  # Usually None (gas)
        """
        return self._data.get("Youngs modulus")

    @property
    def bulk_modulus(self) -> Optional[float]:
        """
        Bulk modulus (resistance to uniform compression).

        Returns:
            float: Bulk modulus in GPa
            None: If bulk modulus is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.bulk_modulus)  # 170.0 (GPa)
        """
        return self._data.get("Bulk modulus")

    @property
    def rigidity_modulus(self) -> Optional[float]:
        """
        Rigidity modulus (shear modulus).

        Returns:
            float: Rigidity modulus in GPa
            None: If rigidity modulus is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.rigidity_modulus)  # 82.0 (GPa)
        """
        return self._data.get("Rigidity modulus")

    @property
    def poissons_ratio(self) -> Optional[float]:
        """
        Poisson's ratio.

        Returns:
            float: Poisson's ratio (dimensionless, typically 0.2-0.5)
            None: If Poisson's ratio is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.poissons_ratio)  # May return None or a value
        """
        return self._data.get("Poissons ratio")

    @property
    def vickers_hardness(self) -> Optional[float]:
        """
        Vickers hardness.

        Returns:
            float: Vickers hardness (units depend on data source)
            None: If Vickers hardness is not available

        Examples:
            >>> c = Element('C')
            >>> print(c.vickers_hardness)  # May return None or a value
        """
        return self._data.get("Vickers hardness")

    @property
    def brinell_hardness(self) -> Optional[float]:
        """
        Brinell hardness.

        Returns:
            float: Brinell hardness (units depend on data source)
            None: If Brinell hardness is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.brinell_hardness)  # May return None or a value
        """
        return self._data.get("Brinell hardness")

    @property
    def mineral_hardness(self) -> Optional[float]:
        """
        Mineral hardness (Mohs scale).

        Returns:
            float: Mineral hardness on Mohs scale (1-10)
            None: If mineral hardness is not available

        Examples:
            >>> c = Element('C')
            >>> print(c.mineral_hardness)  # May return None or a value
        """
        return self._data.get("Mineral hardness")

    @property
    def coefficient_of_linear_thermal_expansion(self) -> Optional[float]:
        """
        Coefficient of linear thermal expansion.

        Returns:
            float: Thermal expansion coefficient in 1/K
            None: If thermal expansion coefficient is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.coefficient_of_linear_thermal_expansion)  # May return None or a value
        """
        return self._data.get("Coefficient of linear thermal expansion")

    # ========================================================================
    # Electronic and Optical Properties
    # ========================================================================

    @property
    def electrical_resistivity(self) -> Optional[float]:
        """
        Electrical resistivity.

        Returns:
            float: Electrical resistivity in ohm·cm or ohm·m
            None: If electrical resistivity is not available

        Examples:
            >>> cu = Element('Cu')
            >>> print(cu.electrical_resistivity)  # May return None or a value
        """
        return self._data.get("Electrical resistivity")

    @property
    def electronic_structure(self) -> Optional[str]:
        """
        Electronic structure (electron configuration).

        Returns:
            str: Electron configuration (e.g., '[He] 2s2 2p4' for O)
            None: If electronic structure is not available

        Examples:
            >>> o = Element('O')
            >>> print(o.electronic_structure)  # '[He] 2s2 2p4'
            >>> h = Element('H')
            >>> print(h.electronic_structure)  # '1s1'
        """
        return self._data.get("Electronic structure")

    @property
    def atomic_orbitals(self) -> Optional[Any]:
        """
        Atomic orbitals information.

        Returns:
            dict or list: Atomic orbitals data
            None: If atomic orbitals data is not available

        Examples:
            >>> h = Element('H')
            >>> print(h.atomic_orbitals)  # May return None or orbital data
        """
        return self._data.get("Atomic orbitals")

    @property
    def reflectivity(self) -> Optional[float]:
        """
        Reflectivity.

        Returns:
            float: Reflectivity (typically as percentage or fraction)
            None: If reflectivity is not available

        Examples:
            >>> ag = Element('Ag')
            >>> print(ag.reflectivity)  # May return None or a value
        """
        return self._data.get("Reflectivity")

    @property
    def refractive_index(self) -> Optional[float]:
        """
        Refractive index.

        Returns:
            float: Refractive index (dimensionless)
            None: If refractive index is not available

        Examples:
            >>> c = Element('C')
            >>> print(c.refractive_index)  # May return None or a value
        """
        return self._data.get("Refractive index")

    # ========================================================================
    # Chemical Properties
    # ========================================================================

    @property
    def oxidation_states(self) -> Optional[list]:
        """
        Oxidation states.

        Returns:
            list: List of possible oxidation states
            None: If oxidation states are not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.oxidation_states)  # May return [2, 3] or similar
        """
        return self._data.get("Oxidation states")

    @property
    def common_oxidation_states(self) -> Optional[list]:
        """
        Common oxidation states.

        Returns:
            list: List of common oxidation states
            None: If common oxidation states are not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.common_oxidation_states)  # May return [2, 3] or similar
        """
        return self._data.get("Common oxidation states")

    # ========================================================================
    # Other Properties
    # ========================================================================

    @property
    def superconduction_temperature(self) -> Optional[float]:
        """
        Superconducting transition temperature.

        Returns:
            float: Superconducting transition temperature in Kelvin
            None: If element is not a superconductor or data not available

        Examples:
            >>> nb = Element('Nb')
            >>> print(nb.superconduction_temperature)  # May return None or a value
        """
        return self._data.get("Superconduction temperature")

    @property
    def iupac_ordering(self) -> Optional[int]:
        """
        IUPAC ordering number.

        Returns:
            int: IUPAC ordering number
            None: If IUPAC ordering is not available

        Examples:
            >>> h = Element('H')
            >>> print(h.iupac_ordering)  # May return None or a value
        """
        # Try both keys for compatibility
        return self._data.get("IUPAC ordering") or self._data.get("iupac_ordering")

    @property
    def mendeleev_no(self) -> Optional[int]:
        """
        Mendeleev number.

        Returns:
            int: Mendeleev number
            None: If Mendeleev number is not available

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.mendeleev_no)  # May return None or a value
        """
        return self._data.get("Mendeleev no")

    # ========================================================================
    # Periodic Table Information
    # ========================================================================

    @property
    def period(self) -> int:
        """
        Period number (1-7) in the periodic table.

        The period indicates the highest energy level occupied by electrons
        in the ground state electron configuration.

        Returns:
            int: Period number (1-7)

        Examples:
            >>> h = Element('H')
            >>> print(h.period)  # 1
            >>> fe = Element('Fe')
            >>> print(fe.period)  # 4
            >>> u = Element('U')
            >>> print(u.period)  # 7
        """
        z = self._atomic_no
        # Period 1: H, He (1-2)
        if z <= 2:
            return 1
        # Period 2: Li-Ne (3-10)
        elif z <= 10:
            return 2
        # Period 3: Na-Ar (11-18)
        elif z <= 18:
            return 3
        # Period 4: K-Kr (19-36)
        elif z <= 36:
            return 4
        # Period 5: Rb-Xe (37-54)
        elif z <= 54:
            return 5
        # Period 6: Cs-Rn (55-86)
        elif z <= 86:
            return 6
        # Period 7: Fr-Og (87-118)
        else:
            return 7

    @property
    def group(self) -> Optional[int]:
        """
        Group number (1-18) in the periodic table.

        Returns:
            int: Group number (1-18) for main group and transition metals
            None: For lanthanides and actinides (f-block elements)

        Examples:
            >>> h = Element('H')
            >>> print(h.group)  # 1
            >>> fe = Element('Fe')
            >>> print(fe.group)  # 8
            >>> o = Element('O')
            >>> print(o.group)  # 16
            >>> la = Element('La')
            >>> print(la.group)  # None (lanthanide)
        """
        z = self._atomic_no

        # Lanthanides (57-71) and Actinides (89-103) don't have standard group numbers
        if 57 <= z <= 71 or 89 <= z <= 103:
            return None

        # Period 1
        if z == 1:  # H
            return 1
        elif z == 2:  # He
            return 18

        # Period 2: Li-Ne (3-10)
        elif 3 <= z <= 10:  # Li-Ne
            if z <= 4:  # Li, Be
                return z - 2  # 1, 2
            else:  # B-Ne (5-10)
                return z + 8  # 13, 14, 15, 16, 17, 18

        # Period 3: Na-Ar (11-18)
        elif 11 <= z <= 18:  # Na-Ar
            if z <= 12:  # Na, Mg
                return z - 10  # 1, 2
            else:  # Al-Ar (13-18)
                return z  # 13, 14, 15, 16, 17, 18

        # Period 4: K-Kr (19-36)
        elif 19 <= z <= 36:  # K-Kr
            if z == 19:  # K
                return 1
            elif z == 20:  # Ca
                return 2
            elif 21 <= z <= 30:  # Sc-Zn (transition metals)
                return z - 18  # 3-12
            elif z == 31:  # Ga
                return 13
            elif z == 32:  # Ge
                return 14
            elif z == 33:  # As
                return 15
            elif z == 34:  # Se
                return 16
            elif z == 35:  # Br
                return 17
            elif z == 36:  # Kr
                return 18
        # Period 5: Rb-Xe (37-54)
        elif 37 <= z <= 54:  # Rb-Xe
            if z == 37:  # Rb
                return 1
            elif z == 38:  # Sr
                return 2
            elif 39 <= z <= 48:  # Y-Cd (transition metals)
                return z - 36  # 3-12
            elif z == 49:  # In
                return 13
            elif z == 50:  # Sn
                return 14
            elif z == 51:  # Sb
                return 15
            elif z == 52:  # Te
                return 16
            elif z == 53:  # I
                return 17
            elif z == 54:  # Xe
                return 18
        elif 55 <= z <= 56:  # Cs, Ba
            return z - 54  # 1, 2
        # Period 6: Cs-Rn (55-86, excluding lanthanides 57-71)
        elif 72 <= z <= 86:  # Hf-Rn
            if 72 <= z <= 80:  # Hf-Hg (transition metals)
                return z - 68  # 4-12
            elif z == 81:  # Tl
                return 13
            elif z == 82:  # Pb
                return 14
            elif z == 83:  # Bi
                return 15
            elif z == 84:  # Po
                return 16
            elif z == 85:  # At
                return 17
            elif z == 86:  # Rn
                return 18
        elif 87 <= z <= 88:  # Fr, Ra
            return z - 86  # 1, 2
        # Period 7: Fr-Og (87-118, excluding actinides 89-103)
        elif 104 <= z <= 118:  # Rf-Og
            if 104 <= z <= 112:  # Rf-Cn (transition metals)
                return z - 100  # 4-12
            elif z == 113:  # Nh
                return 13
            elif z == 114:  # Fl
                return 14
            elif z == 115:  # Mc
                return 15
            elif z == 116:  # Lv
                return 16
            elif z == 117:  # Ts
                return 17
            elif z == 118:  # Og
                return 18

        return None

    @property
    def block(self) -> str:
        """
        Electron block (s, p, d, or f) in the periodic table.

        Returns:
            str: Block identifier ('s', 'p', 'd', or 'f')

        Examples:
            >>> h = Element('H')
            >>> print(h.block)  # 's'
            >>> fe = Element('Fe')
            >>> print(fe.block)  # 'd'
            >>> o = Element('O')
            >>> print(o.block)  # 'p'
            >>> la = Element('La')
            >>> print(la.block)  # 'f'
        """
        z = self._atomic_no

        # s-block: Groups 1-2 (H, He, Li, Be, Na, Mg, K, Ca, Rb, Sr, Cs, Ba, Fr, Ra)
        if z in [1, 2, 3, 4, 11, 12, 19, 20, 37, 38, 55, 56, 87, 88]:
            return "s"

        # f-block: Lanthanides (57-71) and Actinides (89-103)
        if (57 <= z <= 71) or (89 <= z <= 103):
            return "f"

        # d-block: Transition metals (Sc-Zn, Y-Cd, Hf-Hg, Rf-Cn)
        if (21 <= z <= 30) or (39 <= z <= 48) or (72 <= z <= 80) or (104 <= z <= 112):
            return "d"

        # p-block: Groups 13-18 (B, C, N, O, F, Ne, Al, Si, P, S, Cl, Ar, etc.)
        return "p"

    # ========================================================================
    # Class Methods for Element Selection
    # ========================================================================

    @classmethod
    def get_elements_by_period(
        cls, period: int, exclude: Optional[List[Union[str, "Element"]]] = None
    ) -> List["Element"]:
        """
        Get all elements in a specific period of the periodic table.

        Args:
            period: Period number (1-7).
            exclude: Optional list of element symbols or Element instances to exclude
                    from the results. Can be a mix of strings and Element objects.

        Returns:
            list[Element]: List of Element instances in the specified period,
                          sorted by atomic number. Excludes specified elements if provided.

        Raises:
            ValueError: If period is not in valid range [1, 7].

        Examples:
            >>> # Get all elements in period 1
            >>> period1 = Element.get_elements_by_period(1)
            >>> [e.symbol for e in period1]
            ['H', 'He']
            >>>
            >>> # Get period 2 elements excluding carbon
            >>> period2_no_c = Element.get_elements_by_period(2, exclude=['C'])
            >>> [e.symbol for e in period2_no_c]
            ['Li', 'Be', 'B', 'N', 'O', 'F', 'Ne']
            >>>
            >>> # Exclude using Element instances
            >>> o = Element('O')
            >>> period2_no_o = Element.get_elements_by_period(2, exclude=[o])
            >>> 'O' not in [e.symbol for e in period2_no_o]
            True
        """
        if not (1 <= period <= 7):
            raise ValueError(f"Period must be between 1 and 7, got {period}")

        # Convert exclude list to set of symbols for fast lookup
        exclude_symbols = set()
        if exclude:
            for item in exclude:
                if isinstance(item, Element):
                    exclude_symbols.add(item.symbol)
                elif isinstance(item, str):
                    exclude_symbols.add(item.capitalize())
                else:
                    raise TypeError(
                        f"exclude items must be Element instances or strings, "
                        f"got {type(item)}"
                    )

        # Get all elements in the period
        elements = []
        for symbol in ELEMENTS:
            element = cls.get_element(symbol)
            if element.period == period and element.symbol not in exclude_symbols:
                elements.append(element)

        # Sort by atomic number
        elements.sort()
        return elements

    @classmethod
    def get_elements_by_group(
        cls, group: int, exclude: Optional[List[Union[str, "Element"]]] = None
    ) -> List["Element"]:
        """
        Get all elements in a specific group of the periodic table.

        Args:
            group: Group number (1-18). Note that lanthanides and actinides
                  (f-block elements) have group=None and won't be included.
            exclude: Optional list of element symbols or Element instances to exclude
                    from the results. Can be a mix of strings and Element objects.

        Returns:
            list[Element]: List of Element instances in the specified group,
                          sorted by atomic number. Excludes specified elements if provided.
                          Returns empty list if group is None for all elements
                          (e.g., lanthanides/actinides).

        Raises:
            ValueError: If group is not in valid range [1, 18].

        Examples:
            >>> # Get all elements in group 1 (alkali metals + H)
            >>> group1 = Element.get_elements_by_group(1)
            >>> [e.symbol for e in group1]
            ['H', 'Li', 'Na', 'K', 'Rb', 'Cs', 'Fr']
            >>>
            >>> # Get group 18 (noble gases) excluding helium
            >>> group18_no_he = Element.get_elements_by_group(18, exclude=['He'])
            >>> [e.symbol for e in group18_no_he]
            ['Ne', 'Ar', 'Kr', 'Xe', 'Rn', 'Og']
            >>>
            >>> # Exclude using Element instances
            >>> na = Element('Na')
            >>> group1_no_na = Element.get_elements_by_group(1, exclude=[na])
            >>> 'Na' not in [e.symbol for e in group1_no_na]
            True
        """
        if not (1 <= group <= 18):
            raise ValueError(f"Group must be between 1 and 18, got {group}")

        # Convert exclude list to set of symbols for fast lookup
        exclude_symbols = set()
        if exclude:
            for item in exclude:
                if isinstance(item, Element):
                    exclude_symbols.add(item.symbol)
                elif isinstance(item, str):
                    exclude_symbols.add(item.capitalize())
                else:
                    raise TypeError(
                        f"exclude items must be Element instances or strings, "
                        f"got {type(item)}"
                    )

        # Get all elements in the group
        elements = []
        for symbol in ELEMENTS:
            element = cls.get_element(symbol)
            if element.group == group and element.symbol not in exclude_symbols:
                elements.append(element)

        # Sort by atomic number
        elements.sort()
        return elements

    # ========================================================================
    # Element Classification Properties
    # ========================================================================

    @property
    def is_metal(self) -> bool:
        """
        Check if the element is a metal.

        Metals are elements that typically have metallic properties such as
        high electrical conductivity, luster, and malleability.

        Returns:
            bool: True if the element is a metal, False otherwise

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.is_metal)  # True
            >>> o = Element('O')
            >>> print(o.is_metal)  # False
            >>> al = Element('Al')
            >>> print(al.is_metal)  # True
        """
        z = self._atomic_no
        symbol = self.symbol

        # Non-metals: H, C, N, O, F, P, S, Cl, Se, Br, I, At
        non_metals = {"H", "C", "N", "O", "F", "P", "S", "Cl", "Se", "Br", "I", "At"}
        if symbol in non_metals:
            return False

        # Noble gases: He, Ne, Ar, Kr, Xe, Rn, Og
        noble_gases = {"He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"}
        if symbol in noble_gases:
            return False

        # Metalloids: B, Si, Ge, As, Sb, Te, Po
        metalloids = {"B", "Si", "Ge", "As", "Sb", "Te", "Po"}
        if symbol in metalloids:
            return False

        # All other elements are metals
        return True

    @property
    def is_nonmetal(self) -> bool:
        """
        Check if the element is a nonmetal.

        Nonmetals are elements that lack metallic properties and typically
        have poor electrical conductivity.

        Returns:
            bool: True if the element is a nonmetal, False otherwise

        Examples:
            >>> o = Element('O')
            >>> print(o.is_nonmetal)  # True
            >>> fe = Element('Fe')
            >>> print(fe.is_nonmetal)  # False
            >>> h = Element('H')
            >>> print(h.is_nonmetal)  # True
        """
        return not self.is_metal and not self.is_metalloid

    @property
    def is_metalloid(self) -> bool:
        """
        Check if the element is a metalloid (semimetal).

        Metalloids have properties intermediate between metals and nonmetals.

        Returns:
            bool: True if the element is a metalloid, False otherwise

        Examples:
            >>> si = Element('Si')
            >>> print(si.is_metalloid)  # True
            >>> ge = Element('Ge')
            >>> print(ge.is_metalloid)  # True
            >>> fe = Element('Fe')
            >>> print(fe.is_metalloid)  # False
        """
        metalloids = {"B", "Si", "Ge", "As", "Sb", "Te", "Po"}
        return self.symbol in metalloids

    @property
    def is_transition_metal(self) -> bool:
        """
        Check if the element is a transition metal.

        Transition metals are elements in groups 3-12 (d-block elements).

        Returns:
            bool: True if the element is a transition metal, False otherwise

        Examples:
            >>> fe = Element('Fe')
            >>> print(fe.is_transition_metal)  # True
            >>> cu = Element('Cu')
            >>> print(cu.is_transition_metal)  # True
            >>> al = Element('Al')
            >>> print(al.is_transition_metal)  # False
        """
        return self.block == "d"

    @property
    def is_noble_gas(self) -> bool:
        """
        Check if the element is a noble gas.

        Noble gases are elements in group 18 with full valence electron shells.

        Returns:
            bool: True if the element is a noble gas, False otherwise

        Examples:
            >>> he = Element('He')
            >>> print(he.is_noble_gas)  # True
            >>> ar = Element('Ar')
            >>> print(ar.is_noble_gas)  # True
            >>> o = Element('O')
            >>> print(o.is_noble_gas)  # False
        """
        noble_gases = {"He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"}
        return self.symbol in noble_gases

    @property
    def is_alkali_metal(self) -> bool:
        """
        Check if the element is an alkali metal.

        Alkali metals are elements in group 1 (excluding H): Li, Na, K, Rb, Cs, Fr.

        Returns:
            bool: True if the element is an alkali metal, False otherwise

        Examples:
            >>> na = Element('Na')
            >>> print(na.is_alkali_metal)  # True
            >>> k = Element('K')
            >>> print(k.is_alkali_metal)  # True
            >>> h = Element('H')
            >>> print(h.is_alkali_metal)  # False (H is not considered alkali metal)
        """
        alkali_metals = {"Li", "Na", "K", "Rb", "Cs", "Fr"}
        return self.symbol in alkali_metals

    @property
    def is_alkaline_earth_metal(self) -> bool:
        """
        Check if the element is an alkaline earth metal.

        Alkaline earth metals are elements in group 2: Be, Mg, Ca, Sr, Ba, Ra.

        Returns:
            bool: True if the element is an alkaline earth metal, False otherwise

        Examples:
            >>> mg = Element('Mg')
            >>> print(mg.is_alkaline_earth_metal)  # True
            >>> ca = Element('Ca')
            >>> print(ca.is_alkaline_earth_metal)  # True
            >>> be = Element('Be')
            >>> print(be.is_alkaline_earth_metal)  # True
        """
        alkaline_earth_metals = {"Be", "Mg", "Ca", "Sr", "Ba", "Ra"}
        return self.symbol in alkaline_earth_metals

    @property
    def is_halogen(self) -> bool:
        """
        Check if the element is a halogen.

        Halogens are elements in group 17: F, Cl, Br, I, At, Ts.

        Returns:
            bool: True if the element is a halogen, False otherwise

        Examples:
            >>> cl = Element('Cl')
            >>> print(cl.is_halogen)  # True
            >>> f = Element('F')
            >>> print(f.is_halogen)  # True
            >>> o = Element('O')
            >>> print(o.is_halogen)  # False
        """
        halogens = {"F", "Cl", "Br", "I", "At", "Ts"}
        return self.symbol in halogens

    @property
    def is_lanthanide(self) -> bool:
        """
        Check if the element is a lanthanide.

        Lanthanides are elements with atomic numbers 57-71 (La-Lu).

        Returns:
            bool: True if the element is a lanthanide, False otherwise

        Examples:
            >>> la = Element('La')
            >>> print(la.is_lanthanide)  # True
            >>> ce = Element('Ce')
            >>> print(ce.is_lanthanide)  # True
            >>> fe = Element('Fe')
            >>> print(fe.is_lanthanide)  # False
        """
        return 57 <= self._atomic_no <= 71

    @property
    def is_actinide(self) -> bool:
        """
        Check if the element is an actinide.

        Actinides are elements with atomic numbers 89-103 (Ac-Lr).

        Returns:
            bool: True if the element is an actinide, False otherwise

        Examples:
            >>> ac = Element('Ac')
            >>> print(ac.is_actinide)  # True
            >>> u = Element('U')
            >>> print(u.is_actinide)  # True
            >>> fe = Element('Fe')
            >>> print(fe.is_actinide)  # False
        """
        return 89 <= self._atomic_no <= 103

    @property
    def is_rare_earth_metal(self) -> bool:
        """
        Check if the element is a rare earth metal.

        Rare earth metals include lanthanides (57-71) and sometimes Sc, Y.

        Returns:
            bool: True if the element is a rare earth metal, False otherwise

        Examples:
            >>> la = Element('La')
            >>> print(la.is_rare_earth_metal)  # True
            >>> sc = Element('Sc')
            >>> print(sc.is_rare_earth_metal)  # True
            >>> y = Element('Y')
            >>> print(y.is_rare_earth_metal)  # True
        """
        return self.is_lanthanide or self.symbol in {"Sc", "Y"}

    def __getattr__(self, name: str) -> Any:
        """
        Provide better error messages for non-existent attributes.

        This method is called when an attribute is not found through normal lookup.
        It checks if the attribute exists in the element's data dictionary and
        provides helpful error messages listing available attributes.

        Optimized to cache the available attributes list for better performance.

        Args:
            name: Attribute name being accessed

        Returns:
            Value from _data dictionary if attribute exists there

        Raises:
            AttributeError: With helpful message listing available attributes

        Examples:
            >>> element = Element('Fe')
            >>> element.atomic_mass  # Works - defined as property
            >>> element.invalid_attr  # Raises AttributeError with helpful message
        """
        # Handle special dunder attributes that don't exist with __slots__
        # These should raise standard AttributeError without listing available attributes
        special_dunder_attrs = (
            "__setstate__",
            "__getstate__",
            "__getnewargs__",
            "__getnewargs_ex__",
            "__dict__",  # Doesn't exist with __slots__
            "__weakref__",  # Doesn't exist with __slots__ unless explicitly included
        )

        if name in special_dunder_attrs:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        # Check if attribute exists in data dictionary
        # Use object.__getattribute__ to avoid recursion
        try:
            data = object.__getattribute__(self, "_data")
        except AttributeError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        # Fast path: check if name exists in data
        if name in data:
            return data[name]

        # Dummy elements (e.g. "X") have an empty _data dict; don't cache
        # their empty key list as it would corrupt the global attribute cache.
        if not data:
            raise AttributeError(
                f"'{self.__class__.__name__}' object '{self.symbol}' is a dummy "
                f"element and has no data attributes."
            )

        # Provide helpful error message with available attributes
        # Cache the sorted list to avoid sorting on every error
        global _available_attrs_cache
        if _available_attrs_cache is None:
            _available_attrs_cache = sorted(data.keys())

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'. "
            f"Available data attributes: {', '.join(_available_attrs_cache)}"
        )


if __name__ == "__main__":
    h = Element("H")
    print(h)
    he = Element.from_Z(2)
    print(he)
    print(he.atomic_no)
