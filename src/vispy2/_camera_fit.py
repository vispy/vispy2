"""Backend-neutral camera fitting."""

from __future__ import annotations

import math
from typing import cast

import numpy as np
import numpy.typing as npt
from gsp.protocol import (
    Camera3D,
    CoordinateSpace,
    MeshVisual,
    OrthographicProjection3D,
    PerspectiveProjection3D,
    PixelVisual,
    PrimitiveVisual,
    SphereVisual,
    TextVisual,
    VectorVisual,
    View3D,
)


def _axes3d_data_bounds(
    visuals: list[
        MeshVisual | PixelVisual | SphereVisual | VectorVisual | PrimitiveVisual | TextVisual
    ],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    minima: list[npt.NDArray[np.float64]] = []
    maxima: list[npt.NDArray[np.float64]] = []
    for visual in visuals:
        if visual.coordinate_space is not CoordinateSpace.DATA or visual.positions.shape[1] != 3:
            continue
        positions = np.asarray(visual.positions, dtype=np.float64)
        if isinstance(visual, SphereVisual):
            radii = np.asarray(visual.radius_values(), dtype=np.float64)[:, None]
            minima.append(positions - radii)
            maxima.append(positions + radii)
        elif isinstance(visual, VectorVisual):
            tails, heads = visual.endpoint_values()
            minima.extend((tails, heads))
            maxima.extend((tails, heads))
        else:
            minima.append(positions)
            maxima.append(positions)
    if not minima:
        raise ValueError("fit_camera() requires at least one DATA-space 3D visual")
    minimum_points = np.concatenate(minima, axis=0)
    maximum_points = np.concatenate(maxima, axis=0)
    if (
        minimum_points.size == 0
        or not np.all(np.isfinite(minimum_points))
        or not np.all(np.isfinite(maximum_points))
    ):
        raise ValueError("fit_camera() requires finite non-empty DATA-space bounds")
    return np.min(minimum_points, axis=0), np.max(maximum_points, axis=0)


def _fit_epsilon(
    bounds: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
) -> float:
    minimum, maximum = bounds
    scale = max(float(np.max(np.abs(minimum))), float(np.max(np.abs(maximum))), 1.0)
    return scale * 1.0e-6


def _expanded_bounds_corners(
    bounds: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
) -> tuple[
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
]:
    minimum, maximum = bounds
    center = (minimum + maximum) * 0.5
    epsilon = _fit_epsilon(bounds)
    half_extent = np.maximum((maximum - minimum) * 0.5, epsilon * 0.5)
    corners = np.asarray(
        [
            center + half_extent * np.asarray((x, y, z), dtype=np.float64)
            for x in (-1.0, 1.0)
            for y in (-1.0, 1.0)
            for z in (-1.0, 1.0)
        ],
        dtype=np.float64,
    )
    return center, half_extent, corners


def _fit_perspective_camera(
    view: View3D,
    bounds: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
    *,
    margin: float,
) -> tuple[Camera3D, PerspectiveProjection3D]:
    projection = view.projection
    if not isinstance(projection, PerspectiveProjection3D):
        raise TypeError("perspective camera fit requires PerspectiveProjection3D")
    center, half_extent, _ = _expanded_bounds_corners(bounds)
    fitted_radius = float(np.linalg.norm(half_extent)) * margin
    vertical_half_angle = math.radians(projection.fov_y_degrees) * 0.5
    aspect_ratio = 1.0 if projection.aspect_ratio is None else projection.aspect_ratio
    horizontal_half_angle = math.atan(math.tan(vertical_half_angle) * aspect_ratio)
    limiting_half_angle = min(vertical_half_angle, horizontal_half_angle)
    epsilon = _fit_epsilon(bounds)
    distance = fitted_radius / math.sin(limiting_half_angle) + epsilon
    basis = view.camera.basis()
    center3 = _array_float3(center)
    eye = tuple(center3[index] - basis.forward[index] * distance for index in range(3))
    near = max(distance - fitted_radius, epsilon)
    far = max(distance + fitted_radius, near + epsilon)
    return (
        Camera3D(eye=cast(tuple[float, float, float], eye), target=center3, up=view.camera.up),
        PerspectiveProjection3D(
            fov_y_degrees=projection.fov_y_degrees,
            near_far=(near, far),
            aspect_ratio=projection.aspect_ratio,
        ),
    )


def _fit_orthographic_camera(
    view: View3D,
    bounds: tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]],
    *,
    margin: float,
) -> tuple[Camera3D, OrthographicProjection3D]:
    projection = view.projection
    if not isinstance(projection, OrthographicProjection3D):
        raise TypeError("orthographic camera fit requires OrthographicProjection3D")
    center, _, corners = _expanded_bounds_corners(bounds)
    center3 = _array_float3(center)
    basis = view.camera.basis()
    centered_corners = corners - center
    right = np.asarray(basis.right, dtype=np.float64)
    true_up = np.asarray(basis.true_up, dtype=np.float64)
    forward = np.asarray(basis.forward, dtype=np.float64)
    xlim = _expanded_projected_interval(centered_corners @ right, margin=margin)
    ylim = _expanded_projected_interval(centered_corners @ true_up, margin=margin)
    forward_offsets = centered_corners @ forward
    distance = float(
        np.linalg.norm(
            np.asarray(view.camera.eye, dtype=np.float64)
            - np.asarray(view.camera.target, dtype=np.float64)
        )
    )
    near, far = _expanded_projected_interval(
        forward_offsets + distance,
        margin=margin,
    )
    epsilon = _fit_epsilon(bounds)
    if near < epsilon:
        shift = epsilon - near
        distance += shift
        near += shift
        far += shift
    eye = tuple(center3[index] - basis.forward[index] * distance for index in range(3))
    if projection.xlim[1] < projection.xlim[0]:
        xlim = (xlim[1], xlim[0])
    if projection.ylim[1] < projection.ylim[0]:
        ylim = (ylim[1], ylim[0])
    return (
        Camera3D(eye=cast(tuple[float, float, float], eye), target=center3, up=view.camera.up),
        OrthographicProjection3D(
            xlim=xlim,
            ylim=ylim,
            near_far=(near, far),
        ),
    )


def _expanded_projected_interval(
    values: npt.NDArray[np.float64],
    *,
    margin: float,
) -> tuple[float, float]:
    low = float(np.min(values))
    high = float(np.max(values))
    center = (low + high) * 0.5
    half_span = (high - low) * 0.5 * margin
    return center - half_span, center + half_span


def _array_float3(array: npt.NDArray[np.float64]) -> tuple[float, float, float]:
    return (float(array[0]), float(array[1]), float(array[2]))
