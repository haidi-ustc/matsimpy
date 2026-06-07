"""AIEngine — orchestrates provider, skills, executor, and REPL."""

from __future__ import annotations
import json
from .conversation import ChatMessage, ToolCall
from .evolution import EvolutionManager
from .provider import DeepSeekProvider
from .runtime import AgentRuntime
from .session_store import SessionStore
from .skill import SkillManager, Skill
from .executor import FunctionExecutor
from .workspace import Workspace
from .memory import AgentMemory
from .skill_loader import list_generated_skills, save_skill_md, parse_skill_md


SYSTEM_PROMPT = """You are a materials science AI assistant powered by MatSimPy.
You can create, modify, analyze, and store crystal and molecular structures.

Guidelines:
- Use the provided tools to call MatSimPy functions directly.
- When creating structures, suggest reasonable defaults if the user is vague.
- Explain what you're doing before calling tools.
- After getting results, summarize what was done and the key findings.
- If a tool returns an error, explain it to the user and suggest alternatives.

Available auto_choice skills (call /load-skill <name> when needed):
{available_skills}
"""


class AIEngine:
    """Main entry point — orchestrates LLM + skills + execution + conversation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        workspace_path: str | None = None,
        system_prompt: str | None = None,
    ):
        self.provider = DeepSeekProvider(api_key, model, base_url)
        self.skill_manager = SkillManager()
        self.executor = FunctionExecutor(self.skill_manager)
        from .executor import _set_active_executor
        _set_active_executor(self.executor)
        self.workspace = Workspace(workspace_path)
        self.memory = AgentMemory()
        self.verbose = False

        # Inject soul into system prompt
        soul = self.memory.get_soul_prompt()
        base_prompt = system_prompt or SYSTEM_PROMPT
        self.system_prompt = f"{base_prompt}\n\n{soul}" if soul.strip() else base_prompt

        self.runtime = AgentRuntime(
            provider=self.provider,
            skill_manager=self.skill_manager,
            session_store=SessionStore(self.workspace.path / "ai-state.db"),
            memory=self.memory,
            workspace_path=self.workspace.path,
            source="engine",
            system_prompt=self._build_system_prompt(),
        )
        self.executor = self.runtime.executor
        self.workspace = self.runtime.workspace
        self.conversation: list[ChatMessage] = [
            ChatMessage.system(self._build_system_prompt()),
        ]

        # Learning state
        self._last_tool_results: list[dict] = []
        self._last_tool_calls: list[str] = []

    def _build_system_prompt(self) -> str:
        """Build system prompt with available auto_choice skills."""
        generated = list_generated_skills()
        skill_list = ""
        for s in generated:
            if s.get("load_mode") == "auto_choice":
                skill_list += f"- **{s['name']}**: {s.get('description', '')}\n"
        if not skill_list:
            skill_list = "  (none — complex workflows will be auto-saved as skills)"
        return self.system_prompt.replace("{available_skills}", skill_list)

    def chat(self, user_message: str) -> str:
        """One turn: user message → runtime task lifecycle → response."""

        self._last_tool_results = []
        self._last_tool_calls = []

        self.runtime.skill_manager = self.skill_manager
        self.runtime.memory = self.memory
        self.runtime.system_prompt = self._build_system_prompt()
        result = self.runtime.run(
            user_message,
            extra_messages=self._explicit_context_messages(),
        )
        self.executor = self.runtime.executor
        self.workspace = self.runtime.workspace
        self.workspace.enter()
        self.conversation = list(self.runtime.messages)
        self._last_tool_calls = [record["name"] for record in result.tool_calls]
        self._last_tool_results = [record["result"] for record in result.tool_calls]

        if result.draft_skill:
            print(f"💾 draft skill: {result.draft_skill['name']} (/drafts to review)")

        return result.final_response

    def _explicit_context_messages(self) -> list[ChatMessage]:
        """Return deliberate REPL context without carrying prior task history."""
        return [
            message
            for message in self.conversation[1:]
            if message.role == "system"
        ]

    def _chat_loop(self, tools: list[dict]) -> str:
        """Core loop: LLM → tool_calls → execute → repeat until stop."""
        max_turns = 10
        for _ in range(max_turns):
            response = self.provider.chat(self.conversation, tools if tools else None)
            self.conversation.append(response.message)

            if response.finish_reason == "stop":
                return response.message.content

            if response.finish_reason == "length":
                return response.message.content + "\n[response truncated]"

            if response.tool_calls:
                for tc in response.tool_calls:
                    args_str = ", ".join(f"{k}={v}" for k, v in tc.arguments.items())
                    print(f"🔧 {tc.name}({args_str})")
                    result = self.executor.execute(tc)
                    if "error" in result:
                        print(f"❌ {tc.name}: {result['error'][:100]}")
                    else:
                        print(f"✅ {tc.name}")
                    self._last_tool_calls.append(tc.name)
                    self._last_tool_results.append(result)
                    self.conversation.append(ChatMessage.tool(
                        content=json.dumps(result, default=str),
                        tool_call_id=tc.id,
                    ))

        return self.conversation[-1].content or "[max turns reached]"

    def _learn(self, user_message: str, response: str) -> None:
        """Learn from this interaction — append to memory."""
        if not self._last_tool_results:
            return

        errors = [r for r in self._last_tool_results if "error" in r]
        success = [r for r in self._last_tool_results if "error" not in r]
        outcome = "success" if not errors else ("partial" if success else "failure")

        self.memory.append_learning({
            "user_intent": user_message[:200],
            "outcome": outcome,
            "tools_used": self._last_tool_calls,
            "insight": f"Used {', '.join(self._last_tool_calls)}. "
                       f"{len(success)} succeeded, {len(errors)} failed."
                       if errors else
                       f"All {len(success)} tool calls succeeded.",
        })

        # Auto-save skill for multi-step successes (3+ tools)
        if len(success) >= 3 and not errors:
            self._auto_save_skill(user_message)

    def _auto_save_skill(self, user_message: str) -> None:
        """Auto-save a multi-step success as a generated skill."""
        # Generate a short name from the first few tool calls
        name = "-".join(self._last_tool_calls[:3])
        if len(name) > 60:
            name = name[:57] + "..."

        # Don't save if skill already exists
        from .skill_loader import SKILLS_DIR
        existing = list(SKILLS_DIR.glob(f"{name}*.skill.md"))
        if existing:
            return

        tools = [{"function": tc, "args_template": {}} for tc in self._last_tool_calls]
        desc = f"Auto-saved workflow: {' → '.join(self._last_tool_calls)}"
        keywords = [w for w in user_message.lower().split() if len(w) > 3][:5]

        path = save_skill_md(
            name=name,
            description=desc,
            tools=tools,
            trigger_keywords=keywords,
            load_mode="auto_choice",
            body=f"# {desc}\n\nAuto-saved from: _{user_message[:100]}_\n",
        )
        print(f"💾 auto-saved skill: {path.name}")

    def repl(self) -> None:
        """Interactive REPL loop with /commands."""
        self.workspace.enter()
        from .provider import MODELS
        from .skill_loader import discover_builtin_skills

        discovered = discover_builtin_skills()
        model_desc = MODELS.get(self.provider.model, "")
        loaded_count = len(self.skill_manager._active)
        total_count = len(discovered)

        print("═" * 50)
        print(f"  ⚛️  MatSimPy AI REPL")
        print(f"  🧠 {self.provider.model} — {model_desc}")
        print(f"  📁 {self.workspace.path}")
        if total_count > 0:
            print(f"  📦 {total_count} skills ready ({loaded_count} loaded) | /skills to see all")
        print(f"  💡 Try: \"create fcc Cu and save to cu.vasp\"")
        print(f"  /help for commands  |  Ctrl+D to exit")
        print("═" * 50)

        if self.verbose:
            from .skill_loader import SKILLS_PKG
            print(f"  📂 skills path: {SKILLS_PKG}")
            for p in sorted(SKILLS_PKG.glob("*.py")):
                if not p.name.startswith("_"):
                    marker = "✓" if p.stem in self.skill_manager._active else " "
                    print(f"     [{marker}] {p.name}")
            print()

        while True:
            try:
                user_input = input("\n👤 › ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                self._handle_command(user_input)
                continue

            try:
                response = self.chat(user_input)
                print(f"\n🤖 › {response}")
            except Exception as e:
                print(f"\n⚠️ › Error: {e}")

    def _handle_command(self, cmd: str) -> None:
        """Handle REPL /commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/q", "/exit"):
            print("Goodbye.")
            raise EOFError

        elif command == "/workspace":
            if arg:
                new_path = arg
                self.workspace = Workspace(new_path)
                self.workspace.enter()
                self.runtime.workspace = self.workspace
                self.runtime.session_store.close()
                self.runtime.session_store = SessionStore(
                    self.workspace.path / "ai-state.db"
                )
                print(f"  Workspace changed to: {self.workspace.path}")
            else:
                print(f"  Current workspace: {self.workspace.path}")
                files = self.workspace.list_files()
                if files:
                    print(f"  Files: {', '.join(files[:10])}")
                    if len(files) > 10:
                        print(f"  ... +{len(files)-10} more")

        elif command == "/skills":
            if arg:
                # /skills <name> — show function details for a specific skill
                skill = self.skill_manager._skills.get(arg)
                if skill is None:
                    # Try generated skills
                    for g in list_generated_skills():
                        if g["name"] == arg:
                            print(f"\n  📦 {g['name']} (generated)")
                            print(f"  {g.get('description', '')}")
                            print(f"  Mode: {g.get('load_mode', 'auto_choice')}")
                            body = g.get("body", "")
                            if body:
                                print(f"\n{body[:1000]}")
                            return
                    print(f"  Skill '{arg}' not found. Use /skills to list all.")
                    return
                loaded = arg in self.skill_manager._active
                status = "✓ loaded" if loaded else "  ready"
                print(f"\n  📦 {skill.name}  {status}  {len(skill.functions)} funcs")
                print(f"  {skill.description}")
                if skill.keywords:
                    print(f"  Keywords: {', '.join(skill.keywords)}")
                print()
                for fn in skill.functions:
                    # Truncate description for display
                    desc = fn.description[:80] + "…" if len(fn.description) > 80 else fn.description
                    print(f"  {fn.name:30s}  {desc}")
                return

            # /skills (no arg) — list all skills
            from .skill_loader import discover_builtin_skills
            discovered = discover_builtin_skills()
            print(f"\n  Use /skills <name> for function details\n")
            for s in discovered:
                status = "✓ loaded" if s["name"] in self.skill_manager._active else "  ready"
                kw_preview = " ".join(s["keywords"][:5])
                if len(s["keywords"]) > 5:
                    kw_preview += " ..."
                if not s["keywords"]:
                    kw_preview = "always"
                print(f"  [{s['name']:20s}] {status:10s} {len(s['functions']):3d} funcs  {kw_preview}")
            # Show generated skills
            generated = list_generated_skills()
            if generated:
                print(f"\n  Generated ({len(generated)}):")
                for g in generated:
                    mode = g.get("load_mode", "auto_choice")
                    print(f"  [{g['name']:20s}] mode={mode:12s}  {g.get('description', '')[:50]}")
            if self.verbose:
                from .skill_loader import SKILLS_PKG
                print(f"\n  📂 builtin from: {SKILLS_PKG}")
                for p in sorted(SKILLS_PKG.glob("*.py")):
                    if not p.name.startswith("_"):
                        print(f"     {p.name}")

        elif command == "/load":
            if not arg:
                print("  Usage: /load <skill_name>")
                return
            for name in arg.split():
                try:
                    self.skill_manager.load(name)
                    print(f"  Loaded: {name}")
                except KeyError:
                    print(f"  Unknown: {name}")

        elif command == "/load-skill":
            if not arg:
                print("  Usage: /load-skill <skill_name>")
                return
            # Load a generated skill as context
            for s in list_generated_skills():
                if s["name"] == arg:
                    body = s.get("body", "")
                    self.conversation.append(ChatMessage.system(
                        f"[Loaded skill: {arg}]\n{body}"
                    ))
                    print(f"  Loaded skill context: {arg}")
                    return
            print(f"  Generated skill '{arg}' not found.")

        elif command == "/unload":
            if not arg:
                print("  Usage: /unload <skill_name>")
                return
            for name in arg.split():
                self.skill_manager.unload(name)
                print(f"  Unloaded: {name}")

        elif command == "/reload":
            from .skill_loader import discover_builtin_skills
            from .skill import Skill

            discovered = discover_builtin_skills()
            new_names = set()
            for s in discovered:
                if s["name"] not in self.skill_manager._skills:
                    skill = Skill(s["name"], s["description"], s["functions"])
                    skill.keywords = s["keywords"]
                    self.skill_manager.register(skill)
                    new_names.add(s["name"])
                    if self.verbose:
                        print(f"  ✓ registered: {s['name']} ({len(s['functions'])} funcs)")
                elif self.verbose:
                    print(f"  · unchanged: {s['name']}")
            if new_names:
                print(f"  📦 {len(new_names)} new skill(s): {', '.join(sorted(new_names))}")
            else:
                print(f"  📦 all {len(discovered)} skills up to date")

        elif command == "/model":
            from .provider import MODELS
            print(f"  Current: {self.provider.model}")
            for name, desc in MODELS.items():
                marker = " ← current" if name == self.provider.model else ""
                print(f"    {name:22s} {desc}{marker}")
            if arg and arg in MODELS:
                self.provider.model = arg
                print(f"  Switched to {arg}")

        elif command == "/memory":
            summary = self.memory.summary
            print(f"  Memory files ({self.memory.dir}):")
            for name, lines in summary.items():
                print(f"    {name}.md — {lines} lines")

        elif command == "/plan":
            result = self.runtime.last_result
            if result is None:
                print("  No task yet.")
                return
            tools = ", ".join(record["name"] for record in result.tool_calls)
            if not tools:
                tools = "none"
            print(f"  Tools: {tools}")
            print(f"  Validation: {result.validation_status}")

        elif command == "/trace":
            result = self.runtime.last_result
            if result is None:
                print("  No trace yet.")
                return
            print(f"  Session: {result.session_id}")
            print(f"  Trace: {result.trace_id if result.trace_id is not None else 'none'}")
            print(f"  Status: {result.status}")

        elif command == "/drafts":
            drafts = self.runtime.session_store.list_skill_drafts("draft")
            if not drafts:
                print("  No drafts.")
                return
            for draft in drafts:
                keywords = draft.get("trigger_keywords", [])
                keyword_text = ", ".join(keywords) if keywords else "no keywords"
                print(f"  {draft['name']}: {keyword_text}")

        elif command == "/approve-skill":
            if not arg:
                print("  Usage: /approve-skill <name>")
                return
            EvolutionManager(self.runtime.session_store).approve(arg)
            print(f"  Approved skill draft: {arg}")

        elif command == "/reject-skill":
            if not arg:
                print("  Usage: /reject-skill <name>")
                return
            EvolutionManager(self.runtime.session_store).reject(arg)
            print(f"  Rejected skill draft: {arg}")

        elif command == "/help":
            if arg:
                fn = self.skill_manager.find_function(arg)
                if fn:
                    print(f"\n  {fn.name}")
                    print(f"  Description: {fn.description}")
                    print(f"  Parameters: {json.dumps(fn.parameters, indent=2)}")
                    print(f"  Help: {fn.get_help()[:500]}")
                else:
                    # Search all registered functions for partial matches
                    all_fns = []
                    for skill in self.skill_manager._skills.values():
                        for f in skill.functions:
                            all_fns.append(f)
                    matches = [f.name for f in all_fns if arg.lower() in f.name.lower()]
                    if matches:
                        print(f"  Function '{arg}' not found. Did you mean: {', '.join(matches[:8])}?")
                    else:
                        loaded = self.skill_manager._active
                        print(f"  Function '{arg}' not found.")
                        print(f"  💡 Try /skills to see available skills, then /load one and use /help <fn>")
                        if loaded:
                            print(f"  Currently loaded: {', '.join(sorted(loaded))}")
            else:
                print("  📦 Skills")
                print("    /skills [name]        List skills, or show functions of a skill")
                print("    /load <name>          Load a builtin skill")
                print("    /load-skill <name>    Load a generated skill as context")
                print("    /unload <name>        Unload a skill")
                print("    /reload               Rescan skill directory (hot reload)")
                print()
                print("  🔧 Session")
                print("    /model [name]         Show or switch model")
                print("    /workspace [dir]      Show or change workspace")
                print("    /memory               Show memory file sizes")
                print("    /plan                 Show last task tools and validation")
                print("    /trace                Show last session trace status")
                print("    /drafts               List draft skills")
                print("    /approve-skill <name> Approve a draft skill")
                print("    /reject-skill <name>  Reject a draft skill")
                print("    /system <text>        Set custom system prompt")
                print("    /history              Show conversation")
                print("    /clear                Reset conversation")
                print()
                print("  💾 Data")
                print("    /save <path>          Save conversation as JSON")
                print("    /save-storage         Save to matsimpy storage backend")
                print("    /load-storage <id>    Load from storage backend")
                print()
                print("  🚪 /quit, /q, /exit     Exit REPL")

        elif command == "/system":
            if arg:
                self.system_prompt = arg
                self.runtime.system_prompt = arg
                self.conversation[0] = ChatMessage.system(arg)
                print(f"  System prompt updated ({len(arg)} chars).")

        elif command == "/history":
            for i, msg in enumerate(self.conversation):
                role = msg.role.upper()
                content = msg.content[:200]
                if msg.tool_calls:
                    content += f" [{len(msg.tool_calls)} tool calls]"
                print(f"  [{i}] {role}: {content}")

        elif command == "/clear":
            self.conversation = [ChatMessage.system(self._build_system_prompt())]
            self.runtime.messages = list(self.conversation)
            self.runtime.last_result = None
            self.executor._call_count = 0
            print("  Conversation cleared. Skills remain loaded.")

        elif command == "/save":
            path = arg or "conversation.json"
            data = {
                "system_prompt": self.system_prompt,
                "messages": [m.to_dict() for m in self.conversation],
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"  Saved to {path}")

        elif command == "/save-storage":
            try:
                from matsimpy.storage import DataStorage, MemoryBackend
                store = DataStorage(backend=MemoryBackend())
                meta = arg or ""
                doc_id = store.store_data({
                    "system_prompt": self.system_prompt,
                    "messages": [m.to_dict() for m in self.conversation],
                    "model": self.provider.model,
                }, metadata={"tag": meta, "type": "conversation"})
                store.close()
                print(f"  Saved to storage: {doc_id[:16]}...")
                print(f"  Use /load-storage {doc_id[:8]} to retrieve later.")
            except Exception as e:
                print(f"  Storage error: {e}")

        elif command == "/load-storage":
            if not arg:
                print("  Usage: /load-storage <doc_id_prefix>")
                return
            try:
                from matsimpy.storage import DataStorage, MemoryBackend
                store = DataStorage(backend=MemoryBackend())
                results = store.query({"metadata.type": "conversation"}, limit=50)
                store.close()
                for r in results:
                    if hasattr(r, 'formula'):
                        continue
                    mid = str(r.get("doc_id", "")) if isinstance(r, dict) else ""
                    if mid.startswith(arg):
                        # Load messages back
                        msgs = r.get("payload", r).get("messages", []) if isinstance(r, dict) else []
                        raw = r.get("payload", r) if isinstance(r, dict) else {}
                        msgs = raw.get("messages", [])
                        if msgs:
                            self.conversation = [
                                ChatMessage(**m) if isinstance(m, dict) else m
                                for m in msgs
                            ]
                            print(f"  Loaded {len(msgs)} messages from {mid[:16]}...")
                            return
                print(f"  No conversation found with prefix '{arg}'")
            except Exception as e:
                print(f"  Storage error: {e}")

        else:
            print(f"  Unknown: {command}. Try /help.")


__all__ = ["AIEngine"]
