"""Tests for the agent runtime loop."""

import os
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


class RaisingProvider:
    model = "fake-runtime-model"

    def chat(self, messages, tools=None, tool_choice="auto"):
        raise RuntimeError("provider unavailable")


class DraftFailingSessionStore(SessionStore):
    def save_skill_draft(
        self,
        name,
        status,
        source_session_id,
        trigger_keywords,
        body,
        metadata,
    ):
        raise RuntimeError("draft persistence unavailable")


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


def _isolated_executor_skill_manager():
    structure = TinyStructure()

    def create_structure():
        return structure

    def consume_structure(structure):
        if not isinstance(structure, TinyStructure):
            raise TypeError("expected TinyStructure")
        return {"consumed": structure.formula}

    skill = Skill(
        "runtime-isolation-test",
        "Runtime isolation test tools",
        [
            FunctionDef(
                name="create_structure",
                description="Create a test structure",
                parameters={"type": "object", "properties": {}},
                callable=create_structure,
            ),
            FunctionDef(
                name="consume_structure",
                description="Consume a live test structure",
                parameters={
                    "type": "object",
                    "properties": {"structure": {"type": "object"}},
                    "required": ["structure"],
                },
                callable=consume_structure,
            ),
        ],
    )
    manager = SkillManager({"runtime-isolation-test": skill})
    manager.load("runtime-isolation-test")
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


def test_runtime_keeps_success_when_draft_generation_fails(tmp_path):
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
    store = DraftFailingSessionStore(tmp_path / "state.db")
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
    assert result.validation_status == "success"
    assert result.final_response == "Created and saved silicon."
    assert result.draft_skill is None
    rows = store.conn.execute("SELECT status FROM sessions").fetchall()
    assert [row["status"] for row in rows] == ["success"]
    traces = store.search_traces("silicon")
    assert [trace["validation_status"] for trace in traces] == ["success"]


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


def test_runtime_finalizes_session_and_restores_cwd_when_provider_raises(tmp_path):
    original_cwd = os.getcwd()
    store = SessionStore(tmp_path / "state.db")
    runtime = AgentRuntime(
        provider=RaisingProvider(),
        skill_manager=SkillManager(),
        session_store=store,
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )

    result = runtime.run("trigger provider failure")

    assert result.status == "failure"
    assert result.validation_status == "failure"
    assert result.final_response == "Runtime error: RuntimeError: provider unavailable"
    assert result.trace_id is not None
    assert result.draft_skill is None
    assert os.getcwd() == original_cwd
    rows = store.conn.execute("SELECT status, ended_at FROM sessions").fetchall()
    assert [(row["status"], row["ended_at"] is not None) for row in rows] == [
        ("failure", True)
    ]
    traces = store.search_traces("provider")
    assert [trace["validation_status"] for trace in traces] == ["failure"]


def test_runtime_starts_each_run_without_prior_task_messages(tmp_path):
    provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("First task done."),
                tool_calls=[],
                finish_reason="stop",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Second task done."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )

    runtime.run("first task unique content")
    runtime.run("second task unique content")

    second_messages = provider.calls[1]["messages"]
    assert [message.role for message in second_messages] == ["system", "user"]
    assert [message.content for message in second_messages] == [
        second_messages[0].content,
        "second task unique content",
    ]
    assert all("first task unique content" not in message.content for message in second_messages)
    assert all("First task done." not in message.content for message in second_messages)


