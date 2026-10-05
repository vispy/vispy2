"""Array conversion and protocol value helpers."""

from __future__ import annotations

from itertools import count
from typing import Any, SupportsFloat, cast

import numpy as np
import numpy.typing as npt
from gsp.protocol import (
    AxisDimension,
    ColorbarGuideStyle,
    ColorbarOrientation,
    ColorbarPlacement,
    ColorMapId,
    CoordinateSpace,
    FontRole,
    ImageColormap,
    ImageInterpolation,
    ImageOrigin,
    MarkerShape,
    MeshColorMode,
    MeshNormalGeneration,
    MeshNormalMode,
    MeshShading,
    PrimitiveTopology,
    StrokeCap,
    StrokeJoin,
    TextAnchorX,
    TextAnchorY,
    TextureFilter,
    TickSpec,
    TickSpecKind,
    VectorAnchor,
    VectorCap,
    VisualTransformBinding,
)

_visual_counter = count(1)
_scale_counter = count(1)
_texture_counter = count(1)


def affine2d(matrix: npt.ArrayLike) -> VisualTransformBinding:
    """Create an inline S027 affine 2D visual transform binding."""
    return VisualTransformBinding.inline_affine(_affine_matrix(matrix))


def _float3(value: npt.ArrayLike, *, field_name: str) -> tuple[float, float, float]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3,):
        raise ValueError(f"{field_name} must contain exactly three values")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} values must be finite")
    return (float(array[0]), float(array[1]), float(array[2]))


def _protocol_float3(value: npt.ArrayLike) -> tuple[float, float, float]:
    """Resolve an exact float3 while leaving semantic validation to GSP."""
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3,):
        raise ValueError("direction_to_light must contain exactly three values")
    return (float(array[0]), float(array[1]), float(array[2]))


def _visual_transform(
    transform: npt.ArrayLike | VisualTransformBinding | None,
) -> VisualTransformBinding | None:
    if transform is None:
        return None
    if isinstance(transform, VisualTransformBinding):
        return transform
    return affine2d(transform)


def _affine_matrix(matrix: npt.ArrayLike) -> npt.NDArray[np.float64]:
    array = np.asarray(matrix, dtype=np.float64)
    if array.shape != (3, 3):
        raise ValueError("affine2d matrix must have shape (3, 3)")
    return np.ascontiguousarray(array)


def _visual_id(prefix: str) -> str:
    return f"visual:{prefix}-{next(_visual_counter)}"


def _scale_id(prefix: str) -> str:
    return f"scale:{prefix}-{next(_scale_counter)}"


def _texture_id(prefix: str) -> str:
    return f"texture:{prefix}-{next(_texture_counter)}"


def _coordinate_space(value: str | CoordinateSpace) -> CoordinateSpace:
    if isinstance(value, CoordinateSpace):
        return value
    return CoordinateSpace(value)


def _colormap_id(value: str | ColorMapId) -> ColorMapId:
    if isinstance(value, ColorMapId):
        return value
    return ColorMapId(value)


def _is_s026_colormap(
    value: str | ImageColormap | ColorMapId | None,
) -> bool:
    if value is None or isinstance(value, ImageColormap):
        return False
    try:
        _colormap_id(value)
    except ValueError:
        return False
    return True


def _scalar_values(value: npt.ArrayLike, *, shape: tuple[int, ...]) -> npt.NDArray[np.float32]:
    array = np.asarray(value, dtype=np.float32)
    if array.shape != shape:
        raise ValueError(f"scalar color values must have shape {shape}")
    return np.ascontiguousarray(array)


def _colorbar_orientation(value: str | ColorbarOrientation) -> ColorbarOrientation:
    if isinstance(value, ColorbarOrientation):
        return value
    return ColorbarOrientation(value)


def _colorbar_placement(
    value: str | ColorbarPlacement | None,
) -> ColorbarPlacement | None:
    if value is None or isinstance(value, ColorbarPlacement):
        return value
    return ColorbarPlacement(value)


def _colorbar_style(
    style: ColorbarGuideStyle | None,
    *,
    ramp_width_px: float | None,
    tick_length_px: float | None,
    label_gap_px: float | None,
    min_length_px: float | None,
    length_fraction: float | None,
) -> ColorbarGuideStyle:
    base = style or ColorbarGuideStyle()
    return ColorbarGuideStyle(
        ramp_width_px=base.ramp_width_px if ramp_width_px is None else ramp_width_px,
        tick_length_px=base.tick_length_px if tick_length_px is None else tick_length_px,
        label_gap_px=base.label_gap_px if label_gap_px is None else label_gap_px,
        min_length_px=base.min_length_px if min_length_px is None else min_length_px,
        length_fraction=base.length_fraction if length_fraction is None else length_fraction,
    )


