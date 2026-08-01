from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import signal
import struct
import subprocess
from typing import Any, Callable, cast
import zipfile

import pytest
from PIL import Image, ImageDraw

import vispy2 as vp


EXAMPLES = Path(__file__).parents[1] / "examples"


def _load(name: str) -> dict[str, Any]:
    return runpy.run_path(str(EXAMPLES / name))


class _FakeProcess:
    def __init__(self, wait_results: list[int | subprocess.TimeoutExpired]) -> None:
        self.pid = 1234
        self.wait_results = wait_results
        self.wait_timeouts: list[float | None] = []
        self.terminate_calls = 0
        self.kill_calls = 0

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        result = self.wait_results.pop(0)
        if isinstance(result, subprocess.TimeoutExpired):
            raise result
        return result

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1


def test_gallery_runner_uses_process_group_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    run = validator["_run"]
    process = _FakeProcess([0])
    popen_calls: list[dict[str, object]] = []

    def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        popen_calls.append(kwargs)
        return process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    run(["python", "check.py"], cwd=tmp_path, env={}, timeout=1.0)

    assert [call["start_new_session"] for call in popen_calls] == [True]


def test_macos_datoviz_runner_uses_direct_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    run = validator["_run"]
    isolation_for_datoviz = validator["_datoviz_process_isolation"]
    process_isolation = validator["ProcessIsolation"]
    process = _FakeProcess([0])
    popen_calls: list[dict[str, object]] = []

    def fake_popen(command: list[str], **kwargs: object) -> _FakeProcess:
        popen_calls.append(kwargs)
        return process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    isolation = isolation_for_datoviz(platform="darwin")
    run(
        ["python", "gallery.py", "datoviz"],
        cwd=tmp_path,
        env={},
        timeout=1.0,
        isolation=isolation,
    )

    assert isolation is process_isolation.DIRECT_CHILD
    assert isolation_for_datoviz(platform="linux") is process_isolation.PROCESS_GROUP
    assert [call["start_new_session"] for call in popen_calls] == [False]


def test_process_group_timeout_sends_term_then_kill_to_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    run = validator["_run"]
    process = _FakeProcess(
        [
            subprocess.TimeoutExpired("gallery", 1.0),
            subprocess.TimeoutExpired("gallery", 2.0),
            0,
        ]
    )
    signals: list[tuple[int, signal.Signals]] = []

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    with pytest.raises(RuntimeError, match="timed out"):
        run(["python", "gallery.py"], cwd=tmp_path, env={}, timeout=1.0)

    assert signals == [(process.pid, signal.SIGTERM), (process.pid, signal.SIGKILL)]
    assert process.terminate_calls == 0
    assert process.kill_calls == 0
    assert process.wait_timeouts == [1.0, 2.0, 2.0]


def test_direct_child_timeout_terminates_then_kills_only_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    run = validator["_run"]
    process_isolation = validator["ProcessIsolation"]
    process = _FakeProcess(
        [
            subprocess.TimeoutExpired("gallery", 1.0),
            subprocess.TimeoutExpired("gallery", 2.0),
            0,
        ]
    )

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        os,
        "killpg",
        lambda *args: pytest.fail("direct-child cleanup must never call killpg"),
    )

    with pytest.raises(RuntimeError, match="timed out"):
        run(
            ["python", "gallery.py", "datoviz"],
            cwd=tmp_path,
            env={},
            timeout=1.0,
            isolation=process_isolation.DIRECT_CHILD,
        )

    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert process.wait_timeouts == [1.0, 2.0, 2.0]


def test_nonzero_child_exit_fails_without_retry_and_timeout_retry_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    run = validator["_run"]
    processes = [_FakeProcess([-11])]

    def fake_popen(*args: object, **kwargs: object) -> _FakeProcess:
        return processes.pop(0)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    with pytest.raises(RuntimeError, match="exit -11"):
        run(["python", "gallery.py"], cwd=tmp_path, env={}, timeout=1.0, retries=1)
    assert not processes

    timed_out = subprocess.TimeoutExpired("gallery", 1.0)
    processes.extend([_FakeProcess([timed_out, 0]), _FakeProcess([timed_out, 0])])
    popen_count = 0

    def counting_popen(*args: object, **kwargs: object) -> _FakeProcess:
        nonlocal popen_count
        popen_count += 1
        return processes.pop(0)

    monkeypatch.setattr(subprocess, "Popen", counting_popen)
    monkeypatch.setattr(os, "killpg", lambda *args: None)
    with pytest.raises(RuntimeError, match="timed out"):
        run(["python", "gallery.py"], cwd=tmp_path, env={}, timeout=1.0, retries=1)
    assert popen_count == 2
    assert not processes


