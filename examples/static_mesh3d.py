"""Render deterministic perspective and orthographic VisPy2 mesh scenes.

Supported backends: Matplotlib and Datoviz v0.4. Matplotlib is the deterministic
reference renderer. Datoviz uses its retained DATA-space View3D mesh path when
the installed public bindings advertise it.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

import vispy2 as vp


POSITIONS = np.asarray(
    [
        [-1.0, -1.0, -1.0],
        [1.0, -1.0, -1.0],
        [1.0, 1.0, -1.0],
        [-1.0, 1.0, -1.0],
        [-1.0, -1.0, 1.0],
        [1.0, -1.0, 1.0],
        [1.0, 1.0, 1.0],
        [-1.0, 1.0, 1.0],
    ],
    dtype=np.float32,
)
FACES = np.asarray(
    [
        [0, 2, 1],
        [0, 3, 2],
        [4, 5, 6],
        [4, 6, 7],
        [0, 1, 5],
        [0, 5, 4],
        [2, 3, 7],
        [2, 7, 6],
        [1, 2, 6],
        [1, 6, 5],
        [3, 0, 4],
        [3, 4, 7],
    ],
    dtype=np.uint32,
)
FACE_COLORS = np.asarray(
    [
        [49, 104, 190, 255],
        [49, 104, 190, 255],
        [100, 181, 246, 255],
        [100, 181, 246, 255],
        [73, 140, 103, 255],
        [73, 140, 103, 255],
        [117, 177, 82, 255],
        [117, 177, 82, 255],
        [238, 169, 72, 255],
        [238, 169, 72, 255],
        [207, 91, 80, 255],
        [207, 91, 80, 255],
    ],
    dtype=np.uint8,
)


def make_figure(*, projection: str) -> vp.Figure:
    """Build one fitted static mesh figure without selecting a backend."""
    figure, axes = vp.subplots(projection="3d")
    axes.set_title(f"{projection.title()} 3D mesh")
    axes.mesh(
        POSITIONS,
        FACES,
        color=FACE_COLORS,
        color_mode="face",
        id=f"visual:cube-{projection}",
    )
    if projection == "perspective":
        axes.set_perspective(fov_y_degrees=45.0, near=0.1, far=1000.0)
    elif projection == "orthographic":
        axes.set_orthographic(xlim=(-1.0, 1.0), ylim=(-1.0, 1.0), near=0.0, far=1000.0)
    else:
        raise ValueError("projection must be 'perspective' or 'orthographic'")
    axes.fit_camera()
    return figure


def render_backend(backend: str, output_dir: str | Path) -> tuple[Path, Path]:
    """Render both scenes after checking the backend's View3D capabilities."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    figures = {
        "perspective": make_figure(projection="perspective"),
        "orthographic": make_figure(projection="orthographic"),
    }
    required = {
        "perspective": "view3d.static.perspective.v1",
        "orthographic": "view3d.static.orthographic.v1",
    }
    paths: list[Path] = []
    with vp.open_session(
        backend,
        require={"output.file", "visual.mesh"},
    ) as session:
        capabilities = session.capabilities
        mesh_capability = "meshvisual.positions3d.data.view3d.v1"
        if not capabilities.supports_view3d_capability(mesh_capability):
            raise RuntimeError(f"{backend} does not support {mesh_capability}")
        for projection, figure in figures.items():
            projection_capability = required[projection]
            if not capabilities.supports_view3d_capability(projection_capability):
                raise RuntimeError(f"{backend} does not support {projection_capability}")
            path = output / f"{backend}-{projection}-mesh3d.png"
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
