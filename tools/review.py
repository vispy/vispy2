"""A resumable console review of VisPy2 and its sibling GSP implementation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any, TextIO

if __package__:
    from .review_catalog import STEPS, ReviewStep, select_steps
else:
    from review_catalog import STEPS, ReviewStep, select_steps

VISPY2 = Path(__file__).resolve().parents[1]
WORKSPACE = VISPY2.parent
COMPLETED = {"pass", "issue", "skip", "not-applicable"}
SEVERITIES = ("blocker", "bug", "doc", "adaptation", "preference")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_state(path: Path) -> dict[str, Any]:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(path), *args], stderr=subprocess.DEVNULL)

    if not path.is_dir():
        return {"path": str(path), "available": False}
    try:
        revision = git("rev-parse", "HEAD").decode().strip()
        status = git("status", "--porcelain").decode()
        files = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
        digest = hashlib.sha256()
        for name in sorted(set(files.split(b"\0")) - {b""}):
            item = path / os.fsdecode(name)
            digest.update(name + b"\0")
            if item.is_symlink():
                digest.update(os.fsencode(os.readlink(item)))
            elif item.is_file():
                digest.update(digest_file(item).encode())
            else:
                digest.update(b"missing-or-submodule")
        digest.update(git("diff", "--binary", "HEAD", "--"))
        return {
            "path": str(path),
            "revision": revision,
            "status": status,
            "sha256": digest.hexdigest(),
        }
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"path": str(path), "available": False, "error": str(exc)}


def candidate_state(python: str, datoviz_source: str | None) -> dict[str, Any]:
    states = {name: repository_state(WORKSPACE / name) for name in ("gsp", "vispy2")}
    if datoviz_source and datoviz_source != "none":
        source = Path(datoviz_source).resolve()
        states["datoviz"] = repository_state(source)
        for native in (source / "build/src/libdatoviz.so", source / "build/src/libdatoviz.dylib"):
            if native.is_file():
                states["datoviz"]["native_sha256"] = digest_file(native)
                break
    return {
        "repositories": states,
        "python": python,
        "tour": [asdict(step) for step in STEPS],
        "environment": {
            name: os.environ.get(name)
            for name in (
                "MPLBACKEND",
                "QT_API",
                "GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV",
            )
        },
    }


def default_output_root() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    return (
        Path(state_home).expanduser() if state_home else Path.home() / ".local/state"
    ) / "gsp/reviews"


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


class Review:
    def __init__(self, directory: Path, state: dict[str, Any]) -> None:
        self.directory = directory
        self.state = state

    @classmethod
    def open(
        cls, directory: Path, *, resume: bool, candidate: dict[str, Any], plan: str, backend: str
    ) -> Review:
        path = directory / "state.json"
        if resume:
            state = json.loads(path.read_text(encoding="utf-8"))
            if state.get("schema") != "gsp.review@1":
                raise ValueError("unsupported review state schema")
            invalidated = False
            if state["candidate"] != candidate:
                invalidated = True
                print(
                    "Inputs changed since this review. Previous verdicts are preserved in history; steps need review again."
                )
                state.setdefault("candidate_history", []).append(
                    {"at": timestamp(), "candidate": state["candidate"]}
                )
                for result in state["steps"].values():
                    result.setdefault("verdict_history", []).append(
                        {"at": timestamp(), "status": result["status"]}
                    )
                    result["status"] = "pending"
                state["candidate"] = candidate
            if state.get("backend") != backend:
                invalidated = True
                # A Matplotlib verdict cannot qualify a later both-backend review.
                for result in state["steps"].values():
                    result.setdefault("verdict_history", []).append(
                        {"at": timestamp(), "status": result["status"]}
                    )
                    result["status"] = "pending"
            state["generation"] = state.get("generation", 0) + int(invalidated)
            state["plan"], state["backend"] = plan, backend
        else:
            if path.exists():
                raise ValueError(
                    f"review already exists: {path}; use --resume or a new output directory"
                )
            state = {
                "schema": "gsp.review@1",
                "created": timestamp(),
                "candidate": candidate,
                "plan": plan,
                "backend": backend,
                "steps": {},
                "position": 0,
                "generation": 0,
            }
        directory.mkdir(parents=True, exist_ok=True)
        review = cls(directory, state)
        for step in STEPS:
            review.result(step)
        review.save()
        return review

    def result(self, step: ReviewStep) -> dict[str, Any]:
        return self.state["steps"].setdefault(
            step.id,
            {
                "title": step.title,
                "status": "pending",
                "notes": [],
                "attempts": [],
            },
        )

    def note(self, step: ReviewStep, text: str, severity: str | None = None) -> None:
        self.result(step)["notes"].append({"at": timestamp(), "text": text, "severity": severity})
        self.save()

    def verdict(self, step: ReviewStep, status: str) -> None:
        result = self.result(step)
        result.setdefault("verdict_history", []).append({"at": timestamp(), "status": status})
        result["status"] = status
        self.save()

    def save(self) -> None:
        self.state["updated"] = timestamp()
        atomic_json(self.directory / "state.json", self.state)
        lines = [
            "# Project review",
            "",
            f"Started: {self.state['created']}",
            f"Plan: {self.state['plan']}; backends: {self.state['backend']}",
            "",
            "Automated checks are not manual visual passes.",
            "",
            "## Reviewed inputs",
            "",
        ]
        for name, source in self.state["candidate"]["repositories"].items():
            lines.append(
                f"- {name}: `{source.get('revision', 'unavailable')}`; worktree SHA-256 `{source.get('sha256', 'unavailable')}`"
            )
        lines.extend(["", "## Steps", "", "| Step | Verdict |", "|---|---|"])
        for step in STEPS:
            lines.append(f"| {step.id}: {step.title} | {self.result(step)['status']} |")
        for step in STEPS:
            result = self.result(step)
            if not result["notes"] and not result["attempts"] and not result.get("verdict_history"):
                continue
            lines.extend(
                [
                    "",
                    f"## {step.id}: {step.title}",
                    "",
                    f"Current verdict: **{result['status']}**",
                    "",
                ]
            )
            for note in result["notes"]:
                severity = note["severity"] or "note"
                lines.extend([f"**{severity} — {note['at']}**", "", note["text"], ""])
            for attempt in result["attempts"]:
                lines.append(
                    f"- {attempt['mode']} run at {attempt['at']}: {attempt.get('outcome', 'running')}"
                )
                for backend, process in attempt["children"].items():
                    lines.append(
                        f"  - {backend}: exit `{process.get('returncode', 'running')}`; [log]({process['log']})"
                    )
                if attempt.get("capture_dir"):
                    for image in sorted((self.directory / attempt["capture_dir"]).glob("*.png")):
                        lines.append(
                            f"  - [capture: {image.name}]({image.relative_to(self.directory).as_posix()})"
                        )
            if result.get("verdict_history"):
                lines.append(
                    "- Verdict history: "
                    + "; ".join(
                        f"{item['at']}: {item['status']}" for item in result["verdict_history"]
                    )
                )
        if self.state.get("candidate_history"):
            lines.extend(
                ["", "Earlier candidate fingerprints and verdicts are retained in state.json."]
            )
        report = self.directory / "report.md"
        temporary = report.with_suffix(".tmp")
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary.replace(report)


def child_environment(datoviz_source: str | None) -> dict[str, str]:
    env = dict(os.environ)
    paths = [VISPY2 / "src", VISPY2 / "examples"] + [
        WORKSPACE / "gsp/packages" / name / "src"
        for name in ("gsp-core", "gsp-matplotlib", "gsp-datoviz")
    ]
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in paths) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    if datoviz_source is not None:
        env["GSP_DATOVIZ_SOURCE"] = datoviz_source
    return env


def step_command(
    step: ReviewStep, backend: str, python: str, headless: bool, capture: Path
) -> list[str]:
    command = list(step.command)
    if command and command[0] in ("python", "python3"):
        command.pop(0)
    if headless and command[0] == "examples/manual_live_compare.py":
        command[0] = "tools/review_static.py"
    args = [python, *command, "--backend", backend]
    if headless:
        if command[0] != "tools/review_static.py":
            args.append("--headless")
        args.extend(["--capture-dir", str(capture)])
    return args


class Running:
    def __init__(self, review: Review, attempt: dict[str, Any]) -> None:
        self.review = review
        self.attempt = attempt
        self.processes: dict[str, subprocess.Popen[bytes]] = {}
        self.logs: list[TextIO] = []
        self.seen_lines: dict[str, int] = {}

    def poll(self) -> bool:
        for backend, process in self.processes.items():
            self.attempt["children"][backend]["returncode"] = process.poll()
            item = self.attempt["children"][backend]
            try:
                lines = (
                    (self.review.directory / item["log"])
                    .read_text(encoding="utf-8", errors="replace")
                    .splitlines()
                )
                for line in lines[self.seen_lines.get(backend, 0) :]:
                    if any(
                        marker in line
                        for marker in (
                            "REVIEW_READY",
                            "UNSUPPORTED:",
                            "Backend diagnostic:",
                            "Adaptation:",
                            "window open",
                            "window closed",
                            "query status",
                            "pick status",
                        )
                    ):
                        print(f"  {backend}: {line}")
                self.seen_lines[backend] = len(lines)
            except OSError:
                pass
        finished = all(process.poll() is not None for process in self.processes.values())
        if finished:
            failed = any(item.get("returncode") != 0 for item in self.attempt["children"].values())
            self.attempt["outcome"] = "failed" if failed else "succeeded"
        for backend, process in self.processes.items():
            code = process.poll()
            item = self.attempt["children"][backend]
            if code not in (None, 0) and not item.get("failure_reported"):
                item["failure_reported"] = True
                print(
                    f"\n{backend} exited with code {code}. Inspect {self.review.directory / item['log']}"
                )
                try:
                    tail = (
                        (self.review.directory / item["log"])
                        .read_text(encoding="utf-8", errors="replace")
                        .splitlines()[-12:]
                    )
                    print("\n".join(tail))
                except OSError:
                    pass
        self.review.save()
        return finished

    def close(self) -> None:
        # Every child owns a process group. Interrupt Python first so contexts unwind.
        for process in self.processes.values():
            if os.name == "posix":
                # A terminated leader can still leave a descendant in its owned group.
                send_signal(process, signal.SIGINT)
            elif process.poll() is None:
                process.terminate()
        for process in self.processes.values():
            if process.poll() is not None:
                continue
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    send_signal(process, signal.SIGTERM)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if os.name == "posix":
                        send_signal(process, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=2)
        if os.name == "posix":
            for process in self.processes.values():
                send_signal(process, signal.SIGTERM)
        if self.attempt.get("outcome") == "running":
            self.attempt["outcome"] = "interrupted"
        for backend, process in self.processes.items():
            self.attempt["children"][backend]["returncode"] = process.poll()
        for log in self.logs:
            log.close()
        self.review.save()


def send_signal(process: subprocess.Popen[bytes], sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def launch(
    review: Review,
    step: ReviewStep,
    *,
    backend: str,
    python: str,
    headless: bool,
    env: dict[str, str],
) -> Running:
    allowed = (
        step.backends
        if backend == "both"
        else tuple(item for item in step.backends if item == backend)
    )
    if not allowed:
        raise ValueError(
            f"this step needs {', '.join(step.backends)}; selected backend is {backend}"
        )
    if (
        not headless
        and sys.platform.startswith("linux")
        and not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))
    ):
        raise ValueError(
            "Live windows need a GUI display. Run on your desktop, or use --headless for checks and captures."
        )
    env = dict(env)
    if headless:
        env["MPLBACKEND"] = "Agg"
    else:
        env.pop("GSP_TEST", None)
        if not env.get("MPLBACKEND"):
            # PySide6 is installed only in the optional development review environment.
            probe = subprocess.run(
                [
                    python,
                    "-c",
                    "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('PySide6') else 1)",
                ],
                capture_output=True,
                timeout=10,
            )
            if probe.returncode == 0:
                env["MPLBACKEND"], env["QT_API"] = "QtAgg", "pyside6"
        if step.id == "navigation":
            env.setdefault("GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV", "1")
            print(
                "This navigation exercise opts in to experimental Datoviz View3D gestures unless explicitly disabled in your environment."
            )
    attempt: dict[str, Any] = {
        "at": timestamp(),
        "mode": "headless" if headless else "live",
        "outcome": "running",
        "children": {},
        "generation": review.state["generation"],
    }
    review.result(step)["attempts"].append(attempt)
    review.result(step)["status"] = "pending"
    running = Running(review, attempt)
    attempt_number = len(review.result(step)["attempts"])
    capture = review.directory / "captures" / f"{step.id}-{attempt_number}"
    capture.mkdir(parents=True, exist_ok=True)
    attempt["capture_dir"] = capture.relative_to(review.directory).as_posix()
    try:
        for name in allowed:
            log_path = review.directory / f"{step.id}-{attempt_number}-{name}.log"
            command = step_command(step, name, python, headless, capture)
            attempt["children"][name] = {
                "command": command,
                "log": log_path.name,
                "returncode": None,
            }
            log = log_path.open("w", encoding="utf-8")
            running.logs.append(log)
            running.processes[name] = subprocess.Popen(
                command,
                cwd=VISPY2,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=os.name == "posix",
            )
        review.save()
        return running
    except BaseException:
        running.close()
        raise


def wait_ready(running: Running) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if running.poll():
            return
        ready = True
        for item in running.attempt["children"].values():
            try:
                text = (running.review.directory / item["log"]).read_text(
                    encoding="utf-8", errors="replace"
                )
                ready &= "REVIEW_READY" in text or "window open" in text
            except OSError:
                ready = False
        if ready:
            return
        time.sleep(0.1)
    print(
        "Some windows are still starting. You can inspect the saved logs or continue taking notes."
    )


def feedback(prompt: str) -> str:
    print(prompt + " Enter '.' on a line to save; an empty first line cancels.")
    lines = []
    while True:
        line = input("  ")
        if line == "." or (not line and not lines):
            return "\n".join(lines)
        lines.append(line)


def show_step(step: ReviewStep, index: int, total: int, review: Review) -> None:
    print(
        f"\n{'=' * 72}\n{index + 1}/{total} · {step.title} [{step.id}] · ~{step.estimated_minutes} minutes\n"
    )
    print(step.explanation)
    print("\nLook for:")
    for check in step.checks:
        print(f"  • {check}")
    print("\nSources:")
    for source in step.sources:
        print(f"  {WORKSPACE / source}")
    print(f"\nSaved verdict: {review.result(step)['status']}")


def show_sources(step: ReviewStep) -> None:
    for number, source in enumerate(step.sources, 1):
        print(f"{number}. {WORKSPACE / source}")
    choice = input("Read source number (Enter returns): ").strip()
    if not choice:
        return
    try:
        number = int(choice)
        if number < 1:
            raise ValueError
        path = WORKSPACE / step.sources[number - 1]
        lines = path.read_text(encoding="utf-8").splitlines()
        print(
            f"\n{path}\n"
            + "\n".join(f"{index}: {line}" for index, line in enumerate(lines[:100], 1))
        )
        if len(lines) > 100:
            print(
                f"Showing first 100/{len(lines)} lines. Open the path in your editor for the complete file."
            )
    except (ValueError, IndexError, OSError) as exc:
        print(f"Unable to show source: {exc}")


def interactive(
    review: Review, steps: tuple[ReviewStep, ...], args: argparse.Namespace, env: dict[str, str]
) -> int:
    index = (
        0
        if args.step
        else next(
            (
                number
                for number, step in enumerate(steps)
                if review.result(step)["status"] not in COMPLETED
            ),
            len(steps),
        )
    )
    running: Running | None = None
    aliases = {
        "r": "run",
        "p": "pass",
        "i": "issue",
        "n": "note",
        "s": "skip",
        "b": "back",
        "d": "docs",
        "q": "quit",
    }
    try:
        while index < len(steps):
            step = steps[index]
            review.state["position"] = index
            review.save()
            show_step(step, index, len(steps), review)
            if args.backend != "both" and args.backend not in step.backends:
                print(
                    f"This exercise requires {', '.join(step.backends)} and is not applicable to the selected {args.backend} scope."
                )
                review.verdict(step, "not-applicable")
                index += 1
                continue
            while True:
                action = (
                    input("\nrun / pass / issue / note / repeat / skip / back / docs / quit > ")
                    .strip()
                    .lower()
                )
                action = aliases.get(action, action or "run")
                if running is not None:
                    running.poll()
                if action in ("run", "repeat"):
                    if not step.command:
                        print(
                            "Reading step: inspect the contract and sources, then record pass, issue, or skip."
                        )
                        continue
                    if running:
                        running.close()
                    try:
                        running = launch(
                            review,
                            step,
                            backend=args.backend,
                            python=args.python,
                            headless=False,
                            env=env,
                        )
                        wait_ready(running)
                        print(
                            "Windows are opening. Write notes here while inspecting; close all windows before passing. Child output is saved in the review logs."
                        )
                    except (OSError, ValueError) as exc:
                        review.note(step, f"Launch failed: {exc}", "blocker")
                        print(exc)
                    continue
                if action == "note":
                    text = feedback("Your observation:")
                    if text:
                        review.note(step, text)
                    continue
                if action == "docs":
                    show_sources(step)
                    continue
                if action == "pass":
                    if step.command:
                        attempts = review.result(step)["attempts"]
                        if (
                            not attempts
                            or attempts[-1]["mode"] != "live"
                            or attempts[-1].get("generation") != review.state["generation"]
                        ):
                            print("Run this step live before recording a manual pass.")
                            continue
                        if running and not running.poll():
                            print(
                                "Close all review windows first. You can continue taking notes while they are open."
                            )
                            continue
                        if attempts[-1]["outcome"] != "succeeded":
                            print(
                                "This run failed or was interrupted. Record an issue, inspect logs, or repeat it."
                            )
                            continue
                    review.verdict(step, "pass")
                elif action == "issue":
                    severity = (
                        input("Severity (blocker/bug/doc/adaptation/preference) [bug]: ")
                        .strip()
                        .lower()
                        or "bug"
                    )
                    if severity not in SEVERITIES:
                        print("Choose one of: " + ", ".join(SEVERITIES))
                        continue
                    text = feedback("Describe expected versus observed behavior:")
                    if not text:
                        print("An issue needs a description.")
                        continue
                    review.note(step, text, severity)
                    review.verdict(step, "issue")
                elif action == "skip":
                    reason = input("Reason for skipping (optional): ").strip()
                    if reason:
                        review.note(step, reason)
                    review.verdict(step, "skip")
                elif action == "back":
                    index = max(0, index - 1)
                    break
                elif action == "quit":
                    return 0
                else:
                    print(
                        "Unknown command. Use run, pass, issue, note, repeat, skip, back, docs, or quit."
                    )
                    continue
                index += 1
                break
            if running:
                running.close()
                running = None
        print("\nTour complete. Findings and skipped steps remain in your report.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nReview paused. Progress saved; use just review --resume to continue.")
        return 0
    finally:
        if running:
            running.close()
        review.save()


def headless(
    review: Review, steps: tuple[ReviewStep, ...], args: argparse.Namespace, env: dict[str, str]
) -> int:
    failures = 0
    for step in steps:
        if not step.command:
            print(f"{step.id}: reading step; manual review pending")
            continue
        if args.backend != "both" and args.backend not in step.backends:
            review.note(step, f"Not applicable to selected backend {args.backend}")
            review.verdict(step, "not-applicable")
            continue
        running = launch(
            review, step, backend=args.backend, python=args.python, headless=True, env=env
        )
        try:
            for process in running.processes.values():
                process.wait(timeout=args.timeout)
            running.poll()
            succeeded = running.attempt["outcome"] == "succeeded"
        except subprocess.TimeoutExpired:
            running.attempt["outcome"] = "timed-out"
            succeeded = False
            review.note(step, f"Headless check exceeded {args.timeout:g} seconds", "blocker")
        finally:
            running.close()
        status = "machine-checked" if succeeded else "failed"
        review.verdict(step, status)
        failures += not succeeded
        print(f"{step.id}: {status}; manual visual review pending")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", choices=("full", "smoke"))
    parser.add_argument("--backend", choices=("both", "matplotlib", "datoviz"))
    parser.add_argument("--resume", nargs="?", const="latest")
    parser.add_argument("--step", choices=tuple(step.id for step in STEPS))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.list:
        steps = (
            tuple(step for step in STEPS if step.id == args.step)
            if args.step
            else select_steps(args.plan or "full")
        )
        for number, step in enumerate(steps, 1):
            print(
                f"{number:2}. {step.id:20} {step.title} ({step.kind}, ~{step.estimated_minutes} min)"
            )
        print(
            f"\n{len(steps)} steps, ~{sum(step.estimated_minutes for step in steps)} minutes; repeat, skip, and pause at any time."
        )
        return 0
    if not args.headless and not sys.stdin.isatty():
        parser.error("interactive review needs a terminal; use --list or --headless for automation")
    root = default_output_root()
    if args.resume == "latest":
        sessions = sorted(root.glob("*/state.json"), key=lambda path: path.stat().st_mtime)
        if not sessions:
            parser.error(
                f"no review to resume under {root}; pass --resume PATH for a custom directory"
            )
        directory = sessions[-1].parent
    elif args.resume:
        directory = Path(args.resume).expanduser().resolve()
        if directory.is_file():
            directory = directory.parent
    else:
        directory = (
            (args.output_dir or root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
            .expanduser()
            .resolve()
        )
    if args.output_dir and args.resume:
        parser.error("--output-dir and --resume are mutually exclusive")
    saved: dict[str, Any] = {}
    if args.resume:
        try:
            saved = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            parser.error(f"cannot resume review: {exc}")
    args.plan = args.plan or saved.get("plan", "full")
    args.backend = args.backend or saved.get("backend", "both")
    if args.backend not in ("both", "matplotlib", "datoviz") or args.plan not in ("full", "smoke"):
        parser.error("saved review has an invalid backend or plan")
    steps = (
        tuple(step for step in STEPS if step.id == args.step)
        if args.step
        else select_steps(args.plan)
    )
    source = os.environ.get("GSP_DATOVIZ_SOURCE")
    if source is None and (WORKSPACE / "datoviz").is_dir():
        source = str(WORKSPACE / "datoviz")
    elif source and source != "none":
        source = str(Path(source).expanduser().resolve())
    env = child_environment(source)
    try:
        review = Review.open(
            directory,
            resume=bool(args.resume),
            candidate=candidate_state(args.python, source),
            plan=args.plan,
            backend=args.backend,
        )
    except (OSError, ValueError, KeyError) as exc:
        parser.error(f"cannot open review: {exc}")
    print(f"Review directory: {directory}\nReport: {directory / 'report.md'}")
    print(
        "Reviewing working-tree sources. Headless checks and skipped steps do not count as human acceptance."
    )
    try:
        result = (
            headless(review, steps, args, env)
            if args.headless
            else interactive(review, steps, args, env)
        )
    except KeyboardInterrupt:
        print("\nReview paused. Progress saved; use --resume to continue.")
        result = 0
    print(f"Saved report: {directory / 'report.md'}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
