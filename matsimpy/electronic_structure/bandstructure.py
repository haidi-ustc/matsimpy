"""Native band-structure result containers."""

from __future__ import annotations

from typing import Any

import numpy as np
from monty.json import MSONable

from matsimpy.core import Crystal, Lattice

from .core import Spin


def _spin_from_key(key: Spin | str | int) -> Spin:
    if isinstance(key, Spin):
        return key
    if isinstance(key, str):
        return Spin[key]
    return Spin(key)


def _spin_array_map(values: dict[Spin | str | int, Any], name: str) -> dict[Spin, np.ndarray]:
    converted = {}
    for spin, array in values.items():
        converted[_spin_from_key(spin)] = np.asarray(array, dtype=float)
    if not converted:
        raise ValueError(f"{name} must contain at least one spin channel")
    return converted


def _spin_map_as_dict(values: dict[Spin, np.ndarray]) -> dict[str, Any]:
    return {spin.name: array.tolist() for spin, array in values.items()}


def _lattice_from_any(lattice: Lattice | dict[str, Any]) -> Lattice:
    if isinstance(lattice, Lattice):
        return lattice
    return Lattice.from_dict(lattice)


def _structure_from_any(structure: Any) -> Any:
    if isinstance(structure, dict) and structure.get("@class") == "Crystal":
        return Crystal.from_dict(structure)
    return structure


class BandStructure(MSONable):
    """Band eigenvalues on a k-point path."""

    def __init__(
        self,
        kpoints: Any,
        eigenvalues: dict[Spin | str | int, Any],
        lattice: Lattice | dict[str, Any],
        efermi: float,
        structure: Any = None,
        projections: dict[Spin | str | int, Any] | None = None,
    ):
        self.kpoints = np.asarray(kpoints, dtype=float)
        if self.kpoints.ndim != 2 or self.kpoints.shape[1] != 3:
            raise ValueError("BandStructure kpoints must have shape (nkpoints, 3)")

        self.lattice = _lattice_from_any(lattice)
        self.efermi = float(efermi)
        self.structure = structure
        self.bands = _spin_array_map(eigenvalues, "eigenvalues")
        self.projections = (
            _spin_array_map(projections, "projections") if projections is not None else None
        )
        self._validate_band_shapes()

    def _validate_band_shapes(self) -> None:
        nkpoints = len(self.kpoints)
        nbands = None
        for band in self.bands.values():
            if band.ndim != 2:
                raise ValueError("Band eigenvalues must have shape (nbands, nkpoints)")
            if band.shape[1] != nkpoints:
                raise ValueError("Band eigenvalue nkpoints must match kpoints length")
            if nbands is None:
                nbands = band.shape[0]
            elif band.shape[0] != nbands:
                raise ValueError("Band eigenvalue spin channels must share band count")

        if self.projections is None:
            return
        if set(self.projections) != set(self.bands):
            raise ValueError("Projection spin channels must match band spin channels")
        for spin, projection in self.projections.items():
            if projection.shape[:2] != self.bands[spin].shape:
                raise ValueError("Projection leading dimensions must match eigenvalues")

    def is_metal(self, tol: float = 1e-4) -> bool:
        for band in self.bands.values():
            band_mins = np.min(band, axis=1)
            band_maxes = np.max(band, axis=1)
            crosses = (band_mins <= self.efermi + tol) & (band_maxes >= self.efermi - tol)
            if np.any(crosses):
                return True
        return False

    def get_band_gap(self) -> dict[str, float]:
        if self.is_metal():
            return {"energy": 0.0}

        occupied = []
        unoccupied = []
        for band in self.bands.values():
            occupied.extend(band[band <= self.efermi].tolist())
            unoccupied.extend(band[band > self.efermi].tolist())

        if not occupied or not unoccupied:
            return {"energy": 0.0}
        return {"energy": float(min(unoccupied) - max(occupied))}

    def as_dict(self) -> dict[str, Any]:
        structure = (
            self.structure.as_dict()
            if hasattr(self.structure, "as_dict")
            else self.structure
        )
        data = {
            "@module": self.__class__.__module__,
            "@class": self.__class__.__name__,
            "kpoints": self.kpoints.tolist(),
            "eigenvalues": _spin_map_as_dict(self.bands),
            "lattice": self.lattice.as_dict(),
            "efermi": self.efermi,
            "structure": structure,
        }
        if self.projections is not None:
            data["projections"] = _spin_map_as_dict(self.projections)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BandStructure":
        return cls(
            data["kpoints"],
            data["eigenvalues"],
            data["lattice"],
            data["efermi"],
            structure=_structure_from_any(data.get("structure")),
            projections=data.get("projections"),
        )

    @classmethod
    def from_branches(
        cls,
        branches: list["BandStructure"],
        merged: dict[Spin, np.ndarray],
        efermi: float,
    ) -> "BandStructure":
        reference = branches[0]
        kpoints = np.concatenate([branch.kpoints for branch in branches], axis=0)
        projections = _merged_projections(branches)
        return cls(
            kpoints,
            merged,
            reference.lattice,
            efermi,
            structure=reference.structure,
            projections=projections,
        )


