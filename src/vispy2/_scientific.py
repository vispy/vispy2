"""Bounded scientific conveniences lowered to existing GSP triangle geometry."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
from gsp.protocol import PrimitiveVisual

if TYPE_CHECKING:
    from ._axes2d import Axes


def _finite_vector(value: npt.ArrayLike, *, name: str) -> npt.NDArray[np.float64]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or not array.size or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite non-empty one-dimensional array")
    return array


def _broadcast(value: npt.ArrayLike, count: int, *, name: str) -> npt.NDArray[np.float64]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        array = np.full(count, float(array))
    if array.shape != (count,) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite and scalar or shape ({count},)")
    return array


def _rectangles(
    left: npt.NDArray[np.float64],
    right: npt.NDArray[np.float64],
    bottom: npt.NDArray[np.float64],
    top: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    vertices = np.stack(
        (
            np.column_stack((left, bottom)),
            np.column_stack((right, bottom)),
            np.column_stack((right, top)),
            np.column_stack((left, bottom)),
            np.column_stack((right, top)),
            np.column_stack((left, top)),
        ),
        axis=1,
    )
    return vertices.reshape(-1, 2)


def bar(
    axes: Axes,
    x: npt.ArrayLike,
    height: npt.ArrayLike,
    *,
    width: npt.ArrayLike = 0.8,
    bottom: npt.ArrayLike = 0,
    color: npt.ArrayLike | None = None,
    id: str | None = None,
) -> PrimitiveVisual:
    centers = _finite_vector(x, name="x")
    heights = _broadcast(height, centers.size, name="height")
    widths = _broadcast(width, centers.size, name="width")
    bottoms = _broadcast(bottom, centers.size, name="bottom")
    if np.any(widths <= 0):
        raise ValueError("bar width must be positive")
    colors = color
    if color is not None:
        color_array = np.asarray(color)
        if color_array.shape == (centers.size, 4):
            colors = np.repeat(color_array, 6, axis=0)
    return axes.primitives(
        _rectangles(centers - widths / 2, centers + widths / 2, bottoms, bottoms + heights),
        topology="triangle_list",
        color=colors,
        id=id,
    )


def fill_between(
    axes: Axes,
    x: npt.ArrayLike,
    y1: npt.ArrayLike,
    y2: npt.ArrayLike = 0,
    *,
    color: npt.ArrayLike | None = None,
    id: str | None = None,
) -> PrimitiveVisual:
    xs = _finite_vector(x, name="x")
    if xs.size < 2 or not (np.all(np.diff(xs) > 0) or np.all(np.diff(xs) < 0)):
        raise ValueError("fill_between x must be strictly monotonic with at least two values")
    first = _broadcast(y1, xs.size, name="y1")
    second = _broadcast(y2, xs.size, name="y2")
    difference = first - second
    nonzero = difference[difference != 0]
    if np.any(nonzero > 0) and np.any(nonzero < 0):
        raise ValueError("fill_between curves must not cross")
    # Each interval is a non-intersecting quadrilateral: lower-left, lower-right,
    # upper-right, upper-left, split along the first-to-third diagonal.
    a = np.column_stack((xs[:-1], second[:-1]))
    b = np.column_stack((xs[1:], second[1:]))
    c = np.column_stack((xs[1:], first[1:]))
    d = np.column_stack((xs[:-1], first[:-1]))
    vertices = np.stack((a, b, c, a, c, d), axis=1).reshape(-1, 2)
    triangles = vertices.reshape(-1, 3, 2)
    sides = triangles[:, 1:] - triangles[:, :1]
    areas = sides[:, 0, 0] * sides[:, 1, 1] - sides[:, 0, 1] * sides[:, 1, 0]
    vertices = triangles[areas != 0].reshape(-1, 2)
    if not len(vertices):
        raise ValueError("fill_between requires a non-zero area band")
    return axes.primitives(vertices, topology="triangle_list", color=color, id=id)


def hist(
    axes: Axes,
    x: npt.ArrayLike,
    *,
    bins: int | npt.ArrayLike = 10,
    range: tuple[float, float] | None = None,
    weights: npt.ArrayLike | None = None,
    density: bool = False,
    cumulative: bool = False,
    color: npt.ArrayLike | None = None,
    id: str | None = None,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], PrimitiveVisual]:
    samples = _finite_vector(x, name="hist samples")
    resolved_weights = None if weights is None else _finite_vector(weights, name="weights")
    if resolved_weights is not None and resolved_weights.shape != samples.shape:
        raise ValueError("hist weights must match samples")
    if range is not None and (not np.all(np.isfinite(range)) or range[0] >= range[1]):
        raise ValueError("hist range must be finite and increasing")
    if isinstance(bins, (int, np.integer)):
        if isinstance(bins, (bool, np.bool_)) or bins < 1:
            raise ValueError("hist bins must be a positive integer")
        resolved_bins: int | npt.NDArray[np.float64] = int(bins)
    else:
        resolved_bins = _finite_vector(bins, name="bin edges")
        if resolved_bins.size < 2 or not np.all(np.diff(resolved_bins) > 0):
            raise ValueError("hist bin edges must be strictly increasing")
    counts, edges = np.histogram(samples, bins=resolved_bins, range=range, weights=resolved_weights)
    values = np.asarray(counts, dtype=np.float64)
    edges = np.asarray(edges, dtype=np.float64)
    widths = np.diff(edges)
    if cumulative:
        values = np.cumsum(values)
        if density:
            total = float(values[-1])
            if not np.isfinite(total) or total <= 0:
                raise ValueError("density histogram requires a positive finite total weight")
            values /= total
    elif density:
        total = float(np.sum(values))
        if not np.isfinite(total) or total <= 0:
            raise ValueError("density histogram requires a positive finite total weight")
        values = values / total / widths
    visual = bar(axes, edges[:-1] + widths / 2, values, width=widths, color=color, id=id)
    return values, edges, visual
