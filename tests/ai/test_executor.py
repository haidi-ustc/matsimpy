"""Tests for FunctionExecutor — serialization, resolution, auto-retry, evolution."""
import pytest
import numpy as np
from matsimpy.ai.executor import FunctionExecutor
from matsimpy.ai.skill import SkillManager, Skill, FunctionDef
from matsimpy.ai.conversation import ToolCall
from matsimpy.core import Crystal, Lattice, Molecule


# ── fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def ex():
    return FunctionExecutor(SkillManager())


@pytest.fixture
def si_crystal():
    return Crystal(["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]], Lattice.cubic(5.43))


@pytest.fixture
def water():
    return Molecule(["O", "H", "H"], [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]])


@pytest.fixture
def registered_ex(ex):
    """An executor with make_supercell registered."""
    from matsimpy.transformation.registry import registry as t_registry

    sm = ex.skill_manager
    ms_spec = t_registry.get("make_supercell")
    fn = FunctionDef("make_supercell", ms_spec.description, {}, ms_spec.callable)
    skill = Skill("transformation", "Transformations", [fn])
    sm.register(skill)
    sm.load("transformation")
    return ex


# ── _resolve_one ───────────────────────────────────────────────────

class TestResolveOne:
    def test_passthrough_string(self, ex):
        assert ex._resolve_one("hello") == "hello"

    def test_passthrough_int(self, ex):
        assert ex._resolve_one(42) == 42

    def test_passthrough_float(self, ex):
        assert ex._resolve_one(3.14) == 3.14

    def test_passthrough_list(self, ex):
        assert ex._resolve_one([1, 2, 3]) == [1, 2, 3]

    def test_passthrough_plain_dict(self, ex):
        d = {"key": "value", "num": 5}
        assert ex._resolve_one(d) == d

    def test_obj_ref_dict_resolves(self, ex, si_crystal):
        ex._registry[1] = si_crystal
        result = ex._resolve_one({"_obj_ref": 1, "formula": "Si2"})
        assert result is si_crystal

    def test_obj_ref_dict_missing_ref_falls_to_legacy(self, ex):
        """_obj_ref pointing nowhere — but has @module/@class, so legacy path resolves."""
        d = {"_obj_ref": 999, "@module": "matsimpy.core.crystal", "@class": "Crystal",
             "species": ["Si"], "positions": [[0, 0, 0]],
             "lattice": {"@module": "matsimpy.core.lattice", "@class": "Lattice",
                         "lattice_vectors": [[5.43, 0, 0], [0, 5.43, 0], [0, 0, 5.43]]},
             "site_properties": []}
        result = ex._resolve_one(d)
        assert isinstance(result, Crystal)

    def test_bare_integer_is_not_resolved_in_normal_path(self, ex, si_crystal):
        """Bare integers should NOT be resolved by _resolve_one — only in auto-retry."""
        ex._registry[1] = si_crystal
        assert ex._resolve_one(1) == 1  # passes through unchanged

    def test_legacy_msonable_crystal(self, ex):
        d = {"@module": "x", "@class": "Crystal",
             "species": ["Si"], "positions": [[0, 0, 0]],
             "lattice": {"@module": "x", "@class": "Lattice",
                         "lattice_vectors": [[5.0, 0, 0], [0, 5.0, 0], [0, 0, 5.0]]},
             "site_properties": []}
        result = ex._resolve_one(d)
        assert isinstance(result, Crystal)

    def test_legacy_msonable_molecule(self, ex):
        d = {"@module": "x", "@class": "Molecule",
             "species": ["O", "H", "H"],
             "positions": [[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]]}
        result = ex._resolve_one(d)
        assert isinstance(result, Molecule)

    def test_legacy_unknown_class_passthrough(self, ex):
        d = {"@module": "x", "@class": "UnknownThing", "data": 1}
        assert ex._resolve_one(d) == d


# ── _resolve_refs ──────────────────────────────────────────────────

class TestResolveRefs:
    def test_resolves_all_keys(self, ex, si_crystal):
        ex._registry[1] = si_crystal
        args = {"a": {"_obj_ref": 1}, "b": 2, "c": "hello"}
        resolved = ex._resolve_refs(args)
        assert resolved["a"] is si_crystal
        assert resolved["b"] == 2     # bare int NOT resolved in normal path
        assert resolved["c"] == "hello"

    def test_empty_args(self, ex):
        assert ex._resolve_refs({}) == {}


# ── _try_resolve_structure ─────────────────────────────────────────

class TestTryResolveStructure:
    def test_obj_ref(self, ex, si_crystal):
        ex._registry[1] = si_crystal
        assert ex._try_resolve_structure({"_obj_ref": 1}) is si_crystal

    def test_bare_integer(self, ex, si_crystal):
        """Bare integers resolve in auto-retry context via _try_resolve_structure."""
        ex._registry[1] = si_crystal
        assert ex._try_resolve_structure(1) is si_crystal

    def test_bare_integer_missing(self, ex):
        assert ex._try_resolve_structure(999) is None

    def test_legacy_dict(self, ex):
        d = {"@module": "x", "@class": "Crystal",
             "species": ["Si"], "positions": [[0, 0, 0]],
             "lattice": {"@module": "x", "@class": "Lattice",
                         "lattice_vectors": [[5.0, 0, 0], [0, 5.0, 0], [0, 0, 5.0]]},
             "site_properties": []}
        assert isinstance(ex._try_resolve_structure(d), Crystal)

    def test_plain_dict_returns_none(self, ex):
        assert ex._try_resolve_structure({"key": "val"}) is None

    def test_empty_dict_returns_none(self, ex):
        assert ex._try_resolve_structure({}) is None

    def test_non_dict_non_int_returns_none(self, ex):
        assert ex._try_resolve_structure("string") is None
        assert ex._try_resolve_structure(3.14) is None


# ── _serialize ─────────────────────────────────────────────────────

class TestSerialize:
    def test_crystal_gets_obj_ref(self, ex, si_crystal):
        result = ex._serialize(si_crystal)
        assert "_obj_ref" in result
        assert result["formula"] == "Si2"
        assert result["num_atoms"] == 2
        assert "_note" in result
        assert 1 in ex._registry

    def test_molecule_gets_obj_ref(self, ex, water):
        result = ex._serialize(water)
        assert "_obj_ref" in result
        assert "O" in result["formula"]
        assert "H" in result["formula"]
        assert result["num_atoms"] == 3

    def test_none(self, ex):
        assert ex._serialize(None) == {"result": None}

    def test_string(self, ex):
        assert ex._serialize("hello") == {"result": "hello"}

    def test_int(self, ex):
        assert ex._serialize(42) == {"result": 42}

    def test_float(self, ex):
        assert ex._serialize(3.14) == {"result": 3.14}

    def test_bool(self, ex):
        assert ex._serialize(True) == {"result": True}

    def test_list(self, ex):
        assert ex._serialize([1, 2, 3]) == {"result": [1, 2, 3]}

    def test_numpy_array(self, ex):
        result = ex._serialize(np.array([1.0, 2.0]))
        assert result == {"result": [1.0, 2.0]}

    def test_plain_dict_passthrough(self, ex):
        d = {"key": "val"}
        assert ex._serialize(d) == d

    def test_object_with_str(self, ex):
        class Foo:
            def __str__(self):
                return "foo"
        assert ex._serialize(Foo()) == {"result": "foo"}


# ── _is_structure ──────────────────────────────────────────────────

class TestIsStructure:
    def test_crystal_is_structure(self, ex, si_crystal):
        assert ex._is_structure(si_crystal) is True

    def test_molecule_is_structure(self, ex, water):
        assert ex._is_structure(water) is True

    def test_dict_is_not_structure(self, ex):
        assert ex._is_structure({"formula": "Si2"}) is False

    def test_int_is_not_structure(self, ex):
        assert ex._is_structure(42) is False


# ── execute (normal path) ──────────────────────────────────────────

class TestExecuteNormal:
    def test_succeeds_with_live_crystal(self, registered_ex, si_crystal):
        args = {"crystal": si_crystal, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="n1", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result
        assert registered_ex._registry[1] is not None

    def test_succeeds_with_obj_ref_dict(self, registered_ex, si_crystal):
        registered_ex._registry[5] = si_crystal
        args = {"crystal": {"_obj_ref": 5}, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="n2", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result

    def test_succeeds_with_legacy_as_dict(self, registered_ex, si_crystal):
        """_resolve_one handles @module/@class dict BEFORE the function call."""
        args = {"crystal": si_crystal.as_dict(), "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="n3", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result


# ── auto-retry ─────────────────────────────────────────────────────

class TestAutoRetry:
    def test_retry_with_bare_integer(self, registered_ex, si_crystal):
        """LLM passes bare int → normal path fails → auto-retry resolves via registry."""
        registered_ex._registry[7] = si_crystal
        # _resolve_one won't resolve bare int 7, so function gets int → TypeError
        args = {"crystal": 7, "scaling_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]}
        tc = ToolCall(id="a1", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result  # auto-retry succeeded

    def test_retry_records_adaptation_for_bare_int(self, registered_ex, si_crystal):
        registered_ex._registry[8] = si_crystal
        args = {"crystal": 8, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="a2", name="make_supercell", arguments=args)
        registered_ex.execute(tc)
        assert "make_supercell" in registered_ex._adaptations
        assert "crystal" in registered_ex._adaptations["make_supercell"]

    def test_non_structure_typeerror_not_retried(self, ex):
        """TypeError without 'crystal'/'molecule'/'structure' in message → no retry."""

        def _raises_weird_typeerror(**kwargs):
            raise TypeError("something about integers not iterable")

        sm = ex.skill_manager
        fn = FunctionDef("bad_fn", "raises", {}, _raises_weird_typeerror)
        sm.register(Skill("test", "", [fn]))
        sm.load("test")

        tc = ToolCall(id="a3", name="bad_fn", arguments={"x": 1})
        result = ex.execute(tc)
        assert "error" in result
        assert "TypeError" in result["error"]
        assert "bad_fn" not in ex._adaptations

    def test_retry_limit(self, registered_ex):
        """After max auto-retries (3), further attempts fail immediately."""
        for i in range(3):
            registered_ex._call_count = 0
            fail_args = {"crystal": 99999, "scaling_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]}
            tc = ToolCall(id=f"a4-{i}", name="make_supercell", arguments=fail_args)
            result = registered_ex.execute(tc)
            assert "error" in result

        # 4th call — limit hit
        registered_ex._call_count = 0
        fail_args = {"crystal": 99999, "scaling_matrix": [[2, 0, 0], [0, 2, 0], [0, 0, 2]]}
        tc = ToolCall(id="a4-final", name="make_supercell", arguments=fail_args)
        result = registered_ex.execute(tc)
        assert "error" in result
        assert "retry limit" in result["error"].lower()

    def test_retry_count_resets_on_success(self, registered_ex, si_crystal):
        """After a successful auto-retry, the retry count resets to 0."""
        # First: fail with unresolvable value → increments retry count
        fail_args = {"crystal": 99999, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc_fail = ToolCall(id="a5a", name="make_supercell", arguments=fail_args)
        registered_ex.execute(tc_fail)
        assert registered_ex._retry_count.get("make_supercell", 0) == 1

        # Then: succeed with bare int that IS in registry → should reset count
        registered_ex._registry[88] = si_crystal
        args = {"crystal": 88, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc_ok = ToolCall(id="a5b", name="make_supercell", arguments=args)
        registered_ex._call_count = 0
        result = registered_ex.execute(tc_ok)
        assert "_obj_ref" in result
        assert registered_ex._retry_count.get("make_supercell", 0) == 0


# ── _apply_adaptations ─────────────────────────────────────────────

class TestApplyAdaptations:
    def test_pre_applies_learned_adaptation(self, registered_ex, si_crystal):
        """After learning that 'crystal' needs deserialization, future calls
        with bare ints get resolved before the function call (no auto-retry needed)."""
        registered_ex._adaptations["make_supercell"] = {"crystal"}
        registered_ex._registry[9] = si_crystal
        args = {"crystal": 9, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="b1", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result
        # Should NOT have triggered auto-retry (no error to catch)
        # _apply_adaptations resolved it pre-emptively


# ── round-trip integration ─────────────────────────────────────────

class TestRoundTrip:
    def test_crystal_roundtrip(self, ex):
        """Serialize a Crystal, then resolve via _obj_ref dict."""
        c = Crystal(["Si"], [[0, 0, 0]], Lattice.cubic(5.43))
        serialized = ex._serialize(c)
        resolved = ex._resolve_one(serialized)
        assert resolved is c

    def test_molecule_roundtrip(self, ex, water):
        serialized = ex._serialize(water)
        resolved = ex._resolve_one(serialized)
        assert resolved is water

    def test_full_pipeline_with_obj_ref(self, registered_ex, si_crystal):
        """End-to-end: serialize → pass _obj_ref dict → function succeeds."""
        serialized = registered_ex._serialize(si_crystal)
        args = {"crystal": serialized, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="r1", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result

    def test_full_pipeline_with_bare_int_via_retry(self, registered_ex, si_crystal):
        """End-to-end: bare int → auto-retry resolves → function succeeds."""
        registered_ex._registry[55] = si_crystal
        args = {"crystal": 55, "scaling_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
        tc = ToolCall(id="r2", name="make_supercell", arguments=args)
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result


# ── edge cases ─────────────────────────────────────────────────────

class TestEdgeCases:
    def test_max_call_depth(self, ex):
        ex._call_count = ex._max_calls
        tc = ToolCall(id="e1", name="anything", arguments={})
        result = ex.execute(tc)
        assert result == {"error": "Maximum tool call depth exceeded"}

    def test_unknown_function(self, ex):
        tc = ToolCall(id="e2", name="nonexistent_fn", arguments={})
        result = ex.execute(tc)
        assert result == {"error": "Unknown function: nonexistent_fn"}

    def test_empty_arguments(self, registered_ex, si_crystal):
        """Function with no required args works with empty args dict."""
        def _noop(**kwargs):
            return si_crystal
        sm = registered_ex.skill_manager
        fn = FunctionDef("noop", "no-op", {"type": "object", "properties": {}}, _noop)
        sm.register(Skill("test", "", [fn]))
        sm.load("test")

        tc = ToolCall(id="e3", name="noop", arguments={})
        result = registered_ex.execute(tc)
        assert "_obj_ref" in result
