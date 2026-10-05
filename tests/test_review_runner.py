"""Persisted acceptance and process lifecycle checks for the console review."""

from __future__ import annotations

import argparse
import importlib.util
from types import ModuleType
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest


@pytest.fixture
def runner(monkeypatch, tmp_path):
    package = ModuleType("_review_runner_test_tools")
    package.__path__ = [str(Path(__file__).parents[1] / "tools")]
    monkeypatch.setitem(sys.modules, package.__name__, package)
    spec = importlib.util.spec_from_file_location(
        package.__name__ + ".review", Path(package.__path__[0]) / "review.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    step = module.ReviewStep(
        "demo",
        "Demo",
        "Inspect geometry",
        ("Expected shape",),
        ("vispy2/source.py",),
        ("python", "examples/review_live.py", "strokes"),
        smoke=True,
        kind="live",
    )
    monkeypatch.setattr(module, "STEPS", (step,))
    monkeypatch.setattr(module, "VISPY2", tmp_path)
    monkeypatch.setattr(module, "WORKSPACE", tmp_path)
    monkeypatch.setattr(module, "select_steps", lambda plan: (step,))
    monkeypatch.setattr(module, "candidate_state", lambda *args: candidate("initial"))
    monkeypatch.setattr(module, "child_environment", lambda source: dict(os.environ))
    return module, step


def candidate(digest):
    return {
        "repositories": {"vispy2": {"revision": "commit", "sha256": digest}},
        "python": sys.executable,
    }


def open_review(module, tmp_path, *, backend="both", plan="smoke"):
    return module.Review.open(
        tmp_path / "review",
        resume=False,
        candidate=candidate("initial"),
        backend=backend,
        plan=plan,
    )


def args(**changes):
    result = dict(step=None, backend="both", python=sys.executable, timeout=0.15)
    result.update(changes)
    return argparse.Namespace(**result)


def inputs(monkeypatch, actions):
    iterator = iter(actions)

    def read(prompt=""):
        value = next(iterator)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            return value()
        return value

    monkeypatch.setattr("builtins.input", read)


@pytest.mark.parametrize("change", ("candidate", "backend"))
def test_resume_invalidates_verdicts_preserving_findings_and_attempt_history(
    runner, tmp_path, change
):
    module, step = runner
    review = open_review(module, tmp_path, backend="matplotlib")
    review.note(step, "Marker clips at boundary", "bug")
    review.result(step)["attempts"].append(
        {"at": "then", "mode": "live", "outcome": "succeeded", "children": {}}
    )
    review.verdict(step, "pass")
    resumed = module.Review.open(
        review.directory,
        resume=True,
        candidate=candidate("changed" if change == "candidate" else "initial"),
        backend="both" if change == "backend" else "matplotlib",
        plan="smoke",
    )
    saved = json.loads((review.directory / "state.json").read_text())
    assert resumed.result(step)["status"] == "pending"
    assert saved["steps"][step.id]["notes"][0]["text"] == "Marker clips at boundary"
    assert saved["steps"][step.id]["attempts"]
    assert any(item["status"] == "pass" for item in saved["steps"][step.id]["verdict_history"])
    if change == "candidate":
        assert saved["candidate_history"][0]["candidate"] == candidate("initial")


@pytest.mark.parametrize("change", ("candidate", "backend"))
def test_changed_inputs_cannot_pass_using_old_successful_live_attempt(
    runner, tmp_path, monkeypatch, change
):
    module, step = runner
    review = open_review(module, tmp_path, backend="matplotlib")
    review.result(step)["attempts"].append(
        {"at": "then", "mode": "live", "outcome": "succeeded", "children": {}}
    )
    review.verdict(step, "pass")
    review = module.Review.open(
        review.directory,
        resume=True,
        candidate=candidate("changed" if change == "candidate" else "initial"),
        backend="both" if change == "backend" else "matplotlib",
        plan="smoke",
    )
    inputs(monkeypatch, ["pass", "quit"])
    module.interactive(review, (step,), args(), {})
    assert review.result(step)["status"] == "pending"


