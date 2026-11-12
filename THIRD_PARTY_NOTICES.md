# Third-party notices

## Historical pymatgen-derived calculator modules

The VASP modules `matsimpy/calculator/vasp/inputs.py`, `outputs.py`, and
`sets.py`, along with their package data, are historical adaptations that
predate the native-runtime work. Their source headers identify the upstream
`pymatgen.io.vasp` paths, pymatgen Development Team copyright, and MIT license.
The native-runtime work preserves those notices; it does not represent those
historical modules as newly original implementations.

Pymatgen is separately used as a black-box behavioral oracle by tests. That
testing role does not make pymatgen a production dependency and is not the
source of the new native electronic-structure or symmetry service
implementations.

## pymatgen test files

The VASP test fixtures in `tests/calculator/fixtures/vasp/` are unmodified
copies of files from the pymatgen 2026.10.24 test data (`test-files/io/vasp/`),
listed in that directory's `PROVENANCE.md`. pymatgen is copyright the pymatgen
Development Team and distributed under the MIT license. No real POTCAR files
are included; the POTCAR fixtures are pymatgen's placeholder ("FAKE") files.

## Atomic Simulation Environment (ASE) 3.29.0 lattice definitions

MatSimPy's `matsimpy/symmetry/kpath.py` narrowly adapts the Setyawan--
Curtarolo definitions of the 14 three-dimensional Bravais lattices and the
special points and paths of the five two-dimensional Bravais lattices (ASE
classes OBL, RECT, CRECT, SQR and HEX2D), as identified in that file's source
notice.

This ASE-derived k-path adaptation was added during the native-runtime work
and is distinct from the older pymatgen-derived VASP calculator modules. The
file-level notice records ASE version 3.29.0, the exact upstream source paths
and functions, the adapted scope, copyright, and BSD-2-Clause license.

Copyright (C) 2010--2025 the ASE developers.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
