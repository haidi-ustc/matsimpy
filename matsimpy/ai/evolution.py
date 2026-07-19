"""Generate reusable workflow skill drafts from successful AI traces."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping, Sequence

import yaml

from .agent_skills import SkillValidationError, parse_skill, validate_skill_name
from .conversation import ToolCall
from .executor import FunctionExecutor, active_executor
from .session_store import SessionStore, SkillVersion
from .skill import FunctionDef, Skill, SkillManager
from .workspace import Workspace

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_LEARN_RE = re.compile(
    r"(?:\b(?:remember|learn)\s+this\b|"
    r"\b(?:remember|learn|save)\b.{0,32}\b(?:workflow|procedure|for next time|how to)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvolutionCandidate:
    """A reviewable learning candidate derived from trace evidence."""

    kind: Literal["skill", "memory"]
    rationale: str
    source_trace_ids: tuple[int, ...]
    payload: dict[str, Any]


SemanticEvaluator = Callable[[Sequence[Mapping[str, Any]]], EvolutionCandidate | None]


@dataclass(frozen=True)
class ReplayContext:
    """Capability-limited deterministic replay environment."""

    workspace: Workspace
    executor: FunctionExecutor
    allowed_tools: frozenset[str]
    tool_catalog: Mapping[str, FunctionDef]

    def execute(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Execute only a tool explicitly granted to this skill version."""
        if name not in self.allowed_tools:
            return {"error": f"Tool is not allowed during replay: {name}"}
        return self.executor.execute(
            ToolCall(id="evolution-replay", name=name, arguments=dict(arguments))
        )

    def artifact_path(self, relative_path: str) -> Path:
        """Resolve a non-symlink artifact path constrained to the workspace."""
        requested = Path(relative_path)
        if requested.is_absolute():
            raise SkillEvolutionError("artifact path escapes replay workspace")
        candidate = (self.workspace.path / requested).resolve(strict=False)
        if not candidate.is_relative_to(self.workspace.path):
            raise SkillEvolutionError("artifact path escapes replay workspace")
        return candidate


ReplayRunner = Callable[[SkillVersion, ReplayContext], Mapping[str, Any]]


class SkillEvolutionError(ValueError):
    """Raised when a skill version cannot safely advance its lifecycle."""


_FORBIDDEN_INSTRUCTIONS = (
    (
        re.compile(r"\bscripts?\s*[/\\]", re.IGNORECASE),
        "scripts cannot be executed by evolved skills",
    ),
    (
        re.compile(r"\b(?:pip|conda|uv|poetry|npm)\s+install\b", re.IGNORECASE),
        "dependencies cannot be installed by evolved skills",
    ),
    (
        re.compile(
            r"\b(?:edit|modify|patch|rewrite|update)\b.{0,80}"
            r"\b(?:matsimpy\s*[/\\]|\.py\b)",
            re.IGNORECASE,
        ),
        "source edits are not allowed in evolved skills",
    ),
    (
        re.compile(r"\bSOUL\.md\b", re.IGNORECASE),
        "SOUL.md edits are not allowed in evolved skills",
    ),
)


