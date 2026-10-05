"""Public compatibility facade and one-shot plotting conveniences."""

from __future__ import annotations

import math as math
from dataclasses import dataclass as dataclass
from dataclasses import field as field
from dataclasses import replace as replace
from itertools import count as count
from pathlib import Path as Path
from typing import Any
from typing import Literal as Literal
from typing import SupportsFloat as SupportsFloat
from typing import cast as cast
from typing import overload as overload

import numpy.typing as npt
from gsp import Scene as Scene
from gsp.backends import BackendSession as BackendSession
from gsp.protocol import AxisDimension as AxisDimension
from gsp.protocol import AxisGuide as AxisGuide
from gsp.protocol import AxisSide as AxisSide
from gsp.protocol import Camera3D as Camera3D
from gsp.protocol import CanvasSize as CanvasSize
from gsp.protocol import ClipScope as ClipScope
from gsp.protocol import (
    ColorbarGuide,
    ColorScale,
    ImageVisual,
    MarkerVisual,
    MeshVisual,
    PathVisual,
    PixelVisual,
    PointVisual,
    PrimitiveTopology,
    PrimitiveVisual,
    SegmentVisual,
    TextVisual,
    VectorVisual,
)
from gsp.protocol import ColorbarGuideStyle as ColorbarGuideStyle
from gsp.protocol import ColorbarOrientation as ColorbarOrientation
from gsp.protocol import ColorbarPlacement as ColorbarPlacement
from gsp.protocol import ColorMapId as ColorMapId
from gsp.protocol import ColorMapRef as ColorMapRef
from gsp.protocol import CoordinateSpace as CoordinateSpace
from gsp.protocol import DirectionalLight3D as DirectionalLight3D
from gsp.protocol import ExplicitPanelLayoutV1 as ExplicitPanelLayoutV1
from gsp.protocol import FontRole as FontRole
from gsp.protocol import ImageColormap as ImageColormap
from gsp.protocol import ImageInterpolation as ImageInterpolation
from gsp.protocol import ImageOrigin as ImageOrigin
from gsp.protocol import LinearNormalize as LinearNormalize
from gsp.protocol import MarkerShape as MarkerShape
from gsp.protocol import MeshColorMode as MeshColorMode
from gsp.protocol import MeshNormalGeneration as MeshNormalGeneration
from gsp.protocol import MeshNormalMode as MeshNormalMode
from gsp.protocol import MeshShading as MeshShading
from gsp.protocol import MeshUVMode as MeshUVMode
from gsp.protocol import NormalizedRenderTargetRect as NormalizedRenderTargetRect
from gsp.protocol import Orbit3DPayload as Orbit3DPayload
from gsp.protocol import OrthographicProjection3D as OrthographicProjection3D
from gsp.protocol import Pan3DPayload as Pan3DPayload
from gsp.protocol import Panel as Panel
from gsp.protocol import PanelPlacement as PanelPlacement
from gsp.protocol import PanelTextGuide as PanelTextGuide
from gsp.protocol import PanelTextRole as PanelTextRole
from gsp.protocol import PerspectiveProjection3D as PerspectiveProjection3D
from gsp.protocol import Projection3D as Projection3D
from gsp.protocol import QueryRequest as QueryRequest
from gsp.protocol import QueryResult as QueryResult
from gsp.protocol import ResolvedLayoutSnapshot as ResolvedLayoutSnapshot
from gsp.protocol import ScalarColorDomain as ScalarColorDomain
from gsp.protocol import ScalarColorEncoding as ScalarColorEncoding
from gsp.protocol import ScalarColorSlot as ScalarColorSlot
from gsp.protocol import SphereVisual as SphereVisual
from gsp.protocol import StrokeCap as StrokeCap
from gsp.protocol import StrokeJoin as StrokeJoin
from gsp.protocol import TextAnchorX as TextAnchorX
from gsp.protocol import TextAnchorY as TextAnchorY
from gsp.protocol import Texture2D as Texture2D
from gsp.protocol import TextureFilter as TextureFilter
from gsp.protocol import TickSpec as TickSpec
from gsp.protocol import TickSpecKind as TickSpecKind
from gsp.protocol import VectorAnchor as VectorAnchor
from gsp.protocol import VectorCap as VectorCap
from gsp.protocol import View2D as View2D
from gsp.protocol import View3D as View3D
from gsp.protocol import VisualAttachment as VisualAttachment
from gsp.protocol import VisualTransformBinding as VisualTransformBinding
from gsp.protocol import Zoom3DPayload as Zoom3DPayload
from gsp.protocol import orbit_view3d as orbit_view3d
from gsp.protocol import pan_view3d as pan_view3d
from gsp.protocol import zoom_view3d as zoom_view3d

