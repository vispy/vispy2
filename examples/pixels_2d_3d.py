"""PixelVisual 2D/3D installed-wheel example.

Matplotlib is strict for 2D square width and adapts 3D pixels to projected square overlays.
The Datoviz adapter lowers both cases through public ``dvz_pixel`` attributes; M283 galleries 1
and 3 provide installed-wheel Datoviz captures.
"""

from pathlib import Path

import vispy2 as vp


def save_artifacts(output_dir: str | Path = "artifacts") -> tuple[Path, Path]:
    """Render deterministic Matplotlib 2D and 3D PixelVisual artifacts."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    figure2d, axes2d = vp.subplots()
    axes2d.pixels(
        [-0.75, -0.25, 0.25, 0.75],
        [0.0, 0.0, 0.0, 0.0],
        color=[
            [230, 57, 70, 255],
            [29, 53, 87, 255],
            [69, 123, 157, 255],
            [241, 250, 238, 255],
        ],
        size=[4.0, 8.0, 12.0, 16.0],
    )
    axes2d.set_xlim(-1.0, 1.0)
    axes2d.set_ylim(-0.5, 0.5)
    path2d = destination / "pixelvisual-2d.png"
    figure2d.savefig(path2d)

    figure3d, axes3d = vp.subplots(projection="3d")
    axes3d.pixels(
        [-1.0, 0.0, 1.0],
        [0.0, 0.5, 0.0],
        [-0.5, 0.0, 0.5],
        color=[
            [230, 57, 70, 255],
            [69, 123, 157, 255],
            [42, 157, 143, 255],
        ],
        size=[8.0, 12.0, 16.0],
    )
    axes3d.fit_camera()
    path3d = destination / "pixelvisual-3d.png"
    figure3d.savefig(path3d)
    return path2d, path3d


if __name__ == "__main__":
    print(*(str(path) for path in save_artifacts()), sep="\n")
