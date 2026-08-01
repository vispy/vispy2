"""Validate the S065 gallery against wheel-installed packages.

Run this script with a Python interpreter whose environment contains the four
local wheels. The harness copies gallery scripts to a temporary directory,
unpacks only the four named project wheels into an isolated project site,
verifies all project imports and Pillow from the requested interpreter,
captures galleries 1--4 with both backends, then exercises capability discovery
and queries. Datoviz subprocesses have a hard timeout and one retry.
"""

from __future__ import annotations

import argparse
from collections import Counter
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path, PureWindowsPath
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
from typing import Any, Final, cast
import zipfile

from PIL import Image


CAPTURE_SCRIPTS: Final = (
    "gallery_01_priority_2d.py",
    "gallery_02_perspective_3d.py",
    "gallery_03_orthographic_3d.py",
    "gallery_04_camera_sequence.py",
)
CHECK_SCRIPTS: Final = ("gallery_06_capabilities.py", "gallery_07_queries.py")
SHARED_SCRIPTS: Final = ("gallery_shared_layout.py",)
WHEEL_PROJECTS: Final = (
    "gsp-core",
    "gsp-matplotlib",
    "gsp-datoviz",
    "vispy2",
)
PROJECT_IMPORTS: Final = {
    "gsp": "gsp",
    "gsp_matplotlib": "gsp_matplotlib",
    "gsp_datoviz": "gsp_datoviz",
    "vispy2": "vispy2",
}
CAPTURE_SUFFIXES: Final = (
    "gallery-01-priority-2d",
    "gallery-02-perspective-3d",
    "gallery-03-orthographic-3d",
    "gallery-04-00-fit",
    "gallery-04-01-orbit",
    "gallery-04-02-pan",
    "gallery-04-03-zoom",
)
EXPECTED_CAPTURE_NAMES: Final = tuple(
    f"{backend}-{suffix}.png"
    for backend in ("matplotlib", "datoviz")
    for suffix in CAPTURE_SUFFIXES
)
TERMINATION_TIMEOUT_SECONDS: Final = 2.0


class ProcessIsolation(Enum):
    PROCESS_GROUP = "process_group"
    DIRECT_CHILD = "direct_child"


def _datoviz_process_isolation(*, platform: str) -> ProcessIsolation:
    if platform == "darwin":
        return ProcessIsolation.DIRECT_CHILD
    return ProcessIsolation.PROCESS_GROUP


def _terminate_process(
    process: subprocess.Popen[str],
    *,
    isolation: ProcessIsolation,
) -> None:
    if isolation is ProcessIsolation.PROCESS_GROUP:
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=TERMINATION_TIMEOUT_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass

    if isolation is ProcessIsolation.PROCESS_GROUP:
        os.killpg(process.pid, signal.SIGKILL)
    else:
        process.kill()
    try:
        process.wait(timeout=TERMINATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError("subprocess did not exit after forced termination") from None


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    retries: int = 0,
    isolation: ProcessIsolation = ProcessIsolation.PROCESS_GROUP,
) -> None:
    for attempt in range(retries + 1):
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            text=True,
            start_new_session=isolation is ProcessIsolation.PROCESS_GROUP,
        )
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _terminate_process(process, isolation=isolation)
            if attempt < retries:
                print(f"timeout; retrying: {' '.join(command)}", file=sys.stderr)
                continue
            raise RuntimeError(f"timed out after {timeout:.0f}s: {' '.join(command)}") from None
        if return_code != 0:
            raise RuntimeError(f"exit {return_code}: {' '.join(command)}")
        return


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise RuntimeError(f"invalid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def _git_revision(path: Path) -> str:
    status = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        check=True,
        text=True,
        capture_output=True,
    )
    if status.stdout:
        raise RuntimeError(f"source checkout must be clean before validation: {path}")
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def _verify_git_revision(path: Path, expected: str) -> None:
    if _git_revision(path) != expected:
        raise RuntimeError(f"source HEAD changed during validation: {path}")