def test_galleries_2_to_4_have_exact_required_view3d_capabilities() -> None:
    shared = _load("gallery_shared_layout.py")
    required_capabilities = cast(
        Callable[[vp.Figure], set[str]],
        shared["_required_view3d_capabilities"],
    )
    figures = {
        2: cast(Callable[[], vp.Figure], _load("gallery_02_perspective_3d.py")["make_figure"])(),
        3: cast(Callable[[], vp.Figure], _load("gallery_03_orthographic_3d.py")["make_figure"])(),
        4: cast(
            Callable[[], tuple[vp.Figure, vp.Axes3D]],
            _load("gallery_04_camera_sequence.py")["make_figure"],
        )()[0],
    }

    expected = {
        2: {
            "view3d.static.perspective.v1",
            "meshvisual.positions3d.data.view3d.v1",
            "spherevisual.v1",
            "vectorvisual.positions3d.data.view3d.v1",
            "textvisual.billboard3d.v1",
        },
        3: {
            "view3d.static.orthographic.v1",
            "pixelvisual.v1",
            "pixelvisual.positions3d.data.view3d.v1",
            "primitivevisual.v1",
            "primitivevisual.indexed.v1",
            "primitivevisual.triangle_strip",
        },
        4: {
            "view3d.static.perspective.v1",
            "meshvisual.positions3d.data.view3d.v1",
        },
    }
    assert {
        gallery: required_capabilities(figure) for gallery, figure in figures.items()
    } == expected


def test_gallery_manifest_provenance_is_portable_and_uses_probed_runtime(
    tmp_path: Path,
) -> None:
    validator = _load("validate_gallery.py")
    logical_import_path = cast(
        Callable[[Path, str], str],
        validator["_logical_import_path"],
    )
    parse_probe = cast(
        Callable[[str, Path], dict[str, object]],
        validator["_parse_probe"],
    )
    runtime_description = cast(
        Callable[[dict[str, object]], str],
        validator["_runtime_description"],
    )
    assert_manifest_schema = cast(
        Callable[[dict[str, object]], None],
        validator["_assert_manifest_schema"],
    )

    assert (
        logical_import_path(
            Path("/temporary/gsp/build/site-packages/gsp/__init__.py"),
            "gsp",
        )
        == "isolated-wheel-site/gsp/__init__.py"
    )
    with pytest.raises(RuntimeError, match="verified gsp/__init__.py"):
        logical_import_path(
            Path("/temporary/gsp/build/site-packages/not-gsp/__init__.py"),
            "gsp",
        )

    project_site = tmp_path / "project-site"
    imports = {
        module: str(project_site / package / "__init__.py")
        for module, package in cast(dict[str, str], validator["PROJECT_IMPORTS"]).items()
    }
    probe_payload = {
        "implementation": "DifferentPython",
        "version": "9.8.7",
        "system": "ProbeOS",
        "machine": "probe-machine",
        "pillow": "PIL.Image",
        "imports": imports,
    }
    probe = parse_probe(json.dumps(probe_payload), project_site)
    runtime = runtime_description(probe)
    assert runtime == "DifferentPython 9.8.7 ProbeOS probe-machine"

    manifest: dict[str, object] = {
        "schema": 2,
        "provenance": {
            "python": runtime,
            "imports": {
                module: logical_import_path(Path(imports[module]), package)
                for module, package in cast(dict[str, str], validator["PROJECT_IMPORTS"]).items()
            },
        },
    }
    assert_manifest_schema(manifest)
    with pytest.raises(RuntimeError, match="absolute path"):
        assert_manifest_schema(
            {
                **manifest,
                "provenance": {"python": "/private/tmp/wheel-env/bin/python"},
            }
        )
    with pytest.raises(RuntimeError, match="absolute path"):
        assert_manifest_schema(
            {
                **manifest,
                "provenance": {"python": r"C:\wheel-env\python.exe"},
            }
        )


def _write_wheel(path: Path, project: str) -> None:
    distribution = project.replace("-", "_")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"{distribution}-0.2.0.dist-info/METADATA",
            f"Metadata-Version: 2.4\nName: {project}\nVersion: 0.2.0\n",
        )


