"""Installed-wheel perspective 3D scene with semantic billboard labels.

This file-output example is Matplotlib-only. Datoviz public lowering and no-capture smoke coverage
are exercised separately; native capture remains assigned to M284. Exact font selection, glyph
raster parity, and depth occlusion are not claimed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import vispy2 as vp


def make_figure() -> vp.Figure:
    """Build three separated 3D objects with independent semantic billboard labels."""
    figure, axes = vp.subplots(projection="3d")
    axes.spheres(
        [-2.2],
        [0.0],
        [0.0],
        radius=0.4,
        color=[230, 80, 70, 255],
        id="visual:billboard-sphere",
    )
    axes.mesh(
        [[-0.55, 0.0, -0.35], [0.55, 0.0, -0.35], [0.0, 0.0, 0.55]],
        [[0, 1, 2]],
        color=[90, 120, 180, 255],
        id="visual:billboard-mesh",
    )
    axes.vectors(
        [2.0],
        [-0.3],
        [-0.3],
        [0.0],
        [0.7],
        [0.8],
        color=[50, 160, 130, 255],
        width=4.0,
        id="visual:billboard-vector",
    )
    axes.text(
        [-2.2],
        [0.0],
        [0.7],
        ["Sans: ASCII"],
        color=[170, 20, 30, 255],
        font_size_px=19.0,
        font_role="sans",
        anchor_x="right",
        anchor_y="bottom",
        z_order=-1,
        id="visual:billboard-label-sans",
    )
    axes.text(
        [0.0],
        [0.0],
        [0.95],
        ["Serif: Δ café"],
        color=[35, 65, 145, 255],
        font_size_px=20.0,
        font_role="serif",
        anchor_x="center",
        anchor_y="bottom",
        z_order=0,
        id="visual:billboard-label-serif",
    )
    axes.text(
        [2.0],
        [0.4],
        [0.75],
        ["Mono: 20°"],
        color=[20, 110, 80, 255],
        font_size_px=19.0,
        font_role="monospace",
        anchor_x="left",
        anchor_y="top",
        rotation_rad=0.3490658503988659,
        z_order=1,
        id="visual:billboard-label-mono",
    )
    axes.set_camera(
        eye=(0.0, -9.0, 4.0),
        target=(0.0, 0.0, 0.2),
        up=(0.0, 0.0, 1.0),
    )
    axes.set_perspective(fov_y_degrees=42.0, near=0.1, far=100.0)
    axes.fit_camera(margin=1.25)
    axes.set_title("Screen-facing 3D billboard text")
    return figure


def render_backend(backend: str, output_dir: str | Path) -> Path:
    """Render through the qualified Matplotlib file-output path."""
    if backend != "matplotlib":
        raise ValueError(
            "text_billboards_3d.py supports Matplotlib file output only; "
            "native Datoviz capture remains assigned to M284"
        )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with vp.open_session(backend, require={"output.file", "visual.text"}) as session:
        capabilities = session.capabilities
        if not capabilities.supports_view3d_capability("textvisual.billboard3d.v1"):
            raise RuntimeError(f"{backend} does not support textvisual.billboard3d.v1")
        if capabilities.supports_view3d_capability("textvisual.billboard3d.depth_occlusion.v1"):
            raise RuntimeError(f"{backend} must not claim billboard depth occlusion")
        if capabilities.font_layout_capability.rasterization_parity:
            raise RuntimeError(f"{backend} must not claim cross-backend glyph parity")
        path = output / f"{backend}-text-billboards3d.png"
        session.render(make_figure().to_scene(), target=path)
    return path


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib",))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args: Any = parser.parse_args(argv)
    return render_backend(args.backend, args.output_dir)


if __name__ == "__main__":
    print(main())
