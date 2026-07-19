"""Density-of-states result objects."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

import numpy as np
from monty.json import MSONable

from matsimpy.core import Crystal
from matsimpy.electronic_structure.core import Orbital, OrbitalType, Spin


def _add_densities(*density_maps):
    spins = set().union(*(densities.keys() for densities in density_maps))
    return {
        spin: sum((densities[spin] for densities in density_maps if spin in densities), start=0)
        for spin in spins
    }


def _orbital_type(orbital):
    if isinstance(orbital, OrbitalType):
        return orbital
    return OrbitalType[Orbital(orbital).name[0]]


class _SiteProjectedDos(Mapping):
    """Site-addressable view backed by indices because CrystalSite is unhashable."""

    def __init__(self, structure, values):
        self.structure = structure
        self._values = list(values)

    def _index(self, site):
        for index, candidate in enumerate(self.structure):
            if candidate == site:
                return index
        raise KeyError(site)

    def __getitem__(self, site):
        return self._values[self._index(site)]

    def __iter__(self):
        return iter(self.structure)

    def __len__(self):
        return len(self._values)

class Dos(MSONable):
    """A total or projected density of states on an energy grid."""

    def __init__(self, efermi, energies, densities):
        self.efermi = float(efermi)
        self.energies = np.asarray(energies, dtype=float)
        self.densities = {Spin(int(key)): np.asarray(values, dtype=float) for key, values in densities.items()}
        if self.energies.ndim != 1 or any(values.shape != self.energies.shape for values in self.densities.values()):
            raise ValueError("DOS energies and densities must be equal-length 1D arrays")

    def get_densities(self, spin=None):
        """Return one spin channel, or the sum of all channels."""
        if spin is not None:
            return self.densities[Spin(spin)]
        return sum(self.densities.values(), start=np.zeros_like(self.energies))

    def get_interpolated_value(self, energy):
        """Interpolate every spin density at ``energy``."""
        return {
            spin: float(np.interp(energy, self.energies, values))
            for spin, values in self.densities.items()
        }

    def get_cbm_vbm(self, tol=1e-4, abs_tol=False, spin=None):
        """Return the first occupied samples above and below the Fermi level."""
        densities = self.get_densities(spin)
        threshold = tol if abs_tol else tol * densities.sum() / max(len(densities), 1)
        occupied = densities > threshold
        below = self.energies[(self.energies <= self.efermi) & occupied]
        above = self.energies[(self.energies >= self.efermi) & occupied]
        if not len(below) or not len(above):
            return self.efermi, self.efermi
        return float(above.min()), float(below.max())

    def get_gap(self, tol=1e-4, abs_tol=False, spin=None):
        """Return the sampled DOS gap around the Fermi level."""
        cbm, vbm = self.get_cbm_vbm(tol=tol, abs_tol=abs_tol, spin=spin)
        return max(cbm - vbm, 0.0)

    def as_dict(self):
        return {
            "@module": type(self).__module__,
            "@class": type(self).__name__,
            "efermi": self.efermi,
            "energies": self.energies.tolist(),
            "densities": {str(int(spin)): values.tolist() for spin, values in self.densities.items()},
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["efermi"], data["energies"], data["densities"])


class CompleteDos(Dos):
    """A total DOS together with site- and orbital-projected densities."""

    def __init__(self, structure, total_dos, pdos, normalize=False):
        self.structure = structure
        factor = structure.volume if normalize else 1.0
        super().__init__(
            total_dos.efermi,
            total_dos.energies,
            {spin: values / factor for spin, values in total_dos.densities.items()},
        )
        source = [pdos[site] for site in structure] if isinstance(pdos, Mapping) else list(pdos)
        values = [
            {
                orbital: {
                    Spin(int(spin)): self._validated_projected_density(density, factor)
                    for spin, density in densities.items()
                }
                for orbital, densities in orbitals.items()
            }
            for orbitals in source
        ]
        if len(values) != len(structure):
            raise ValueError("CompleteDos requires one projected-DOS map per structure site")
        self.pdos = _SiteProjectedDos(structure, values)
        self.is_normalized = bool(normalize)
        self.norm_vol = structure.volume if normalize else None

    def _validated_projected_density(self, density, factor):
        values = np.asarray(density, dtype=float)
        if values.shape != self.energies.shape:
            raise ValueError("DOS energies and densities must be equal-length 1D arrays")
        return values / factor

    def get_normalized(self):
        """Return a volume-normalized copy, or this object if already normalized."""
        if self.is_normalized:
            return self
        return type(self)(self.structure, self, self.pdos, normalize=True)

    def get_site_orbital_dos(self, site, orbital):
        return Dos(self.efermi, self.energies, self.pdos[site][orbital])

    def get_site_dos(self, site):
        return Dos(self.efermi, self.energies, _add_densities(*self.pdos[site].values()))

    def get_site_spd_dos(self, site):
        grouped = defaultdict(list)
        for orbital, densities in self.pdos[site].items():
            grouped[_orbital_type(orbital)].append(densities)
        return {orbital: Dos(self.efermi, self.energies, _add_densities(*values)) for orbital, values in grouped.items()}

    def get_spd_dos(self):
        grouped = defaultdict(list)
        for orbitals in self.pdos.values():
            for orbital, densities in orbitals.items():
                grouped[_orbital_type(orbital)].append(densities)
        return {orbital: Dos(self.efermi, self.energies, _add_densities(*values)) for orbital, values in grouped.items()}

    def as_dict(self):
        data = super().as_dict()
        data.update({
            "structure": self.structure.as_dict(),
            "pdos": [
                {
                    str(int(orbital)): {
                        str(int(spin)): values.tolist() for spin, values in densities.items()
                    }
                    for orbital, densities in self.pdos[site].items()
                }
                for site in self.structure
            ],
            "orbital_types": [
                {str(int(orbital)): type(orbital).__name__ for orbital in self.pdos[site]}
                for site in self.structure
            ],
            "normalize": self.is_normalized,
        })
        return data

    @classmethod
    def from_dict(cls, data):
        structure_data = data["structure"]
        structure = structure_data if isinstance(structure_data, Crystal) else Crystal.from_dict(structure_data)
        total_dos = Dos(data["efermi"], data["energies"], data["densities"])
        pdos = []
        for index, orbital_map in enumerate(data["pdos"]):
            types = data["orbital_types"][index]
            pdos.append({
                (Orbital if types[key] == "Orbital" else OrbitalType)(int(key)): densities
                for key, densities in orbital_map.items()
            })
        # Serialized arrays already carry normalization, so do not divide twice.
        result = cls(structure, total_dos, pdos, normalize=False)
        result.is_normalized = bool(data.get("normalize", False))
        result.norm_vol = structure.volume if result.is_normalized else None
        return result
