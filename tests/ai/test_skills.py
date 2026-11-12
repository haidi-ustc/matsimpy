"""Agent Skills: discovery, progressive loading, management and drafts."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from matsimpy.ai.skills import PACKAGED_SKILLS, SkillError, SkillLibrary, validate


def make_skill(root: Path, name: str, description: str = "Does things.", body: str = "Step 1.",
               extra: str = "", files: dict[str, str] | None = None) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n{extra}---\n\n{body}\n")
    for relative, text in (files or {}).items():
        (directory / relative).parent.mkdir(parents=True, exist_ok=True)
        (directory / relative).write_text(text)
    return directory


TOOLS = '''
from matsimpy.utils.tooling import tool

@tool
def double(x: int) -> int:
    """Double a number.

    Args:
        x: The number.
    """
    return 2 * x

def helper():
    return None
'''


@pytest.fixture
def library(tmp_path):
    return SkillLibrary(tmp_path / "ws", user=tmp_path / "user", packaged=tmp_path / "packaged")


def test_discovery_reads_only_the_frontmatter(library, tmp_path):
    directory = make_skill(tmp_path / "user", "big-skill", body="Instructions.\n")
    # an undecodable body far after the frontmatter is not read by discover()
    with (directory / "SKILL.md").open("ab") as handle:
        handle.write(b"x" * 200_000 + b"\xff\xfe")
    (summary,) = library.discover()
    assert (summary.name, summary.description, summary.source) == ("big-skill", "Does things.", "user")
    with pytest.raises(SkillError, match="not UTF-8"):
        library.activate("big-skill")


def test_activation_loads_instructions_resources_and_tools(library, tmp_path):
    make_skill(tmp_path / "user", "math-help", body="# Math\nUse double.", extra="allowed-tools: translate\n",
               files={"tools.py": TOOLS, "reference/table.md": "| a | b |", "data.csv": "1,2"})
    skill = library.activate("math-help")
    assert skill.instructions == "# Math\nUse double."
    assert skill.resources == ("data.csv", "reference/table.md")
    assert [t.name for t in skill.tools] == ["double"]
    assert skill.tools[0].source == "skill:math-help"
    assert skill.tools[0].parameters["properties"]["x"] == {"type": "integer", "description": "The number."}
    assert skill.tools[0].function(x=4) == 8
    assert skill.allowed_tools == ("translate",)
    assert library.read_resource("math-help", "reference/table.md") == "| a | b |"
    with pytest.raises(SkillError, match="outside"):
        library.read_resource("math-help", "../../secret.txt")
    with pytest.raises(SkillError, match="has no file"):
        library.read_resource("math-help", "missing.md")
    with pytest.raises(SkillError, match="unknown skill"):
        library.activate("nope")


def test_workspace_skills_shadow_user_skills_which_shadow_packaged(library, tmp_path):
    make_skill(tmp_path / "packaged", "shared", description="packaged")
    make_skill(tmp_path / "user", "shared", description="user")
    assert library.get("shared").source == "user"
    make_skill(tmp_path / "ws" / ".matsimpy" / "skills", "shared", description="workspace")
    assert library.get("shared").description == "workspace"
    assert [s.name for s in library.search("shared")] == ["shared"]


def test_invalid_skills_are_reported_not_discovered(library, tmp_path):
    root = tmp_path / "user"
    make_skill(root, "good")
    (root / "no-file").mkdir()
    make_skill(root, "Bad_Name")
    wrong = make_skill(root, "wrong-dir")
    (wrong / "SKILL.md").write_text("---\nname: other\ndescription: x\n---\nbody")
    nodesc = make_skill(root, "no-desc")
    (nodesc / "SKILL.md").write_text("---\nname: no-desc\n---\nbody")
    unclosed = make_skill(root, "unclosed")
    (unclosed / "SKILL.md").write_text("---\nname: unclosed\ndescription: x\n")
    assert [s.name for s in library.discover()] == ["good"]
    problems = "\n".join(library.problems.values())
    for expected in ("no SKILL.md", "lowercase letters", "must equal the directory name", "'description'",
                     "no closing"):
        assert expected in problems


def test_validate_checks_tools_and_links(tmp_path):
    good = make_skill(tmp_path, "good", files={"tools.py": TOOLS})
    assert validate(good) == []
    broken = make_skill(tmp_path, "broken", files={"tools.py": "def f(:\n"})
    assert "tools.py" in validate(broken)[0]
    unmarked = make_skill(tmp_path, "unmarked", files={"tools.py": "def f():\n    return 1\n"})
    assert validate(unmarked) == ["tools.py has no @tool functions"]
    linked = make_skill(tmp_path, "linked")
    (tmp_path / "secret.txt").write_text("secret")
    (linked / "secret.txt").symlink_to(tmp_path / "secret.txt")
    assert validate(linked) == ["secret.txt links outside the skill"]


def test_install_replace_and_remove(library, tmp_path):
    source = make_skill(tmp_path / "src", "my-skill", files={"notes.md": "n"})
    summary = library.install(source)
    assert summary.path == tmp_path / "user" / "my-skill" and library.get("my-skill").source == "user"
    with pytest.raises(SkillError, match="already installed"):
        library.install(source)
    (source / "notes.md").write_text("updated")
    library.install(source, replace=True)
    assert library.read_resource("my-skill", "notes.md") == "updated"
    assert library.remove("my-skill") == tmp_path / "user" / "my-skill"
    assert library.discover() == []
    make_skill(tmp_path / "packaged", "builtin")
    with pytest.raises(SkillError, match="no installed"):
        library.remove("builtin")
    with pytest.raises(SkillError, match="invalid skill"):
        library.install(make_skill(tmp_path / "src", "bad", files={"tools.py": "def f(:"}))


def test_install_from_zip(library, tmp_path):
    source = make_skill(tmp_path / "src", "zipped", files={"tools.py": TOOLS})
    archive = tmp_path / "zipped.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for path in source.rglob("*"):
            handle.write(path, path.relative_to(source.parent))
    library.install(archive)
    assert [t.name for t in library.activate("zipped").tools] == ["double"]

    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as handle:
        handle.writestr("../escape/SKILL.md", "---\nname: escape\ndescription: x\n---\n")
    with pytest.raises(SkillError, match="outside the archive"):
        library.install(evil)


def test_drafts_need_approval(library):
    draft = library.create_draft("slab-recipe", "Build relaxed slabs.", "1. generate_slab\n2. write_structure")
    assert draft.source == "draft"
    assert library.discover() == []  # not usable before approval
    assert [d.name for d in library.drafts()] == ["slab-recipe"]
    assert library.draft("slab-recipe").instructions == "1. generate_slab\n2. write_structure"
    with pytest.raises(SkillError, match="already exists"):
        library.create_draft("slab-recipe", "again", "x")
    with pytest.raises(SkillError, match="invalid skill name"):
        library.create_draft("Bad Name", "x", "y")

    approved = library.approve("slab-recipe")
    assert approved.source == "user" and library.drafts() == []
    assert library.activate("slab-recipe").instructions.startswith("1. generate_slab")

    library.create_draft("throwaway", "Not wanted.", "x")
    library.reject("throwaway")
    assert library.drafts() == []
    with pytest.raises(SkillError, match="no draft"):
        library.approve("throwaway")


def test_packaged_vasp_inputs_skill(tmp_path):
    library = SkillLibrary(tmp_path, user=None)
    assert validate(PACKAGED_SKILLS / "vasp-inputs") == []
    skill = library.activate("vasp-inputs")
    assert skill.source == "packaged" and skill.resources == ("incar-presets.md",)
    assert [t.name for t in skill.tools] == ["kpoint_mesh"]
    assert "ISMEAR" in library.read_resource("vasp-inputs", "incar-presets.md")
    with pytest.raises(SkillError, match="no user or workspace"):
        SkillLibrary(None, user=None).install(PACKAGED_SKILLS / "vasp-inputs")


def test_kpoint_mesh_matches_pymatgen():
    pytest.importorskip("pymatgen")
    from pymatgen.core import Structure
    from pymatgen.io.vasp.inputs import Kpoints

    from matsimpy import io

    (kpoint_mesh,) = SkillLibrary(None, user=None).activate("vasp-inputs").tools
    fixtures = Path(__file__).parents[1] / "calculator" / "fixtures" / "vasp"
    for name in ("POSCAR_C2", "POSCAR_Li2O", "POSCAR.AlN", "POSCAR_Al12O18"):
        ours, reference = io.read(str(fixtures / name)), Structure.from_file(fixtures / name)
        for kppa in (100, 1000, 8000):
            expected = list(Kpoints.automatic_density(reference, kppa).kpts[0])
            assert kpoint_mesh.function(structure=ours, kppa=kppa) == expected, (name, kppa)