class BandStructureSymmLine(BandStructure):
    """Band structure on symmetry-line branches."""

    def __init__(
        self,
        kpoints: Any,
        eigenvalues: dict[Spin | str | int, Any],
        lattice: Lattice | dict[str, Any],
        efermi: float,
        labels_dict: dict[str, Any],
        structure: Any = None,
        projections: dict[Spin | str | int, Any] | None = None,
        branches: list[dict[str, Any]] | None = None,
    ):
        super().__init__(kpoints, eigenvalues, lattice, efermi, structure, projections)
        self.labels_dict = {
            str(label): np.asarray(kpoint, dtype=float).tolist()
            for label, kpoint in labels_dict.items()
        }
        self.branches = branches if branches is not None else self._make_branches()

    def _make_branches(self) -> list[dict[str, Any]]:
        if len(self.kpoints) == 0:
            return []
        start = _label_for_kpoint(self.kpoints[0], self.labels_dict)
        end = _label_for_kpoint(self.kpoints[-1], self.labels_dict)
        name = "-".join(label for label in (start, end) if label)
        return [{"start_index": 0, "end_index": len(self.kpoints) - 1, "name": name}]

    def as_dict(self) -> dict[str, Any]:
        data = super().as_dict()
        data["labels_dict"] = self.labels_dict
        data["branches"] = self.branches
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BandStructureSymmLine":
        return cls(
            data["kpoints"],
            data["eigenvalues"],
            data["lattice"],
            data["efermi"],
            data.get("labels_dict", {}),
            structure=_structure_from_any(data.get("structure")),
            projections=data.get("projections"),
            branches=data.get("branches"),
        )

    @classmethod
    def from_branches(
        cls,
        branches: list[BandStructure],
        merged: dict[Spin, np.ndarray],
        efermi: float,
    ) -> "BandStructureSymmLine":
        reference = branches[0]
        kpoints = np.concatenate([branch.kpoints for branch in branches], axis=0)
        labels_dict = {}
        branch_defs = []
        offset = 0
        for branch in branches:
            labels_dict.update(getattr(branch, "labels_dict", {}))
            length = len(branch.kpoints)
            for branch_def in getattr(branch, "branches", []):
                copied = dict(branch_def)
                copied["start_index"] = copied.get("start_index", 0) + offset
                copied["end_index"] = copied.get("end_index", length - 1) + offset
                branch_defs.append(copied)
            offset += length
        projections = _merged_projections(branches)
        return cls(
            kpoints,
            merged,
            reference.lattice,
            efermi,
            labels_dict,
            structure=reference.structure,
            projections=projections,
            branches=branch_defs,
        )


def _label_for_kpoint(kpoint: np.ndarray, labels_dict: dict[str, Any]) -> str | None:
    for label, labeled_kpoint in labels_dict.items():
        if np.allclose(kpoint, np.asarray(labeled_kpoint, dtype=float)):
            return label
    return None


def _merged_projections(branches: list[BandStructure]) -> dict[Spin, np.ndarray] | None:
    if all(branch.projections is None for branch in branches):
        return None
    if any(branch.projections is None for branch in branches):
        raise ValueError("All branches must provide projections when any branch does")
    reference = branches[0]
    return {
        spin: np.concatenate([branch.projections[spin] for branch in branches], axis=1)
        for spin in reference.bands
    }


def _validate_reconstructable(branches: list[BandStructure]) -> None:
    reference = branches[0]
    reference_spins = set(reference.bands)
    reference_nbands = {spin: band.shape[0] for spin, band in reference.bands.items()}
    for branch in branches[1:]:
        if branch.lattice != reference.lattice:
            raise ValueError("All band-structure branches must share a lattice")
        if set(branch.bands) != reference_spins:
            raise ValueError("All band-structure branches must share spin channels")
        for spin, band in branch.bands.items():
            if band.shape[0] != reference_nbands[spin]:
                raise ValueError("All band-structure branches must share band dimensions")


def get_reconstructed_band_structure(
    branches: list[BandStructure],
    efermi: float | None = None,
) -> BandStructure:
    if not branches:
        raise ValueError("At least one band-structure branch is required")
    _validate_reconstructable(branches)
    reference = branches[0]
    merged = {
        spin: np.concatenate([branch.bands[spin] for branch in branches], axis=1)
        for spin in reference.bands
    }
    cls = (
        BandStructureSymmLine
        if all(isinstance(branch, BandStructureSymmLine) for branch in branches)
        else BandStructure
    )
    return cls.from_branches(branches, merged, reference.efermi if efermi is None else efermi)
