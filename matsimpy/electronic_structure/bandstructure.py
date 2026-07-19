"""Native electronic band-structure result objects."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from monty.json import MSONable, MontyDecoder

from matsimpy.core import Lattice
from matsimpy.electronic_structure.core import Spin


class Kpoint(MSONable):
    def __init__(self, coords, lattice, to_unit_cell=False, coords_are_cartesian=False, label=None):
        self._lattice = lattice
        values = np.asarray(coords, dtype=float)
        self._frac_coords = lattice.fractional_coords(values) if coords_are_cartesian else values.copy()
        if self._frac_coords.shape != (3,):
            raise ValueError("k-point coordinates must have shape (3,)")
        if to_unit_cell:
            self._frac_coords %= 1
        self._cart_coords = lattice.cartesian_coords(self._frac_coords)
        self._label = label

    def __str__(self):
        return f"{self.frac_coords} {self.cart_coords} {self.label}"

    def __eq__(self, other):
        return isinstance(other, Kpoint) and np.allclose(self.frac_coords, other.frac_coords) and np.allclose(self.lattice.matrix, other.lattice.matrix) and self.label == other.label

    @property
    def lattice(self): return self._lattice
    @property
    def label(self): return self._label
    @label.setter
    def label(self, value): self._label = value
    @property
    def frac_coords(self): return self._frac_coords.copy()
    @property
    def cart_coords(self): return self._cart_coords.copy()
    @property
    def a(self): return self._frac_coords[0]
    @property
    def b(self): return self._frac_coords[1]
    @property
    def c(self): return self._frac_coords[2]

    def as_dict(self):
        return {"@module": type(self).__module__, "@class": type(self).__name__,
                "lattice": self.lattice.as_dict(), "fcoords": self.frac_coords.tolist(),
                "ccoords": self.cart_coords.tolist(), "label": self.label}

    @classmethod
    def from_dict(cls, data):
        lattice = MontyDecoder().process_decoded(data["lattice"])
        return cls(data["fcoords"], lattice, label=data.get("label"))


class BandStructure(MSONable):
    def __init__(self, kpoints, eigenvals, lattice, efermi, labels_dict=None,
                 coords_are_cartesian=False, structure=None, projections=None):
        coords = [np.asarray(k, dtype=float) for k in kpoints]
        self.efermi = float(efermi)
        self.lattice_rec = lattice
        self.structure = structure
        self.labels_dict = {}
        labels_dict = labels_dict or {}
        self.kpoints = []
        for coords_i in coords:
            label = next((name for name, point in labels_dict.items()
                          if np.linalg.norm(coords_i - np.asarray(getattr(point, "frac_coords", point))) < 1e-4), None)
            kpoint = Kpoint(coords_i, lattice, label=label, coords_are_cartesian=coords_are_cartesian)
            self.kpoints.append(kpoint)
            if label is not None:
                self.labels_dict[label] = kpoint
        nkpoints = len(self.kpoints)
        self.bands = {Spin(int(spin)): np.asarray(values, dtype=float) for spin, values in eigenvals.items()}
        if not self.bands:
            raise ValueError("at least one spin channel is required")
        shapes = {values.shape for values in self.bands.values()}
        shape = next(iter(shapes))
        if len(shapes) != 1 or len(shape) != 2 or shape[1] != nkpoints:
            raise ValueError("every eigenvalue array must have shape (nbands, nkpoints)")
        self.nb_bands = shape[0]
        self.projections = {Spin(int(spin)): np.asarray(values, dtype=float) for spin, values in (projections or {}).items()}
        for spin, values in self.projections.items():
            if spin not in self.bands or values.ndim < 2 or values.shape[:2] != (self.nb_bands, nkpoints):
                raise ValueError("every projection array must have leading shape (nbands, nkpoints)")
        self.is_spin_polarized = len(self.bands) == 2

    @property
    def _efermi(self): return self.efermi
    @_efermi.setter
    def _efermi(self, value): self.efermi = float(value)

    def is_metal(self, efermi_tol=1e-4):
        return any(np.any(band < self.efermi - efermi_tol) and np.any(band > self.efermi + efermi_tol)
                   for values in self.bands.values() for band in values)

    def _edge(self, valence):
        if self.is_metal():
            return {"band_index": [], "kpoint_index": [], "kpoint": [], "energy": None, "projections": {}}
        candidates = []
        for spin, values in self.bands.items():
            mask = values <= self.efermi if valence else values > self.efermi
            for band_i, kpoint_i in zip(*np.where(mask)):
                candidates.append((float(values[band_i, kpoint_i]), spin, band_i, kpoint_i))
        if not candidates:
            return {"band_index": defaultdict(list), "kpoint_index": [], "kpoint": [], "energy": None, "projections": {}}
        energy, _, _, index = (max(candidates) if valence else min(candidates))
        point = self.kpoints[index]
        indices = [i for i, k in enumerate(self.kpoints) if point.label is not None and k.label == point.label] or [index]
        band_indices = defaultdict(list)
        for spin, values in self.bands.items():
            for band_i in range(self.nb_bands):
                if math.isclose(values[band_i, index], energy, abs_tol=1e-3, rel_tol=0):
                    band_indices[spin].append(band_i)
        projections = {spin: values[band_indices[spin][0], indices[0]] for spin, values in self.projections.items() if band_indices[spin]}
        return {"band_index": band_indices, "kpoint_index": indices, "kpoint": point, "energy": energy, "projections": projections}

    def get_vbm(self): return self._edge(True)
    def get_cbm(self): return self._edge(False)

    def get_band_gap(self):
        if self.is_metal():
            return {"energy": 0.0, "direct": False, "transition": None}
        vbm, cbm = self.get_vbm(), self.get_cbm()
        if vbm["energy"] is None or cbm["energy"] is None:
            return {"energy": 0.0, "direct": False, "transition": None}
        direct = np.linalg.norm(vbm["kpoint"].cart_coords - cbm["kpoint"].cart_coords) < .01
        def name(point):
            return point.label or f"({','.join(f'{v:.3f}' for v in point.frac_coords)})"
        return {"energy": cbm["energy"] - vbm["energy"], "direct": direct,
                "transition": f"{name(vbm['kpoint'])}-{name(cbm['kpoint'])}"}

    def as_dict(self):
        return {"@module": type(self).__module__, "@class": type(self).__name__,
                "lattice_rec": self.lattice_rec.as_dict(), "efermi": self.efermi,
                "kpoints": [k.frac_coords.tolist() for k in self.kpoints],
                "bands": {str(int(s)): v.tolist() for s, v in self.bands.items()},
                "labels_dict": {name: point.frac_coords.tolist() for name, point in self.labels_dict.items()},
                "is_spin_polarized": self.is_spin_polarized,
                "projections": {str(int(s)): v.tolist() for s, v in self.projections.items()},
                **({"structure": self.structure.as_dict()} if self.structure is not None else {})}

    @classmethod
    def from_dict(cls, data):
        decoder = MontyDecoder()
        lattice = decoder.process_decoded(data["lattice_rec"])
        structure = decoder.process_decoded(data["structure"]) if data.get("structure") else None
        return cls(data["kpoints"], data["bands"], lattice, data["efermi"],
                   {k.strip(): v for k, v in data.get("labels_dict", {}).items()}, structure=structure,
                   projections=data.get("projections"))


class BandStructureSymmLine(BandStructure):
    def __init__(self, kpoints, eigenvals, lattice, efermi, labels_dict,
                 coords_are_cartesian=False, structure=None, projections=None):
        super().__init__(kpoints, eigenvals, lattice, efermi, labels_dict,
                         coords_are_cartesian, structure, projections)
        self.distance, groups = [], []
        previous, distance, previous_label, group = self.kpoints[0], 0.0, self.kpoints[0].label, []
        for i, point in enumerate(self.kpoints):
            label = point.label
            distance = distance if label is not None and previous_label is not None else distance + np.linalg.norm(point.cart_coords - previous.cart_coords)
            self.distance.append(float(distance))
            # A repeated labelled point marks the boundary between two line
            # segments.  Distinct adjacent labelled points form a valid
            # two-point segment and must remain together.
            if (label is not None and previous_label is not None and group
                    and np.allclose(point.frac_coords, previous.frac_coords)):
                groups.append(group); group = []
            group.append(i)
            previous, previous_label = point, label
        if group: groups.append(group)
        self.branches = [{"start_index": g[0], "end_index": g[-1],
                          "name": f"{self.kpoints[g[0]].label}-{self.kpoints[g[-1]].label}"} for g in groups]

    def as_dict(self):
        data = super().as_dict(); data["branches"] = self.branches; return data


def get_reconstructed_band_structure(branches, efermi=None):
    if not branches:
        raise ValueError("at least one band-structure branch is required")
    reference = branches[0]
    spins = set(reference.bands)
    if any(set(branch.bands) != spins or branch.nb_bands != reference.nb_bands for branch in branches):
        raise ValueError("all branches must have identical spin channels and band counts")
    labels = {name: point.frac_coords for branch in branches for name, point in branch.labels_dict.items()}
    coords = [point.frac_coords for branch in branches for point in branch.kpoints]
    bands = {spin: np.concatenate([branch.bands[spin] for branch in branches], axis=1) for spin in spins}
    projections = {}
    if any(branch.projections for branch in branches):
        if any(set(branch.projections) != spins for branch in branches):
            raise ValueError("all branches must provide identical projection spin channels")
        projections = {spin: np.concatenate([branch.projections[spin] for branch in branches], axis=1) for spin in spins}
    return BandStructureSymmLine(coords, bands, reference.lattice_rec,
                                 reference.efermi if efermi is None else efermi, labels,
                                 structure=reference.structure, projections=projections)
