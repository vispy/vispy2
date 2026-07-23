"""Gallery 1: the priority 2D visual families in one semantic scene.

Backends: Matplotlib (deterministic adapted publication output) and Datoviz v0.4
(strict public visual lowering when the probed capabilities are available).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import vispy2 as vp


def make_figure() -> vp.Figure:
    figure, axes = vp.subplots()
    axes.scatter(
        [-1.6, -1.1, -0.6],
        [0.9, 1.25, 0.8],
        size=[14.0, 24.0, 18.0],
        color=[31, 119, 180, 255],
        id="visual:points",
    )
    axes.markers(
        [-1.6, -1.1, -0.6],
        [0.0, 0.35, -0.1],
        shape=["disc", "square", "triangle"],
        size=26.0,
        color=[214, 39, 40, 255],
        id="visual:markers",
    )
    axes.pixels(
        [-1.6, -1.1, -0.6],
        [-0.9, -0.75, -1.0],
        size=[5.0, 10.0, 15.0],
        color=[44, 160, 44, 255],
        id="visual:pixels",
    )
    axes.vectors(
        [0.25, 0.8, 1.35],
        [0.9, 0.9, 0.9],
        [0.25, -0.15, 0.2],
        [0.35, 0.4, -0.35],
        width=2.5,
        color=[148, 103, 189, 255],
        id="visual:vectors",
    )
    axes.primitives(
        [[0.2, -1.0], [0.8, -0.2], [1.4, -1.0]],
        topology="triangle_list",
        color=[
            [255, 127, 14, 255],
            [255, 187, 120, 255],
            [255, 127, 14, 255],
        ],
        id="visual:primitive",
    )
    axes.text(
        [0.8],
        [-1.2],
        ["semantic families"],
        font_size_px=16.0,
        color=[35, 35, 35, 255],
        id="visual:text",
    )
    axes.set_xlim(-2.0, 1.8)
    axes.set_ylim(-1.5, 1.6)
    axes.set_title("GSP priority 2D families")
    axes.grid(True)
    return figure


def render(backend: str, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    required = {
        "output.file",
        "visual.points",
        "visual.markers",
        "visual.pixels",
        "visual.vector",
        "visual.primitive",
        "visual.text",
    }
    path = output / f"{backend}-gallery-01-priority-2d.png"
    with vp.open_session(backend, require=required) as session:
        session.render(make_figure().to_scene(), target=path)
    return path


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()
    return render(args.backend, args.output_dir)


if __name__ == "__main__":
    print(main())
