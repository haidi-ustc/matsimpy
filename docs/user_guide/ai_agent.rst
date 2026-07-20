AI Agent and REPL
=================

Install the optional interface with ``pip install 'matsimpy[ai]'``. Provider
credentials are read from ``DEEPSEEK_API_KEY``; they are never skill metadata.
For offline tests or another provider, inject an object implementing
``ChatProvider``.

Python quickstart
-----------------

``Agent`` is the supported Python facade. A workspace contains artifacts and
its ``ai-state.db`` audit database::

   from matsimpy.ai import Agent

   agent = Agent(workspace="project")
   result = agent.run("Build FCC copper and save it as copper.cif")
   print(result.response, result.status)
   print(result.tools, result.artifacts, result.trace_id)

``AgentResult`` also exposes ``usage`` and inactive ``evolution_candidates``.
Use ``add_context(ChatMessage(...))``, ``conversation_messages()``, and
``switch_workspace(path)`` for explicit context, inspection, and isolation.
``review_evolution()``, ``approve_skill()``, ``reject_skill()``, and
``rollback_skill()`` implement the reviewed skill lifecycle. ``AgentSession``,
``AgentRuntime``, and ``ReplController`` remain public for custom clients, but
``Agent`` is the stable high-level entry point. ``AIEngine`` remains available
as a deprecated compatibility facade.

Diagnostics
-----------

Run local, secret-safe diagnostics before starting the REPL::

   matsimpy-ai doctor --workspace project

Doctor is offline by default and reports only whether credentials exist. Add
``--network`` to make one explicit provider connectivity request. The Python
equivalent is ``Doctor(workspace="project").run(network=False)``.

REPL commands
-------------

Start with ``matsimpy-ai --workspace project``. Commands return structured data
through ``ReplController``; terminal rendering is a separate layer.
In the enhanced terminal, Enter submits the current prompt and Esc+Enter inserts
a newline for multiline input.

============================  ===============================================
Command                       Effect
============================  ===============================================
``/new``                      Start a clean durable conversation
``/sessions``                 List saved conversations
``/resume <session-id>``      Restore the active branch after restart
``/retry``                    Replace the final turn with a linked retry
``/undo``                     Remove the final turn from active context
``/skills [query]``           List, search, or inspect skills
``/load-skill <name>``        Explicitly activate standard skill context
``/trace``                    Show the latest trace identity and status
``/usage``                    Show provider usage when available
``/drafts``                   List legacy draft records
``/evolve review [candidate]`` Evaluate and inspect candidate evidence
``/approve <version-id>``     Materialize an evaluated, approvable version
``/reject <version-id>``      Archive a candidate without activation
``/rollback <version-id>``    Create and activate a reviewed rollback version
``/quit`` (``/q``, ``/exit``) Exit
============================  ===============================================

``/approve-skill`` and ``/reject-skill`` are compatibility aliases. Approval
commands take a positive numeric version ID, not a skill name.

Standard Agent Skills
---------------------

A standard skill is a directory whose resolved name matches frontmatter
``name``::

   inspect-crystal/
   |-- SKILL.md
   `-- references/
       `-- workflow.md

``SKILL.md`` begins with YAML frontmatter::

   ---
   name: inspect-crystal
   description: Inspect a saved crystal
   compatibility: MatSimPy 0.8+
   allowed-tools: read_structure analyze_structure
   ---
   Read references/workflow.md, then use only the allowed tools.

Sources use precedence ``workspace > user > packaged``. Workspace skills live
under ``<workspace>/.matsimpy/skills`` and user skills under
``~/.matsimpy/ai/skills``. Higher-precedence definitions shadow lower ones with
a diagnostic. Discovery reads bounded metadata only; activation reads the body,
and resources are read only through explicit contained paths. Requested
``allowed-tools`` are intersected with the live catalog. Absolute paths,
escaping ``..`` paths, escaping symlinks, invalid UTF-8, malformed metadata,
and files over the size bound are rejected.

Legacy ``*.skill.md`` files can be converted without activation::

   from pathlib import Path
   from matsimpy.ai.skill_loader import migrate_legacy_skill

   result = migrate_legacy_skill(
       Path("legacy/example.skill.md"),
       Path.home() / ".matsimpy/ai/skills",
       dry_run=True,
   )

Review ``result.destination``, then repeat with ``dry_run=False``. Existing
non-identical destinations are never overwritten. Draft status is preserved,
so migrated drafts remain undiscoverable until approved.

Security and approval lifecycle
-------------------------------

Tool calls are schema validated and file outputs are workspace-relative.
Session attempts and traces are immutable audit evidence. A successful reusable
workflow may produce a draft, but no draft runs or becomes discoverable
automatically. The lifecycle is:

#. Draft from successful trace IDs and a current allowed-tool set.
#. ``/evolve review <version-id>`` performs static checks and deterministic
   replay in a temporary workspace limited to those tools.
#. Inspect provenance, diff, deterministic evidence, optional judge evidence,
   and ``approvable``.
#. Use ``/approve <version-id>`` or ``/reject <version-id>`` explicitly.
#. Revisions repeat review and approval. ``/rollback <version-id>`` creates a
   new audited version rather than rewriting history.

Approval rechecks the content hash and the live ``FunctionDef`` catalog, so a
candidate cannot be approved after its reviewed content or tool bindings change.
Evolved skills cannot install dependencies, run bundled scripts, edit MatSimPy
source, or use tools outside their recorded allow-list.
