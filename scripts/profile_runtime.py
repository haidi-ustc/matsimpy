"""Profile AgentRuntime phases to identify remaining bottlenecks."""
import time
from pathlib import Path
import tempfile

from matsimpy.ai.conversation import ChatMessage, ChatResponse, ToolCall
from matsimpy.ai.memory import AgentMemory
from matsimpy.ai.runtime import AgentRuntime
from matsimpy.ai.session_store import SessionStore
from matsimpy.ai.skill import FunctionDef, Skill, SkillManager


class TinyStructure:
    formula = "SiO2"
    species = ["Si", "O", "O"]

    def __len__(self):
        return 3


class TimingProvider:
    """Wraps a real-ish chat cycle: tool_calls → stop, timing the 'LLM' portion."""
    model = "fake"

    def __init__(self, structure, tmp_path):
        self.structure = structure
        self.tmp_path = tmp_path
        self.call_count = 0

    def chat(self, messages, tools=None, tool_choice="auto"):
        self.call_count += 1
        t0 = time.perf_counter()
        if self.call_count % 2 == 1:
            # Simulate tool_calls response
            last_user = [m for m in messages if m.role == "user"][-1].content
            if "save" in last_user.lower():
                tc = ToolCall(id="call-save", name="save_structure",
                              arguments={"path": "test.vasp"})
            else:
                tc = ToolCall(id="call-gen", name="create_structure", arguments={})
            msg = ChatMessage.assistant(
                "",
                tool_calls=[{
                    "id": tc.id, "type": "function",
                    "function": {"name": tc.name, "arguments": "{}"},
                }],
            )
            elapsed = time.perf_counter() - t0
            return ChatResponse(message=msg, tool_calls=[tc], finish_reason="tool_calls")
        else:
            elapsed = time.perf_counter() - t0
            return ChatResponse(
                message=ChatMessage.assistant("Done."),
                tool_calls=[],
                finish_reason="stop",
            )


def build_skill_manager(tmp_path):
    structure = TinyStructure()

    def create_structure():
        return structure

    def save_structure(path):
        output_path = Path(path)
        output_path.write_text("saved")
        return {"saved_to": path, "formula": structure.formula, "num_atoms": len(structure)}

    skill = Skill(
        "profile-test",
        "Profile test tools",
        [
            FunctionDef(
                name="create_structure",
                description="Create a test structure",
                parameters={"type": "object", "properties": {}},
                callable=create_structure,
            ),
            FunctionDef(
                name="save_structure",
                description="Save structure",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                callable=save_structure,
            ),
        ],
    )
    skill.keywords = ["sio2", "crystal", "structure"]
    manager = SkillManager({"profile-test": skill})
    return manager


def time_phase(label, fn):
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    return result, elapsed


