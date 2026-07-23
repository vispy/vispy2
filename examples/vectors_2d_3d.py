"""Render installed-wheel 2D and 3D straight vector-field examples with Matplotlib.

This historical reference example does not offer a Datoviz mode; M283 galleries 1 and 2 provide
the installed-wheel Datoviz capture path. Matplotlib deterministically preserves resolved
endpoints, colors, and logical-pixel widths. Its 3D renderer is a projected overlay with adapted
marker heads, not a native 3D-axes vector implementation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

import vispy2 as vp


def make_2d_figure() -> vp.Figure:
    """Build a centered 2D rotational vector field."""
    figure, axes = vp.subplots()
    grid = np.linspace(-1.0, 1.0, 7, dtype=np.float32)
    x, y = np.meshgrid(grid, grid)
    nonzero = np.hypot(x, y) > 0.0
    axes.vectors(
        x[nonzero],
        y[nonzero],
        -y[nonzero],
        x[nonzero],
        color=[42, 157, 143, 255],
        width=2.0,
        scale=0.18,
        anchor="center",
        start_cap="butt",
        end_cap="triangle_out",
    )
    axes.set_xlim(-1.25, 1.25)
    axes.set_ylim(-1.25, 1.25)
    axes.set_title("2D semantic vector field")
    return figure


def make_3d_figure() -> vp.Figure:
    """Build a perspective 3D vector field with DATA-space displacements."""
    figure, axes = vp.subplots(projection="3d")
    theta = np.linspace(0.0, 2.0 * np.pi, 16, endpoint=False, dtype=np.float32)
    x = np.cos(theta)
    y = np.sin(theta)
    z = np.linspace(-0.75, 0.75, theta.size, dtype=np.float32)
    axes.vectors(
        x,
        y,
        z,
        -0.35 * y,
        0.35 * x,
        np.full_like(z, 0.2),
        color=[230, 57, 70, 255],
        width=2.5,
        anchor="tail",
        end_cap="triangle_out",
    )
    axes.fit_camera(margin=1.2)
    axes.set_title("3D semantic vector field")
    return figure


def render_backend(backend: str, output_dir: str | Path) -> tuple[Path, Path]:
    """Render both fields through the qualified Matplotlib file-output path."""
    if backend != "matplotlib":
        raise ValueError(
            "vectors_2d_3d.py supports Matplotlib file output only; "
            "use gallery_01 or gallery_02 for the qualified Datoviz journey"
        )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with vp.open_session(
        backend,
        require={"output.file", "visual.vector"},
    ) as session:
        capabilities = session.capabilities
        for capability in (
            "vectorvisual.straight.v1",
            "vectorvisual.positions3d.data.view3d.v1",
            "vectorvisual.triangle_head.v1",
        ):
            if not capabilities.supports_view3d_capability(capability):
                raise RuntimeError(f"{backend} does not support {capability}")
        path2d = output / f"{backend}-vectors2d.png"
        path3d = output / f"{backend}-vectors3d.png"
        session.render(make_2d_figure().to_scene(), target=path2d)
        session.render(make_3d_figure().to_scene(), target=path3d)
    return path2d, path3d


def main(argv: list[str] | None = None) -> tuple[Path, Path]:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib",))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args: Any = parser.parse_args(argv)
    return render_backend(args.backend, args.output_dir)


if __name__ == "__main__":
    for rendered_path in main():
        print(rendered_path)
