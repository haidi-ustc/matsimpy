"""AIEngine — orchestrates provider, skills, executor, and REPL."""

from __future__ import annotations
import json
from .conversation import ChatMessage, ToolCall
from .provider import DeepSeekProvider
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
        self.workspace = Workspace(workspace_path)
        self.memory = AgentMemory()

        # Inject soul into system prompt
        soul = self.memory.get_soul_prompt()
        base_prompt = system_prompt or SYSTEM_PROMPT
        self.system_prompt = f"{base_prompt}\n\n{soul}" if soul.strip() else base_prompt

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
        """One turn: user message → LLM → tool execution loop → response."""
        self.workspace.enter()

        # Auto-load relevant skills
        loaded = self.skill_manager.auto_load(user_message)
        if loaded:
            print(f"[loaded skills: {', '.join(loaded)}]")

        self._last_tool_results = []
        self._last_tool_calls = []

        self.conversation.append(ChatMessage.user(user_message))
        tools = self.skill_manager.get_tools()

        response = self._chat_loop(tools)

        # Learn from this turn
        self._learn(user_message, response)

        return response

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
                    result = self.executor.execute(tc)
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
        print(f"[auto-saved skill: {path.name}]")

    def repl(self) -> None:
        """Interactive REPL loop with /commands."""
        self.workspace.enter()
        from .provider import MODELS
        model_desc = MODELS.get(self.provider.model, "")
        print("=" * 60)
        print(f"  MatSimPy AI REPL")
        print(f"  Model: {self.provider.model} — {model_desc}")
        print(f"  Workspace: {self.workspace.path}")
        print(f"  Memory: {self.memory.dir}")
        print("  Type /help for commands, Ctrl+D or /quit to exit")
        print("=" * 60)

        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                self._handle_command(user_input)
                continue

            try:
                response = self.chat(user_input)
                print(f"\n{response}")
            except Exception as e:
                print(f"\nError: {e}")

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
                print(f"  Workspace changed to: {self.workspace.path}")
            else:
                print(f"  Current workspace: {self.workspace.path}")
                files = self.workspace.list_files()
                if files:
                    print(f"  Files: {', '.join(files[:10])}")
                    if len(files) > 10:
                        print(f"  ... +{len(files)-10} more")

        elif command == "/skills":
            # Show builtin skills
            for s in self.skill_manager.list_skills():
                status = "✓ loaded" if s["loaded"] else "  ready"
                print(f"  [builtin] {s['name']:20s} {status:10s}  {s['functions']:3d} funcs")
            # Show generated skills
            generated = list_generated_skills()
            if generated:
                print(f"\n  Generated skills ({len(generated)}):")
                for s in generated:
                    mode = s.get("load_mode", "auto_choice")
                    print(f"  [generated] {s['name']:20s}  mode={mode:12s}  {s.get('description', '')[:50]}")

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

        elif command == "/help":
            if arg:
                fn = self.skill_manager.find_function(arg)
                if fn:
                    print(f"\n  {fn.name}")
                    print(f"  Description: {fn.description}")
                    print(f"  Parameters: {json.dumps(fn.parameters, indent=2)}")
                    print(f"  Help: {fn.get_help()[:500]}")
                else:
                    print(f"  Function '{arg}' not found.")
            else:
                print("  Commands:")
                print("  /skills           List skills (builtin + generated)")
                print("  /load <name>      Load builtin skill(s)")
                print("  /load-skill <name> Load a generated skill as context")
                print("  /unload <name>    Unload skill(s)")
                print("  /model [name]     Show or switch model")
                print("  /workspace [dir]  Show or change workspace")
                print("  /memory           Show memory file sizes")
                print("  /help [fn]        Show function help")
                print("  /system <text>    Set custom system prompt")
                print("  /history          Show conversation")
                print("  /clear            Reset conversation")
                print("  /save <path>      Save conversation as JSON")
                print("  /quit             Exit REPL")

        elif command == "/system":
            if arg:
                self.system_prompt = arg
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

        else:
            print(f"  Unknown: {command}. Try /help.")


__all__ = ["AIEngine"]