def test_gallery_validator_requires_four_exact_named_unique_wheels(
    tmp_path: Path,
) -> None:
    validator = _load("validate_gallery.py")
    validate_wheels = cast(
        Callable[[dict[str, Path]], dict[str, dict[str, str]]],
        validator["_validate_wheels"],
    )
    projects = cast(tuple[str, ...], validator["WHEEL_PROJECTS"])
    wheels = {}
    for project in projects:
        path = tmp_path / f"{project}-0.2.0-py3-none-any.whl"
        _write_wheel(path, project)
        wheels[project] = path

    evidence = validate_wheels(wheels)
    assert set(evidence) == set(projects)
    assert all(set(item) == {"sha256"} for item in evidence.values())
    assert all(len(item["sha256"]) == 64 for item in evidence.values())
    assert not any(str(tmp_path) in str(item) for item in evidence.values())

    missing = dict(wheels)
    missing.pop("vispy2")
    with pytest.raises(RuntimeError, match="exactly four"):
        validate_wheels(missing)

    duplicate = dict(wheels)
    duplicate["vispy2"] = duplicate["gsp-core"]
    with pytest.raises(RuntimeError, match="duplicate"):
        validate_wheels(duplicate)

    unknown = tmp_path / "unknown-0.2.0-py3-none-any.whl"
    _write_wheel(unknown, "unknown")
    mismatched = {**wheels, "vispy2": unknown}
    with pytest.raises(RuntimeError, match="unknown project"):
        validate_wheels(mismatched)

    nonexistent = {**wheels, "vispy2": tmp_path / "missing.whl"}
    with pytest.raises(RuntimeError, match="does not exist"):
        validate_wheels(nonexistent)

    not_wheel = tmp_path / "vispy2.zip"
    _write_wheel(not_wheel, "vispy2")
    wrong_suffix = {**wheels, "vispy2": not_wheel}
    with pytest.raises(RuntimeError, match=r"not a \.whl"):
        validate_wheels(wrong_suffix)


def test_geometry_bounds_uses_plot_background_not_canvas_background(
    tmp_path: Path,
) -> None:
    validator = _load("validate_gallery.py")
    geometry_bounds = cast(
        Callable[[Path, list[object]], list[int]],
        validator["_geometry_bounds"],
    )
    path = tmp_path / "local-plot-background.png"
    image = Image.new("RGBA", (100, 80), (15, 16, 22, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 89, 69), fill=(255, 255, 255, 255))
    draw.rectangle((35, 25, 64, 49), fill=(70, 130, 220, 255))
    image.save(path)

    assert geometry_bounds(path, [10.0, 10.0, 80.0, 60.0]) == [35, 25, 64, 49]


def test_camera_geometry_gate_accepts_background_difference_but_rejects_scale(
    tmp_path: Path,
) -> None:
    validator = _load("validate_gallery.py")
    camera_geometry_evidence = cast(
        Callable[[Path, dict[str, dict[str, object]]], dict[str, dict[str, object]]],
        validator["_camera_geometry_evidence"],
    )
    states = ("00-fit", "01-orbit", "02-pan", "03-zoom")
    evidence: dict[str, dict[str, object]] = {}

    def write_capture(backend: str, state: str, *, right: int = 64) -> None:
        canvas = (255, 255, 255, 255) if backend == "matplotlib" else (15, 16, 22, 255)
        image = Image.new("RGBA", (100, 80), canvas)
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 89, 69), fill=(255, 255, 255, 255))
        draw.rectangle((35, 25, right, 49), fill=(70, 130, 220, 255))
        image.save(tmp_path / f"{backend}-gallery-04-{state}.png")

    for state in states:
        for backend in ("matplotlib", "datoviz"):
            evidence[f"{backend}-gallery-04-{state}"] = {"plot_rect": [10.0, 10.0, 80.0, 60.0]}
            write_capture(backend, state)

    result = camera_geometry_evidence(tmp_path, evidence)
    assert all(
        item["datoviz_to_matplotlib_width_ratio"] == 1.0
        and item["datoviz_to_matplotlib_height_ratio"] == 1.0
        for item in result.values()
    )

    write_capture("datoviz", "03-zoom", right=68)
    with pytest.raises(RuntimeError, match="ratios exceed 2% tolerance"):
        camera_geometry_evidence(tmp_path, evidence)


