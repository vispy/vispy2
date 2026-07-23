"""Gallery 2: perspective mesh, spheres, vectors, and billboard labels.

Matplotlib adapts 3D spheres/vectors/text to deterministic projected artists.
Datoviz is strict only for capabilities advertised by its probed v0.4 binding.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import vispy2 as vp


def make_figure() -> vp.Figure:
    figure, axes = vp.subplots(projection="3d")
    axes.mesh(
        [[-1.4, 0.0, -0.5], [-0.2, 0.0, -0.5], [-0.8, 0.0, 0.7]],
        [[0, 1, 2]],
        color=[65, 105, 225, 255],
        id="visual:mesh",
    )
    axes.spheres(
        [0.25, 1.1],
        [0.0, 0.15],
        [0.0, 0.25],
        radius=[0.42, 0.28],
        color=[[230, 57, 70, 255], [42, 157, 143, 255]],
        id="visual:spheres",
    )
    axes.vectors(
        [-1.2, 0.25, 1.1],
        [0.0, 0.0, 0.15],
        [0.0, 0.0, 0.25],
        [0.0, 0.0, 0.0],
        [0.35, 0.45, 0.35],
        [0.55, 0.7, 0.5],
        width=3.0,
        color=[244, 162, 97, 255],
        id="visual:vectors",
    )
    axes.text(
        [-1.15, 0.0, 1.45],
        [-0.15, -0.35, 0.45],
        [1.05, 1.0, 1.15],
        ["mesh", "sphere A", "sphere B"],
        font_size_px=16.0,
        color=[25, 25, 25, 255],
        anchor_x="center",
        anchor_y="bottom",
        id="visual:billboards",
    )
    axes.set_camera(eye=(3.5, -7.0, 3.2), target=(0.0, 0.0, 0.2), up=(0.0, 0.0, 1.0))
    axes.set_perspective(fov_y_degrees=42.0, near=0.1, far=100.0)
    axes.fit_camera(margin=1.25)
    axes.set_title("Perspective semantic 3D scene")
    return figure


def render(backend: str, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{backend}-gallery-02-perspective-3d.png"
    required = {
        "output.file",
        "visual.mesh",
        "visual.sphere",
        "visual.vector",
        "visual.text",
    }
    with vp.open_session(backend, require=required) as session:
        for capability in (
            "view3d.static.perspective.v1",
            "meshvisual.positions3d.data.view3d.v1",
            "spherevisual.v1",
            "vectorvisual.positions3d.data.view3d.v1",
            "textvisual.billboard3d.v1",
        ):
            if not session.capabilities.supports_view3d_capability(capability):
                raise RuntimeError(f"{backend} does not advertise {capability}")
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
