"""Render bounded DATA-space spheres in perspective and orthographic views.

Datoviz lowers these visuals to raycast impostors with analytic surface depth. Matplotlib is a
reference adaptation: it projects a view-plane radius to a circle and orders circles far-to-near
by center depth, so it does not claim analytic sphere-surface depth.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import vispy2 as vp


def make_figure(*, projection: str) -> vp.Figure:
    """Build overlapping spheres that expose radius, color, camera, and depth behavior."""
    figure, axes = vp.subplots(projection="3d")
    axes.set_camera(
        eye=(0.0, -6.0, 2.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 0.0, 1.0),
    )
    axes.spheres(
        [-0.9, 0.0, 0.75, 0.0],
        [0.0, 0.35, 0.0, -0.65],
        [0.0, 0.0, 0.1, -0.2],
        radius=[0.55, 0.9, 0.4, 0.3],
        color=[
            [230, 57, 70, 255],
            [69, 123, 157, 255],
            [42, 157, 143, 255],
            [252, 163, 17, 255],
        ],
        id=f"visual:spheres-{projection}",
    )
    if projection == "perspective":
        axes.set_perspective(fov_y_degrees=42.0, near=0.1, far=100.0)
    elif projection == "orthographic":
        axes.set_orthographic(near=0.0, far=100.0)
    else:
        raise ValueError("projection must be 'perspective' or 'orthographic'")
    axes.fit_camera(margin=1.2)
    axes.set_title(f"{projection.title()} DATA-space spheres")
    return figure


def render_backend(backend: str, output_dir: str | Path) -> tuple[Path, Path]:
    """Render both projections after explicit sphere capability checks."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    with vp.open_session(
        backend,
        require={"output.file", "visual.sphere"},
    ) as session:
        caps = session.capabilities
        if not caps.supports_view3d_capability("spherevisual.v1"):
            raise RuntimeError(f"{backend} does not support spherevisual.v1")
        if backend == "datoviz" and not caps.supports_view3d_capability(
            "spherevisual.analytic_surface_depth.v1"
        ):
            raise RuntimeError("Datoviz does not prove analytic sphere-surface depth")
        if backend == "matplotlib" and caps.supports_view3d_capability(
            "spherevisual.analytic_surface_depth.v1"
        ):
            raise RuntimeError("Matplotlib must not claim analytic sphere-surface depth")
        for projection in ("perspective", "orthographic"):
            figure = make_figure(projection=projection)
            path = output / f"{backend}-{projection}-spheres3d.png"
            session.render(figure.to_scene(), target=path)
            paths.append(path)
    return paths[0], paths[1]


def main(argv: list[str] | None = None) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args: Any = parser.parse_args(argv)
    return render_backend(args.backend, args.output_dir)


if __name__ == "__main__":
    for rendered_path in main():
        print(rendered_path)