from ._axes2d import Axes as Axes
from ._axes3d import Axes3D as Axes3D
from ._camera_fit import _array_float3 as _array_float3
from ._camera_fit import _axes3d_data_bounds as _axes3d_data_bounds
from ._camera_fit import _expanded_bounds_corners as _expanded_bounds_corners
from ._camera_fit import _expanded_projected_interval as _expanded_projected_interval
from ._camera_fit import _fit_epsilon as _fit_epsilon
from ._camera_fit import _fit_orthographic_camera as _fit_orthographic_camera
from ._camera_fit import _fit_perspective_camera as _fit_perspective_camera
from ._figure import Figure as Figure
from ._figure import subplots as subplots
from ._inputs import _affine_matrix as _affine_matrix
from ._inputs import _angles as _angles
from ._inputs import _colorbar_orientation as _colorbar_orientation
from ._inputs import _colorbar_placement as _colorbar_placement
from ._inputs import _colorbar_style as _colorbar_style
from ._inputs import _colormap as _colormap
from ._inputs import _colormap_id as _colormap_id
from ._inputs import _colors as _colors
from ._inputs import _coordinate_space as _coordinate_space
from ._inputs import _explicit_tick_spec as _explicit_tick_spec
from ._inputs import _faces as _faces
from ._inputs import _float3 as _float3
from ._inputs import _font_role as _font_role
from ._inputs import _grid_dimensions as _grid_dimensions
from ._inputs import _interpolation as _interpolation
from ._inputs import _is_s026_colormap as _is_s026_colormap
from ._inputs import _marker_shape as _marker_shape
from ._inputs import _marker_shapes as _marker_shapes
from ._inputs import _mesh_color as _mesh_color
from ._inputs import _mesh_color_mode as _mesh_color_mode
from ._inputs import _mesh_normal_generation as _mesh_normal_generation
from ._inputs import _mesh_normal_mode as _mesh_normal_mode
from ._inputs import _mesh_normals as _mesh_normals
from ._inputs import _mesh_shading as _mesh_shading
from ._inputs import _mesh_uvs as _mesh_uvs
from ._inputs import _origin as _origin
from ._inputs import _path_lengths as _path_lengths
from ._inputs import _positions as _positions
from ._inputs import _positions3d as _positions3d
from ._inputs import _positive_values as _positive_values
from ._inputs import _primitive_indices as _primitive_indices
from ._inputs import _primitive_positions as _primitive_positions
from ._inputs import _primitive_topology as _primitive_topology
from ._inputs import _protocol_float3 as _protocol_float3
from ._inputs import _radii as _radii
from ._inputs import _scalar_values as _scalar_values
from ._inputs import _scale_id as _scale_id
from ._inputs import _sizes as _sizes
from ._inputs import _stroke_cap as _stroke_cap
from ._inputs import _stroke_color as _stroke_color
from ._inputs import _stroke_join as _stroke_join
from ._inputs import _text_anchor_x as _text_anchor_x
from ._inputs import _text_anchor_x_value as _text_anchor_x_value
from ._inputs import _text_anchor_y as _text_anchor_y
from ._inputs import _text_anchor_y_value as _text_anchor_y_value
from ._inputs import _text_rgba as _text_rgba
from ._inputs import _text_values as _text_values
from ._inputs import _texture_filter as _texture_filter
from ._inputs import _texture_id as _texture_id
from ._inputs import _tick_values as _tick_values
from ._inputs import _vector_anchor as _vector_anchor
from ._inputs import _vector_cap as _vector_cap
from ._inputs import _vector_components as _vector_components
from ._inputs import _visual_id as _visual_id
from ._inputs import _visual_transform as _visual_transform
from ._inputs import affine2d as affine2d
from .session import require_session as require_session


def scatter(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> PointVisual:
    """Create a point visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.scatter(x, y, **kwargs)


def pixels(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> PixelVisual:
    """Create a pixel visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.pixels(x, y, **kwargs)


def vectors(
    x: npt.ArrayLike,
    y: npt.ArrayLike,
    u: npt.ArrayLike,
    v: npt.ArrayLike,
    **kwargs: Any,
) -> VectorVisual:
    """Create a 2D vector visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.vectors(x, y, u, v, **kwargs)


def primitives(
    positions: npt.ArrayLike,
    *,
    topology: str | PrimitiveTopology,
    **kwargs: Any,
) -> PrimitiveVisual:
    """Create bounded 2D primitive geometry in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.primitives(positions, topology=topology, **kwargs)


def quiver(
    x: npt.ArrayLike,
    y: npt.ArrayLike,
    u: npt.ArrayLike,
    v: npt.ArrayLike,
    **kwargs: Any,
) -> VectorVisual:
    """Thin alias for :func:`vectors`; no Matplotlib API emulation is provided."""
    return vectors(x, y, u, v, **kwargs)


def markers(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> MarkerVisual:
    """Create a marker visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.markers(x, y, **kwargs)


def segments(start: npt.ArrayLike, end: npt.ArrayLike, **kwargs: Any) -> SegmentVisual:
    """Create a segment visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.segments(start, end, **kwargs)


def path(positions: npt.ArrayLike, **kwargs: Any) -> PathVisual:
    """Create a path visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.path(positions, **kwargs)


def plot(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> PathVisual:
    """Create a path visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.plot(x, y, **kwargs)


def text(
    x: npt.ArrayLike,
    y: npt.ArrayLike | None,
    texts: str | tuple[str, ...] | list[str],
    **kwargs: Any,
) -> TextVisual:
    """Create a text visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.text(x, y, texts, **kwargs)


def mesh(positions: npt.ArrayLike, faces: npt.ArrayLike, **kwargs: Any) -> MeshVisual:
    """Create a mesh visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.mesh(positions, faces, **kwargs)


def imshow(image: npt.ArrayLike, **kwargs: Any) -> ImageVisual:
    """Create an image visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.imshow(image, **kwargs)


def color_scale(**kwargs: Any) -> ColorScale:
    """Create a color scale in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.color_scale(**kwargs)


def colorbar(color_scale: str | ColorScale, **kwargs: Any) -> ColorbarGuide:
    """Create a colorbar guide in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.colorbar(color_scale, **kwargs)
