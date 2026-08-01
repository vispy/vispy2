"""Gallery 3: orthographic 3D primitive geometry and logical-pixel squares."""

from __future__ import annotations

import argparse
from pathlib import Path

import vispy2 as vp
from gsp.protocol import CanvasSize


def make_figure() -> vp.Figure:
    figure, axes = vp.subplots(projection="3d", canvas_size=CanvasSize.pixel_exact(800, 600))
    axes.primitives(
        [
            [-1.2, -0.8, -0.2],
            [0.0, 1.0, 0.3],
            [1.2, -0.8, 0.7],
            [-0.5, -0.2, 1.0],
        ],
        topology="triangle_strip",
        indices=[0, 1, 2, 3],
        color=[49, 104, 190, 255],
        id="visual:indexed-strip",
    )
    axes.pixels(
        [-1.0, -0.15, 1.0, 0.45],
        [-0.55, 0.72, -0.48, -0.05],
        [1.15, 1.18, 1.22, 1.28],
        size=[6.0, 10.0, 14.0, 18.0],
        color=[230, 57, 70, 255],
        id="visual:pixels",
    )
    axes.set_camera(eye=(3.5, -6.0, 3.5), target=(0.0, 0.0, 0.35), up=(0.0, 0.0, 1.0))
    axes.set_orthographic(near=0.0, far=100.0)
    axes.fit_camera(margin=1.2)
    axes.set_title("Orthographic primitive + pixel scene")
    return figure


def render(
    backend: str,
    output_dir: str | Path,
    *,
    evidence_dir: str | Path | None = None,
) -> Path:
    from gallery_shared_layout import render_with_shared_layout

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{backend}-gallery-03-orthographic-3d.png"
    evidence_path = Path(evidence_dir) / f"{path.stem}.json" if evidence_dir is not None else None
    render_with_shared_layout(
        make_figure(),
        backend,
        path,
        anchor_points=((-1.2, -0.8, -0.2), (0.45, -0.05, 1.28)),
        evidence_path=evidence_path,
    )
    return path


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    return render(args.backend, args.output_dir, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    print(main())
