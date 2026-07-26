"""Validate the S065 gallery against wheel-installed packages.

Run this script with a Python interpreter whose environment contains the four
local wheels. The harness copies gallery scripts to a temporary directory,
verifies that ``gsp`` and ``vispy2`` are not imported from either source tree,
captures galleries 1--4 with both backends, then exercises capability discovery
and queries. Datoviz subprocesses have a hard timeout and one retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
from typing import Final

from PIL import Image


CAPTURE_SCRIPTS: Final = (
    "gallery_01_priority_2d.py",
    "gallery_02_perspective_3d.py",
    "gallery_03_orthographic_3d.py",
    "gallery_04_camera_sequence.py",
)
CHECK_SCRIPTS: Final = ("gallery_06_capabilities.py", "gallery_07_queries.py")
SHARED_SCRIPTS: Final = ("gallery_shared_layout.py",)


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    retries: int = 0,
) -> None:
    for attempt in range(retries + 1):
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            text=True,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
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
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


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
                if abs(float(left_value) - float(right_value)) > 1.0:
                    raise RuntimeError(f"{suffix} projected anchors differ by over one pixel")

        aspect = matplotlib["effective_perspective_aspect"]
        if aspect is not None:
            plot_rect = matplotlib["plot_rect"]
            assert isinstance(plot_rect, list)
            plot_ratio = float(plot_rect[2]) / float(plot_rect[3])
            if abs(float(aspect) - plot_ratio) > 1e-12:
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
        if backend == "datoviz":
            if title_status != "unsupported":
                raise RuntimeError("Datoviz title limitation is not recorded as unsupported")
            if "panel_text_title_unsupported_no_public_renderer_path" not in diagnostics:
                raise RuntimeError("Datoviz title diagnostic is missing")
        elif title_status == "unsupported":
            raise RuntimeError("Matplotlib unexpectedly reports titles as unsupported")


def _geometry_bounds(path: Path, plot_rect: list[object]) -> list[int]:
    image = Image.open(path).convert("RGBA")
    x0 = max(0, int(float(plot_rect[0])))
    y0 = max(0, int(float(plot_rect[1])))
    x1 = min(image.width, int(float(plot_rect[0]) + float(plot_rect[2]) + 1.0))
    y1 = min(image.height, int(float(plot_rect[1]) + float(plot_rect[3]) + 1.0))
    background = image.getpixel((0, 0))
    pixels = image.load()
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gsp-source", type=Path, required=True)
    parser.add_argument("--vispy2-source", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", str(output_dir / ".matplotlib"))

    with tempfile.TemporaryDirectory(prefix="vispy2-m288-gallery-") as temporary:
        run_dir = Path(temporary)
        evidence_dir = run_dir / "evidence"
        for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS, *SHARED_SCRIPTS):
            shutil.copy2(script_dir / name, run_dir / name)

        probe = subprocess.run(
            [
                str(args.python),
                "-c",
                "import gsp, vispy2; print(gsp.__file__); print(vispy2.__file__)",
            ],
            cwd=run_dir,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
        import_paths = tuple(Path(line).resolve() for line in probe.stdout.splitlines())
        source_roots = (args.gsp_source.resolve(), args.vispy2_source.resolve())
        if any(path.is_relative_to(root) for path in import_paths for root in source_roots):
            raise RuntimeError(f"source-tree import detected: {import_paths}")

        for backend in ("matplotlib", "datoviz"):
            for script in CAPTURE_SCRIPTS:
                command = [
                    str(args.python),
                    script,
                    backend,
                    "--output-dir",
                    str(output_dir),
                ]
                if script != "gallery_01_priority_2d.py":
                    command.extend(["--evidence-dir", str(evidence_dir)])
                _run(
                    command,
                    cwd=run_dir,
                    env=env,
                    timeout=args.timeout,
                    retries=1 if backend == "datoviz" else 0,
                )
        for script in CHECK_SCRIPTS:
            _run(
                [str(args.python), script],
                cwd=run_dir,
                env=env,
                timeout=args.timeout,
            )

        pngs = sorted(output_dir.glob("*-gallery-*.png"))
        if len(pngs) != 14:
            raise RuntimeError(f"expected 14 gallery PNGs, found {len(pngs)}")
        wrong_sizes = {
            path.name: _png_size(path)
            for path in pngs
            if _png_size(path) != (800, 600)
        }
        if wrong_sizes:
            raise RuntimeError(f"gallery PNG dimensions must all be 800x600: {wrong_sizes}")
        evidence = _load_evidence(evidence_dir)
        _assert_shared_geometry(evidence)
        camera_geometry = _camera_geometry_evidence(output_dir, evidence)

    manifest = {
        "schema": 2,
        "provenance": {
            "python": str(args.python.resolve()),
            "gsp_import": str(import_paths[0]),
            "vispy2_import": str(import_paths[1]),
            "gsp_source_revision": _git_revision(args.gsp_source),
            "vispy2_source_revision": _git_revision(args.vispy2_source),
            "execution": "copied scripts outside both source trees; wheel-installed imports",
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
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(pngs)} captures; manifest={output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
