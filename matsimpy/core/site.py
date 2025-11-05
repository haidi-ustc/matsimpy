import numpy as np
from typing import List, Optional, Union
from monty.json import MSONable
from .lattice import Lattice
from .periodic_table import Element

class Site(MSONable):
    def __init__(self, position: Union[List[float],np.ndarray], 
            specie: Union[str, int, Element] = 'X' ,
            properties: Optional[dict] = None):
        self._position = self._validate_position(position)
        self._specie = self._validate_specie(specie)
        self._properties = self._validate_properties(properties)

    def as_dict(self):
        return {"position": self.position.tolist(), "specie": self.specie, "properties": self.properties}

    @classmethod
    def from_dict(cls, d):
        return cls(position=d["position"], specie=d.get("specie"), properties=d.get("properties"))

    def _validate_specie(self, specie: Optional[Union[str, int, Element]]) -> Optional[Union[str, int, Element]]:
        if specie is not None:
            if not isinstance(specie, (str, int, Element)):
                raise TypeError("Specie must be a string, integer, or Element object.")
            if isinstance(specie, int):
                return Element.from_Z(specie).symbol
            if isinstance(specie, str):
                return specie
            if isinstance(specie, Element):
                return specie.symbol

        return specie

    def _validate_properties(self, properties: Optional[dict]) -> dict:
        if properties is not None and not isinstance(properties, dict):
            raise TypeError("Properties must be a dictionary.")
        return properties or {}

    def _validate_position(self, position: Union[List[float],np.ndarray]) -> np.ndarray:
        
        if isinstance(position, np.ndarray):
            return position
        if not isinstance(position, list):
            raise TypeError("Position must be a list of floats.")
        if len(position) != 3:
            raise ValueError("Position must have three elements.")
        for coord in position:
            if not isinstance(coord, (int, float)):
                raise TypeError("Position elements must be integers or floats.")
        return np.array(position)

    @property
    def properties(self) -> dict:
        return self._properties

    @properties.setter
    def properties(self, properties: Optional[dict]) -> None:
        self._properties = self._validate_properties(properties)

    @property
    def specie(self) -> Union[str, int, Element]:
        return self._specie

    @specie.setter
    def specie(self, specie: Union[str, int, Element]) -> None:
        self._specie = self._validate_specie(specie)

    @property
    def position(self) -> np.ndarray:
        return np.array(self._position)

    @position.setter
    def position(self, position: List[float]) -> None:
        self._position = self._validate_position(position)

    def __repr__(self):
        return f"Site(position={self.position}, specie={self.specie}, properties={self.properties})"

    def __str__(self):
        return self.__repr__()

class CrystalSite(Site):
    def __init__(
        self,
        position: List[float],
        specie: Union[str, int, Element] ,
        lattice: Union[List[list[float]], Lattice],
        properties: Optional[dict] = None,
        coords_are_cartesian: bool = False
    ):
        self._lattice = self._validate_lattice(lattice)
       
        if coords_are_cartesian:
            self.cart_position = np.array(position)
            self.frac_position = self._convert_to_fractional()
        else:
            self.frac_position = np.array(position)
            self.cart_position = self._convert_to_cartesian()

        position = self.frac_position
        super().__init__(position, specie, properties)


    def as_dict(self):
        d = super().as_dict()
        d["@class"] = self.__class__.__name__
        d["@module"] = self.__class__.__module__
        d["lattice"] = self._lattice.as_dict()
        return d

    @classmethod
    def from_dict(cls, d):
        position = d["position"]
        specie = d.get("specie")
        properties = d.get("properties")
        lattice = Lattice.from_dict ( d.get("lattice") )
        return cls(position=position, specie=specie, properties=properties, lattice=lattice)

    def __repr__(self):
        return f"CrystalSite(position={self.position}, specie={self.specie}, properties={self.properties}, lattice={self.lattice})"

    def __str__(self):
        return f"{self.specie} @ {self.position} in {self.lattice}"

    def _validate_lattice(self, lattice: Union[List[List[float]],Lattice]) -> Lattice:

        if  isinstance(lattice, Lattice):
            return lattice

        if not isinstance(lattice, list):
            raise TypeError("Lattice must be a list of lists of floats.")
        if len(lattice) != 3:
            raise ValueError("Lattice must have three vectors.")
        for vector in lattice:
            if not isinstance(vector, list):
                raise TypeError("Lattice vectors must be lists of floats.")
            if len(vector) != 3:
                raise ValueError("Lattice vectors must have three elements.")
            for coord in vector:
                if not isinstance(coord, (int, float)):
                    raise TypeError("Lattice vector elements must be integers or floats.")
        return Lattice(lattice_vectors=lattice)

    @property
    def lattice(self) -> Lattice:
        return self._lattice

    @lattice.setter
    def lattice(self, lattice: Union[List[float],Lattice]) -> None:
        self._lattice = self._validate_lattice(lattice)

    def _convert_to_fractional(self) -> np.ndarray:
        """
        Get the fractional coordinates of the site in the unit cell.
        """
        return np.dot(self.cart_position, np.linalg.inv(self.lattice.matrix))

    def _convert_to_cartesian(self) -> np.ndarray:
        """
        Get the cartesian coordinates of the site.
        """
        return  np.dot(self.frac_position, self.lattice.matrix)
