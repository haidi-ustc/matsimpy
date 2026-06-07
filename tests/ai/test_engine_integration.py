"""Integration tests for AIEngine context continuity across turns."""

from matsimpy.ai.conversation import ChatMessage, ChatResponse, ToolCall
from matsimpy.ai.engine import AIEngine
from matsimpy.ai.skill import FunctionDef, Skill


class _FakeProvider:
    model = "fake-engine-model"

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, tools=None, tool_choice="auto"):
        self.calls.append({
            "messages": list(messages),
            "tools": tools,
            "tool_choice": tool_choice,
        })
        return self._responses.pop(0)


def _assistant_tool_message(*tool_calls):
    return ChatMessage.assistant(
        "",
        tool_calls=[
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": "{}"},
            }
            for tc in tool_calls
        ],
    )


class _TinyStructure:
    formula = "SiO2"
    species = ["Si", "O", "O"]

    def __len__(self):
        return 3


def test_engine_preserves_context_across_multiple_turns(tmp_path):
    """Turn 1 generates a structure, turn 2 saves it — context must carry forward."""
    structure = _TinyStructure()

    def create_sio2():
        return structure

    def save_structure(path):
        output_path = tmp_path / path
        output_path.write_text("saved SiO2")
        return {"saved_to": path, "formula": structure.formula, "num_atoms": len(structure)}

    create_call = ToolCall(id="call-1", name="create_sio2", arguments={})
    save_call = ToolCall(id="call-2", name="save_structure", arguments={"path": "sio2.vasp"})

    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.runtime.provider = _FakeProvider([
        # Turn 1: create SiO2
        ChatResponse(
            message=_assistant_tool_message(create_call),
            tool_calls=[create_call],
            finish_reason="tool_calls",
        ),
        ChatResponse(
            message=ChatMessage.assistant(
                "The random SiO2 crystal has been generated successfully."
            ),
            tool_calls=[],
            finish_reason="stop",
        ),
        # Turn 2: save to file
        ChatResponse(
            message=_assistant_tool_message(save_call),
            tool_calls=[save_call],
            finish_reason="tool_calls",
        ),
        ChatResponse(
            message=ChatMessage.assistant("Saved to sio2.vasp."),
            tool_calls=[],
            finish_reason="stop",
        ),
    ])

    skill = Skill(
        "sio2-test",
        "Test skill for SiO2 workflow",
        [
            FunctionDef(
                name="create_sio2",
                description="Generate random SiO2 structure",
                parameters={"type": "object", "properties": {}},
                callable=create_sio2,
            ),
            FunctionDef(
                name="save_structure",
                description="Save a structure to a file",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                callable=save_structure,
            ),
        ],
    )
    skill.keywords = ["sio2", "structure", "symmetry"]
    engine.skill_manager.register(skill)
    engine.skill_manager.load("sio2-test")

    # Turn 1: generate structure
    response1 = engine.chat("generate random SiO2 structure with symmetry")
    assert "SiO2" in response1

    # Turn 2: save it — context from turn 1 must be present
    response2 = engine.chat("save to current folder with .vasp format")
    assert "Saved" in response2
    assert (tmp_path / "sio2.vasp").exists()

    # Verify turn 2's provider call included turn 1's context
    turn2_call = engine.runtime.provider.calls[-2]  # second-to-last: the tool_calls response
    messages = turn2_call["messages"]
    user_messages = [m.content for m in messages if m.role == "user"]
    assert any("generate random SiO2" in content for content in user_messages), \
        f"Turn 1 user message missing from turn 2 context. Messages: {user_messages}"
    assert any("save to current folder" in content for content in user_messages), \
        f"Turn 2 user message missing. Messages: {user_messages}"


def test_engine_context_includes_assistant_and_tool_messages(tmp_path):
    """Verify assistant responses and tool results from prior turns are in context."""
    def noop_tool():
        return {"result": "done", "formula": "X", "num_atoms": 1}

    tool_call = ToolCall(id="call-1", name="noop_tool", arguments={})

    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.runtime.provider = _FakeProvider([
        # Turn 1: tool call + response
        ChatResponse(
            message=_assistant_tool_message(tool_call),
            tool_calls=[tool_call],
            finish_reason="tool_calls",
        ),
        ChatResponse(
            message=ChatMessage.assistant("Turn 1 complete with results."),
            tool_calls=[],
            finish_reason="stop",
        ),
        # Turn 2: no tools, just a follow-up question
        ChatResponse(
            message=ChatMessage.assistant("I remember the previous result."),
            tool_calls=[],
            finish_reason="stop",
        ),
    ])

    skill = Skill(
        "noop-test",
        "Test skill",
        [FunctionDef(
            name="noop_tool",
            description="No-op tool",
            parameters={"type": "object", "properties": {}},
            callable=noop_tool,
        )],
    )
    engine.skill_manager.register(skill)
    engine.skill_manager.load("noop-test")

    engine.chat("do something")
    engine.chat("follow up question")

    # Second turn should include assistant message from turn 1
    turn2_call = engine.runtime.provider.calls[-1]
    messages = turn2_call["messages"]
    assistant_contents = [m.content for m in messages if m.role == "assistant"]
    assert any("Turn 1 complete" in c for c in assistant_contents), \
        f"Turn 1 assistant response missing from turn 2 context. Assistant messages: {assistant_contents}"
    tool_roles = [m.role for m in messages]
    assert "tool" in tool_roles, \
        f"Turn 1 tool result missing from turn 2 context. Roles: {tool_roles}"
