"""Validate the M283 gallery against wheel-installed packages.

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
import subprocess
import sys
import tempfile
from typing import Final


CAPTURE_SCRIPTS: Final = (
    "gallery_01_priority_2d.py",
    "gallery_02_perspective_3d.py",
    "gallery_03_orthographic_3d.py",
    "gallery_04_camera_sequence.py",
)
CHECK_SCRIPTS: Final = ("gallery_06_capabilities.py", "gallery_07_queries.py")


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


def _git_revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


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

    with tempfile.TemporaryDirectory(prefix="vispy2-m283-gallery-") as temporary:
        run_dir = Path(temporary)
        for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS):
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
                _run(
                    [
                        str(args.python),
                        script,
                        backend,
                        "--output-dir",
                        str(output_dir),
                    ],
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
    manifest = {
        "schema": 1,
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
            for name in (*CAPTURE_SCRIPTS, *CHECK_SCRIPTS)
        },
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)} for path in pngs
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(pngs)} captures; manifest={output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