def _positions(x: npt.ArrayLike, y: npt.ArrayLike | None) -> npt.NDArray[np.float32]:
    x_array = np.asarray(x, dtype=np.float32)
    if y is None:
        if x_array.ndim != 2 or x_array.shape[1] not in (2, 3):
            raise ValueError("scatter requires x/y arrays or an array with shape (N, 2) or (N, 3)")
        return np.ascontiguousarray(x_array)
    y_array = np.asarray(y, dtype=np.float32)
    if x_array.ndim != 1 or y_array.ndim != 1 or x_array.shape[0] != y_array.shape[0]:
        raise ValueError("x and y must be one-dimensional arrays with the same length")
    return np.ascontiguousarray(np.column_stack([x_array, y_array]).astype(np.float32))


def _primitive_positions(positions: npt.ArrayLike, *, dimensions: int) -> npt.NDArray[np.float32]:
    vertices = np.asarray(positions)
    if vertices.ndim != 2 or vertices.shape[1] != dimensions:
        raise ValueError(f"primitive positions must have shape (N, {dimensions})")
    if not (
        np.issubdtype(vertices.dtype, np.integer) or np.issubdtype(vertices.dtype, np.floating)
    ):
        raise TypeError("primitive positions must use a real integer or floating dtype")
    if not np.all(np.isfinite(vertices)):
        raise ValueError("primitive positions must be finite")
    float32_limit = np.finfo(np.float32).max
    if np.any(vertices > float32_limit) or np.any(vertices < -float32_limit):
        raise ValueError("primitive positions must be representable as float32")
    return np.ascontiguousarray(vertices, dtype=np.float32)


def _primitive_indices(indices: npt.ArrayLike | None) -> npt.NDArray[Any] | None:
    if indices is None:
        return None
    values = np.asarray(indices)
    if values.ndim != 1:
        raise ValueError("primitivevisual_invalid_indices_shape: indices must be flat")
    return np.ascontiguousarray(values)


def _primitive_topology(value: str | PrimitiveTopology) -> PrimitiveTopology:
    if isinstance(value, PrimitiveTopology):
        return value
    try:
        return PrimitiveTopology(value)
    except ValueError as exc:
        raise ValueError(f"unsupported primitive topology: {value!r}") from exc


def _positions3d(
    x: npt.ArrayLike,
    y: npt.ArrayLike | None,
    z: npt.ArrayLike | None,
) -> npt.NDArray[np.float32]:
    if y is None and z is None:
        positions = _positions(x, None)
        if positions.shape[1] != 3:
            raise ValueError("Axes3D.pixels() requires x/y/z arrays or an array with shape (N, 3)")
        return positions
    if y is None or z is None:
        raise ValueError("Axes3D.pixels() requires both y and z")
    arrays = tuple(np.asarray(value, dtype=np.float32) for value in (x, y, z))
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("x, y, and z must be one-dimensional")
    if len({array.shape[0] for array in arrays}) != 1:
        raise ValueError("x, y, and z must have the same length")
    return np.ascontiguousarray(np.column_stack(arrays).astype(np.float32))


def _vector_components(
    values: tuple[npt.ArrayLike, ...], *, dimensions: int
) -> npt.NDArray[np.float32]:
    if len(values) != dimensions:
        raise ValueError(f"vectors require exactly {dimensions} components")
    arrays = tuple(np.asarray(value, dtype=np.float32) for value in values)
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("vector components must be one-dimensional")
    if len({array.shape[0] for array in arrays}) != 1:
        raise ValueError("vector components must have the same length")
    return np.ascontiguousarray(np.column_stack(arrays).astype(np.float32))


def _faces(value: npt.ArrayLike) -> npt.NDArray[np.uint32]:
    array = np.asarray(value)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError("faces must have shape (M, 3)")
    if not np.issubdtype(array.dtype, np.integer):
        raise ValueError("faces must use an integer dtype")
    return np.ascontiguousarray(array.astype(np.uint32, copy=False))


def _colors(
    value: npt.ArrayLike | None, count_: int
) -> npt.NDArray[np.uint8] | npt.NDArray[np.float32]:
    if value is None:
        return np.tile(np.array([[31, 119, 180, 255]], dtype=np.uint8), (count_, 1))
    array = np.asarray(value)
    if array.ndim == 1 and array.shape[0] == 4:
        array = np.tile(array.reshape(1, 4), (count_, 1))
    if array.ndim != 2 or array.shape != (count_, 4):
        raise ValueError("color must be RGBA with shape (4,) or (N, 4)")
    if array.dtype == np.dtype(np.uint8):
        return np.ascontiguousarray(array)
    if np.issubdtype(array.dtype, np.integer):
        return np.ascontiguousarray(array.astype(np.uint8))
    return np.ascontiguousarray(array.astype(np.float32))


