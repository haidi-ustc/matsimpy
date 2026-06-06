"""Integration tests for cross-layer workflows.

Tests: builder → transformation → IO → storage round-trip.
"""

import tempfile
import pytest
from matsimpy.core import Crystal, Molecule, Lattice
from matsimpy.builders.bulk import from_prototype
from matsimpy.transformation.lattice import apply_strain
from matsimpy.transformation.atomic import create_vacancy
from matsimpy.transformation.chemical import substitute
from matsimpy.io import read, write
from matsimpy.storage import DataStorage, MemoryBackend


@pytest.fixture
def fcc_cu():
    return from_prototype('fcc', 'Cu', 3.61)


class TestBuilderTransformIOStorageWorkflow:

    def test_full_round_trip(self, fcc_cu, tmp_path):
        """builder → transform → IO → storage round-trip."""
        # 1. Transform
        strained = apply_strain(
            fcc_cu,
            [[0.01, 0, 0], [0, 0, 0], [0, 0, 0]],
        )
        vac = create_vacancy(strained, 0)

        # 2. IO round-trip
        path = tmp_path / "test.json"
        write(vac, str(path))
        reloaded = read(str(path))

        assert reloaded.formula == vac.formula
        assert len(reloaded) == len(vac)

        # 3. Storage round-trip
        storage = DataStorage(backend=MemoryBackend())
        doc_id = storage.store_data(reloaded, metadata={"source": "integration_test"})
        retrieved = storage.retrieve_data(doc_id)

        assert retrieved == reloaded

    def test_pipeline_with_registry(self, fcc_cu):
        """Pipeline executes registered transforms."""
        from matsimpy.transformation import (
            TransformationStep, TransformationPlan, registry,
        )

        plan = TransformationPlan(
            steps=[
                TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
            ],
            name="2x2x2 supercell",
        )
        result = registry.apply_plan(plan, fcc_cu)
        assert len(result) == len(fcc_cu) * 8  # 2*2*2 = 8

    def test_substitute_and_round_trip(self, fcc_cu, tmp_path):
        """Substitute → write → read → storage."""
        substituted = substitute(fcc_cu, 0, 'Ag')
        path = tmp_path / "sub.cif"
        write(substituted, str(path))
        reloaded = read(str(path))
        assert reloaded.species[0] == 'Ag'

        storage = DataStorage(backend=MemoryBackend())
        doc_id = storage.store_data(reloaded)
        assert storage.retrieve_data(doc_id) == reloaded


class TestErrorHandlingIntegration:

    def test_type_mismatch_raises(self, fcc_cu, tmp_path):
        """Writing Crystal to .xyz raises StructureTypeError."""
        from matsimpy.exceptions import StructureTypeError

        path = tmp_path / "test.xyz"
        with pytest.raises(StructureTypeError):
            write(fcc_cu, str(path))

    def test_registry_type_validation(self, fcc_cu):
        """Registry.apply rejects incompatible types."""
        from matsimpy.core import Molecule
        from matsimpy.transformation.registry import registry

        mol = Molecule(['H'], [[0, 0, 0]])
        with pytest.raises(TypeError):
            registry.apply('apply_strain', mol,
                           strain=[[0.01, 0, 0], [0, 0, 0], [0, 0, 0]])

    def test_registry_unknown_transform(self, fcc_cu):
        """Registry.apply raises KeyError for unknown transform."""
        from matsimpy.transformation.registry import registry
        with pytest.raises(KeyError):
            registry.apply('nonexistent_transform', fcc_cu)

    def test_storage_id_stability(self, fcc_cu):
        """Same content → same ID."""
        storage = DataStorage(backend=MemoryBackend())
        id1 = storage.store_data(fcc_cu)
        id2 = storage.store_data(fcc_cu)
        assert id1 == id2
        assert len(id1) == 64  # sha256


class TestRegistryIntegration:

    def test_transformation_registry_list(self):
        """TransformationRegistry lists 20+ registered transforms."""
        from matsimpy.transformation.registry import registry
        all_specs = registry.list_all()
        assert len(all_specs) >= 20
        categories = {s.category for s in all_specs}
        assert categories >= {'geometric', 'lattice', 'atomic', 'chemical', 'structural'}

    def test_builder_registry_list(self):
        """BuilderRegistry lists 8+ registered builders."""
        from matsimpy.builders.registry import registry
        all_specs = registry.list_all()
        assert len(all_specs) >= 8
        categories = {s.category for s in all_specs}
        assert categories >= {'bulk', 'surface', 'molecule', 'nanostructure'}

    def test_io_registry_list(self):
        """IO FormatRegistry lists 9+ registered handlers."""
        from matsimpy.io.registry import registry
        readers = registry.list_readers()
        assert len(readers) >= 9  # vasp-poscar, vasp-contcar, cif, xyz, pdb, xsf, mol, json, ase
