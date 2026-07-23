import numpy as np
import pytest

import vispy2 as vp
from gsp.protocol import CoordinateSpace, SphereVisual


def test_axes3d_spheres_emits_attached_data_visual() -> None:
    figure, axes = vp.subplots(projection="3d")
    visual = axes.spheres(
        [0.0, 1.0],
        [0.0, -1.0],
        [0.5, 1.5],
        radius=[0.25, 0.75],
        color=[[255, 0, 0, 255], [0, 0, 255, 255]],
        id="sphere:producer",
    )
    assert isinstance(visual, SphereVisual)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.radius_values().tolist() == [0.25, 0.75]
    scene = figure.to_scene()
    assert scene.visuals == (visual,)
    assert scene.attachments[0].visual_id == visual.id


def test_axes3d_sphere_fit_includes_radius_bounds() -> None:
    _, axes = vp.subplots(projection="3d")
    axes.spheres(
        [-4.0, 2.0],
        [1.0, 1.0],
        [0.0, 0.0],
        radius=[1.0, 3.0],
        color=[255, 255, 255, 255],
    )
    fitted = axes.fit_camera()
    assert fitted.camera.target == pytest.approx((0.0, 1.0, 0.0))
    assert np.linalg.norm(np.asarray(fitted.camera.eye) - np.asarray(fitted.camera.target)) > 5.0


def test_axes3d_spheres_broadcasts_scalar_radius_and_uniform_color() -> None:
    _, axes = vp.subplots(projection="3d")
    visual = axes.spheres(
        [0.0, 1.0],
        [0.0, 1.0],
        [0.0, 1.0],
        radius=0.5,
        color=[10, 20, 30, 255],
    )
    assert visual.radius_values().tolist() == [0.5, 0.5]
    assert visual.colors.tolist() == [[10, 20, 30, 255], [10, 20, 30, 255]]


def test_axes3d_spheres_rejects_invalid_shapes_and_radius() -> None:
    _, axes = vp.subplots(projection="3d")
    with pytest.raises(ValueError, match="same length"):
        axes.spheres([0.0], [0.0, 1.0], [0.0], radius=1.0, color=[255, 0, 0, 255])
    with pytest.raises(ValueError, match="positive"):
        axes.spheres([0.0], [0.0], [0.0], radius=0.0, color=[255, 0, 0, 255])
    with pytest.raises(ValueError, match="radius must be scalar or shape"):
        axes.spheres(
            [0.0, 1.0],
            [0.0, 1.0],
            [0.0, 1.0],
            radius=[1.0],
            color=[255, 0, 0, 255],
        )
