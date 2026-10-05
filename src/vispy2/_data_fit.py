"""Finite DATA-space bounds for explicit two-dimensional view fitting."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import numpy.typing as npt
from gsp.protocol import (
    CoordinateSpace,
    ImageVisual,
    MarkerVisual,
    MeshVisual,
    PathVisual,
    PixelVisual,
    PointVisual,
    PrimitiveVisual,
    SegmentVisual,
    TextVisual,
    VectorVisual,
)


def _axes2d_data_bounds(
    visuals: Iterable[
        PointVisual
        | PixelVisual
        | VectorVisual
        | PrimitiveVisual
        | MarkerVisual
        | SegmentVisual
        | PathVisual
        | MeshVisual
        | ImageVisual
        | TextVisual
    ],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    points: list[npt.NDArray[np.float64]] = []
    for visual in visuals:
        if visual.coordinate_space is not CoordinateSpace.DATA:
            continue
        if isinstance(visual, ImageVisual):
            left, right, bottom, top = visual.extent
            positions = np.asarray(((left, bottom), (right, top)), dtype=np.float64)
        elif isinstance(visual, SegmentVisual):
            positions = np.concatenate((visual.start_positions, visual.end_positions)).astype(
                np.float64
            )
        elif isinstance(visual, VectorVisual):
            positions = np.concatenate(visual.endpoint_values()).astype(np.float64)
        else:
            positions = np.asarray(visual.positions, dtype=np.float64)
        if positions.shape[1] != 2:
            raise ValueError("fit_data() requires two-dimensional DATA-space geometry")
        transform = getattr(visual, "transform", None)
        if transform is not None:
            if transform.inline is None:
                raise ValueError("fit_data() cannot resolve referenced visual transforms")
            homogeneous = np.column_stack((positions, np.ones(len(positions))))
            positions = (homogeneous @ transform.inline.matrix.T)[:, :2]
        if positions.size:
            points.append(positions)
    if not points:
        raise ValueError("fit_data() requires non-empty DATA-space geometry")
    combined = np.concatenate(points)
    if not np.all(np.isfinite(combined)):
        raise ValueError("fit_data() requires finite DATA-space geometry")
    return np.min(combined, axis=0), np.max(combined, axis=0)


def _fit_interval(low: float, high: float, *, margin: float, reverse: bool) -> tuple[float, float]:
    center = low * 0.5 + high * 0.5
    span = high - low
    if span == 0:
        span = max(abs(center), 1.0) * 1e-6
    half_span = span * 0.5 * margin
    result = (center - half_span, center + half_span)
    return (result[1], result[0]) if reverse else result