class EvolutionPolicy:
    """Classify reusable experience using deterministic evidence first."""

    def __init__(self, evaluator: SemanticEvaluator | None = None):
        self.evaluator = evaluator

    def classify(
        self,
        trace_history: Sequence[Mapping[str, Any]],
        correction: str | None = None,
        source_trace_id: int | None = None,
    ) -> EvolutionCandidate | None:
        successful = [
            trace for trace in trace_history
            if trace.get("validation_status") == "success"
        ]
        if correction is not None and correction.strip():
            if source_trace_id is not None:
                if (
                    isinstance(source_trace_id, bool)
                    or not isinstance(source_trace_id, int)
                    or source_trace_id <= 0
                ):
                    raise ValueError("source_trace_id must be a positive integer")
                if not any(
                    trace.get("trace_id") == source_trace_id
                    for trace in trace_history
                ):
                    raise ValueError("source_trace_id is not present in trace_history")
                provenance_ids = (source_trace_id,)
            elif trace_history:
                provenance_ids = _trace_ids([trace_history[-1]])
            else:
                provenance_ids = ()
            return EvolutionCandidate(
                "memory",
                "explicit user correction",
                provenance_ids,
                {
                    "content": correction.strip(),
                    "confidence": 1.0,
                    "provenance": "trace" if provenance_ids else "explicit_request",
                },
            )
        if not successful:
            return None

        latest = successful[-1]
        if _LEARN_RE.search(str(latest.get("user_request", ""))):
            return EvolutionCandidate(
                "skill",
                "explicit learn request",
                _trace_ids([latest]),
                {"tool_sequence": _tool_sequence(latest)},
            )

        if has_corrective_retry(latest.get("tool_calls", ())):
            return EvolutionCandidate(
                "skill",
                "validated recovery from tool failure",
                _trace_ids([latest]),
                {"tool_sequence": _tool_sequence(latest)},
            )

        latest_sequence = tuple(_tool_sequence(latest))
        matches = [
            trace for trace in successful
            if latest_sequence and tuple(_tool_sequence(trace)) == latest_sequence
        ]
        if len(matches) >= 2:
            return EvolutionCandidate(
                "skill",
                "repeated validated workflow",
                _trace_ids(matches),
                {"tool_sequence": list(latest_sequence), "occurrences": len(matches)},
            )

        sequence = _tool_sequence(latest)
        if len(sequence) >= 3:
            return EvolutionCandidate(
                "skill",
                "nontrivial validated workflow",
                _trace_ids([latest]),
                {"tool_sequence": sequence},
            )

        if self.evaluator is not None:
            return self.evaluator(trace_history)
        return None