def _mesh_color_mode(value: str | MeshColorMode | None) -> MeshColorMode | None:
    if value is None or isinstance(value, MeshColorMode):
        return value
    return MeshColorMode(value)


def _mesh_normal_mode(value: str | MeshNormalMode | None) -> MeshNormalMode | None:
    if value is None or isinstance(value, MeshNormalMode):
        return value
    return MeshNormalMode(value)


def _mesh_normal_generation(
    value: str | MeshNormalGeneration,
) -> MeshNormalGeneration:
    if isinstance(value, MeshNormalGeneration):
        return value
    return MeshNormalGeneration(value)


def _mesh_shading(value: str | MeshShading) -> MeshShading:
    if isinstance(value, MeshShading):
        return value
    return MeshShading(value)


def _texture_filter(value: str | TextureFilter) -> TextureFilter:
    if isinstance(value, TextureFilter):
        return value
    return TextureFilter(value)


def _mesh_normals(value: npt.ArrayLike | None) -> npt.NDArray[np.float32] | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError("mesh normals must have shape (F, 3) or (N, 3)")
    return np.ascontiguousarray(array)


def _mesh_uvs(value: npt.ArrayLike | None, vertex_count: int) -> npt.NDArray[np.float32]:
    if value is None:
        raise ValueError("texture and uvs must be supplied together")
    array = np.asarray(value, dtype=np.float32)
    if array.shape != (vertex_count, 2):
        raise ValueError(f"meshvisual_uv_shape_mismatch: uvs must have shape ({vertex_count}, 2)")
    if not np.all(np.isfinite(array)):
        raise ValueError("meshvisual_uv_nonfinite: uvs must be finite")
    return np.ascontiguousarray(array)


def _mesh_color(
    value: npt.ArrayLike,
) -> npt.NDArray[np.uint8] | npt.NDArray[np.float32]:
    array = np.asarray(value)
    if array.ndim == 1:
        if array.shape[0] != 4:
            raise ValueError("mesh color must be RGBA with shape (4,), (M, 4), or (N, 4)")
    elif array.ndim == 2:
        if array.shape[1] != 4:
            raise ValueError("mesh color must be RGBA with shape (4,), (M, 4), or (N, 4)")
    else:
        raise ValueError("mesh color must be RGBA with shape (4,), (M, 4), or (N, 4)")
    if array.dtype == np.dtype(np.uint8):
        return np.ascontiguousarray(array)
    if np.issubdtype(array.dtype, np.integer):
        return np.ascontiguousarray(array.astype(np.uint8))
    return np.ascontiguousarray(array.astype(np.float32))


def _sizes(value: npt.ArrayLike | float, count_: int) -> npt.NDArray[np.float32] | float:
    if np.isscalar(value):
        return float(cast(SupportsFloat, value))
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 1 or array.shape[0] != count_:
        raise ValueError("size must be scalar or shape (N,)")
    return np.ascontiguousarray(array).astype(np.float32, copy=False)


def _radii(value: npt.ArrayLike | float, count_: int) -> npt.NDArray[np.float32] | float:
    if np.isscalar(value):
        return float(cast(SupportsFloat, value))
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 1 or array.shape[0] != count_:
        raise ValueError("radius must be scalar or shape (N,)")
    return np.ascontiguousarray(array).astype(np.float32, copy=False)


def _angles(value: npt.ArrayLike | float, count_: int) -> npt.NDArray[np.float32] | float:
    if np.isscalar(value):
        return float(cast(SupportsFloat, value))
    array = np.asarray(value, dtype=np.float32)
    if array.ndim != 1 or array.shape[0] != count_:
        raise ValueError("angle must be scalar or shape (N,)")
    return np.ascontiguousarray(array).astype(np.float32, copy=False)


def _text_values(texts: str | tuple[str, ...] | list[str], count_: int) -> tuple[str, ...]:
    if isinstance(texts, str):
        if count_ != 1:
            raise ValueError("single text string requires exactly one position")
        return (texts,)
    values = tuple(texts)
    if len(values) != count_:
        raise ValueError("texts length must match positions")
    return values


def _text_rgba(
    value: npt.ArrayLike | None, count_: int
) -> npt.NDArray[np.uint8] | npt.NDArray[np.float32]:
    if value is None:
        return np.array([0, 0, 0, 255], dtype=np.uint8)
    return _colors(value, count_)


def _positive_values(
    value: npt.ArrayLike | float, count_: int, *, field_name: str
) -> npt.NDArray[np.float32] | float:
    values = _sizes(value, count_)
    if isinstance(values, np.ndarray):
        if np.any(values <= 0):
            raise ValueError(f"{field_name} must be positive")
        return values
    if values <= 0:
        raise ValueError(f"{field_name} must be positive")
    return values


