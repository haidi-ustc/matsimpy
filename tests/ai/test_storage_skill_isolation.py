"""The storage skill keeps one database per agent session (executor).

It used a single module-level store, so every agent in the process shared
(and could read) the same documents.
"""

import pytest

from matsimpy import Crystal, Lattice
from matsimpy.ai.executor import FunctionExecutor, active_executor
from matsimpy.ai.skill import SkillManager
from matsimpy.ai.skills import storage
from matsimpy.io import write


@pytest.fixture
def structure_file(tmp_path):
    path = tmp_path / "NaCl.json"
    write(Crystal(["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]], Lattice.cubic(5.64)), str(path))
    return str(path)


def test_sessions_do_not_share_documents(structure_file):
    first, second = FunctionExecutor(SkillManager()), FunctionExecutor(SkillManager())

    with active_executor(first):
        stored = storage._store_structure(structure_file, metadata={"tag": "a"})
        assert storage._retrieve_structure(stored["doc_id"])["formula"] == stored["formula"]
        assert storage._query_structures("tag", "a")["count"] == 1

    with active_executor(second):
        assert storage._query_structures("tag", "a")["count"] == 0
        with pytest.raises(Exception):
            storage._retrieve_structure(stored["doc_id"])

    with active_executor(first):  # the first session still has its document
        assert storage._query_structures("tag", "a")["count"] == 1


def test_storage_functions_require_an_active_session(structure_file):
    with pytest.raises(RuntimeError, match="inside an agent tool call"):
        storage._store_structure(structure_file)


def test_reserved_metadata_rejected_through_skill(structure_file):
    with active_executor(FunctionExecutor(SkillManager())):
        with pytest.raises(ValueError, match="reserved"):
            storage._store_structure(structure_file, metadata={"doc_id": "shadow"})