class EvolutionManager:
    """Manage semi-automatic skill draft evolution from validated sessions."""

    def __init__(
        self,
        store: SessionStore,
        policy: EvolutionPolicy | None = None,
        *,
        user_skill_root: str | Path | None = None,
        available_tools: Mapping[str, Any] | Sequence[str] | set[str] | None = None,
        replay: ReplayRunner | None = None,
    ):
        self.store = store
        self.policy = policy or EvolutionPolicy()
        self.user_skill_root = Path(
            user_skill_root or Path.home() / ".matsimpy" / "ai" / "skills"
        )
        self.available_tools = frozenset(
            available_tools.keys()
            if isinstance(available_tools, Mapping)
            else (available_tools or ())
        )
        self._tool_definitions = {
            name: definition
            for name, definition in (
                available_tools.items() if isinstance(available_tools, Mapping) else ()
            )
            if isinstance(definition, FunctionDef)
        }
        self._catalog_errors = tuple(
            f"tool {name!r} does not resolve to a matching FunctionDef"
            for name in self.available_tools
            if name not in self._tool_definitions
            or self._tool_definitions[name].name != name
        )
        self.replay = replay

    def set_tool_catalog(self, tools: Mapping[str, FunctionDef]) -> None:
        """Refresh executable definitions without replacing lifecycle state."""
        self.available_tools = frozenset(tools)
        self._tool_definitions = dict(tools)
        self._catalog_errors = tuple(
            f"tool {name!r} does not resolve to a matching FunctionDef"
            for name, definition in tools.items()
            if not isinstance(definition, FunctionDef) or definition.name != name
        )

    def review(
        self,
        candidate: int | str | None = None,
        *,
        judge_result: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Evaluate and render inactive candidates before an approval decision."""
        if candidate is None:
            legacy = [
                self._legacy_review(draft)
                for draft in self.store.list_skill_drafts("draft")
            ]
            versions = [
                self._version_review(version)
                for version in self.store.list_skill_versions()
                if version.status in {"draft", "evaluated"}
            ]
            return [*legacy, *versions]
        if isinstance(candidate, str):
            draft = self._find_draft(candidate)
            if draft is None:
                raise KeyError(f"Unknown generated skill draft: {candidate}")
            rationale = self._legacy_review(draft)["rationale"]
            version = self._migrate_legacy_draft(candidate)
        else:
            rationale = None
            version = self.store.get_skill_version(candidate)
        if version.status == "draft":
            version = self.evaluate(version.id, judge_result=judge_result)
        reviewed = self._version_review(version)
        if rationale is not None:
            reviewed["rationale"] = rationale
        return reviewed

    @staticmethod
    def _version_review(version: SkillVersion) -> dict[str, Any]:
        return {
            "version_id": version.id,
            "name": version.name,
            "version": version.version,
            "status": version.status,
            "rationale": "revision" if version.parent_version_id else "new reusable workflow",
            "source_trace_ids": list(version.source_trace_ids),
            "deterministic_evidence": version.deterministic_result,
            "judge_evidence": version.judge_result,
            "content_diff": version.diff,
            "approvable": version.approvable,
        }

    @staticmethod
    def _legacy_review(draft: Mapping[str, Any]) -> dict[str, Any]:
        evolution = draft.get("metadata", {}).get("evolution", {})
        return {
            "version_id": None,
            "name": draft["name"],
            "status": draft["status"],
            "rationale": evolution.get("rationale", "legacy workflow candidate"),
            "source_trace_ids": list(evolution.get("source_trace_ids", ())),
            "deterministic_evidence": None,
            "judge_evidence": None,
            "content_diff": "",
            "approvable": False,
        }

    def draft_skill(
        self,
        name: str,
        description: str,
        body: str,
        tools: Sequence[str],
        source_trace_ids: Sequence[int],
    ) -> SkillVersion:
        """Create an inactive first version after static safety validation."""
        if self._versions_for(name):
            raise SkillEvolutionError(f"skill {name!r} already exists; draft a revision")
        return self._create_version(
            name=name,
            description=description,
            body=body,
            tools=tools,
            source_trace_ids=source_trace_ids,
            parent=None,
        )

    def draft_revision(
        self,
        parent_version_id: int,
        *,
        description: str | None = None,
        body: str | None = None,
        tools: Sequence[str] | None = None,
        source_trace_ids: Sequence[int],
    ) -> SkillVersion:
        """Create an inactive child version and retain its unified diff."""
        parent = self.store.get_skill_version(parent_version_id)
        try:
            active = self.store.get_active_skill_version(parent.name)
        except KeyError as exc:
            raise SkillEvolutionError(
                "revision parent must be the active approved version"
            ) from exc
        if parent.status != "approved" or active.id != parent.id:
            raise SkillEvolutionError(
                "revision parent must be the active approved version"
            )
        return self._create_version(
            name=parent.name,
            description=description if description is not None else parent.description,
            body=body if body is not None else parent.body,
            tools=tools if tools is not None else parent.allowed_tools,
            source_trace_ids=source_trace_ids,
            parent=parent,
        )

    def evaluate(
        self, version_id: int, judge_result: Mapping[str, Any] | None = None
    ) -> SkillVersion:
        """Validate and replay a draft in isolation before it can be approved."""
        version = self.store.get_skill_version(version_id)
        if version.status != "draft":
            raise SkillEvolutionError(f"cannot evaluate {version.status} skill version")
        content_hash = self._content_hash(version)
        if content_hash != version.content_hash:
            raise SkillEvolutionError("skill content hash does not match immutable draft")
        self._validate_content(
            version.name, version.description, version.body, version.allowed_tools
        )
        if self._catalog_errors:
            raise SkillEvolutionError(
                "invalid executable tool catalog: " + "; ".join(self._catalog_errors)
            )
        unresolved = [
            name
            for name in version.allowed_tools
            if name not in self._tool_definitions
            or self._tool_definitions[name].name != name
        ]
        if unresolved:
            raise SkillEvolutionError(
                "deterministic replay requires concrete FunctionDef entries: "
                + ", ".join(sorted(unresolved))
            )
        if self.replay is None:
            result: Mapping[str, Any] = {
                "passed": False,
                "error": "no deterministic replay runner configured",
            }
        else:
            with tempfile.TemporaryDirectory(
                prefix="matsimpy-skill-replay-"
            ) as workspace:
                context = self._replay_context(Path(workspace), version.allowed_tools)
                with context.workspace.activate(), active_executor(context.executor):
                    result = self.replay(version, context)
                self._validate_replay_artifacts(context, result)
        if not isinstance(result, Mapping) or not isinstance(result.get("passed"), bool):
            raise SkillEvolutionError("deterministic replay must return a boolean 'passed' result")
        deterministic_pass = bool(result["passed"])
        judge = dict(judge_result) if judge_result is not None else None
        judge_pass = judge is None or judge.get("passed") is True
        return self.store.evaluate_skill_version(
            version_id, deterministic_pass, dict(result), judge,
            content_hash,
            approvable=deterministic_pass and judge_pass,
        )

    def approve(self, version: int | str) -> SkillVersion | None:
        """Atomically materialize an evaluated version, or support legacy names."""
        if isinstance(version, str):
            migrated = self._migrate_legacy_draft(version)
            raise SkillEvolutionError(
                f"legacy draft migrated to version {migrated.id}; "
                "evaluate and approve that version id"
            )
        record = self.store.get_skill_version(version)
        if record.status != "evaluated" or not record.approvable:
            raise SkillEvolutionError("skill version is not approvable")
        content_hash = self._content_hash(record)
        if (
            content_hash != record.content_hash
            or record.evaluated_hash != record.content_hash
        ):
            raise SkillEvolutionError("skill content changed after evaluation")
        self._validate_content(
            record.name, record.description, record.body, record.allowed_tools
        )
        return self._approve_with_compensation(record)

    def reject(self, version: int | str) -> SkillVersion | None:
        """Reject a version without deleting its evidence; retain legacy support."""
        if isinstance(version, str):
            self.store.set_skill_draft_status(version, "archived")
            return None
        record = self.store.get_skill_version(version)
        if record.status == "approved":
            raise SkillEvolutionError("an approved version cannot be rejected")
        return self.store.set_skill_version_status(record.id, "rejected")

    def rollback(
        self,
        target_version_id: int | str,
        *,
        source_trace_ids: Sequence[int] | None = None,
    ) -> SkillVersion:
        """Create and activate a new approved version containing prior content."""
        if isinstance(target_version_id, str):
            if not hasattr(self.store, "conn"):
                raise SkillEvolutionError("skill rollback is not available for this store")
            row = self.store.conn.execute(
                """SELECT id FROM skill_versions
                   WHERE name = ? AND status = 'approved' AND active = 0
                   ORDER BY version DESC LIMIT 1""",
                (target_version_id,),
            ).fetchone()
            if row is None:
                raise SkillEvolutionError(
                    f"no prior approved version is available for {target_version_id!r}"
                )
            target_version_id = int(row[0])
        target = self.store.get_skill_version(target_version_id)
        if target.status != "approved":
            raise SkillEvolutionError("rollback target must be an approved version")
        current = self.store.get_active_skill_version(target.name)
        provenance = (
            tuple(source_trace_ids)
            if source_trace_ids is not None
            else target.source_trace_ids
        )
        rolled_back = self._create_version(
            name=target.name,
            description=target.description,
            body=target.body,
            tools=target.allowed_tools,
            source_trace_ids=provenance,
            parent=current,
            rollback_of_version_id=target.id,
        )
        self.store.prepend_skill_version_diff(
            rolled_back.id,
            f"Rollback target: skill_version_id={target.id}, version={target.version}\n",
        )
        rolled_back = self.store.get_skill_version(rolled_back.id)
        evaluated = self.evaluate(rolled_back.id)
        return self.approve(evaluated.id)  # type: ignore[return-value]

    def _create_version(
        self,
        *,
        name: str,
        description: str,
        body: str,
        tools: Sequence[str],
        source_trace_ids: Sequence[int],
        parent: SkillVersion | None,
        rollback_of_version_id: int | None = None,
    ) -> SkillVersion:
        normalized_tools = tuple(dict.fromkeys(tools))
        self._validate_content(name, description, body, normalized_tools)
        traces = tuple(source_trace_ids)
        if not traces:
            raise SkillEvolutionError("at least one source trace id is required")
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in traces
        ):
            raise SkillEvolutionError("source trace ids must be positive integers")
        if traces:
            placeholders = ",".join("?" for _ in traces)
            rows = self.store.conn.execute(
                f"SELECT id FROM task_traces WHERE id IN ({placeholders})", traces
            ).fetchall()
            found = {int(row[0]) for row in rows}
            missing = sorted(set(traces) - found)
            if missing:
                raise SkillEvolutionError(
                    f"source trace ids do not exist: {', '.join(map(str, missing))}"
                )
        content = self._standard_content(
            name, description, body, normalized_tools, "draft"
        )
        diff = "".join(
            difflib.unified_diff(
                (),
                content.splitlines(True),
                fromfile="/dev/null",
                tofile="draft",
            )
        )
        if parent is not None:
            before = self._standard_content(
                parent.name,
                parent.description,
                parent.body,
                parent.allowed_tools,
                "approved",
            )
            diff = "".join(
                difflib.unified_diff(
                    before.splitlines(True),
                    content.splitlines(True),
                    fromfile=f"v{parent.version}",
                    tofile="draft",
                )
            )
        return self.store.create_skill_version(
            name=name,
            description=description,
            body=body,
            allowed_tools=normalized_tools,
            source_trace_ids=traces,
            content_hash=hashlib.sha256(content.encode()).hexdigest(),
            parent_version_id=parent.id if parent else None,
            rollback_of_version_id=rollback_of_version_id,
            diff=diff,
        )

    def _validate_content(
        self, name: str, description: str, body: str, tools: Sequence[str]
    ) -> None:
        try:
            validate_skill_name(name, Path(name))
        except SkillValidationError as exc:
            raise SkillEvolutionError(str(exc)) from exc
        if (
            not isinstance(description, str)
            or not description.strip()
            or len(description) > 1024
        ):
            raise SkillEvolutionError("description must be 1-1024 characters")
        unknown = sorted(set(tools) - self.available_tools)
        if unknown:
            raise SkillEvolutionError(
                f"unknown tool permission requested: {', '.join(unknown)}"
            )
        for pattern, message in _FORBIDDEN_INSTRUCTIONS:
            if pattern.search(body):
                raise SkillEvolutionError(message)
        with tempfile.TemporaryDirectory(prefix="matsimpy-skill-validate-") as temporary:
            root = Path(temporary) / name
            root.mkdir()
            (root / "SKILL.md").write_text(
                self._standard_content(name, description, body, tools, "draft"),
                encoding="utf-8",
            )
            try:
                parse_skill(root)
            except SkillValidationError as exc:
                raise SkillEvolutionError(str(exc)) from exc

    @staticmethod
    def _standard_content(
        name: str, description: str, body: str, tools: Sequence[str], status: str
    ) -> str:
        frontmatter: dict[str, Any] = {
            "name": name,
            "description": description,
            "metadata": {"matsimpy": {"status": status}},
        }
        if tools:
            frontmatter["allowed-tools"] = " ".join(tools)
        dumped = yaml.safe_dump(frontmatter, sort_keys=False)
        return f"---\n{dumped}---\n{body.strip()}\n"

    def _stage_materialization(self, version: SkillVersion) -> tuple[Path, bytes | None]:
        self.user_skill_root.mkdir(parents=True, exist_ok=True)
        root = self.user_skill_root.resolve(strict=True)
        if self.user_skill_root.is_symlink():
            raise SkillEvolutionError("user skill root must not be a symlink")
        destination = self.user_skill_root / version.name
        if not destination.resolve(strict=False).is_relative_to(root):
            raise SkillEvolutionError("skill destination escapes user skill root")
        if destination.is_symlink():
            raise SkillEvolutionError("skill destination must not be a symlink")
        if destination.exists():
            unexpected = [
                item for item in destination.iterdir() if item.name != "SKILL.md"
            ]
            if unexpected:
                raise SkillEvolutionError(
                    "approval will not retain scripts or other bundled resources"
                )
        else:
            destination.mkdir()
        content = self._standard_content(
            version.name,
            version.description,
            version.body,
            version.allowed_tools,
            "approved",
        )
        target = destination / "SKILL.md"
        if target.is_symlink():
            raise SkillEvolutionError("active SKILL.md must not be a symlink")
        prior = target.read_bytes() if target.exists() else None
        fd, temporary = tempfile.mkstemp(prefix=".SKILL.md.tmp-", dir=destination)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return Path(temporary), prior

    def _approve_with_compensation(self, version: SkillVersion) -> SkillVersion:
        try:
            prior = self.store.get_active_skill_version(version.name)
        except KeyError:
            prior = None
        staged, prior_bytes = self._stage_materialization(version)
        target = self.user_skill_root / version.name / "SKILL.md"
        published = False
        activated = False
        try:
            os.replace(staged, target)
            published = True
            approved = self.store.set_skill_version_status(
                version.id, "approved", activate=True, expected_status="evaluated"
            )
            activated = True
            return approved
        except BaseException:
            staged.unlink(missing_ok=True)
            if published:
                if prior_bytes is None:
                    target.unlink(missing_ok=True)
                    try:
                        target.parent.rmdir()
                    except OSError:
                        pass
                else:
                    restore_fd, restore_name = tempfile.mkstemp(
                        prefix=".SKILL.md.restore-", dir=target.parent
                    )
                    with os.fdopen(restore_fd, "wb") as stream:
                        stream.write(prior_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(restore_name, target)
            try:
                persisted = self.store.get_active_skill_version(version.name)
                activated = persisted.id == version.id
            except KeyError:
                pass
            if activated:
                self.store.restore_skill_activation(
                    version.id, prior.id if prior is not None else None
                )
            raise

    def _replay_context(
        self, workspace: Path, allowed_tools: Sequence[str]
    ) -> ReplayContext:
        definitions = [
            self._tool_definitions[name]
            for name in allowed_tools
            if name in self._tool_definitions
        ]
        skill = Skill("evolution-replay", "Restricted skill replay", definitions)
        manager = SkillManager({skill.name: skill})
        manager.load(skill.name)
        return ReplayContext(
            workspace=Workspace(workspace),
            executor=FunctionExecutor(manager),
            allowed_tools=frozenset(allowed_tools),
            tool_catalog=MappingProxyType(
                {definition.name: definition for definition in definitions}
            ),
        )

    def _validate_replay_artifacts(
        self, context: ReplayContext, result: Mapping[str, Any]
    ) -> None:
        for item in context.workspace.path.rglob("*"):
            if item.is_symlink():
                raise SkillEvolutionError("replay artifact must not be a symlink")
            if not item.resolve().is_relative_to(context.workspace.path):
                raise SkillEvolutionError("replay artifact escapes workspace")
        artifacts = result.get("artifacts", ()) if isinstance(result, Mapping) else ()
        if isinstance(artifacts, (str, bytes)):
            artifacts = (artifacts,)
        for artifact in artifacts:
            if not isinstance(artifact, str):
                raise SkillEvolutionError("replay artifact paths must be strings")
            path = context.artifact_path(artifact)
            if not path.exists() or not path.is_file() or path.is_symlink():
                raise SkillEvolutionError(
                    f"declared replay artifact is not a regular file: {artifact}"
                )

    def _content_hash(self, version: SkillVersion) -> str:
        content = self._standard_content(
            version.name,
            version.description,
            version.body,
            version.allowed_tools,
            "draft",
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _migrate_legacy_draft(self, name: str) -> SkillVersion:
        draft = self._find_draft(name)
        if draft is None:
            raise KeyError(f"Unknown generated skill draft: {name}")
        metadata = draft.get("metadata", {})
        evolution = metadata.get("evolution", {})
        trace_ids = evolution.get("source_trace_ids", [])
        if not trace_ids and draft.get("source_session_id") is not None:
            rows = self.store.conn.execute(
                "SELECT id FROM task_traces WHERE session_id = ? ORDER BY id",
                (draft["source_session_id"],),
            ).fetchall()
            trace_ids = [int(row[0]) for row in rows]
        version = self.draft_skill(
            name=name,
            description=metadata.get("description")
            or f"Generated skill draft for {name}",
            body=draft.get("body", ""),
            tools=[item["function"] for item in _normalize_tools(metadata.get("tools", []))],
            source_trace_ids=trace_ids,
        )
        self.store.set_skill_draft_status(name, "archived")
        return version

    def _versions_for(self, name: str) -> list[int]:
        rows = self.store.conn.execute(
            "SELECT id FROM skill_versions WHERE name = ?", (name,)
        ).fetchall()
        return [int(row[0]) for row in rows]

    def draft_from_trace(
        self,
        session_id: int,
        user_request: str,
        final_response: str,
        validation_status: str,
    ) -> dict | None:
        """Create a draft skill from a successful trace with reusable tool evidence."""
        if validation_status != "success":
            return None

        tool_calls = self._tool_calls(session_id)
        trace_history = self._trace_history()
        if not any(trace.get("session_id") == session_id for trace in trace_history):
            trace_id = self.store.add_task_trace(
                session_id=session_id,
                user_request=user_request,
                plan_summary="generated evolution evidence",
                validation_status=validation_status,
                final_response=final_response,
                tool_names=[call["tool_name"] for call in tool_calls],
            )
            trace_history.append({
                "trace_id": trace_id,
                "session_id": session_id,
                "user_request": user_request,
                "validation_status": validation_status,
                "tool_calls": tool_calls,
            })
        candidate = self.policy.classify(trace_history)
        if candidate is None or candidate.kind != "skill":
            return None

        tool_calls = [call for call in tool_calls if call["status"] == "success"]

        tools = [call["tool_name"] for call in tool_calls]
        name = self._unique_draft_name(_slug(user_request))
        trigger_keywords = _keywords(user_request)
        body = self._draft_body(user_request, final_response, validation_status, tool_calls)
        metadata = {
            "tools": tools,
            "source_request": user_request,
            "validation_status": validation_status,
            "final_response": final_response,
            "evolution": {
                "kind": candidate.kind,
                "rationale": candidate.rationale,
                "source_trace_ids": list(candidate.source_trace_ids),
                "payload": candidate.payload,
            },
        }

        self.store.save_skill_draft(
            name=name,
            status="draft",
            source_session_id=session_id,
            trigger_keywords=trigger_keywords,
            body=body,
            metadata=metadata,
        )

        drafts = self.store.list_skill_drafts(None)
        for draft in drafts:
            if draft["name"] == name:
                return draft
        return {
            "name": name,
            "status": "draft",
            "source_session_id": session_id,
            "trigger_keywords": trigger_keywords,
            "body": body,
            "metadata": metadata,
        }

    def _unique_draft_name(self, base_name: str) -> str:
        existing_names = {draft["name"] for draft in self.store.list_skill_drafts(None)}
        if base_name not in existing_names:
            return base_name

        suffix = 2
        while f"{base_name}-{suffix}" in existing_names:
            suffix += 1
        return f"{base_name}-{suffix}"

    def _find_draft(self, name: str) -> dict | None:
        for draft in self.store.list_skill_drafts(status=None):
            if draft["name"] == name:
                return draft
        return None

    def _tool_calls(self, session_id: int) -> list[dict]:
        rows = self.store.conn.execute(
            """
            SELECT tool_name, arguments_json, result_json, status
            FROM tool_calls
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()
        return [
            {
                "tool_name": row["tool_name"],
                "arguments": _json_load(row["arguments_json"], {}),
                "result": _json_load(row["result_json"], {}),
                "status": row["status"],
            }
            for row in rows
        ]

    def _trace_history(self) -> list[dict]:
        rows = self.store.conn.execute(
            """
            SELECT id, session_id, user_request, validation_status
            FROM task_traces
            ORDER BY id
            """
        ).fetchall()
        return [
            {
                "trace_id": row["id"],
                "session_id": row["session_id"],
                "user_request": row["user_request"],
                "validation_status": row["validation_status"],
                "tool_calls": self._tool_calls(row["session_id"]),
            }
            for row in rows
        ]

    @staticmethod
    def _draft_body(
        user_request: str,
        final_response: str,
        validation_status: str,
        tool_calls: list[dict],
    ) -> str:
        lines = [
            f"# {_title(user_request)}",
            "",
            "## Source request",
            user_request,
            "",
            "## Procedure",
        ]
        for index, call in enumerate(tool_calls, 1):
            lines.append(f"{index}. Run `{call['tool_name']}` with arguments:")
            lines.append(f"   `{json.dumps(call['arguments'], sort_keys=True, default=str)}`")
            lines.append("   Expected evidence:")
            lines.append(f"   `{json.dumps(call['result'], sort_keys=True, default=str)}`")

        lines.extend(
            [
                "",
                "## Validation evidence",
                f"- Status: {validation_status}",
                f"- Final response: {final_response}",
            ]
        )
        return "\n".join(lines) + "\n"


def _json_load(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _trace_ids(traces: Sequence[Mapping[str, Any]]) -> tuple[int, ...]:
    return tuple(
        int(trace["trace_id"])
        for trace in traces
        if trace.get("trace_id") is not None
    )


def _tool_sequence(trace: Mapping[str, Any]) -> list[str]:
    tools = trace.get("tools")
    if isinstance(tools, (list, tuple)):
        return [str(tool) for tool in tools]
    calls = trace.get("tool_calls", ())
    return [
        str(call.get("name", call.get("tool_name")))
        for call in calls
        if isinstance(call, Mapping)
        and call.get("status") == "success"
        and call.get("name", call.get("tool_name")) is not None
    ]


def has_corrective_retry(calls: Any) -> bool:
    """Return whether every failed operation is retried successfully later."""
    if not isinstance(calls, (list, tuple)):
        return False
    unresolved: set[str] = set()
    failure_seen = False
    for call in calls:
        if not isinstance(call, Mapping):
            continue
        name = call.get("name", call.get("tool_name"))
        if not isinstance(name, str) or not name:
            continue
        if call.get("status") == "failure":
            unresolved.add(name)
            failure_seen = True
        elif call.get("status") == "success":
            unresolved.discard(name)
    return failure_seen and not unresolved


def _normalize_tools(tools: Any) -> list[dict]:
    if not isinstance(tools, list):
        return []

    normalized = []
    for tool in tools:
        if isinstance(tool, str):
            normalized.append({"function": tool})
        elif isinstance(tool, dict):
            if "function" in tool:
                normalized.append(tool)
            elif "name" in tool:
                normalized.append({**tool, "function": tool["name"]})
    return normalized


def _keywords(text: str) -> list[str]:
    seen = set()
    result = []
    for token in _TOKEN_RE.findall(text.lower()):
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result[:12]


def _slug(text: str) -> str:
    keywords = _keywords(text)
    if not keywords:
        return "generated-skill"
    return "-".join(keywords[:8])


def _title(text: str) -> str:
    words = _keywords(text)
    if not words:
        return "Generated Skill Draft"
    return " ".join(word.capitalize() for word in words[:8])


__all__ = [
    "EvolutionCandidate",
    "EvolutionManager",
    "EvolutionPolicy",
    "has_corrective_retry",
]