def _runtime_description(probe: dict[str, object]) -> str:
    implementation = probe.get("implementation")
    version = probe.get("version")
    system = probe.get("system")
    machine = probe.get("machine")
    if not all(
        isinstance(value, str) and value for value in (implementation, version, system, machine)
    ):
        raise RuntimeError("runtime probe fields must be non-empty strings")
    display_system = "macOS" if system == "Darwin" else system
    return f"{implementation} {version} {display_system} {machine}"


def _logical_import_path(path: Path, package: str) -> str:
    expected_suffix = (package, "__init__.py")
    if path.parts[-2:] != expected_suffix:
        raise RuntimeError(f"installed import is not a verified {package}/__init__.py path")
    return str(Path("isolated-wheel-site", *expected_suffix))


def _wheel_project_name(path: Path) -> str:
    metadata_names: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith(".dist-info/METADATA"):
                    continue
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.startswith("Name: "):
                        metadata_names.append(line.removeprefix("Name: ").strip())
                        break
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"invalid wheel: {path}") from exc
    if len(metadata_names) != 1 or not metadata_names[0]:
        raise RuntimeError(f"wheel must contain exactly one project name: {path}")
    return metadata_names[0]


def _validate_wheels(wheels: dict[str, Path]) -> dict[str, dict[str, str]]:
    if set(wheels) != set(WHEEL_PROJECTS):
        raise RuntimeError("exactly four named project wheels are required")
    resolved = [path.resolve() for path in wheels.values()]
    if len(set(resolved)) != len(resolved):
        raise RuntimeError("duplicate wheel inputs are not allowed")
    evidence: dict[str, dict[str, str]] = {}
    for expected_name in WHEEL_PROJECTS:
        path = wheels[expected_name]
        if not path.is_file():
            raise RuntimeError(f"{expected_name} wheel does not exist: {path}")
        if path.suffix != ".whl":
            raise RuntimeError(f"{expected_name} input is not a .whl file: {path}")
        actual_name = _wheel_project_name(path)
        if actual_name != expected_name:
            raise RuntimeError(f"{expected_name} wheel contains unknown project {actual_name!r}")
        evidence[expected_name] = {"sha256": _sha256(path)}
    return evidence


def _unpack_wheels(wheels: dict[str, Path], project_site: Path) -> None:
    project_site.mkdir(parents=True)
    for project in WHEEL_PROJECTS:
        with zipfile.ZipFile(wheels[project]) as archive:
            for member in archive.infolist():
                destination = (project_site / member.filename).resolve()
                if not destination.is_relative_to(project_site.resolve()):
                    raise RuntimeError(f"unsafe wheel member: {member.filename}")
            archive.extractall(project_site)


