"""P1 regression tests for AI storage skill isolation."""

from matsimpy import Molecule
from matsimpy.ai.executor import FunctionExecutor, _set_active_executor
from matsimpy.ai.skill import SkillManager
from matsimpy.ai.skills import storage


def test_storage_skill_uses_active_executor_store(tmp_path, monkeypatch):
    first = FunctionExecutor(SkillManager())
    second = FunctionExecutor(SkillManager())
    helium = tmp_path / "helium.xyz"
    neon = tmp_path / "neon.xyz"
    helium.write_text("1\nhelium\nHe 0 0 0\n")
    neon.write_text("1\nneon\nNe 0 0 0\n")
    monkeypatch.chdir(tmp_path)

    _set_active_executor(first)
    first_id = storage._store_structure("helium.xyz", {"owner": "first"})["doc_id"]

    _set_active_executor(second)
    second_id = storage._store_structure("neon.xyz", {"owner": "second"})["doc_id"]

    assert storage._retrieve_structure(second_id)["formula"] == Molecule(["Ne"], [[0, 0, 0]]).formula

    _set_active_executor(first)
    assert storage._retrieve_structure(first_id)["formula"] == Molecule(["He"], [[0, 0, 0]]).formula
    assert storage._query_structures("owner", "second")["count"] == 0
