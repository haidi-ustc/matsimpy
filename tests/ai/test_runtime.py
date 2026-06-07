"""Tests for the agent runtime loop."""

from pathlib import Path

from matsimpy.ai.conversation import ChatMessage, ChatResponse, ToolCall
from matsimpy.ai.memory import AgentMemory
from matsimpy.ai.runtime import AgentRuntime
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import FunctionDef, Skill, SkillManager


class FakeProvider:
    model = "fake-runtime-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append(
            {
                "messages": list(messages),
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        return self._responses.pop(0)


class TinyStructure:
    formula = "Si2"
    species = ["Si", "Si"]

    def __len__(self):
        return 2


def _assistant_tool_message(*tool_calls):
    return ChatMessage.assistant(
        "",
        tool_calls=[
            {
                "id": tool_call.id,
                "type": "function",
                "function": {"name": tool_call.name, "arguments": "{}"},
            }
            for tool_call in tool_calls
        ],
    )


def _runtime_skill_manager(workspace):
    structure = TinyStructure()

    def create_structure():
        return structure

    def save_structure(path):
        output_path = Path(path)
        output_path.write_text("saved structure")
        return {"saved_to": path, "formula": structure.formula, "num_atoms": len(structure)}

    skill = Skill(
        "runtime-test",
        "Runtime test tools",
        [
            FunctionDef(
                name="create_structure",
                description="Create a test structure",
                parameters={"type": "object", "properties": {}},
                callable=create_structure,
            ),
            FunctionDef(
                name="save_structure",
                description="Save a test structure",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                callable=save_structure,
            ),
        ],
    )
    skill.keywords = ["silicon"]
    manager = SkillManager({"runtime-test": skill})
    return manager


def test_runtime_executes_tools_persists_trace_and_drafts_skill(tmp_path):
    create_call = ToolCall(id="call-create", name="create_structure", arguments={})
    save_call = ToolCall(id="call-save", name="save_structure", arguments={"path": "si.txt"})
    provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(create_call, save_call),
                tool_calls=[create_call, save_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Created and saved silicon."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    store = SessionStore(tmp_path / "state.db")
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=_runtime_skill_manager(tmp_path),
        session_store=store,
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )

    result = runtime.run("create silicon and save it")

    assert result.status == "success"
    assert result.final_response == "Created and saved silicon."
    assert result.validation_status == "success"
    assert result.session_id is not None
    assert result.trace_id is not None
    assert [call["name"] for call in result.tool_calls] == ["create_structure", "save_structure"]
    assert result.draft_skill is not None
    assert result.draft_skill["status"] == "draft"
    assert (tmp_path / "si.txt").exists()
    assert len(provider.calls) == 2
    assert provider.calls[0]["messages"][0].role == "system"

    traces = store.search_traces("silicon")
    assert [trace["id"] for trace in traces] == [result.trace_id]
    drafts = store.list_skill_drafts("draft")
    assert [draft["name"] for draft in drafts] == [result.draft_skill["name"]]


def test_runtime_reports_tool_error_as_failure(tmp_path):
    bad_call = ToolCall(id="call-bad", name="missing_tool", arguments={})
    provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(bad_call),
                tool_calls=[bad_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("I could not finish."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    store = SessionStore(tmp_path / "state.db")
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=store,
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )

    result = runtime.run("run a missing tool")

    assert result.status == "failure"
    assert result.validation_status == "failure"
    assert result.final_response == "I could not finish."
    assert result.draft_skill is None
    assert result.tool_calls[0]["status"] == "failure"
    assert "Unknown function" in result.tool_calls[0]["result"]["error"]

    traces = store.search_traces("missing")
    assert [trace["validation_status"] for trace in traces] == ["failure"]
