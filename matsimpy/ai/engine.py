"""AIEngine — orchestrates provider, skills, executor, and REPL."""

from __future__ import annotations
import json
from .conversation import ChatMessage, ToolCall
from .provider import DeepSeekProvider
from .skill import SkillManager
from .executor import FunctionExecutor


SYSTEM_PROMPT = """You are a materials science AI assistant powered by MatSimPy.
You can create, modify, analyze, and store crystal and molecular structures.

Guidelines:
- Use the provided tools to call MatSimPy functions directly.
- When creating structures, suggest reasonable defaults if the user is vague.
- Explain what you're doing before calling tools.
- After getting results, summarize what was done and the key findings.
- If a tool returns an error, explain it to the user and suggest alternatives.
"""


class AIEngine:
    """Main entry point — orchestrates LLM + skills + execution + conversation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        system_prompt: str | None = None,
    ):
        self.provider = DeepSeekProvider(api_key, model, base_url)
        self.skill_manager = SkillManager()
        self.executor = FunctionExecutor(self.skill_manager)
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.conversation: list[ChatMessage] = [
            ChatMessage.system(self.system_prompt),
        ]

    def chat(self, user_message: str) -> str:
        """One turn: user message → LLM → tool execution loop → response."""
        # Auto-load relevant skills
        loaded = self.skill_manager.auto_load(user_message)
        if loaded:
            print(f"[loaded skills: {', '.join(loaded)}]")

        self.conversation.append(ChatMessage.user(user_message))
        tools = self.skill_manager.get_tools()

        # Main loop: call LLM, execute tools, feed back results
        return self._chat_loop(tools)

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

            # Execute tool calls
            if response.tool_calls:
                for tc in response.tool_calls:
                    result = self.executor.execute(tc)
                    self.conversation.append(ChatMessage.tool(
                        content=json.dumps(result, default=str),
                        tool_call_id=tc.id,
                    ))

        return self.conversation[-1].content or "[max turns reached]"

    def repl(self) -> None:
        """Interactive REPL loop with /commands."""
        from .provider import MODELS
        model_desc = MODELS.get(self.provider.model, "")
        print("=" * 60)
        print(f"  MatSimPy AI REPL")
        print(f"  Model: {self.provider.model} — {model_desc}")
        print(f"  Endpoint: {self.provider._endpoint}")
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

        elif command == "/skills":
            for s in self.skill_manager.list_skills():
                status = "✓ loaded" if s["loaded"] else "  ready"
                print(f"  {s['name']:20s} {status:10s}  {s['functions']:3d} funcs  ~{s['tokens_approx']} tok")
            if not self.skill_manager.list_skills():
                print("  No skills registered.")

        elif command == "/load":
            if not arg:
                print("  Usage: /load <skill_name>")
                return
            for name in arg.split():
                try:
                    self.skill_manager.load(name)
                    print(f"  Loaded skill: {name}")
                except KeyError:
                    print(f"  Unknown skill: {name}")

        elif command == "/unload":
            if not arg:
                print("  Usage: /unload <skill_name>")
                return
            for name in arg.split():
                self.skill_manager.unload(name)
                print(f"  Unloaded skill: {name}")

        elif command == "/model":
            from .provider import MODELS
            print(f"  Current: {self.provider.model}")
            print(f"  Available models:")
            for name, desc in MODELS.items():
                marker = " ← current" if name == self.provider.model else ""
                print(f"    {name:22s} {desc}{marker}")
            if arg and arg in MODELS:
                self.provider.model = arg
                self.provider._endpoint = f"{self.provider.base_url}/v1/chat/completions"
                print(f"  Switched to {arg}")

        elif command == "/help":
            if arg:
                fn = self.skill_manager.find_function(arg)
                if fn:
                    print(f"\n  {fn.name}")
                    print(f"  Description: {fn.description}")
                    print(f"  Parameters: {json.dumps(fn.parameters, indent=2)}")
                    print(f"  Help: {fn.get_help()[:500]}")
                else:
                    print(f"  Function '{arg}' not found in loaded skills.")
            else:
                print("  Commands:")
                print("  /skills           List all skills and load status")
                print("  /load <name>      Load skill(s) by name")
                print("  /model [name]     Show or switch model (v4-pro, v4-flash)")
                print("  /unload <name>    Unload skill(s)")
                print("  /help [function]  Show function help text")
                print("  /system <text>    Set custom system prompt")
                print("  /history          Show conversation messages")
                print("  /clear            Reset conversation")
                print("  /save <path>      Save conversation as JSON")
                print("  /quit             Exit REPL")

        elif command == "/system":
            if arg:
                self.system_prompt = arg
                self.conversation[0] = ChatMessage.system(arg)
                print(f"  System prompt updated ({len(arg)} chars).")
                print("  Use /clear to start a fresh conversation with this prompt.")

        elif command == "/history":
            for i, msg in enumerate(self.conversation):
                role = msg.role.upper()
                content = msg.content[:200]
                if msg.tool_calls:
                    content += f" [{len(msg.tool_calls)} tool calls]"
                print(f"  [{i}] {role}: {content}")

        elif command == "/clear":
            self.conversation = [ChatMessage.system(self.system_prompt)]
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
            print(f"  Unknown command: {command}. Try /help.")


__all__ = ["AIEngine"]