def test_stale_output_cannot_satisfy_failed_capture_or_publish_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    validate_capture_set = cast(
        Callable[[Path], list[Path]],
        validator["_validate_capture_set"],
    )
    publish_capture = cast(
        Callable[[Path, Path], None],
        validator["_publish_capture"],
    )
    expected_names = cast(tuple[str, ...], validator["EXPECTED_CAPTURE_NAMES"])
    output_dir = tmp_path / "published"
    capture_dir = tmp_path / "fresh-capture"
    output_dir.mkdir()
    capture_dir.mkdir()
    stale_gallery = output_dir / "stale-gallery-old.png"
    stale_gallery.write_bytes(b"stale")
    unrelated = output_dir / "review-notes.txt"
    unrelated.write_text("preserve me\n", encoding="utf-8")
    old_manifest = output_dir / "manifest.json"
    old_manifest.write_text('{"old": true}\n', encoding="utf-8")

    with pytest.raises(RuntimeError, match="incorrect PNG set"):
        validate_capture_set(capture_dir)

    assert old_manifest.read_text(encoding="utf-8") == '{"old": true}\n'

    header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(
            ">II",
            800,
            600,
        )
    )
    for name in expected_names:
        (capture_dir / name).write_bytes(header)
    unexpected = capture_dir / "extra-gallery-output.png"
    unexpected.write_bytes(header)
    with pytest.raises(RuntimeError, match="unexpected=.*extra-gallery-output"):
        validate_capture_set(capture_dir)
    unexpected.unlink()
    (capture_dir / "manifest.json").write_text('{"schema": 2}\n', encoding="utf-8")

    replacements: list[str] = []
    real_replace = os.replace

    def recording_replace(source: str | Path, destination: str | Path) -> None:
        replacements.append(Path(destination).name)
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", recording_replace)
    publish_capture(capture_dir, output_dir)

    assert not stale_gallery.exists()
    assert unrelated.read_text(encoding="utf-8") == "preserve me\n"
    assert {path.name for path in output_dir.glob("*-gallery-*.png")} == set(expected_names)
    assert old_manifest.read_text(encoding="utf-8") == '{"schema": 2}\n'
    assert replacements[-1] == "manifest.json"


def test_failed_publish_invalidates_old_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validator = _load("validate_gallery.py")
    publish_capture = cast(
        Callable[[Path, Path], None],
        validator["_publish_capture"],
    )
    expected_names = cast(tuple[str, ...], validator["EXPECTED_CAPTURE_NAMES"])
    capture_dir = tmp_path / "capture"
    output_dir = tmp_path / "output"
    capture_dir.mkdir()
    output_dir.mkdir()
    header = (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(
            ">II",
            800,
            600,
        )
    )
    for name in expected_names:
        (capture_dir / name).write_bytes(header)
    (capture_dir / "manifest.json").write_text('{"schema": 2}\n', encoding="utf-8")
    (output_dir / "manifest.json").write_text('{"old": true}\n', encoding="utf-8")

    def failed_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("injected publication failure")

    monkeypatch.setattr(os, "replace", failed_replace)
    with pytest.raises(OSError, match="injected publication failure"):
        publish_capture(capture_dir, output_dir)

    assert not (output_dir / "manifest.json").exists()


def test_source_revision_must_be_clean_and_stable(tmp_path: Path) -> None:
    validator = _load("validate_gallery.py")
    git_revision = cast(Callable[[Path], str], validator["_git_revision"])
    verify_git_revision = cast(
        Callable[[Path, str], None],
        validator["_verify_git_revision"],
    )
    repository = tmp_path / "candidate"
    repository.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "gallery-test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Gallery Test"],
        cwd=repository,
        check=True,
    )
    source = repository / "source.txt"
    source.write_text("first\n", encoding="utf-8")
    subprocess.run(["git", "add", "source.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "first"], cwd=repository, check=True)
    first_revision = git_revision(repository)

    source.write_text("dirty\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be clean"):
        git_revision(repository)

    source.write_text("first\n", encoding="utf-8")
    source.write_text("second\n", encoding="utf-8")
    subprocess.run(["git", "add", "source.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "second"], cwd=repository, check=True)
    with pytest.raises(RuntimeError, match="HEAD changed"):
        verify_git_revision(repository, first_revision)
