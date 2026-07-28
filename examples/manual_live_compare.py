"""Open matching Matplotlib and Datoviz review windows from one terminal.

The parent process launches one child per backend. This keeps native Datoviz
isolated while both windows remain visible concurrently. Both children resolve
the same Matplotlib reference layout before display, so titles and axes do not
silently change the shared data viewport.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

import vispy2 as vp
from gsp.protocol import (
    CanvasSize,
    MESH3D_DATA_VIEW3D_CAPABILITY,
    MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
    MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
    MESH_NORMALS_FACE3D_CAPABILITY,
    VIEW3D_LIGHT_AMBIENT_CAPABILITY,
    VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
)

from gallery_01_priority_2d import make_figure as make_priority_2d
from gallery_02_perspective_3d import make_figure as make_perspective_3d
from gallery_03_orthographic_3d import make_figure as make_orthographic_3d
from gallery_04_camera_sequence import make_figure as make_camera_figure
from gallery_05_datoviz_navigation import make_figure as make_flat_lambert
from gallery_shared_layout import (
    _required_capabilities,
    _validate_view3d_capabilities,
    resolve_shared_layout,
)


BACKENDS = ("matplotlib", "datoviz")
CAMERA_CASES = (
    "camera-fit",
    "camera-orbit",
    "camera-pan",
    "camera-zoom",
    "camera-reset",
)
CASES = (
    "priority-2d",
    "perspective-3d",
    "orthographic-3d",
    "flat-lambert",
    *CAMERA_CASES,
)
FLAT_LAMBERT_CAPABILITIES = {
    MESH3D_DATA_VIEW3D_CAPABILITY,
    MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
    MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
    MESH_NORMALS_FACE3D_CAPABILITY,
    VIEW3D_LIGHT_AMBIENT_CAPABILITY,
    VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
}


def run_datoviz_until_close(renderer: object) -> None:
    """Pump bounded frames so GSP can unsubscribe before Datoviz reaps the view.

    ``dvz_app_run(app, 0)`` performs per-view close cleanup before returning.
    That invalidates the input router while the GSP adapter still owns a
    callback subscription. Polling one frame at a time lets Python observe the
    close request first; the session context can then unsubscribe and destroy
    the app in the correct order.
    """
    show = getattr(renderer, "show", None)
    dvz = getattr(renderer, "dvz", None)
    should_exit = getattr(dvz, "dvz_app_should_exit", None)
    if not callable(show) or not callable(should_exit):
        raise RuntimeError(
            "safe Datoviz live review requires bounded frame pumping and "
            "dvz_app_should_exit()"
        )
    if os.environ.get("GSP_TEST") == "True":
        show(frame_count=1)
        return
    app = getattr(renderer, "app", None)
    if app is None:
        show(frame_count=1)
        app = getattr(renderer, "app", None)
    if app is None:
        raise RuntimeError("Datoviz did not create an app for live review")
    while not should_exit(app):
        show(frame_count=1)


def _camera_figure(case: str) -> vp.Figure:
    figure, axes = make_camera_figure()
    if case in {"camera-orbit", "camera-pan", "camera-zoom", "camera-reset"}:
        axes.orbit(yaw_radians=0.35, pitch_radians=-0.15)
    if case in {"camera-pan", "camera-zoom", "camera-reset"}:
        axes.pan(right=0.18, up=-0.08)
    if case in {"camera-zoom", "camera-reset"}:
        axes.zoom(1.25)
    if case == "camera-reset":
        axes.reset_camera()
    return figure


def make_figure(case: str) -> vp.Figure:
    """Build one backend-neutral semantic scene for a live comparison."""
    builders: dict[str, Callable[[], vp.Figure]] = {
        "priority-2d": make_priority_2d,
        "perspective-3d": make_perspective_3d,
        "orthographic-3d": make_orthographic_3d,
        "flat-lambert": make_flat_lambert,
    }
    if case in CAMERA_CASES:
        return _camera_figure(case)
    try:
        figure = builders[case]()
    except KeyError as exc:
        raise ValueError(f"unknown comparison case: {case!r}") from exc
    if case == "flat-lambert":
        figure.canvas_size = CanvasSize.pixel_exact(800, 600)
    return figure


def _show_child(case: str, backend: str) -> None:
    figure = make_figure(case)
    scene = figure.to_scene()
    layout = resolve_shared_layout(figure) if scene.view3d is not None else None
    required = _required_capabilities(figure) - {"output.file"}
    if case == "flat-lambert" and backend == "datoviz":
        required.update(FLAT_LAMBERT_CAPABILITIES)
    with vp.open_session(backend, require=required) as session:
        if scene.view3d is not None:
            _validate_view3d_capabilities(figure, backend, session.capabilities)
        if layout is None:
            renderer = figure.display(session, block=False)
        else:
            renderer = figure.display(session, block=False, layout_snapshot=layout)
        print(f"{backend}: window open for {case}; close it when finished.", flush=True)
        if backend == "datoviz":
            run_datoviz_until_close(renderer)
        else:
            session.run()
    print(f"{backend}: window closed cleanly.", flush=True)


def _terminate_children(children: list[subprocess.Popen[bytes]]) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        if child.poll() is not None:
            continue
        try:
            child.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def _launch_pair(case: str) -> None:
    script = Path(__file__).resolve()
    env = dict(os.environ)
    commands = [
        [sys.executable, str(script), case, "--backend", backend]
        for backend in BACKENDS
    ]
    children = [subprocess.Popen(command, env=env) for command in commands]
    print(
        f"Opened {case!r} through Matplotlib and Datoviz. "
        "Move the windows side by side, then close both.",
        flush=True,
    )
    try:
        return_codes = [child.wait() for child in children]
    except KeyboardInterrupt:
        print("Interrupted; closing both backend children.", flush=True)
        _terminate_children(children)
        return
    failed = {
        backend: return_code
        for backend, return_code in zip(BACKENDS, return_codes, strict=True)
        if return_code != 0
    }
    if failed:
        raise RuntimeError(f"live comparison child failed: {failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=(*CASES, "all"))
    parser.add_argument("--backend", choices=BACKENDS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.backend is None:
        cases = CASES if args.case == "all" else (args.case,)
        for case in cases:
            _launch_pair(case)
    else:
        if args.case == "all":
            parser.error("'all' is available only from the parent comparison command")
        _show_child(args.case, args.backend)


if __name__ == "__main__":
    main()