def _font_role(value: str | FontRole) -> FontRole:
    if isinstance(value, FontRole):
        return value
    return FontRole(value)


def _text_anchor_x(
    value: str | TextAnchorX | tuple[str | TextAnchorX, ...] | list[str | TextAnchorX],
    count_: int,
) -> TextAnchorX | tuple[TextAnchorX, ...]:
    if isinstance(value, (str, TextAnchorX)):
        return _text_anchor_x_value(value)
    anchors = tuple(_text_anchor_x_value(item) for item in value)
    if len(anchors) != count_:
        raise ValueError("anchor_x must be scalar or shape (N,)")
    return anchors


def _text_anchor_x_value(value: str | TextAnchorX) -> TextAnchorX:
    if isinstance(value, TextAnchorX):
        return value
    return TextAnchorX(value)


def _text_anchor_y(
    value: str | TextAnchorY | tuple[str | TextAnchorY, ...] | list[str | TextAnchorY],
    count_: int,
) -> TextAnchorY | tuple[TextAnchorY, ...]:
    if isinstance(value, (str, TextAnchorY)):
        return _text_anchor_y_value(value)
    anchors = tuple(_text_anchor_y_value(item) for item in value)
    if len(anchors) != count_:
        raise ValueError("anchor_y must be scalar or shape (N,)")
    return anchors


def _text_anchor_y_value(value: str | TextAnchorY) -> TextAnchorY:
    if isinstance(value, TextAnchorY):
        return value
    return TextAnchorY(value)


def _marker_shapes(
    value: str | MarkerShape | tuple[str | MarkerShape, ...] | list[str | MarkerShape],
    count_: int,
) -> MarkerShape | tuple[MarkerShape, ...]:
    if isinstance(value, (str, MarkerShape)):
        return _marker_shape(value)
    shapes = tuple(_marker_shape(item) for item in value)
    if len(shapes) != count_:
        raise ValueError("shape must be scalar or shape (N,)")
    return shapes


def _marker_shape(value: str | MarkerShape) -> MarkerShape:
    if isinstance(value, MarkerShape):
        return value
    return MarkerShape(value)


def _stroke_cap(value: str | StrokeCap) -> StrokeCap:
    if isinstance(value, StrokeCap):
        return value
    return StrokeCap(value)


def _stroke_join(value: str | StrokeJoin) -> StrokeJoin:
    if isinstance(value, StrokeJoin):
        return value
    return StrokeJoin(value)


def _vector_anchor(value: str | VectorAnchor) -> VectorAnchor:
    if isinstance(value, VectorAnchor):
        return value
    return VectorAnchor(value)


def _vector_cap(value: str | VectorCap) -> VectorCap:
    if isinstance(value, VectorCap):
        return value
    return VectorCap(value)


def _path_lengths(
    value: tuple[int, ...] | list[int] | npt.ArrayLike | None, count_: int
) -> tuple[int, ...]:
    if value is None:
        return (count_,)
    array = np.asarray(value, dtype=np.int64)
    if array.ndim != 1:
        raise ValueError("path_lengths must be one-dimensional")
    return tuple(int(item) for item in array)


def _stroke_color(
    value: npt.ArrayLike | None,
) -> npt.NDArray[np.uint8] | npt.NDArray[np.float32]:
    colors = _colors(value, 1)
    return np.ascontiguousarray(colors[0])


def _origin(value: str | ImageOrigin) -> ImageOrigin:
    if isinstance(value, ImageOrigin):
        return value
    return ImageOrigin(value)


def _interpolation(value: str | ImageInterpolation) -> ImageInterpolation:
    if isinstance(value, ImageInterpolation):
        return value
    return ImageInterpolation(value)


def _colormap(value: str | ImageColormap | None) -> ImageColormap | None:
    if value is None:
        return None
    if isinstance(value, ImageColormap):
        return value
    return ImageColormap(value)


def _tick_values(values: npt.ArrayLike) -> tuple[float, ...]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError("ticks must be one-dimensional")
    return tuple(float(value) for value in array)


def _explicit_tick_spec(
    values: tuple[float, ...], labels: tuple[str, ...] | list[str] | None
) -> TickSpec:
    if not values:
        return TickSpec(kind=TickSpecKind.NONE, target_count=None)
    return TickSpec(
        kind=TickSpecKind.EXPLICIT,
        explicit_values=values,
        explicit_labels=tuple(labels) if labels is not None else None,
        target_count=None,
    )


def _grid_dimensions(axis: str) -> tuple[AxisDimension, ...]:
    if axis == "both":
        return (AxisDimension.X, AxisDimension.Y)
    if axis == "x":
        return (AxisDimension.X,)
    if axis == "y":
        return (AxisDimension.Y,)
    raise ValueError("axis must be 'both', 'x', or 'y'")