def main():
    tmp_path = Path(tempfile.mkdtemp())
    skill_manager = build_skill_manager(tmp_path)

    # Pre-populate memory with realistic content to measure read cost
    memory = AgentMemory(tmp_path / "memory")
    memory.write("user", "User preferences: prefer VASP format for output.\n")
    memory.write("memory", "- Learned: SiO2 generates with P1 symmetry by default\n" * 20)

    provider = TimingProvider(TinyStructure(), tmp_path)
    store = SessionStore(tmp_path / "state.db")
    runtime = AgentRuntime(
        provider=provider,
        skill_manager=skill_manager,
        session_store=store,
        memory=memory,
        workspace_path=tmp_path,
        source="test",
        verbose_hook=None,  # silent for profiling
    )

    results = {}
    n_warmup = 1
    n_runs = 5
    total = n_warmup + n_runs

    for i in range(total):
        run_times = {}

        # Measure _initial_messages (includes memory compaction)
        _, t = time_phase("initial_messages", runtime._initial_messages)
        run_times["_initial_messages (memory read)"] = t

        # Measure auto_load
        _, t = time_phase("auto_load", lambda: runtime.skill_manager.auto_load(
            "generate random SiO2 crystal"
        ))
        run_times["auto_load"] = t

        # Measure full run (the rest is inside)
        t0 = time.perf_counter()
        result = runtime.run("generate random SiO2 crystal")
        run_times["full run (turn 1)"] = time.perf_counter() - t0

        # The runtime emits its own timing breakdown via the result
        results[i] = run_times

    # Print results (skip warmup)
    print("=" * 70)
    print("Phase timing breakdown (avg of {} runs, ms)".format(n_runs))
    print("=" * 70)
    phases = list(results[n_warmup].keys())
    for phase in phases:
        avg_ms = sum(results[i][phase] for i in range(n_warmup, total)) / n_runs * 1000
        print(f"  {phase:40s} {avg_ms:8.2f} ms")

    # Now also instrument the post-loop operations separately
    print()
    print("=" * 70)
    print("Post-loop phase timing (single run, ms)")
    print("=" * 70)

    # Fresh run with detailed post-loop timing
    provider.call_count = 0
    runtime2 = AgentRuntime(
        provider=TimingProvider(TinyStructure(), tmp_path),
        skill_manager=skill_manager,
        session_store=SessionStore(tmp_path / "state2.db"),
        memory=memory,
        workspace_path=tmp_path,
        source="test",
        verbose_hook=None,
    )

    # Instrument _try_draft_skill_from_trace
    import time as _time
    _orig_draft = runtime2._try_draft_skill_from_trace

    def timed_draft(*args, **kwargs):
        t0 = _time.perf_counter()
        result = _orig_draft(*args, **kwargs)
        elapsed = _time.perf_counter() - t0
        print(f"  {'_try_draft_skill_from_trace':40s} {elapsed*1000:8.2f} ms")
        return result

    runtime2._try_draft_skill_from_trace = timed_draft

    # Instrument batch writes
    _orig_msg_batch = runtime2.session_store.add_messages_batch
    _orig_tc_batch = runtime2.session_store.add_tool_calls_batch

    def timed_msg_batch(*args, **kwargs):
        t0 = _time.perf_counter()
        result = _orig_msg_batch(*args, **kwargs)
        print(f"  {'add_messages_batch':40s} {(_time.perf_counter()-t0)*1000:8.2f} ms")
        return result

    def timed_tc_batch(*args, **kwargs):
        t0 = _time.perf_counter()
        result = _orig_tc_batch(*args, **kwargs)
        print(f"  {'add_tool_calls_batch':40s} {(_time.perf_counter()-t0)*1000:8.2f} ms")
        return result

    runtime2.session_store.add_messages_batch = timed_msg_batch
    runtime2.session_store.add_tool_calls_batch = timed_tc_batch

    _orig_start = runtime2.session_store.start_session
    def timed_start(*args, **kwargs):
        t0 = _time.perf_counter()
        result = _orig_start(*args, **kwargs)
        print(f"  {'start_session':40s} {(_time.perf_counter()-t0)*1000:8.2f} ms")
        return result
    runtime2.session_store.start_session = timed_start

    _orig_end = runtime2.session_store.end_session
    def timed_end(*args, **kwargs):
        t0 = _time.perf_counter()
        result = _orig_end(*args, **kwargs)
        print(f"  {'end_session':40s} {(_time.perf_counter()-t0)*1000:8.2f} ms")
        return result
    runtime2.session_store.end_session = timed_end

    result = runtime2.run("generate random SiO2 crystal")
    print(f"  {'full run total':40s} {(time.perf_counter()-t0)*1000:8.2f} ms")

    # Also time a second turn (save) to measure short turns
    print()
    print("=" * 70)
    print("Turn 2 (save) post-loop timing (single run, ms)")
    print("=" * 70)
    runtime2.messages = list(runtime2._initial_messages())
    runtime2.messages.append(ChatMessage.system("[Loaded skill context]"))
    runtime2.messages.append(ChatMessage.user("generate random SiO2 crystal"))
    runtime2.messages.append(ChatMessage.assistant("Done."))
    result2 = runtime2.run("save to .vasp file")

    print()
    memory_dir = tmp_path / "memory"
    print(f"Memory dir size: {sum(f.stat().st_size for f in memory_dir.glob('*.md') if f.is_file())} bytes")
    print(f"State db size: {(tmp_path / 'state.db').stat().st_size} bytes")


if __name__ == "__main__":
    main()