def _parse_probe(stdout: str, project_site: Path) -> dict[str, object]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("interpreter probe did not return JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("interpreter probe must return an object")
    if set(value) != {
        "implementation",
        "version",
        "system",
        "machine",
        "pillow",
        "imports",
    }:
        raise RuntimeError("interpreter probe has invalid fields")
    _runtime_description(value)
    imports = value.get("imports")
    if not isinstance(imports, dict) or set(imports) != set(PROJECT_IMPORTS):
        raise RuntimeError("interpreter probe has invalid project imports")
    site = project_site.resolve()
    for module, package in PROJECT_IMPORTS.items():
        raw_path = imports[module]
        if not isinstance(raw_path, str) or not raw_path:
            raise RuntimeError(f"interpreter probe import {module} must be a path string")
        path = Path(raw_path).resolve()
        if not path.is_relative_to(site):
            raise RuntimeError(f"{module} was not imported from the isolated wheel site")
        _logical_import_path(path, package)
    pillow = value.get("pillow")
    if not isinstance(pillow, str) or not pillow:
        raise RuntimeError("interpreter probe did not prove Pillow importability")
    return value


def _assert_no_absolute_paths(value: object, *, context: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_no_absolute_paths(item, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_absolute_paths(item, context=f"{context}[{index}]")
    elif isinstance(value, str) and (
        Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
    ):
        raise RuntimeError(f"{context} contains an absolute path")


def _assert_manifest_schema(manifest: dict[str, object]) -> None:
    if manifest.get("schema") != 2:
        raise RuntimeError("gallery manifest must use schema 2")
    _assert_no_absolute_paths(manifest)


def _number(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"{context} must be numeric")
    return float(value)


def _load_evidence(evidence_dir: Path) -> dict[str, dict[str, object]]:
    evidence: dict[str, dict[str, object]] = {}
    for path in sorted(evidence_dir.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"invalid gallery evidence object: {path}")
        evidence[path.stem] = value
    if len(evidence) != 12:
        raise RuntimeError(f"expected 12 layout evidence records, found {len(evidence)}")
    return evidence


def _matching_evidence(
    evidence: dict[str, dict[str, object]], suffix: str
) -> tuple[dict[str, object], dict[str, object]]:
    return (
        evidence[f"matplotlib-{suffix}"],
        evidence[f"datoviz-{suffix}"],
    )


def _assert_shared_geometry(evidence: dict[str, dict[str, object]]) -> None:
    for suffix in (
        "gallery-02-perspective-3d",
        "gallery-03-orthographic-3d",
        "gallery-04-00-fit",
        "gallery-04-01-orbit",
        "gallery-04-02-pan",
        "gallery-04-03-zoom",
    ):
        matplotlib, datoviz = _matching_evidence(evidence, suffix)
        for key in ("canvas_size", "panel_rect", "plot_rect"):
            if matplotlib[key] != datoviz[key]:
                raise RuntimeError(f"{suffix} backend {key} mismatch")
        if matplotlib["canvas_size"] != [800, 600]:
            raise RuntimeError(f"{suffix} resolved canvas is not 800x600")
        if matplotlib["projection_snapshot_id"] != datoviz["projection_snapshot_id"]:
            raise RuntimeError(f"{suffix} projection snapshot mismatch")
        for backend_evidence in (matplotlib, datoviz):
            if (
                backend_evidence["backend_projection_snapshot_id"]
                != backend_evidence["projection_snapshot_id"]
            ):
                raise RuntimeError(f"{suffix} backend projection readback mismatch")
        left_anchors = matplotlib["projected_anchors"]
        right_anchors = datoviz["projected_anchors"]
        if not isinstance(left_anchors, list) or not isinstance(right_anchors, list):
            raise RuntimeError(f"{suffix} projected anchor evidence is invalid")
        if len(left_anchors) != len(right_anchors):
            raise RuntimeError(f"{suffix} projected anchor count mismatch")
        for left, right in zip(left_anchors, right_anchors, strict=True):
            for left_value, right_value in zip(
                left["logical_pixel"], right["logical_pixel"], strict=True
            ):
                if (
                    abs(
                        _number(left_value, context=f"{suffix} left anchor")
                        - _number(right_value, context=f"{suffix} right anchor")
                    )
                    > 1.0
                ):
                    raise RuntimeError(f"{suffix} projected anchors differ by over one pixel")

        aspect = matplotlib["effective_perspective_aspect"]
        if aspect is not None:
            plot_rect = matplotlib["plot_rect"]
            assert isinstance(plot_rect, list)
            plot_ratio = _number(plot_rect[2], context=f"{suffix} plot width") / _number(
                plot_rect[3], context=f"{suffix} plot height"
            )
            if abs(_number(aspect, context=f"{suffix} aspect ratio") - plot_ratio) > 1e-12:
                raise RuntimeError(f"{suffix} perspective aspect does not use plot ratio")
            if aspect != datoviz["effective_perspective_aspect"]:
                raise RuntimeError(f"{suffix} perspective aspect mismatch")
            if matplotlib["authored_perspective_aspect"] is not None:
                raise RuntimeError(f"{suffix} unexpectedly authored a perspective aspect")

    perspective, _ = _matching_evidence(evidence, "gallery-02-perspective-3d")
    orthographic, _ = _matching_evidence(evidence, "gallery-03-orthographic-3d")
    if perspective["projection_kind"] != "perspective":
        raise RuntimeError("Gallery 2 projection evidence is not perspective")
    if orthographic["projection_kind"] != "orthographic":
        raise RuntimeError("Gallery 3 projection evidence is not orthographic")
    for value in evidence.values():
        backend = value["backend"]
        title_status = value["title_status"]
        diagnostics = value["layout_diagnostics"]
        render_diagnostics = value["render_diagnostics"]
        if not isinstance(diagnostics, list) or not all(
            isinstance(item, str) for item in diagnostics
        ):
            raise RuntimeError("layout diagnostics evidence is invalid")
        if not isinstance(render_diagnostics, list) or not all(
            isinstance(item, str) for item in render_diagnostics
        ):
            raise RuntimeError("render diagnostics evidence is invalid")
        if backend == "datoviz":
            if title_status != "unsupported":
                raise RuntimeError("Datoviz title limitation is not recorded as unsupported")
            if "panel_text_title_unsupported_no_public_renderer_path" not in diagnostics:
                raise RuntimeError("Datoviz title diagnostic is missing")
            if render_diagnostics != ["panel_text_title_unsupported_no_public_renderer_path"]:
                raise RuntimeError(
                    "Datoviz accepted render did not record exactly one title diagnostic"
                )
        elif title_status == "unsupported":
            raise RuntimeError("Matplotlib unexpectedly reports titles as unsupported")
        elif render_diagnostics:
            raise RuntimeError("Matplotlib unexpectedly recorded a render diagnostic")


def _geometry_bounds(path: Path, plot_rect: list[object]) -> list[int]:
    image = Image.open(path).convert("RGBA")
    plot_x = _number(plot_rect[0], context="plot x")
    plot_y = _number(plot_rect[1], context="plot y")
    plot_width = _number(plot_rect[2], context="plot width")
    plot_height = _number(plot_rect[3], context="plot height")
    x0 = max(0, math.floor(plot_x))
    y0 = max(0, math.floor(plot_y))
    x1 = min(
        image.width,
        math.ceil(plot_x + plot_width),
    )
    y1 = min(
        image.height,
        math.ceil(plot_y + plot_height),
    )
    if x1 <= x0 or y1 <= y0:
        raise RuntimeError(f"empty plot rectangle for {path.name}")
    background = _plot_background(image, x0=x0, y0=y0, x1=x1, y1=y1)
    pixels = cast(Any, image.load())
    selected = [
        (x, y)
        for y in range(y0, y1)
        for x in range(x0, x1)
        if max(abs(pixels[x, y][channel] - background[channel]) for channel in range(3)) > 8
    ]
    if not selected:
        raise RuntimeError(f"no non-background geometry found in {path.name}")
    xs = [coordinate[0] for coordinate in selected]
    ys = [coordinate[1] for coordinate in selected]
    return [min(xs), min(ys), max(xs), max(ys)]


def _plot_background(
    image: Image.Image,
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> tuple[int, int, int, int]:
    """Return the dominant inset-perimeter color of one resolved plot rectangle."""
    inset = 1 if x1 - x0 > 2 and y1 - y0 > 2 else 0
    left = x0 + inset
    right = x1 - 1 - inset
    top = y0 + inset
    bottom = y1 - 1 - inset
    samples = [
        *(image.getpixel((x, top)) for x in range(left, right + 1)),
        *(image.getpixel((x, bottom)) for x in range(left, right + 1)),
        *(image.getpixel((left, y)) for y in range(top + 1, bottom)),
        *(image.getpixel((right, y)) for y in range(top + 1, bottom)),
    ]
    if not samples:
        raise RuntimeError("plot rectangle has no background samples")
    background, count = Counter(samples).most_common(1)[0]
    if count * 2 <= len(samples):
        raise RuntimeError("plot rectangle has no dominant perimeter background")
    return cast(tuple[int, int, int, int], background)


def _camera_geometry_evidence(
    output_dir: Path, evidence: dict[str, dict[str, object]]
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for state in ("00-fit", "01-orbit", "02-pan", "03-zoom"):
        suffix = f"gallery-04-{state}"
        matplotlib, datoviz = _matching_evidence(evidence, suffix)
        plot_rect = matplotlib["plot_rect"]
        assert isinstance(plot_rect, list)
        bounds = {}
        for backend in ("matplotlib", "datoviz"):
            bounds[backend] = _geometry_bounds(
                output_dir / f"{backend}-{suffix}.png",
                plot_rect,
            )
        mpl_width = bounds["matplotlib"][2] - bounds["matplotlib"][0] + 1
        mpl_height = bounds["matplotlib"][3] - bounds["matplotlib"][1] + 1
        dvz_width = bounds["datoviz"][2] - bounds["datoviz"][0] + 1
        dvz_height = bounds["datoviz"][3] - bounds["datoviz"][1] + 1
        width_ratio = dvz_width / mpl_width
        height_ratio = dvz_height / mpl_height
        if abs(width_ratio - 1.0) > 0.02 or abs(height_ratio - 1.0) > 0.02:
            raise RuntimeError(
                f"{suffix} raster geometry ratios exceed 2% tolerance: "
                f"width={width_ratio:.6f}, height={height_ratio:.6f}"
            )
        result[state] = {
            "bounds": bounds,
            "datoviz_to_matplotlib_width_ratio": width_ratio,
            "datoviz_to_matplotlib_height_ratio": height_ratio,
            "tolerance": 0.02,
        }
    return result


def _validate_capture_set(capture_dir: Path) -> list[Path]:
    actual_names = {path.name for path in capture_dir.glob("*.png") if path.is_file()}
    expected_names = set(EXPECTED_CAPTURE_NAMES)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        raise RuntimeError(
            f"fresh capture has incorrect PNG set: missing={missing}, unexpected={unexpected}"
        )
    pngs = [capture_dir / name for name in sorted(EXPECTED_CAPTURE_NAMES)]
    wrong_sizes = {path.name: _png_size(path) for path in pngs if _png_size(path) != (800, 600)}
    if wrong_sizes:
        raise RuntimeError(f"gallery PNG dimensions must all be 800x600: {wrong_sizes}")
    return pngs


def _publish_capture(capture_dir: Path, output_dir: Path) -> None:
    pngs = _validate_capture_set(capture_dir)
    manifest = capture_dir / "manifest.json"
    if not manifest.is_file():
        raise RuntimeError("validated capture has no manifest")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".vispy2-gallery-publish-",
        dir=output_dir.parent,
    ) as temporary:
        staged = Path(temporary)
        for path in pngs:
            shutil.copy2(path, staged / path.name)
        shutil.copy2(manifest, staged / manifest.name)

        output_dir.mkdir(parents=True, exist_ok=True)
        destination_manifest = output_dir / manifest.name
        destination_manifest.unlink(missing_ok=True)
        for stale in output_dir.glob("*-gallery-*.png"):
            if stale.is_file():
                stale.unlink()
        for name in sorted(EXPECTED_CAPTURE_NAMES):
            os.replace(staged / name, output_dir / name)
        os.replace(staged / manifest.name, destination_manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gsp-source", type=Path, required=True)
    parser.add_argument("--vispy2-source", type=Path, required=True)
    parser.add_argument("--gsp-core-wheel", type=Path, required=True)
    parser.add_argument("--gsp-matplotlib-wheel", type=Path, required=True)
    parser.add_argument("--gsp-datoviz-wheel", type=Path, required=True)
    parser.add_argument("--vispy2-wheel", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_dir = args.output_dir.resolve()
    wheels = {
        "gsp-core": args.gsp_core_wheel,
        "gsp-matplotlib": args.gsp_matplotlib_wheel,
        "gsp-datoviz": args.gsp_datoviz_wheel,
        "vispy2": args.vispy2_wheel,
    }
    wheel_evidence = _validate_wheels(wheels)
    source_paths = {
        "gsp": args.gsp_source.resolve(),
        "vispy2": args.vispy2_source.resolve(),
    }
    source_revisions = {project: _git_revision(path) for project, path in source_paths.items()}
    env = dict(os.environ)

    with tempfile.TemporaryDirectory(prefix="vispy2-m290-gallery-") as temporary:
        run_dir = Path(temporary)
        project_site = run_dir / "project-site"
        capture_dir = run_dir / "captures"
        evidence_dir = run_dir / "evidence"
        capture_dir.mkdir()
        _unpack_wheels(wheels, project_site)
        env["PYTHONPATH"] = str(project_site)
        env["MPLCONFIGDIR"] = str(run_dir / ".matplotlib")
        for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS, *SHARED_SCRIPTS):
            shutil.copy2(script_dir / name, run_dir / name)

        probe = subprocess.run(
            [
                str(args.python),
                "-c",
                (
                    "import json, platform, gsp, gsp_matplotlib, gsp_datoviz, vispy2; "
                    "from PIL import Image; "
                    "print(json.dumps({'implementation': platform.python_implementation(), "
                    "'version': platform.python_version(), 'system': platform.system(), "
                    "'machine': platform.machine(), 'pillow': Image.__name__, "
                    "'imports': {'gsp': gsp.__file__, "
                    "'gsp_matplotlib': gsp_matplotlib.__file__, "
                    "'gsp_datoviz': gsp_datoviz.__file__, "
                    "'vispy2': vispy2.__file__}}))"
                ),
            ],
            cwd=run_dir,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        probe_value = _parse_probe(probe.stdout, project_site)
        import_values = cast(dict[str, str], probe_value["imports"])

        for backend in ("matplotlib", "datoviz"):
            for script in CAPTURE_SCRIPTS:
                command = [
                    str(args.python),
                    script,
                    backend,
                    "--output-dir",
                    str(capture_dir),
                ]
                if script != "gallery_01_priority_2d.py":
                    command.extend(["--evidence-dir", str(evidence_dir)])
                _run(
                    command,
                    cwd=run_dir,
                    env=env,
                    timeout=args.timeout,
                    retries=1 if backend == "datoviz" else 0,
                    isolation=(
                        _datoviz_process_isolation(platform=sys.platform)
                        if backend == "datoviz"
                        else ProcessIsolation.PROCESS_GROUP
                    ),
                )
        for script in CHECK_SCRIPTS:
            _run(
                [str(args.python), script],
                cwd=run_dir,
                env=env,
                timeout=args.timeout,
            )

        pngs = _validate_capture_set(capture_dir)
        evidence = _load_evidence(evidence_dir)
        _assert_shared_geometry(evidence)
        camera_geometry = _camera_geometry_evidence(capture_dir, evidence)

        manifest = {
            "schema": 2,
            "provenance": {
                "python": _runtime_description(probe_value),
                "imports": {
                    module: _logical_import_path(Path(import_values[module]), package)
                    for module, package in PROJECT_IMPORTS.items()
                },
                "project_wheels": wheel_evidence,
                "gsp_source_revision": source_revisions["gsp"],
                "vispy2_source_revision": source_revisions["vispy2"],
                "execution": (
                    "copied scripts outside both source trees; four project wheels "
                    "unpacked into an isolated project site; third-party dependencies "
                    "provided by the requested Python environment"
                ),
                "datoviz_timeout_seconds": args.timeout,
                "datoviz_retries": 1,
            },
            "scripts": {
                name: {"sha256": _sha256(script_dir / name)}
                for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS, *SHARED_SCRIPTS)
            },
            "layout_projection_evidence": evidence,
            "camera_geometry_evidence": camera_geometry,
            "artifacts": {
                path.name: {
                    "bytes": path.stat().st_size,
                    "width": _png_size(path)[0],
                    "height": _png_size(path)[1],
                    "sha256": _sha256(path),
                }
                for path in pngs
            },
        }
        _assert_manifest_schema(manifest)
        (capture_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for project, path in source_paths.items():
            _verify_git_revision(path, source_revisions[project])
        _publish_capture(capture_dir, output_dir)
    print(f"validated {len(pngs)} captures; manifest={output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
