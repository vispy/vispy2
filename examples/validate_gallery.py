"""Validate the S065 gallery against wheel-installed packages.

Run this script with a Python interpreter whose environment contains the four
local project wheels. The harness copies gallery scripts to a temporary directory,
unpacks the named project wheels and an optional Datoviz runtime wheel into an
isolated project site, verifies project imports and Pillow, captures galleries 1--4
and the mixed-panel gallery with both backends, then exercises capability discovery and queries. When supplied,
the Datoviz runtime wheel and its native binding are also proven isolated. Datoviz
subprocesses have a hard timeout and one retry.
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
import re
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
    "gallery_mixed_panels.py",
)
CHECK_SCRIPTS: Final = (
    "gallery_06_capabilities.py",
    "gallery_07_queries.py",
    "check_retained_updates.py",
    "check_mesh_pick.py",
    "check_scientific_grid.py",
)
CHECK_SCRIPT_BACKENDS: Final = {
    "check_retained_updates.py": ("matplotlib", "datoviz"),
    "check_mesh_pick.py": ("datoviz",),
    "check_scientific_grid.py": ("matplotlib", "datoviz"),
}
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
DATOVIZ_RUNTIME_IMPORTS: Final = {
    "datoviz": "datoviz",
}
CAPTURE_SUFFIXES: Final = (
    "gallery-01-priority-2d",
    "gallery-02-perspective-3d",
    "gallery-03-orthographic-3d",
    "gallery-04-00-fit",
    "gallery-04-01-orbit",
    "gallery-04-02-pan",
    "gallery-04-03-zoom",
    "gallery-mixed-panels",
)
EXPECTED_CAPTURE_NAMES: Final = tuple(
    f"{backend}-{suffix}.png"
    for backend in ("matplotlib", "datoviz")
    for suffix in CAPTURE_SUFFIXES
)
TERMINATION_TIMEOUT_SECONDS: Final = 2.0
DATOVIZ_RUNTIME_VERSION_RANGE: Final = ">=0.4.0rc3,<0.5"
_VERSION_PATTERN: Final = re.compile(
    r"^(?P<release>[0-9]+(?:\.[0-9]+)*)"
    r"(?:(?P<pre>a|b|rc)(?P<pre_number>[0-9]+))?"
    r"(?P<post>\.post[0-9]+)?(?P<dev>\.dev[0-9]+)?"
    r"(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?$",
    re.IGNORECASE,
)


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


def _git_source_state(path: Path, *, allow_dirty: bool) -> dict[str, object]:
    status = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        text=True,
        capture_output=True,
    )
    dirty = bool(status.stdout)
    if dirty and not allow_dirty:
        raise RuntimeError(f"source checkout must be clean before validation: {path}")
    revision = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            "HEAD",
            "--",
        ],
        check=True,
        capture_output=True,
    ).stdout
    tracked_files = _hash_worktree_paths(path, changed)
    untracked = subprocess.run(
        ["git", "-C", str(path), "ls-files", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    ).stdout
    untracked_files = _hash_worktree_paths(path, untracked)
    tracked_diff = subprocess.run(
        ["git", "-C", str(path), "diff", "--binary", "--submodule=diff", "HEAD", "--"],
        check=True,
        capture_output=True,
    ).stdout
    return {
        "baseline_revision": revision,
        "dirty": dirty,
        "tracked_worktree_files": tracked_files,
        "tracked_worktree_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "untracked_worktree_files": untracked_files,
    }


def _hash_worktree_paths(path: Path, names: bytes) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for raw_name in names.split(b"\0"):
        if not raw_name:
            continue
        name = os.fsdecode(raw_name)
        file_path = path / name
        if file_path.is_symlink():
            digest = hashlib.sha256(os.fsencode(os.readlink(file_path))).hexdigest()
        elif file_path.is_file():
            digest = _sha256(file_path)
        elif file_path.is_dir():
            submodule = subprocess.run(
                ["git", "-C", str(file_path), "rev-parse", "HEAD"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            digest = hashlib.sha256(submodule.encode("ascii")).hexdigest()
        else:
            digest = None
        hashes[name] = digest
    return hashes


def _verify_git_source_state(path: Path, expected: dict[str, object], *, allow_dirty: bool) -> None:
    if _git_source_state(path, allow_dirty=allow_dirty) != expected:
        raise RuntimeError(f"source checkout changed during validation: {path}")


def _project_wheel_source_relation(source_states: dict[str, dict[str, object]]) -> str:
    if any(state["dirty"] for state in source_states.values()):
        return (
            "source checkouts were dirty; wheel hashes identify the tested artifacts, but no "
            "correspondence to baseline commits is claimed"
        )
    return (
        "candidate checkouts were clean at recorded commits; wheel build provenance is not "
        "independently verified"
    )


def _validate_revision(value: str, *, option: str) -> str:
    if re.fullmatch(r"[0-9a-fA-F]{40}", value) is None:
        raise RuntimeError(f"{option} must be a full 40-character Git SHA")
    return value.lower()


def _validate_datoviz_mode(
    *,
    datoviz_source: Path | None,
    datoviz_source_revision: str | None,
    runtime_wheel: Path | None,
    pre_rc3_runtime: bool,
    runtime_source_revision: str | None,
) -> tuple[str | None, str | None]:
    if datoviz_source_revision and datoviz_source is None:
        raise RuntimeError("--datoviz-source-revision requires --datoviz-source")
    source_revision = (
        _validate_revision(datoviz_source_revision, option="--datoviz-source-revision")
        if datoviz_source_revision
        else None
    )
    if pre_rc3_runtime:
        if runtime_wheel is None:
            raise RuntimeError("--pre-rc3-runtime requires --datoviz-runtime-wheel")
        if not runtime_source_revision:
            raise RuntimeError("--pre-rc3-runtime requires --datoviz-runtime-source-revision")
    elif runtime_source_revision:
        raise RuntimeError("--datoviz-runtime-source-revision requires --pre-rc3-runtime")
    declared_revision = (
        _validate_revision(
            runtime_source_revision,
            option="--datoviz-runtime-source-revision",
        )
        if runtime_source_revision
        else None
    )
    if runtime_wheel is None and datoviz_source is None:
        raise RuntimeError("Datoviz captures require --datoviz-runtime-wheel or --datoviz-source")
    return source_revision, declared_revision


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


def _logical_imports(
    import_paths: dict[str, str],
    packages: dict[str, str],
    *,
    datoviz_source: Path | None,
    runtime_wheel: bool,
) -> dict[str, str]:
    logical: dict[str, str] = {}
    for module, package in packages.items():
        imported_path = Path(import_paths[module]).resolve()
        if module == "datoviz" and datoviz_source is not None and not runtime_wheel:
            logical[module] = str(
                Path("datoviz-source") / imported_path.relative_to(datoviz_source.resolve())
            )
        else:
            logical[module] = _logical_import_path(imported_path, package)
    return logical


def _wheel_distribution_metadata(path: Path) -> dict[str, str]:
    metadata_records: list[dict[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith(".dist-info/METADATA"):
                    continue
                record: dict[str, str] = {}
                for line in archive.read(name).decode("utf-8").splitlines():
                    if line.startswith("Name: "):
                        record["name"] = line.removeprefix("Name: ").strip()
                    elif line.startswith("Version: "):
                        record["version"] = line.removeprefix("Version: ").strip()
                metadata_records.append(record)
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"invalid wheel: {path}") from exc
    if len(metadata_records) != 1:
        raise RuntimeError(f"wheel must contain exactly one distribution metadata record: {path}")
    metadata = metadata_records[0]
    if set(metadata) != {"name", "version"} or not all(metadata.values()):
        raise RuntimeError(f"wheel distribution metadata must contain Name and Version: {path}")
    return metadata


def _is_compatible_datoviz_runtime_version(version: str) -> bool:
    match = _VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise RuntimeError(f"Datoviz runtime wheel has invalid version metadata {version!r}")
    release_parts = [int(item) for item in match.group("release").split(".")]
    while len(release_parts) > 1 and release_parts[-1] == 0:
        release_parts.pop()
    release = tuple(release_parts)
    if release < (0, 4) or release >= (0, 5):
        return False
    if release > (0, 4):
        return True
    pre = match.group("pre")
    if pre is None:
        return match.group("dev") is None
    return (
        pre.lower() == "rc"
        and int(match.group("pre_number")) >= 3
        and not (int(match.group("pre_number")) == 3 and match.group("dev") is not None)
    )


def _validate_wheel(path: Path, expected_name: str) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError(f"{expected_name} wheel does not exist: {path}")
    if path.suffix != ".whl":
        raise RuntimeError(f"{expected_name} input is not a .whl file: {path}")
    metadata = _wheel_distribution_metadata(path)
    actual_name = metadata["name"]
    if actual_name != expected_name:
        raise RuntimeError(f"{expected_name} wheel contains unknown project {actual_name!r}")
    return {"sha256": _sha256(path)}


def _validate_datoviz_runtime_wheel(path: Path) -> dict[str, str]:
    evidence = _validate_wheel(path, "datoviz")
    version = _wheel_distribution_metadata(path)["version"]
    if not _is_compatible_datoviz_runtime_version(version):
        raise RuntimeError(
            f"Datoviz runtime wheel version {version!r} is outside {DATOVIZ_RUNTIME_VERSION_RANGE}"
        )
    return {**evidence, "version": version}


def _is_pre_rc3_datoviz_runtime_version(version: str) -> bool:
    match = _VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise RuntimeError(f"Datoviz runtime wheel has invalid version metadata {version!r}")
    release = tuple(int(item) for item in match.group("release").split("."))
    while len(release) > 1 and release[-1] == 0:
        release = release[:-1]
    return (
        release == (0, 4)
        and match.group("pre") is not None
        and match.group("pre").lower() == "rc"
        and int(match.group("pre_number")) < 3
    )


def _validate_wheels(
    wheels: dict[str, Path],
    runtime_wheel: Path | None = None,
    *,
    allow_pre_rc3_runtime: bool = False,
) -> dict[str, dict[str, str]]:
    if set(wheels) != set(WHEEL_PROJECTS):
        raise RuntimeError("exactly four named project wheels are required")
    resolved = [path.resolve() for path in wheels.values()]
    if runtime_wheel is not None:
        resolved.append(runtime_wheel.resolve())
    if len(set(resolved)) != len(resolved):
        raise RuntimeError("duplicate wheel inputs are not allowed")
    evidence: dict[str, dict[str, str]] = {}
    for expected_name in WHEEL_PROJECTS:
        evidence[expected_name] = _validate_wheel(wheels[expected_name], expected_name)
    if runtime_wheel is not None:
        if allow_pre_rc3_runtime:
            wheel_evidence = _validate_wheel(runtime_wheel, "datoviz")
            version = _wheel_distribution_metadata(runtime_wheel)["version"]
            if not _is_pre_rc3_datoviz_runtime_version(version):
                raise RuntimeError(
                    "pre-RC3 mode accepts only Datoviz 0.4 release candidates before rc3"
                )
            evidence["datoviz"] = {**wheel_evidence, "version": version}
        else:
            evidence["datoviz"] = _validate_datoviz_runtime_wheel(runtime_wheel)
    return evidence


def _unpack_wheels(
    wheels: dict[str, Path], project_site: Path, runtime_wheel: Path | None = None
) -> None:
    project_site.mkdir(parents=True)
    for project in WHEEL_PROJECTS:
        with zipfile.ZipFile(wheels[project]) as archive:
            for member in archive.infolist():
                destination = (project_site / member.filename).resolve()
                if not destination.is_relative_to(project_site.resolve()):
                    raise RuntimeError(f"unsafe wheel member: {member.filename}")
            archive.extractall(project_site)
    if runtime_wheel is not None:
        with zipfile.ZipFile(runtime_wheel) as archive:
            for member in archive.infolist():
                destination = (project_site / member.filename).resolve()
                if not destination.is_relative_to(project_site.resolve()):
                    raise RuntimeError(f"unsafe wheel member: {member.filename}")
            archive.extractall(project_site)


def _parse_probe(
    stdout: str,
    project_site: Path,
    *,
    require_datoviz_runtime: bool = False,
    datoviz_source: Path | None = None,
) -> dict[str, object]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("interpreter probe did not return JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("interpreter probe must return an object")
    expected_fields = {
        "implementation",
        "version",
        "system",
        "machine",
        "pillow",
        "imports",
    }
    require_datoviz_binding = require_datoviz_runtime or datoviz_source is not None
    if require_datoviz_binding:
        expected_fields.add("datoviz_native")
    if set(value) != expected_fields:
        raise RuntimeError("interpreter probe has invalid fields")
    _runtime_description(value)
    imports = value.get("imports")
    expected_imports = dict(PROJECT_IMPORTS)
    if require_datoviz_binding:
        expected_imports.update(DATOVIZ_RUNTIME_IMPORTS)
    if not isinstance(imports, dict) or set(imports) != set(expected_imports):
        raise RuntimeError("interpreter probe has invalid project imports")
    site = project_site.resolve()
    for module, package in expected_imports.items():
        raw_path = imports[module]
        if not isinstance(raw_path, str) or not raw_path:
            raise RuntimeError(f"interpreter probe import {module} must be a path string")
        path = Path(raw_path).resolve()
        if module == "datoviz" and datoviz_source is not None and not require_datoviz_runtime:
            if not path.is_relative_to(datoviz_source.resolve()):
                raise RuntimeError("Datoviz binding was not imported from the requested source")
            if path.parts[-2:] != (package, "__init__.py"):
                raise RuntimeError("Datoviz source import is not a verified package path")
        else:
            if not path.is_relative_to(site):
                raise RuntimeError(f"{module} was not imported from the isolated wheel site")
            _logical_import_path(path, package)
    if require_datoviz_binding:
        native_path = value["datoviz_native"]
        if not isinstance(native_path, str) or not native_path:
            raise RuntimeError("interpreter probe native binding path must be a string")
        native = Path(native_path).resolve()
        source_binding = datoviz_source is not None and not require_datoviz_runtime
        expected_root = datoviz_source.resolve() if source_binding else site
        if not native.is_relative_to(expected_root):
            origin = "requested source checkout" if source_binding else "isolated wheel site"
            raise RuntimeError(f"Datoviz native binding was not loaded from the {origin}")
        if not native.is_file():
            raise RuntimeError("interpreter probe native binding does not exist")
    pillow = value.get("pillow")
    if not isinstance(pillow, str) or not pillow:
        raise RuntimeError("interpreter probe did not prove Pillow importability")
    return value


def _datoviz_probe_provenance(
    probe: dict[str, object],
    project_site: Path,
    *,
    runtime_wheel: bool,
    datoviz_source: Path | None,
) -> dict[str, str]:
    imports = cast(dict[str, str], probe["imports"])
    imported_binding = Path(imports["datoviz"]).resolve()
    native_path = Path(cast(str, probe["datoviz_native"])).resolve()
    if runtime_wheel:
        binding = _logical_import_path(imported_binding, "datoviz")
        native = str(Path("isolated-wheel-site") / native_path.relative_to(project_site.resolve()))
    elif datoviz_source is not None:
        source = datoviz_source.resolve()
        binding = str(Path("datoviz-source") / imported_binding.relative_to(source))
        native = str(Path("datoviz-source") / native_path.relative_to(source))
    else:
        raise RuntimeError("Datoviz probe provenance requires a wheel or source checkout")
    return {
        "datoviz_import": binding,
        "datoviz_native": native,
        "datoviz_native_sha256": _sha256(native_path),
    }


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
    if len(evidence) != 14:
        raise RuntimeError(f"expected 14 layout evidence records, found {len(evidence)}")
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
    for evidence_name, value in evidence.items():
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
            expected_title_diagnostic = "panel_text_title_unsupported_no_public_renderer_path"
            if evidence_name.endswith("gallery-mixed-panels"):
                if set(render_diagnostics) - {expected_title_diagnostic}:
                    raise RuntimeError("Datoviz mixed-panel render recorded unexpected diagnostics")
            elif render_diagnostics != [expected_title_diagnostic]:
                raise RuntimeError(
                    "Datoviz accepted render did not record exactly one title diagnostic"
                )
        elif title_status == "unsupported":
            raise RuntimeError("Matplotlib unexpectedly reports titles as unsupported")
        elif render_diagnostics:
            raise RuntimeError("Matplotlib unexpectedly recorded a render diagnostic")


def _assert_mixed_panel_evidence(output_dir: Path, evidence: dict[str, dict[str, object]]) -> None:
    matplotlib, datoviz = _matching_evidence(evidence, "gallery-mixed-panels")
    expected_panels = ["panel:1", "panel:2"]
    expected_views = {"panel:1": "view:1", "panel:2": "view:2"}
    expected_allocations = [[0.0, 0.0, 0.5, 1.0], [0.5, 0.0, 0.5, 1.0]]
    expected_attachments = [
        {"visual_id": "visual:mixed-2d", "panel_id": "panel:1", "view_id": "view:1"},
        {"visual_id": "visual:mixed-3d", "panel_id": "panel:2", "view_id": "view:2"},
    ]
    for backend, backend_evidence in (("matplotlib", matplotlib), ("datoviz", datoviz)):
        if backend_evidence["canvas_size"] != [800, 600]:
            raise RuntimeError(f"{backend} mixed-panel capture is not 800x600")
        if backend_evidence["warmup_canvas_size"] != [640, 360]:
            raise RuntimeError(f"{backend} mixed-panel warmup is not 640x360")
        if backend_evidence["scene_panels"] != expected_panels:
            raise RuntimeError(f"{backend} mixed-panel scene identities differ")
        if backend_evidence["scene_views"] != expected_views:
            raise RuntimeError(f"{backend} mixed-panel view routing differs")
        if backend_evidence["allocation_rects"] != expected_allocations:
            raise RuntimeError(f"{backend} mixed-panel allocations differ")
        if backend_evidence["attachments"] != expected_attachments:
            raise RuntimeError(f"{backend} mixed-panel attachments differ")
        if backend_evidence["session_teardown"] != "closed":
            raise RuntimeError(f"{backend} mixed-panel session did not close")

        resolved = backend_evidence["resolved_panels"]
        if not isinstance(resolved, list) or [
            (item["panel_id"], item["view_id"]) for item in resolved
        ] != list(expected_views.items()):
            raise RuntimeError(f"{backend} mixed-panel resolved identities differ")
        capture = output_dir / f"{backend}-gallery-mixed-panels.png"
        _assert_panel_contains_color(capture, resolved[0]["plot_rect"], expected_rgb=(220, 60, 80))
        _assert_panel_contains_color(capture, resolved[1]["plot_rect"], expected_rgb=(60, 120, 220))

        point_query = backend_evidence["point_query"]
        if not isinstance(point_query, dict) or point_query.get("status") not in {
            "hit",
            "unsupported",
        }:
            raise RuntimeError(f"{backend} mixed-panel point query was not structured")
        invalid_query = backend_evidence["invalid_panel_query"]
        if not isinstance(invalid_query, dict) or invalid_query.get("status") != "unsupported":
            raise RuntimeError(f"{backend} missing-panel query was not unsupported")


def _assert_panel_contains_color(
    path: Path,
    plot_rect: list[object],
    *,
    expected_rgb: tuple[int, int, int],
) -> None:
    image = Image.open(path).convert("RGB")
    plot_x = _number(plot_rect[0], context="mixed plot x")
    plot_y = _number(plot_rect[1], context="mixed plot y")
    plot_width = _number(plot_rect[2], context="mixed plot width")
    plot_height = _number(plot_rect[3], context="mixed plot height")
    x0 = max(0, math.floor(plot_x))
    y0 = max(0, math.floor(plot_y))
    x1 = min(image.width, math.ceil(plot_x + plot_width))
    y1 = min(image.height, math.ceil(plot_y + plot_height))
    matching = sum(
        max(
            abs(channel - expected)
            for channel, expected in zip(image.getpixel((x, y)), expected_rgb)
        )
        <= 40
        for y in range(y0, y1)
        for x in range(x0, x1)
    )
    if matching < 4:
        raise RuntimeError(
            f"{path.name} panel does not contain expected RGB {expected_rgb}: {matching} pixels"
        )


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
    parser.add_argument(
        "--allow-dirty-project-sources",
        action="store_true",
        help="record dirty source checkouts while withholding any claim that wheels match them",
    )
    parser.add_argument(
        "--datoviz-source",
        type=Path,
        help="Datoviz source checkout used for binding bootstrap or source provenance",
    )
    parser.add_argument(
        "--datoviz-source-revision",
        help="optional full SHA expected for --datoviz-source",
    )
    parser.add_argument("--gsp-core-wheel", type=Path, required=True)
    parser.add_argument("--gsp-matplotlib-wheel", type=Path, required=True)
    parser.add_argument("--gsp-datoviz-wheel", type=Path, required=True)
    parser.add_argument("--vispy2-wheel", type=Path, required=True)
    parser.add_argument(
        "--datoviz-runtime-wheel",
        type=Path,
        help="optional RC3 Datoviz runtime wheel; isolates native binding from source checkouts",
    )
    parser.add_argument(
        "--pre-rc3-runtime",
        action="store_true",
        help="explicitly qualify a local Datoviz 0.4 rc1/rc2 metadata wheel",
    )
    parser.add_argument(
        "--datoviz-runtime-source-revision",
        help="caller-declared full source SHA for a pre-RC3 Datoviz runtime wheel",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    datoviz_source = args.datoviz_source.resolve() if args.datoviz_source else None
    expected_datoviz_revision, declared_runtime_revision = _validate_datoviz_mode(
        datoviz_source=datoviz_source,
        datoviz_source_revision=args.datoviz_source_revision,
        runtime_wheel=args.datoviz_runtime_wheel,
        pre_rc3_runtime=args.pre_rc3_runtime,
        runtime_source_revision=args.datoviz_runtime_source_revision,
    )

    script_dir = Path(__file__).resolve().parent
    output_dir = args.output_dir.resolve()
    wheels = {
        "gsp-core": args.gsp_core_wheel,
        "gsp-matplotlib": args.gsp_matplotlib_wheel,
        "gsp-datoviz": args.gsp_datoviz_wheel,
        "vispy2": args.vispy2_wheel,
    }
    wheel_evidence = _validate_wheels(
        wheels,
        args.datoviz_runtime_wheel,
        allow_pre_rc3_runtime=args.pre_rc3_runtime,
    )
    source_paths = {
        "gsp": args.gsp_source.resolve(),
        "vispy2": args.vispy2_source.resolve(),
    }
    if datoviz_source is not None:
        source_paths["datoviz"] = datoviz_source
    source_states = {
        project: _git_source_state(path, allow_dirty=args.allow_dirty_project_sources)
        for project, path in source_paths.items()
    }
    if (
        expected_datoviz_revision is not None
        and source_states["datoviz"]["baseline_revision"] != expected_datoviz_revision
    ):
        raise RuntimeError("Datoviz source HEAD does not match --datoviz-source-revision")
    env = dict(os.environ)
    require_datoviz_runtime = args.datoviz_runtime_wheel is not None
    if require_datoviz_runtime:
        for name in ("DATOVIZ_LIBRARY", "DVZ_WHEEL_RUNTIME_DIRS", "GSP_DATOVIZ_SOURCE"):
            env.pop(name, None)
        env["GSP_DATOVIZ_SOURCE"] = "none"
    elif datoviz_source is not None:
        env["GSP_DATOVIZ_SOURCE"] = str(datoviz_source)
    probe_imports = dict(PROJECT_IMPORTS)
    if require_datoviz_runtime or datoviz_source is not None:
        probe_imports.update(DATOVIZ_RUNTIME_IMPORTS)

    with tempfile.TemporaryDirectory(prefix="vispy2-m290-gallery-") as temporary:
        run_dir = Path(temporary)
        project_site = run_dir / "project-site"
        capture_dir = run_dir / "captures"
        evidence_dir = run_dir / "evidence"
        capture_dir.mkdir()
        _unpack_wheels(wheels, project_site, args.datoviz_runtime_wheel)
        python_paths = [str(project_site)]
        if datoviz_source is not None and not require_datoviz_runtime:
            python_paths.append(str(datoviz_source))
        env["PYTHONPATH"] = os.pathsep.join(python_paths)
        env["MPLCONFIGDIR"] = str(run_dir / ".matplotlib")
        for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS, *SHARED_SCRIPTS):
            shutil.copy2(script_dir / name, run_dir / name)

        require_datoviz_binding = require_datoviz_runtime or datoviz_source is not None
        datoviz_probe_imports = (
            "import datoviz; import datoviz.raw; import datoviz._ctypes as datoviz_ctypes; "
            if require_datoviz_binding
            else ""
        )
        datoviz_probe_values = ", 'datoviz': datoviz.__file__" if require_datoviz_binding else ""
        datoviz_native_value = (
            ", 'datoviz_native': datoviz_ctypes.dvz._name" if require_datoviz_binding else ""
        )
        probe = subprocess.run(
            [
                str(args.python),
                "-c",
                (
                    "import json, platform, gsp, gsp_matplotlib, gsp_datoviz, vispy2; "
                    + datoviz_probe_imports
                    + "from PIL import Image; "
                    "print(json.dumps({'implementation': platform.python_implementation(), "
                    "'version': platform.python_version(), 'system': platform.system(), "
                    "'machine': platform.machine(), 'pillow': Image.__name__, "
                    "'imports': {'gsp': gsp.__file__, "
                    "'gsp_matplotlib': gsp_matplotlib.__file__, "
                    "'gsp_datoviz': gsp_datoviz.__file__, "
                    "'vispy2': vispy2.__file__"
                    + datoviz_probe_values
                    + "}"
                    + datoviz_native_value
                    + "}))"
                ),
            ],
            cwd=run_dir,
            env=env,
            check=False,
            text=True,
            capture_output=True,
        )
        if probe.returncode != 0:
            detail = probe.stderr.strip() or probe.stdout.strip() or "no diagnostic output"
            raise RuntimeError(f"interpreter probe failed: {detail}")
        probe_value = _parse_probe(
            probe.stdout,
            project_site,
            require_datoviz_runtime=require_datoviz_runtime,
            datoviz_source=datoviz_source,
        )
        import_values = cast(dict[str, str], probe_value["imports"])
        logical_imports = _logical_imports(
            import_values,
            probe_imports,
            datoviz_source=datoviz_source,
            runtime_wheel=require_datoviz_runtime,
        )

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
            backends = CHECK_SCRIPT_BACKENDS.get(script, (None,))
            for backend in backends:
                command = [str(args.python), script]
                if backend is not None:
                    command.extend(["--backend", backend])
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

        pngs = _validate_capture_set(capture_dir)
        evidence = _load_evidence(evidence_dir)
        _assert_shared_geometry(evidence)
        _assert_mixed_panel_evidence(capture_dir, evidence)
        camera_geometry = _camera_geometry_evidence(capture_dir, evidence)

        provenance: dict[str, object] = {
            "python": _runtime_description(probe_value),
            "imports": logical_imports,
            "project_wheels": wheel_evidence,
            "source_checkouts": source_states,
            "project_wheel_source_relation": _project_wheel_source_relation(source_states),
            "execution": (
                "copied scripts outside both source trees; four project wheels and the "
                "optional Datoviz runtime wheel unpacked into an isolated project site; "
                "third-party dependencies provided by the requested Python environment"
            ),
            "datoviz_timeout_seconds": args.timeout,
            "datoviz_retries": 1,
        }
        if require_datoviz_runtime:
            provenance.update(
                _datoviz_probe_provenance(
                    probe_value,
                    project_site,
                    runtime_wheel=True,
                    datoviz_source=datoviz_source,
                )
            )
        elif datoviz_source is not None:
            provenance.update(
                _datoviz_probe_provenance(
                    probe_value,
                    project_site,
                    runtime_wheel=False,
                    datoviz_source=datoviz_source,
                )
            )
        if args.pre_rc3_runtime:
            provenance["datoviz_runtime_source"] = {
                "revision": declared_runtime_revision,
                "qualification": "caller-declared; not verified against runtime wheel contents",
                "api_qualification": (
                    "the wheel binding was imported from the isolated site and its native "
                    "library passed gallery capture, query, and retained update checks"
                ),
            }
        manifest = {
            "schema": 2,
            "provenance": provenance,
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
            _verify_git_source_state(
                path,
                source_states[project],
                allow_dirty=args.allow_dirty_project_sources,
            )
        _publish_capture(capture_dir, output_dir)
    print(f"validated {len(pngs)} captures; manifest={output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
