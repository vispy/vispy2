from __future__ import annotations

from pathlib import Path
import runpy
from typing import Any, cast

import numpy as np

import vispy2 as vp


def test_gallery_3_uses_uniform_primitive_color_and_distinct_pixel_anchors() -> None:
    namespace = runpy.run_path(
        str(Path(__file__).parents[1] / "examples" / "gallery_03_orthographic_3d.py")
    )
    figure = cast(Any, namespace["make_figure"])()
    assert isinstance(figure, vp.Figure)
    scene = figure.to_scene()
    primitive, pixels = scene.visuals

    assert np.unique(primitive.colors, axis=0).shape == (1, 4)
    assert not any(
        np.array_equal(pixel_position, primitive_position)
        for pixel_position in pixels.positions
        for primitive_position in primitive.positions
    )
    assert scene.view3d is not None
    camera = scene.view3d.camera
    forward = np.asarray(camera.target) - np.asarray(camera.eye)
    forward /= np.linalg.norm(forward)
    primitive_depths = primitive.positions @ forward
    pixel_depths = pixels.positions @ forward
    assert np.min(np.abs(pixel_depths[:, None] - primitive_depths[None, :])) > 0.05
    pixel_depth_separation = np.abs(pixel_depths[:, None] - pixel_depths[None, :])
    np.fill_diagonal(pixel_depth_separation, np.inf)
    assert np.min(pixel_depth_separation) > 0.05
    assert scene.canvas_size is not None
    resolved = scene.canvas_size.resolve()
    assert (resolved.framebuffer_width, resolved.framebuffer_height) == (800, 600)
