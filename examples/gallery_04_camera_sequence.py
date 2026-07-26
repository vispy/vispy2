"""Gallery 4: deterministic fit/orbit/pan/zoom before-and-after captures."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import vispy2 as vp
from gsp.protocol import CanvasSize

def make_figure() -> tuple[vp.Figure, vp.Axes3D]:
    figure, axes = vp.subplots(
        projection="3d", canvas_size=CanvasSize.pixel_exact(800, 600)
    )
    axes.mesh(
        np.asarray([[-1, -1, 0], [1, -1, 0], [0, 1, 0.4], [0, 0, 1.5]], dtype=np.float32),
        np.asarray([[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]], dtype=np.uint32),
        color=[70, 130, 220, 255],
        id="visual:camera-mesh",
    )
    axes.fit_camera(margin=1.15)
    # Fitting computes a tight depth interval for the fitted pose.  The following
    # orbit/pan/dolly sequence needs a deliberately wider interval so later states
    # cannot clip geometry that was visible in the first frame.
    axes.set_perspective(fov_y_degrees=45.0, near=0.01, far=100.0)
    axes.set_title("Programmatic camera")
    return figure, axes


def render(
    backend: str,
    output_dir: str | Path,
    *,
    evidence_dir: str | Path | None = None,
) -> tuple[Path, ...]:
    from gallery_shared_layout import render_with_shared_layout

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    figure, axes = make_figure()
    paths: list[Path] = []
    for name in ("00-fit", "01-orbit", "02-pan", "03-zoom"):
        if name == "01-orbit":
            axes.orbit(yaw_radians=0.35, pitch_radians=-0.15)
        elif name == "02-pan":
            axes.pan(right=0.18, up=-0.08)
        elif name == "03-zoom":
            axes.zoom(1.25)
        path = output / f"{backend}-gallery-04-{name}.png"
        evidence_path = (
            Path(evidence_dir) / f"{path.stem}.json"
            if evidence_dir is not None
            else None
        )
        render_with_shared_layout(
            figure,
            backend,
            path,
            anchor_points=((-1.0, -1.0, 0.0), (0.0, 0.0, 1.5)),
            evidence_path=evidence_path,
        )
        paths.append(path)
    return tuple(paths)


def main() -> tuple[Path, ...]:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    return render(args.backend, args.output_dir, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    print(*(str(path) for path in main()), sep="\n")
