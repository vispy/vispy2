"""Render a deterministic programmatic View3D camera sequence.

Supported backends: Matplotlib and Datoviz v0.4 static/offscreen rendering.
The caller explicitly owns the GSP session for the complete sequence. Live
Datoviz input remains deferred pending M284 native lifecycle qualification and
owner interaction review; this example does not advertise or enable it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

import numpy as np

import vispy2 as vp


POSITIONS = np.asarray(
    [
        [-1.0, -1.0, 0.0],
        [1.0, -1.0, 0.0],
        [0.0, 1.0, 0.5],
        [0.0, 0.0, 1.5],
    ],
    dtype=np.float32,
)
FACES = np.asarray(
    [[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]],
    dtype=np.uint32,
)


def make_figure() -> tuple[vp.Figure, vp.Axes3D]:
    """Build the backend-neutral camera example scene."""
    figure, axes = vp.subplots(projection="3d")
    axes.mesh(
        POSITIONS,
        FACES,
        color=[70, 130, 220, 255],
        id="visual:camera-mesh",
    )
    axes.fit_camera()
    axes.set_title("Programmatic View3D camera")
    return figure, axes


def render_camera_sequence(backend: str, output_dir: str | Path) -> tuple[Path, ...]:
    """Render successive semantic camera states with one caller-owned session."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    figure, axes = make_figure()
    states: tuple[tuple[str, Callable[[], object] | None], ...] = (
        ("00-fitted", None),
        ("01-orbit", lambda: axes.orbit(yaw_radians=0.35, pitch_radians=-0.15)),
        ("02-pan", lambda: axes.pan(right=0.2, up=-0.1)),
        ("03-zoom", lambda: axes.zoom(1.25)),
        ("04-reset", axes.reset_camera),
    )
    paths: list[Path] = []

    # Interactive and non-blocking use must keep this explicit session ownership.
    with vp.open_session(
        backend,
        require={"output.file", "visual.mesh"},
    ) as session:
        capabilities = session.capabilities
        required = "view3d.static.perspective.v1"
        if not capabilities.supports_view3d_capability(required):
            raise RuntimeError(f"{backend} does not support {required}")
        for name, update in states:
            if update is not None:
                update()
            path = output / f"{backend}-{name}.png"
            session.render(figure.to_scene(), target=path)
            paths.append(path)

    return tuple(paths)


def main(argv: list[str] | None = None) -> tuple[Path, ...]:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args: Any = parser.parse_args(argv)
    return render_camera_sequence(args.backend, args.output_dir)


if __name__ == "__main__":
    for rendered_path in main():
        print(rendered_path)
