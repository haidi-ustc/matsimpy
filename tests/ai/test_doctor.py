"""Offline, secret-safe diagnostics for the AI command line."""

from __future__ import annotations

import sqlite3

from typer.testing import CliRunner

from matsimpy.ai.doctor import Diagnostic, Doctor, render_diagnostics


def _by_code(items):
    return {item.code: item for item in items}


def test_doctor_interfaces_are_public():
    from matsimpy.ai import Diagnostic as PublicDiagnostic
    from matsimpy.ai import Doctor as PublicDoctor

    assert PublicDiagnostic is Diagnostic
    assert PublicDoctor is Doctor


def test_doctor_reports_key_presence_without_disclosing_value(tmp_path):
    secret = "malicious-secret-that-must-never-appear"
    results = Doctor(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        environ={"DEEPSEEK_API_KEY": secret},
    ).run()

    provider = _by_code(results)["provider-api-key"]
    rendered = render_diagnostics(results)
    assert provider.status == "pass"
    assert provider.summary == "configured"
    assert secret not in rendered
    assert "Authorization" not in rendered


def test_doctor_missing_key_is_actionable(tmp_path):
    results = Doctor(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        environ={},
    ).run()
    item = _by_code(results)["provider-api-key"]
    assert item.status == "warn"
    assert item.summary == "missing"
    assert "DEEPSEEK_API_KEY" in item.action
    assert _by_code(results)["provider-model"].summary in {"configured", "default"}
    assert _by_code(results)["provider-base-url"].summary in {"configured", "default"}


def test_doctor_reports_unwritable_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    real_access = __import__("os").access
    monkeypatch.setattr(
        "matsimpy.ai.doctor.os.access",
        lambda path, mode: False if path == workspace else real_access(path, mode),
    )
    item = _by_code(Doctor(workspace=workspace, state_dir=tmp_path / "state").run())[
        "workspace"
    ]
    assert item.status == "fail"
    assert "writable" in item.action


def test_doctor_reports_invalid_skill_without_echoing_malicious_content(tmp_path):
    skills = tmp_path / "skills"
    bad = skills / "bad"
    bad.mkdir(parents=True)
    secret = "skill-embedded-secret-value"
    (bad / "SKILL.md").write_text(f"---\nname: BAD NAME\ndescription: {secret}\n---\n")

    results = Doctor(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        skill_roots=[skills],
    ).run()
    item = _by_code(results)["skills"]
    assert item.status == "fail"
    assert "invalid" in item.summary
    assert secret not in render_diagnostics(results)


def test_doctor_reports_incompatible_database_read_only(tmp_path):
    database = tmp_path / "state" / "state.db"
    database.parent.mkdir()
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE schema_meta (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_meta VALUES (999)")

    item = _by_code(
        Doctor(
            workspace=tmp_path / "workspace",
            state_dir=database.parent,
            database=database,
        ).run()
    )["database"]
    assert item.status == "fail"
    assert "newer" in item.summary
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT version FROM schema_meta").fetchone() == (999,)


def test_doctor_reports_optional_terminal_packages(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "matsimpy.ai.doctor.importlib.util.find_spec",
        lambda name: object() if name == "prompt_toolkit" else None,
    )
    results = _by_code(
        Doctor(workspace=tmp_path / "workspace", state_dir=tmp_path / "state").run()
    )
    assert results["ui-prompt-toolkit"].status == "pass"
    assert results["ui-rich"].status == "warn"
    assert "repl" in results["ui-rich"].action


def test_doctor_is_offline_unless_network_requested(tmp_path):
    calls = []

    def probe():
        calls.append(True)

    doctor = Doctor(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        network_probe=probe,
    )
    assert "provider-network" not in _by_code(doctor.run())
    assert not calls
    assert _by_code(doctor.run(network=True))["provider-network"].status == "pass"
    assert calls == [True]


def test_network_probe_failure_cannot_leak_secret(tmp_path):
    secret = "probe-secret-value"

    def probe():
        raise RuntimeError(f"Authorization: Bearer {secret}")

    results = Doctor(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        environ={"DEEPSEEK_API_KEY": secret},
        network_probe=probe,
    ).run(network=True)
    rendered = render_diagnostics(results)
    assert _by_code(results)["provider-network"].status == "fail"
    assert secret not in rendered
    assert "Bearer" not in rendered


def test_cli_doctor_does_not_construct_engine_and_preserves_root_command(monkeypatch):
    from matsimpy.ai import cli

    monkeypatch.setattr(
        cli,
        "Doctor",
        lambda **kwargs: type(
            "FakeDoctor",
            (),
            {"run": lambda self, network=False: [Diagnostic("ok", "pass", "ready", "")]},
        )(),
    )
    monkeypatch.setattr(
        cli, "AIEngine", lambda **kwargs: (_ for _ in ()).throw(AssertionError("engine"))
    )
    result = CliRunner().invoke(cli.app, ["doctor"])
    assert result.exit_code == 0
    assert "ready" in result.output


def test_cli_doctor_forwards_network_only_when_explicit(monkeypatch):
    from matsimpy.ai import cli

    calls = []

    class FakeDoctor:
        def __init__(self, **kwargs):
            pass

        def run(self, network=False):
            calls.append(network)
            return [Diagnostic("network", "pass", "checked", "")]

    monkeypatch.setattr(cli, "Doctor", FakeDoctor)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["doctor"]).exit_code == 0
    assert runner.invoke(cli.app, ["doctor", "--network"]).exit_code == 0
    assert calls == [False, True]