def test_runtime_reuses_executor_object_refs_across_runs(tmp_path):
    create_call = ToolCall(id="call-create", name="create_structure", arguments={})
    consume_call = ToolCall(
        id="call-consume",
        name="consume_structure",
        arguments={"structure": {"_obj_ref": 1}},
    )
    provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(create_call),
                tool_calls=[create_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Created structure."),
                tool_calls=[],
                finish_reason="stop",
            ),
            ChatResponse(
                message=_assistant_tool_message(consume_call),
                tool_calls=[consume_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Consumed structure successfully."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=_isolated_executor_skill_manager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )

    first = runtime.run("create isolated structure")
    second = runtime.run("consume structure ref from prior run")

    assert first.status == "success"
    assert first.tool_calls[0]["result"]["_obj_ref"] == 1
    assert second.status == "success"
    assert second.tool_calls[0]["status"] == "success"
    assert "consumed" in second.tool_calls[0]["result"]


def test_engine_chat_uses_runtime_with_fake_provider(tmp_path):
    from matsimpy.ai.engine import AIEngine

    tool_call = ToolCall(
        id="call-make-result",
        name="make_result",
        arguments={"value": "reusable"},
    )
    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.runtime.provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(tool_call),
                tool_calls=[tool_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Task complete."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )

    fn = FunctionDef(
        name="make_result",
        description="Make a result",
        parameters={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        callable=lambda value: {"result": value},
        skill="test",
    )
    skill = Skill("test", "Test skill", [fn])
    engine.skill_manager.register(skill)
    engine.skill_manager.load("test")

    response = engine.chat("make a reusable result")

    assert response == "Task complete."
    assert engine.runtime.last_result.validation_status == "success"


def test_engine_chat_keeps_repl_workspace_cwd_for_relative_commands(tmp_path):
    from matsimpy.ai.engine import AIEngine

    original_cwd = Path.cwd()
    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.runtime.provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("Ready to save."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )

    try:
        engine.workspace.enter()
        response = engine.chat("prepare a saveable conversation")

        assert response == "Ready to save."
        assert Path.cwd() == engine.workspace.path

        engine._handle_command("/save rel-conversation.json")

        assert (engine.workspace.path / "rel-conversation.json").exists()
    finally:
        os.chdir(original_cwd)


def test_engine_chat_passes_preloaded_context_to_runtime_provider(tmp_path):
    from matsimpy.ai.engine import AIEngine

    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.runtime.provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("Used loaded context."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    engine.conversation.append(ChatMessage.system("[Loaded skill: x]\nimportant workflow"))

    response = engine.chat("use the loaded workflow")

    assert response == "Used loaded context."
    messages = engine.runtime.provider.calls[0]["messages"]
    assert [message.role for message in messages] == ["system", "system", "user"]
    assert messages[1].content == "[Loaded skill: x]\nimportant workflow"
    assert messages[2].content == "use the loaded workflow"


def test_workspace_command_moves_runtime_session_store_and_chat_state(tmp_path):
    from matsimpy.ai.engine import AIEngine

    original_workspace = tmp_path / "original"
    new_workspace = tmp_path / "new"
    engine = AIEngine(api_key="unused", workspace_path=original_workspace)
    engine.runtime.provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("Stored in new workspace."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )

    engine._handle_command(f"/workspace {new_workspace}")

    expected_db = new_workspace / "ai-state.db"
    assert engine.workspace.path == new_workspace.resolve()
    assert engine.runtime.workspace.path == new_workspace.resolve()
    assert engine.runtime.session_store.path == expected_db.resolve()

    response = engine.chat("write state after workspace switch")

    assert response == "Stored in new workspace."
    assert expected_db.exists()
    traces = engine.runtime.session_store.search_traces("workspace")
    assert [trace["final_response"] for trace in traces] == ["Stored in new workspace."]
    original_store = SessionStore(original_workspace / "ai-state.db")
    try:
        rows = original_store.conn.execute("SELECT id FROM sessions").fetchall()
    finally:
        original_store.close()
    assert rows == []


def test_engine_chat_auto_loads_user_message_once(tmp_path):
    from matsimpy.ai.engine import AIEngine

    class CountingSkillManager(SkillManager):
        def __init__(self):
            super().__init__()
            self.auto_load_messages = []

        def auto_load(self, message):
            self.auto_load_messages.append(message)
            return []

    skill_manager = CountingSkillManager()
    engine = AIEngine(api_key="unused", workspace_path=tmp_path)
    engine.skill_manager = skill_manager
    engine.runtime.skill_manager = skill_manager
    engine.runtime.provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("Loaded once."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )

    response = engine.chat("trigger one auto load")

    assert response == "Loaded once."
    assert skill_manager.auto_load_messages == ["trigger one auto load"]


def test_runtime_calls_verbose_hook_for_skill_loading_and_tool_execution(tmp_path):
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
    emitted: list[str] = []

    runtime = AgentRuntime(
        provider=provider,
        skill_manager=_runtime_skill_manager(tmp_path),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
        verbose_hook=emitted.append,
    )

    result = runtime.run("create silicon and save it")

    assert result.status == "success"
    assert any("loaded:" in msg for msg in emitted), f"expected skill loading message, got: {emitted}"
    assert any("create_structure" in msg for msg in emitted), f"expected create_structure call, got: {emitted}"
    assert any("save_structure" in msg for msg in emitted), f"expected save_structure call, got: {emitted}"


def test_runtime_verbose_hook_reports_failures(tmp_path):
    bad_call = ToolCall(id="call-bad", name="missing_tool", arguments={})
    provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(bad_call),
                tool_calls=[bad_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Failed."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    emitted: list[str] = []

    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
        verbose_hook=emitted.append,
    )

    result = runtime.run("run missing tool")

    assert result.status == "failure"
    assert any("missing_tool" in msg for msg in emitted)
    assert any("❌ missing_tool" in msg for msg in emitted)


def test_runtime_does_not_emit_when_verbose_hook_is_none(tmp_path):
    provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("Silent response."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
        verbose_hook=None,
    )

    result = runtime.run("silent task")
    assert result.status == "success"


def test_runtime_reuses_executor_across_runs(tmp_path):
    provider = FakeProvider(
        [
            ChatResponse(
                message=ChatMessage.assistant("First run done."),
                tool_calls=[],
                finish_reason="stop",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Second run done."),
                tool_calls=[],
                finish_reason="stop",
            ),
        ]
    )
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=AgentMemory(tmp_path / "memory"),
        workspace_path=tmp_path,
        source="test",
    )
    executor_before = runtime.executor

    runtime.run("first task")
    assert runtime.executor is executor_before

    runtime.run("second task")
    assert runtime.executor is executor_before


def test_runtime_defers_persistence_until_loop_ends(tmp_path):
    create_call = ToolCall(id="call-create", name="create_structure", arguments={})
    provider = FakeProvider(
        [
            ChatResponse(
                message=_assistant_tool_message(create_call),
                tool_calls=[create_call],
                finish_reason="tool_calls",
            ),
            ChatResponse(
                message=ChatMessage.assistant("Structure created."),
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

    result = runtime.run("create silicon structure")

    assert result.status == "success"
    messages = store.conn.execute(
        "SELECT role FROM messages WHERE session_id = ? ORDER BY id",
        (result.session_id,),
    ).fetchall()
    tool_calls = store.conn.execute(
        "SELECT tool_name FROM tool_calls WHERE session_id = ? ORDER BY id",
        (result.session_id,),
    ).fetchall()
    assert [m["role"] for m in messages] == ["user", "assistant", "tool", "assistant"]
    assert [t["tool_name"] for t in tool_calls] == ["create_structure"]
    traces = store.search_traces("structure")
    assert len(traces) == 1
    assert traces[0]["validation_status"] == "success"


def test_runtime_prompt_forbids_invented_scientific_tool_arguments():
    from matsimpy.ai.runtime import RUNTIME_SYSTEM_PROMPT

    prompt = RUNTIME_SYSTEM_PROMPT.lower()

    assert "orchestrator" in prompt
    assert "do not invent coordinates" in prompt
    assert "forces" in prompt
    assert "energies" in prompt
    assert "tool-call arguments" in prompt
    assert "pass returned structure references" in prompt


def test_runtime_initial_prompt_keeps_memory_after_core_rules(tmp_path):
    memory = AgentMemory(tmp_path / "memory")
    memory.append_learning({
        "user_intent": "create a large generated crystal",
        "outcome": "failure",
        "tools_used": ["create_crystal"],
        "insight": "Prefer builder functions over generated coordinate arrays.",
    })
    runtime = AgentRuntime(
        provider=FakeProvider([]),
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=memory,
        workspace_path=tmp_path,
        source="test",
    )

    system_message = runtime._initial_messages()[0].content.lower()

    assert "do not invent coordinates" in system_message
    assert "relevant memory" in system_message
    assert "prefer builder functions" in system_message


def test_runtime_appends_learning_when_tool_execution_fails(tmp_path):
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
    memory = AgentMemory(tmp_path / "memory")
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=memory,
        workspace_path=tmp_path,
        source="test",
    )

    result = runtime.run("create a crystal with generated coordinates")
    next_prompt = runtime._initial_messages()[0].content

    assert result.status == "failure"
    assert "missing_tool" in memory.read("memory")
    assert "create a crystal with generated coordinates" in memory.read("memory")
    assert "missing_tool" in next_prompt


def test_runtime_appends_learning_when_provider_raises_after_session_start(tmp_path):
    class LateRaisingProvider(FakeProvider):
        model = "fake-runtime-model"

        def chat(self, messages, tools=None, tool_choice="auto"):
            self.calls.append({"messages": list(messages), "tools": tools, "tool_choice": tool_choice})
            raise RuntimeError("provider unavailable after session start")

    memory = AgentMemory(tmp_path / "memory")
    runtime = AgentRuntime(
        provider=LateRaisingProvider([]),
        skill_manager=SkillManager(),
        session_store=SessionStore(tmp_path / "state.db"),
        memory=memory,
        workspace_path=tmp_path,
        source="test",
    )

    result = runtime.run("run an unavailable workflow")

    assert result.status == "failure"
    assert "provider unavailable after session start" in memory.read("memory")
    assert "run an unavailable workflow" in memory.read("memory")
