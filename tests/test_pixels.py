import numpy as np
import pytest

import vispy2 as vp
from gsp.protocol import CoordinateSpace, PixelVisual


def test_axes_pixels_emits_attached_2d_pixel_visual() -> None:
    figure, axes = vp.subplots()
    visual = axes.pixels(
        [0.0, 1.0],
        [1.0, 0.0],
        color=[[255, 0, 0, 255], [0, 255, 0, 255]],
        size=[3.0, 7.0],
        id="pixel:2d",
    )
    assert isinstance(visual, PixelVisual)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.pixel_size_values().tolist() == [3.0, 7.0]
    assert figure.to_scene().visuals == (visual,)
    assert figure.to_scene().attachments[0].visual_id == visual.id


def test_axes3d_pixels_accepts_xyz_and_position_array() -> None:
    figure, axes = vp.subplots(projection="3d")
    xyz = axes.pixels(
        [0.0, 1.0],
        [0.0, 1.0],
        [0.0, -1.0],
        color=[255, 255, 255, 255],
        size=5.0,
    )
    array = axes.pixels(
        np.array([[0.0, 0.0, 0.0]], dtype=np.float32),
        color=[255, 0, 255, 255],
    )
    assert xyz.positions.shape == (2, 3)
    assert array.positions.shape == (1, 3)
    assert figure.to_scene().view3d is axes.view
    axes.fit_camera()


def test_module_pixels_and_invalid_axes_shapes() -> None:
    visual = vp.pixels([0.0], [0.0], size=2.0)
    assert isinstance(visual, PixelVisual)
    _, axes = vp.subplots()
    with pytest.raises(ValueError, match=r"shape \(N, 2\)"):
        axes.pixels([[0.0, 0.0, 0.0]])
    _, axes3d = vp.subplots(projection="3d")
    with pytest.raises(ValueError, match="both y and z"):
        axes3d.pixels([0.0], [0.0])
