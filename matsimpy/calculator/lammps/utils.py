"""LAMMPS utilities — adapted from pymatgen (https://pymatgen.org/).
Original: pymatgen.io.lammps.utils
Copyright (c) pymatgen Development Team. MIT License.

Only ``LammpsRunner`` is provided.  The pymatgen ``Polymer`` and
``PackmolRunner`` helpers relied on mutable SiteCollection APIs and never ran
under MatSimPy's immutable structures; they were removed in 0.8.6.
"""

from __future__ import annotations

import logging
from shutil import which
from subprocess import PIPE, Popen

__author__ = "Kiran Mathew, Brandon Wood, Michael Humbert"
__email__ = "kmathew@lbl.gov"

logger = logging.getLogger(__name__)


class LammpsRunner:
    """LAMMPS wrapper."""

    def __init__(self, input_filename: str = "lammps.in", bin: str = "lammps") -> None:  # noqa: A002
        """
        Args:
            input_filename (str): input file name
            bin (str): command to run, excluding the input file name.
        """
        self.lammps_bin = bin.split()
        if not which(self.lammps_bin[-1]):
            raise RuntimeError(
                f"LammpsRunner requires the executable {self.lammps_bin[-1]} to be in the path. "
                "Please download and install LAMMPS from "
                "https://www.lammps.org/. "
                "Don't forget to add the binary to your path"
            )
        self.input_filename = input_filename

    def run(self) -> tuple[bytes, bytes]:
        """Write the input/data files and run LAMMPS."""
        lammps_cmd = [*self.lammps_bin, "-in", self.input_filename]
        logger.info(f"Running: {' '.join(lammps_cmd)}")
        with Popen(lammps_cmd, stdout=PIPE, stderr=PIPE) as process:
            stdout, stderr = process.communicate()
        return stdout, stderr


__all__ = ["LammpsRunner"]
