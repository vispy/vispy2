"""Gallery 3: orthographic 3D primitive geometry and logical-pixel squares."""

from __future__ import annotations

import argparse
from pathlib import Path

import vispy2 as vp


def make_figure() -> vp.Figure:
    figure, axes = vp.subplots(projection="3d")
    axes.primitives(
        [
            [-1.2, -0.8, -0.2],
            [0.0, 1.0, 0.3],
            [1.2, -0.8, 0.7],
            [-0.5, -0.2, 1.0],
        ],
        topology="triangle_strip",
        indices=[0, 1, 2, 3],
        color=[
            [49, 104, 190, 255],
            [100, 181, 246, 255],
            [73, 140, 103, 255],
            [238, 169, 72, 255],
        ],
        id="visual:indexed-strip",
    )
    axes.pixels(
        [-1.2, 0.0, 1.2, -0.5],
        [-0.8, 1.0, -0.8, -0.2],
        [-0.2, 0.3, 0.7, 1.0],
        size=[6.0, 10.0, 14.0, 18.0],
        color=[230, 57, 70, 255],
        id="visual:pixels",
    )
    axes.set_camera(eye=(3.5, -6.0, 3.5), target=(0.0, 0.0, 0.35), up=(0.0, 0.0, 1.0))
    axes.set_orthographic(near=0.0, far=100.0)
    axes.fit_camera(margin=1.2)
    axes.set_title("Orthographic primitive + pixel scene")
    return figure


def render(backend: str, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{backend}-gallery-03-orthographic-3d.png"
    with vp.open_session(
        backend,
        require={"output.file", "visual.primitive", "visual.pixels"},
    ) as session:
        for capability in (
            "view3d.static.orthographic.v1",
            "primitivevisual.v1",
            "primitivevisual.indexed.v1",
            "primitivevisual.triangle_strip",
            "pixelvisual.v1",
            "pixelvisual.positions3d.data.view3d.v1",
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