def test_explicit_completed_step_reopens_instead_of_skipping(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    review.verdict(step, "skip")
    inputs(monkeypatch, ["note", "Second look", ".", "quit"])
    module.interactive(review, (step,), args(step=step.id), {})
    assert review.result(step)["notes"][-1]["text"] == "Second look"


def test_resume_cli_keeps_saved_plan_and_backend(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path, backend="matplotlib", plan="smoke")
    seen = []
    monkeypatch.setattr(
        module,
        "headless",
        lambda review, steps, args, env: seen.append((args.plan, args.backend)) or 0,
    )
    assert module.main(["--resume", str(review.directory), "--headless"]) == 0
    assert seen == [("smoke", "matplotlib")]


def test_notes_are_on_disk_while_child_still_running(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)

    class Child:
        attempt = {"children": {}}

        def poll(self):
            return False

        def close(self):
            pass

    monkeypatch.setattr(module, "launch", lambda *a, **kw: Child())

    def inspect_disk():
        saved = json.loads((review.directory / "state.json").read_text())
        assert saved["steps"][step.id]["notes"][-1]["text"] == "Visible while open"
        return "quit"

    inputs(monkeypatch, ["run", "note", "Visible while open", ".", inspect_disk])
    module.interactive(review, (step,), args(), {})


@pytest.mark.parametrize("ending", ("quit", EOFError()))
def test_quit_or_eof_closes_owned_children(runner, tmp_path, monkeypatch, ending):
    module, step = runner
    review = open_review(module, tmp_path)
    closed = []

    class Child:
        attempt = {"children": {}}

        def poll(self):
            return False

        def close(self):
            closed.append(True)

    monkeypatch.setattr(module, "launch", lambda *a, **kw: Child())
    inputs(monkeypatch, ["run", ending])
    assert module.interactive(review, (step,), args(), {}) == 0
    assert closed == [True]


def child_command(monkeypatch, module, code):
    monkeypatch.setattr(module, "step_command", lambda *a, **kw: [sys.executable, "-c", code])


def launch_real(module, step, review, *, headless):
    env = dict(os.environ, MPLBACKEND="Agg", DISPLAY=":review-test")
    return module.launch(
        review, step, backend="matplotlib", python=sys.executable, headless=headless, env=env
    )


def test_failed_live_child_cannot_receive_manual_pass(runner, tmp_path, monkeypatch, capsys):
    module, step = runner
    review = open_review(module, tmp_path)
    child_command(monkeypatch, module, "print('render failed', flush=True); raise SystemExit(7)")
    original = module.launch

    def launch(*a, **kw):
        kw["env"] = dict(os.environ, MPLBACKEND="Agg", DISPLAY=":review-test")
        running = original(*a, **kw)
        for process in running.processes.values():
            process.wait(timeout=3)
        return running

    monkeypatch.setattr(module, "launch", launch)
    inputs(monkeypatch, ["run", "pass", "quit"])
    module.interactive(review, (step,), args(backend="matplotlib"), {})
    assert review.result(step)["status"] == "pending"
    assert review.result(step)["attempts"][-1]["outcome"] == "failed"
    assert "render failed" in capsys.readouterr().out


def test_headless_success_is_machine_checked_and_requires_live_pass(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    child_command(monkeypatch, module, "print('bounded capture checked')")
    assert (
        module.headless(review, (step,), args(backend="matplotlib", timeout=3), dict(os.environ))
        == 0
    )
    assert review.result(step)["status"] == "machine-checked"
    inputs(monkeypatch, ["pass", "quit"])
    module.interactive(review, (step,), args(backend="matplotlib"), {})
    assert review.result(step)["status"] == "machine-checked"


def test_headless_timeout_records_failure_and_reaps_child(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    child_command(monkeypatch, module, "import time; time.sleep(60)")
    original = module.launch
    launched = []

    def launch(*a, **kw):
        running = original(*a, **kw)
        launched.append(running)
        return running

    monkeypatch.setattr(module, "launch", launch)
    assert module.headless(review, (step,), args(backend="matplotlib"), dict(os.environ)) == 1
    assert review.result(step)["status"] == "failed"
    assert review.result(step)["attempts"][-1]["outcome"] == "timed-out"
    assert all(p.poll() is not None for p in launched[0].processes.values())
    assert all(log.closed for log in launched[0].logs)


def test_partial_launch_failure_closes_first_backend(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    child_command(monkeypatch, module, "import time; time.sleep(60)")
    original = subprocess.Popen
    started = []

    def popen(*a, **kw):
        if started:
            raise OSError("second backend unavailable")
        process = original(*a, **kw)
        started.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", popen)
    with pytest.raises(OSError, match="second backend"):
        module.launch(
            review, step, backend="both", python=sys.executable, headless=True, env=dict(os.environ)
        )
    assert started[0].poll() is not None
    saved = json.loads((review.directory / "state.json").read_text())
    assert saved["steps"][step.id]["attempts"][-1]["outcome"] != "running"


def test_argv_preserves_python_and_capture_paths_with_spaces(runner, tmp_path):
    module, step = runner
    python = str(tmp_path / "python environment" / "bin" / "python")
    capture = tmp_path / "review captures"
    command = module.step_command(step, "matplotlib", python, True, capture)
    assert command[0] == python
    assert command[-2:] == ["--capture-dir", str(capture)]
    assert command.count(python) == 1


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="descendant liveness uses Linux /proc"
)
def test_cleanup_reaps_descendant_even_if_group_leader_has_exited(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    marker = tmp_path / "descendant.pid"
    grandchild = (
        "import os,time; from pathlib import Path; Path(%r).write_text(str(os.getpid())); time.sleep(60)"
        % str(marker)
    )
    child_command(
        monkeypatch,
        module,
        "import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r])" % grandchild,
    )
    running = launch_real(module, step, review, headless=True)
    pid = None
    try:
        process = next(iter(running.processes.values()))
        process.wait(timeout=3)
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
        pid = int(marker.read_text())
        running.close()

        def active():
            proc = Path(f"/proc/{pid}/stat")
            return proc.exists() and proc.read_text().split()[2] != "Z"

        deadline = time.monotonic() + 1
        while active() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not active(), "exited group leader left a live descendant"
    finally:
        if pid:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        running.close()


def test_explicit_completed_step_can_launch_a_fresh_attempt(runner, tmp_path, monkeypatch):
    module, step = runner
    review = open_review(module, tmp_path)
    review.verdict(step, "pass")
    child_command(monkeypatch, module, "print('REVIEW_READY fake demo', flush=True)")
    original = module.launch

    def launch(*a, **kw):
        kw["env"] = dict(os.environ, MPLBACKEND="Agg", DISPLAY=":review-test")
        running = original(*a, **kw)
        for process in running.processes.values():
            process.wait(timeout=3)
        return running

    monkeypatch.setattr(module, "launch", launch)
    inputs(monkeypatch, ["run", "quit"])
    module.interactive(review, (step,), args(step=step.id, backend="matplotlib"), {})
    assert review.result(step)["status"] == "pending"
    assert len(review.result(step)["attempts"]) == 1
    assert review.result(step)["attempts"][0]["mode"] == "live"
    assert any(item["status"] == "pass" for item in review.result(step)["verdict_history"])
