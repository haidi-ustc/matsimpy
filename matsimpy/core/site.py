"""Immutable per-atom snapshots.

``Site`` (molecules) and ``CrystalSite`` (crystals) are detached, read-only
views of one atom.  They are produced by ``structure.sites`` / ``structure[i]``
and carry no link back to the structure; changing a structure is done through
the structure's own ``with_*`` / transformation API, never through a site.

``position`` is always Cartesian (Angstrom).  ``CrystalSite`` adds
``frac_position``, ``cart_position`` (== ``position``) and ``lattice``.

Example:
    >>> site = Site([0, 0, 0], "Fe")
    >>> site.position            # array([0., 0., 0.])
    >>> cs = CrystalSite([0.5, 0.5, 0.5], "Fe", Lattice.cubic(10.0))
    >>> cs.frac_position, cs.cart_position
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import numpy as np
from monty.json import MSONable

from ._validation import normalize_species
from .lattice import Lattice
from .periodic_table import Element
from ..utils.dict_utils import copy_properties


def _readonly(array: np.ndarray) -> np.ndarray:
    view = array.view()
    view.flags.writeable = False
    return view


def _validate_position(position: Union[List[float], np.ndarray]) -> np.ndarray:
    """Return a frozen float64 (3,) copy of *position*; reject bad input."""
    if isinstance(position, np.ndarray):
        if position.shape != (3,):
            raise ValueError(f"Position array must have shape (3,), got {position.shape}")
    elif isinstance(position, (list, tuple)):
        if len(position) != 3:
            raise ValueError("Position must have exactly three elements.")
        if not all(isinstance(c, (int, float, np.integer, np.floating)) for c in position):
            raise TypeError("Position elements must be integers or floats.")
    else:
        raise TypeError("Position must be a list or numpy array.")
    array = np.array(position, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise ValueError("Position coordinates must be finite numbers (no NaN or inf)")
    if np.any(np.abs(array) > 1e6):  # 1e6 Angstrom = 100 km: almost surely a unit error
        warnings.warn(
            f"Position coordinates seem unusually large: {array}. "
            "Values > 1e6 Angstroms may indicate an error.",
            UserWarning,
        )
    array.flags.writeable = False
    return array


class Site(MSONable):
    """One atom of a molecule: Cartesian position, species and properties."""

    __slots__ = ("_position", "_specie", "_properties")

    def __init__(
        self,
        position: Union[List[float], np.ndarray],
        specie: Union[str, int, Element] = "X",
        properties: Optional[Dict[str, Any]] = None,
    ):
        object.__setattr__(self, "_position", _validate_position(position))
        object.__setattr__(self, "_specie", normalize_species(specie, none_as_dummy=True))
        object.__setattr__(self, "_properties", copy_properties(properties))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable; cannot set {name!r}")

    def __getstate__(self):
        return {name: getattr(self, name) for name in self._all_slots()}

    def __setstate__(self, state: Dict[str, Any]) -> None:
        for name, value in state.items():
            if isinstance(value, np.ndarray):
                value.flags.writeable = False
            object.__setattr__(self, name, value)

    @classmethod
    def _all_slots(cls):
        return [s for klass in cls.__mro__ for s in getattr(klass, "__slots__", ())]

    # -- accessors -----------------------------------------------------------

    @property
    def specie(self) -> str:
        return self._specie

    @property
    def position(self) -> np.ndarray:
        """Cartesian position (Angstrom), read-only."""
        return _readonly(self._position)

    @property
    def properties(self) -> Dict[str, Any]:
        """Deep copy of the per-site properties."""
        return copy_properties(self._properties)

    # -- serialization -------------------------------------------------------

    def as_dict(self) -> Dict[str, Any]:
        return {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "position": self._position.tolist(),
            "specie": self._specie,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Site":
        return cls(d["position"], d.get("specie", "X"), d.get("properties"))

    # -- dunder --------------------------------------------------------------

    def _props_suffix(self) -> str:
        return f", {self._properties}" if self._properties else ""

    def __repr__(self) -> str:
        return f"{self._specie} @ {self._position.tolist()} (cartesian){self._props_suffix()}"

    def __str__(self) -> str:
        props = f", properties={self._properties}" if self._properties else ""
        return f"Site(position={self._position.tolist()}, specie='{self._specie}'{props})"

    def __eq__(self, other: Any) -> bool:
        return (
            type(other) is type(self)
            and self._specie == other._specie
            and np.allclose(self._position, other._position)
            and self._properties == other._properties
        )

    __hash__ = None  # value object with float coordinates: compare, don't hash


class CrystalSite(Site):
    """One atom of a crystal: adds the lattice and fractional coordinates.

    ``position`` / ``cart_position`` are Cartesian, ``frac_position`` is
    fractional.  ``coords_are_cartesian`` only says how *position* is given to
    the constructor; it is not stored.
    """

    __slots__ = ("_frac_position", "_lattice")

    def __init__(
        self,
        position: Union[List[float], np.ndarray],
        specie: Union[str, int, Element],
        lattice: Union[List[List[float]], Lattice],
        properties: Optional[Dict[str, Any]] = None,
        coords_are_cartesian: bool = False,
    ):
        if isinstance(lattice, list):
            lattice = Lattice(lattice)
        elif not isinstance(lattice, Lattice):
            raise TypeError(f"Lattice must be Lattice object or list, got {type(lattice)}")
        given = _validate_position(position)
        if coords_are_cartesian:
            cart, frac = given, given @ lattice.inv_matrix
        else:
            frac, cart = given, given @ lattice.matrix
        super().__init__(cart, specie, properties)
        frac = np.array(frac, dtype=np.float64)
        frac.flags.writeable = False
        object.__setattr__(self, "_frac_position", frac)
        object.__setattr__(self, "_lattice", lattice)

    @classmethod
    def _snapshot(cls, specie: str, frac: np.ndarray, cart: np.ndarray, lattice: Lattice,
                  properties: Optional[Dict[str, Any]]) -> "CrystalSite":
        """Trusted fast path for ``Crystal.sites``: rows are already validated and frozen."""
        site = object.__new__(cls)
        for name, value in (("_specie", specie), ("_position", cart), ("_frac_position", frac),
                            ("_lattice", lattice), ("_properties", copy_properties(properties))):
            object.__setattr__(site, name, value)
        return site

    @property
    def lattice(self) -> Lattice:
        return self._lattice

    @property
    def frac_position(self) -> np.ndarray:
        return _readonly(self._frac_position)

    @property
    def cart_position(self) -> np.ndarray:
        return _readonly(self._position)

    def wrap(self) -> "CrystalSite":
        """Return a new site with fractional coordinates wrapped into [0, 1)."""
        return CrystalSite(self._frac_position % 1.0, self._specie, self._lattice, self._properties)

    def as_dict(self) -> Dict[str, Any]:
        d = super().as_dict()
        d["position"] = self._frac_position.tolist()
        d["lattice"] = self._lattice.as_dict()
        d["coords_are_cartesian"] = False
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrystalSite":
        if d.get("lattice") is None:
            raise ValueError("Lattice is required for CrystalSite")
        return cls(
            d["position"], d.get("specie", "X"), Lattice.from_dict(d["lattice"]),
            d.get("properties"), coords_are_cartesian=d.get("coords_are_cartesian", False),
        )

    def __repr__(self) -> str:
        return f"{self._specie} @ {self._frac_position.tolist()} (frac){self._props_suffix()}"

    def __str__(self) -> str:
        props = f", properties={self._properties}" if self._properties else ""
        return (
            f"CrystalSite(frac_position={self._frac_position.tolist()}, "
            f"specie='{self._specie}'{props}, lattice={self._lattice!r})"
        )

    def __eq__(self, other: Any) -> bool:
        return super().__eq__(other) and np.allclose(self._lattice.matrix, other._lattice.matrix)

    __hash__ = None
