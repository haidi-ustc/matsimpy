"""Agent runtime core for task-oriented AI execution."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .conversation import ChatMessage, ToolCall
from .evolution import EvolutionManager
from .executor import FunctionExecutor, _set_active_executor
from .memory import AgentMemory
from .providers import ChatProvider
from .session_store import SessionStore
from .skill import SkillManager
from .workspace import Workspace


RUNTIME_SYSTEM_PROMPT = """You are a materials science AI assistant powered by MatSimPy.
Use the available tools to complete the user's task, preserve intermediate structure
references exactly as returned, and give a concise final response with the result and
any saved files. If a tool fails, explain the failure and stop inventing evidence."""


@dataclass
class TaskResult:
    status: str
    final_response: str
    validation_status: str
    session_id: int
    trace_id: int | None = None
    tool_calls: list[dict] = field(default_factory=list)
    draft_skill: dict | None = None


class AgentRuntime:
    """Run a single task through provider chat, tools, persistence, and learning."""

    def __init__(
        self,
        provider: ChatProvider,
        skill_manager: SkillManager,
        session_store: SessionStore | None = None,
        memory: AgentMemory | None = None,
        workspace_path: str | Path | None = None,
        source: str = "cli",
        system_prompt: str = RUNTIME_SYSTEM_PROMPT,
        max_turns: int = 10,
    ):
        self.provider = provider
        self.skill_manager = skill_manager
        self.session_store = session_store or SessionStore()
        self.memory = memory or AgentMemory()
        self.workspace = Workspace(workspace_path)
        self.source = source
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.executor = FunctionExecutor(skill_manager)
        _set_active_executor(self.executor)
        self.messages = self._initial_messages()
        self.last_result: TaskResult | None = None

    def run(self, user_message: str) -> TaskResult:
        """Execute one user task and return persisted runtime evidence."""
        self.messages = self._initial_messages()
        self.executor = FunctionExecutor(self.skill_manager)
        _set_active_executor(self.executor)
        self.workspace.enter()
        session_id: int | None = None
        tool_records: list[dict] = []
        final_response = ""
        max_turns_reached = False
        trace_id: int | None = None

        try:
            self.skill_manager.auto_load(user_message)
            session_id = self.session_store.start_session(
                source=self.source,
                workspace=str(self.workspace.path),
                model=getattr(self.provider, "model", "unknown"),
                provider=type(self.provider).__name__,
            )
            self.messages.append(ChatMessage.user(user_message))
            self.session_store.add_message(session_id, "user", user_message)

            for _ in range(self.max_turns):
                tools = self.skill_manager.get_tools()
                response = self.provider.chat(
                    self.messages,
                    tools if tools else None,
                    tool_choice="auto",
                )
                self.messages.append(response.message)
                self.session_store.add_message(
                    session_id=session_id,
                    role=response.message.role,
                    content=response.message.content,
                    tool_calls=response.message.tool_calls,
                    tool_call_id=response.message.tool_call_id,
                )

                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        record = self._execute_tool_call(session_id, tool_call)
                        tool_records.append(record)
                    continue

                final_response = response.message.content
                if response.finish_reason == "length":
                    final_response = f"{final_response}\n[response truncated]"
                break
            else:
                max_turns_reached = True
                final_response = self.messages[-1].content or "[max turns reached]"

            validation_status = self._validate_tool_records(tool_records)
            if max_turns_reached:
                validation_status = "failure"
            status = "success" if validation_status == "success" else "failure"
            plan_summary = self._plan_summary(tool_records, max_turns_reached)
            trace_id = self.session_store.add_task_trace(
                session_id=session_id,
                user_request=user_message,
                plan_summary=plan_summary,
                validation_status=validation_status,
                final_response=final_response,
            )
            self.session_store.end_session(session_id, status)
            draft_skill = EvolutionManager(self.session_store).draft_from_trace(
                session_id=session_id,
                user_request=user_message,
                final_response=final_response,
                validation_status=validation_status,
            )

            self.last_result = TaskResult(
                status=status,
                final_response=final_response,
                validation_status=validation_status,
                session_id=session_id,
                trace_id=trace_id,
                tool_calls=tool_records,
                draft_skill=draft_skill,
            )
            return self.last_result
        except Exception as exc:
            self.last_result = self._finalize_runtime_failure(
                session_id=session_id,
                user_message=user_message,
                tool_records=tool_records,
                trace_id=trace_id,
                exc=exc,
            )
            return self.last_result
        finally:
            self.workspace.leave()

    def _initial_messages(self) -> list[ChatMessage]:
        prompt = self.system_prompt.strip()
        memory_context = self._compact_memory_context()
        if memory_context:
            prompt = f"{prompt}\n\nRelevant memory:\n{memory_context}"
        return [ChatMessage.system(prompt)]

    def _compact_memory_context(self, max_chars: int = 2400) -> str:
        chunks = []
        for name in ("user", "memory"):
            text = self.memory.read(name)
            tail = self._concise_tail(text)
            if tail:
                chunks.append(f"{name}.md:\n{tail}")
        context = "\n\n".join(chunks)
        if len(context) <= max_chars:
            return context
        return context[-max_chars:].lstrip()

    @staticmethod
    def _concise_tail(text: str, max_lines: int = 24) -> str:
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[-max_lines:])

    def _execute_tool_call(self, session_id: int, tool_call: ToolCall) -> dict:
        result = self.executor.execute(tool_call)
        status = self._validate_tool_result(result)
        self.session_store.add_tool_call(
            session_id=session_id,
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            result=result,
            status=status,
        )
        self.messages.append(
            ChatMessage.tool(
                content=json.dumps(result, default=str),
                tool_call_id=tool_call.id,
            )
        )
        self.session_store.add_message(
            session_id=session_id,
            role="tool",
            content=json.dumps(result, default=str),
            tool_call_id=tool_call.id,
        )
        return {
            "id": tool_call.id,
            "name": tool_call.name,
            "arguments": tool_call.arguments,
            "result": result,
            "status": status,
        }

    def _validate_tool_records(self, records: list[dict]) -> str:
        if any(record["status"] == "failure" for record in records):
            return "failure"
        return "success"

    def _validate_tool_result(self, result: dict[str, Any]) -> str:
        if "error" in result:
            return "failure"

        saved_to = result.get("saved_to")
        if saved_to is not None and not self.workspace.resolve(str(saved_to)).exists():
            return "failure"

        if "_obj_ref" in result and (
            "formula" not in result or "num_atoms" not in result
        ):
            return "failure"

        return "success"

    @staticmethod
    def _plan_summary(records: list[dict], max_turns_reached: bool) -> str:
        if max_turns_reached:
            return "Stopped after reaching the maximum runtime turns."
        if not records:
            return "Answered without tool execution."
        tools = ", ".join(record["name"] for record in records)
        return f"Executed tools: {tools}."

    def _finalize_runtime_failure(
        self,
        session_id: int | None,
        user_message: str,
        tool_records: list[dict],
        trace_id: int | None,
        exc: Exception,
    ) -> TaskResult:
        final_response = f"Runtime error: {type(exc).__name__}: {exc}"
        if session_id is None:
            return TaskResult(
                status="failure",
                final_response=final_response,
                validation_status="failure",
                session_id=-1,
                tool_calls=tool_records,
            )

        if trace_id is None:
            trace_id = self._try_add_failure_trace(
                session_id=session_id,
                user_message=user_message,
                tool_records=tool_records,
                final_response=final_response,
            )
        try:
            self.session_store.end_session(session_id, "failure")
        except Exception:
            pass

        return TaskResult(
            status="failure",
            final_response=final_response,
            validation_status="failure",
            session_id=session_id,
            trace_id=trace_id,
            tool_calls=tool_records,
        )

    def _try_add_failure_trace(
        self,
        session_id: int,
        user_message: str,
        tool_records: list[dict],
        final_response: str,
    ) -> int | None:
        try:
            return self.session_store.add_task_trace(
                session_id=session_id,
                user_request=user_message,
                plan_summary=self._plan_summary(tool_records, max_turns_reached=False),
                validation_status="failure",
                final_response=final_response,
            )
        except Exception:
            return None


__all__ = ["RUNTIME_SYSTEM_PROMPT", "TaskResult", "AgentRuntime"]
