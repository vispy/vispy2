from __future__ import annotations

import math
from typing import assert_type

import numpy as np
import pytest

import gsp
from gsp.protocol import (
    Camera3D,
    OrthographicProjection3D,
    PerspectiveProjection3D,
    project_view3d_data_point,
)
import vispy2 as vp


CUBE_POSITIONS = np.asarray(
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
CUBE_FACES = np.asarray(
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


def _cube(axes: vp.Axes3D, *, coordinate_space: str = "data") -> None:
    axes.mesh(
        CUBE_POSITIONS,
        CUBE_FACES,
        color=[70, 130, 220, 255],
        coordinate_space=coordinate_space,
        id=f"visual:cube-{coordinate_space}",
    )


def test_typed_subplots_builds_default_axes3d_scene() -> None:
    figure, axes = vp.subplots(projection="3d")
    assert_type(axes, vp.Axes3D)
    assert isinstance(axes, vp.Axes3D)
    assert axes.get_camera() == Camera3D(
        eye=(3.0, 3.0, 3.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 0.0, 1.0),
    )
    assert axes.get_projection() == PerspectiveProjection3D(
        fov_y_degrees=45.0,
        near_far=(0.1, 1000.0),
    )

    _cube(axes)
    axes.set_title("Static 3D mesh")
    scene = figure.to_scene()

    assert isinstance(scene, gsp.Scene)
    assert scene.view2d is None
    assert scene.view3d is axes.view
    assert scene.visuals == tuple(axes.visuals)
    assert scene.attachments == tuple(axes.attachments)
    assert scene.attachments[0].view_id == axes.view.id
    assert scene.axis_guides == ()
    assert scene.panel_text_guides[0].text == "Static 3D mesh"


def test_camera_projection_and_navigation_each_increment_revision() -> None:
    _, axes = vp.subplots(projection="3d")
    revisions = [axes.view.revision]

    axes.set_camera(eye=(4, 4, 4), target=(0, 0, 0), up=(0, 0, 1))
    revisions.append(axes.view.revision)
    axes.set_perspective(fov_y_degrees=50, near=0.2, far=200, aspect_ratio=1.5)
    revisions.append(axes.view.revision)
    axes.orbit(yaw_radians=0.2, pitch_radians=-0.1)
    revisions.append(axes.view.revision)
    axes.pan(right=0.5, up=-0.25)
    revisions.append(axes.view.revision)
    axes.zoom(1.25)
    revisions.append(axes.view.revision)
    axes.set_orthographic(xlim=(-2, 2), ylim=(-3, 3), near=0, far=100)
    revisions.append(axes.view.revision)
    axes.zoom(2.0, anchor_ndc=(0.25, -0.5))
    revisions.append(axes.view.revision)

    assert revisions == list(range(len(revisions)))
    reset = axes.reset_camera()
    assert reset.revision == revisions[-1] + 1
    assert reset.camera.eye == (3.0, 3.0, 3.0)
    assert reset.projection == PerspectiveProjection3D(
        fov_y_degrees=45.0,
        near_far=(0.1, 1000.0),
    )


def test_perspective_fit_uses_bounding_sphere_and_limiting_fov() -> None:
    _, axes = vp.subplots(projection="3d")
    _cube(axes)
    before_forward = np.asarray(axes.get_camera().basis().forward)

    fitted = axes.fit_camera(margin=1.1)

    radius = math.sqrt(3.0) * 1.1
    expected_distance = radius / math.sin(math.radians(22.5)) + 1.0e-6
    distance = np.linalg.norm(np.asarray(fitted.camera.eye) - np.asarray(fitted.camera.target))
    assert distance == pytest.approx(expected_distance)
    np.testing.assert_allclose(fitted.camera.target, (0.0, 0.0, 0.0))
    np.testing.assert_allclose(fitted.camera.basis().forward, before_forward)
    assert fitted.projection.near_far == pytest.approx(
        (expected_distance - radius, expected_distance + radius)
    )
    assert fitted.revision == 1

    axes.set_perspective(aspect_ratio=0.5)
    narrow_fit = axes.fit_camera()
    assert (
        np.linalg.norm(np.asarray(narrow_fit.camera.eye) - np.asarray(narrow_fit.camera.target))
        > distance
    )


def test_perspective_fit_contains_every_bounds_corner() -> None:
    _, axes = vp.subplots(projection="3d")
    axes.set_perspective(aspect_ratio=0.5)
    _cube(axes)

    fitted = axes.fit_camera()
    projected = np.empty((len(CUBE_POSITIONS), 3), dtype=np.float64)
    for index, point in enumerate(CUBE_POSITIONS):
        projected[index] = project_view3d_data_point(
            fitted,
            (float(point[0]), float(point[1]), float(point[2])),
        )

    assert np.all(np.abs(projected) <= 1.0 + 1.0e-12)


def test_orthographic_fit_preserves_reversed_limits_and_fits_depth() -> None:
    _, axes = vp.subplots(projection="3d")
    axes.set_camera(eye=(0, 0, 10), target=(0, 0, 0), up=(0, 1, 0))
    axes.set_orthographic(xlim=(1, -1), ylim=(2, -2), near=0, far=100)
    axes.mesh(
        [
            [-2, 0, -1],
            [4, 0, -1],
            [4, 2, -1],
            [-2, 2, -1],
            [-2, 0, 3],
            [4, 0, 3],
            [4, 2, 3],
            [-2, 2, 3],
        ],
        CUBE_FACES,
        color=[255, 255, 255, 255],
    )

    fitted = axes.fit_camera()

    assert fitted.camera.target == pytest.approx((1.0, 1.0, 1.0))
    assert isinstance(fitted.projection, OrthographicProjection3D)
    assert fitted.projection.xlim == pytest.approx((3.3, -3.3))
    assert fitted.projection.ylim == pytest.approx((1.1, -1.1))
    assert fitted.projection.near_far == pytest.approx((7.8, 12.2))


def test_orthographic_fit_contains_every_bounds_corner() -> None:
    _, axes = vp.subplots(projection="3d")
    axes.set_camera(eye=(3, 4, 5), target=(0, 0, 0), up=(0, 0, 1))
    axes.set_orthographic(xlim=(1, -1), ylim=(1, -1))
    _cube(axes)

    fitted = axes.fit_camera()
    projected = np.empty((len(CUBE_POSITIONS), 3), dtype=np.float64)
    for index, point in enumerate(CUBE_POSITIONS):
        projected[index] = project_view3d_data_point(
            fitted,
            (float(point[0]), float(point[1]), float(point[2])),
        )

    assert np.all(np.abs(projected) <= 1.0 + 1.0e-12)


def test_fit_handles_planar_degenerate_bounds_deterministically() -> None:
    _, axes = vp.subplots(projection="3d")
    axes.set_camera(eye=(0, 0, 5), target=(0, 0, 0), up=(0, 1, 0))
    axes.set_orthographic()
    axes.mesh(
        [[-1, -1, 2], [1, -1, 2], [1, 1, 2], [-1, 1, 2]],
        [[0, 1, 2], [0, 2, 3]],
        color=[255, 255, 255, 255],
    )

    first = axes.fit_camera()
    first_projection = first.projection
    second = axes.fit_camera()

    assert isinstance(first_projection, OrthographicProjection3D)
    assert first_projection.near_far[1] > first_projection.near_far[0] >= 0
    assert second.camera == first.camera
    assert second.projection == first.projection
    assert second.revision == first.revision + 1


@pytest.mark.parametrize("margin", [0.0, 0.999, float("nan"), float("inf")])
def test_fit_rejects_invalid_margin(margin: float) -> None:
    _, axes = vp.subplots(projection="3d")
    _cube(axes)
    with pytest.raises(ValueError, match="margin"):
        axes.fit_camera(margin=margin)


def test_axes3d_reports_explicit_invalid_inputs() -> None:
    _, axes = vp.subplots(projection="3d")
    with pytest.raises(ValueError, match="DATA-space 3D visual"):
        axes.fit_camera()
    with pytest.raises(ValueError, match=r"shape \(N, 3\)"):
        axes.mesh(
            [[0, 0], [1, 0], [0, 1]],
            [[0, 1, 2]],
            color=[255, 255, 255, 255],
        )
    with pytest.raises(ValueError, match="transforms are not supported"):
        axes.mesh(
            CUBE_POSITIONS,
            CUBE_FACES,
            color=[255, 255, 255, 255],
            transform=np.eye(3),
        )
    with pytest.raises(ValueError, match="finite"):
        axes.set_camera(
            eye=(float("nan"), 0, 1),
            target=(0, 0, 0),
            up=(0, 1, 0),
        )
    _cube(axes, coordinate_space="ndc")
    with pytest.raises(ValueError, match="DATA-space 3D visual"):
        axes.fit_camera()


def test_figure_rejects_missing_multiple_or_invalid_projection_views() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        vp.Figure().to_scene()
    figure = vp.Figure()
    figure.add_axes()
    figure.add_axes(projection="3d")
    with pytest.raises(ValueError, match="exactly one"):
        figure.to_scene()
    with pytest.raises(ValueError, match="projection"):
        vp.subplots(projection="polar")  # type: ignore[call-overload]
