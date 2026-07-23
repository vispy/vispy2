"""Render all five bounded PrimitiveVisual topologies from an installed wheel.

Matplotlib supports deterministic file output with explicit point/line/triangle adaptation.
M283 galleries 1 and 3 provide the installed-wheel Datoviz capture path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import vispy2 as vp


def make_figure() -> vp.Figure:
    """Build an indexed/unindexed gallery containing every bounded topology."""
    figure, axes = vp.subplots()
    colors = (
        [230, 57, 70, 255],
        [42, 157, 143, 255],
        [69, 123, 157, 255],
        [244, 162, 97, 255],
        [131, 56, 236, 255],
    )
    axes.primitives(
        [[-4.0, 1.5], [-3.5, 1.5], [-3.0, 1.5]],
        topology="point_list",
        color=colors[0],
    )
    axes.primitives(
        [[-2.0, 1.0], [-1.0, 2.0], [-1.0, 1.0], [-2.0, 2.0]],
        topology="line_list",
        color=colors[1],
        indices=[0, 1, 2, 3],
    )
    axes.primitives(
        [[0.0, 1.0], [0.5, 2.0], [1.0, 1.0], [1.5, 2.0]],
        topology="line_strip",
        color=colors[2],
    )
    axes.primitives(
        [[2.0, 1.0], [3.0, 1.0], [2.5, 2.0]],
        topology="triangle_list",
        color=colors[3],
        indices=[0, 1, 2],
    )
    axes.primitives(
        [[-1.0, -2.0], [0.0, -2.0], [-1.0, -1.0], [0.0, -1.0]],
        topology="triangle_strip",
        color=colors[4],
    )
    axes.set_xlim(-4.5, 3.5)
    axes.set_ylim(-2.5, 2.5)
    axes.set_title("Bounded primitive topologies")
    return figure


def render_backend(backend: str, output_dir: str | Path) -> Path:
    """Render through the qualified Matplotlib installed-wheel path."""
    if backend != "matplotlib":
        raise ValueError(
            "primitive_topologies.py supports Matplotlib file output only; "
            "use gallery_01 or gallery_03 for the qualified Datoviz journey"
        )
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with vp.open_session(
        backend,
        require={"output.file", "visual.primitive"},
    ) as session:
        for capability in (
            "primitivevisual.v1",
            "primitivevisual.indexed.v1",
            "primitivevisual.point_list",
            "primitivevisual.line_list",
            "primitivevisual.line_strip",
            "primitivevisual.triangle_list",
            "primitivevisual.triangle_strip",
        ):
            if not session.capabilities.supports_view3d_capability(capability):
                raise RuntimeError(f"{backend} does not support {capability}")
        path = output / f"{backend}-primitive-topologies.png"
        session.render(make_figure().to_scene(), target=path)
    return path


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib",))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args: Any = parser.parse_args(argv)
    return render_backend(args.backend, args.output_dir)


if __name__ == "__main__":
    main()
