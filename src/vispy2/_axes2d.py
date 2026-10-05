"""Semantic two-dimensional axes."""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import numpy.typing as npt
from gsp.protocol import (
    AxisDimension,
    AxisGuide,
    AxisSide,
    ClipScope,
    ColorbarGuide,
    ColorbarGuideStyle,
    ColorbarOrientation,
    ColorbarPlacement,
    ColorMapId,
    ColorMapRef,
    ColorScale,
    CoordinateSpace,
    FontRole,
    ImageColormap,
    ImageInterpolation,
    ImageOrigin,
    ImageVisual,
    LinearNormalize,
    MarkerShape,
    MarkerVisual,
    MeshColorMode,
    MeshNormalGeneration,
    MeshNormalMode,
    MeshShading,
    MeshUVMode,
    MeshVisual,
    Panel,
    PanelTextGuide,
    PanelTextRole,
    PathVisual,
    PixelVisual,
    PointVisual,
    PrimitiveTopology,
    PrimitiveVisual,
    ScalarColorDomain,
    ScalarColorEncoding,
    ScalarColorSlot,
    SegmentVisual,
    StrokeCap,
    StrokeJoin,
    TextAnchorX,
    TextAnchorY,
    Texture2D,
    TextureFilter,
    TextVisual,
    TickSpecKind,
    VectorAnchor,
    VectorCap,
    VectorVisual,
    View2D,
    VisualAttachment,
    VisualTransformBinding,
)

from . import _scientific
from ._data_fit import _axes2d_data_bounds, _fit_interval
from ._inputs import (
    _angles,
    _colorbar_orientation,
    _colorbar_placement,
    _colorbar_style,
    _colormap,
    _colormap_id,
    _colors,
    _coordinate_space,
    _explicit_tick_spec,
    _faces,
    _font_role,
    _grid_dimensions,
    _interpolation,
    _is_s026_colormap,
    _marker_shapes,
    _mesh_color,
    _mesh_color_mode,
    _mesh_normal_generation,
    _mesh_normal_mode,
    _mesh_normals,
    _mesh_shading,
    _mesh_uvs,
    _origin,
    _path_lengths,
    _positions,
    _positive_values,
    _primitive_indices,
    _primitive_positions,
    _primitive_topology,
    _scalar_values,
    _scale_id,
    _sizes,
    _stroke_cap,
    _stroke_color,
    _stroke_join,
    _text_anchor_x,
    _text_anchor_y,
    _text_rgba,
    _text_values,
    _texture_filter,
    _texture_id,
    _tick_values,
    _vector_anchor,
    _vector_cap,
    _vector_components,
    _visual_id,
    _visual_transform,
)

if TYPE_CHECKING:
    from ._figure import Figure


@dataclass(slots=True)
class Axes:
    """Axes-like producer that appends GSP visuals, guides, and resources."""

    figure: Figure
    visuals: list[
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
    ] = field(default_factory=list)
    panel: Panel = field(init=False)
    view: View2D = field(init=False)
    attachments: list[VisualAttachment] = field(default_factory=list)
    axis_guides: list[AxisGuide] = field(default_factory=list)
    panel_text_guides: list[PanelTextGuide] = field(default_factory=list)
    colorbar_guides: list[ColorbarGuide] = field(default_factory=list)
    _clip_scope: ClipScope = field(default=ClipScope.PLOT, init=False, repr=False)

    def __post_init__(self) -> None:
        index = len(self.figure.axes) + 1
        panel_id = f"panel:{index}"
        view_id = f"view:{index}"
        self.panel = Panel(id=panel_id)
        self.view = View2D(id=view_id, panel_id=panel_id)
        self.axis_guides.extend(
            [
                AxisGuide(
                    id=f"guide:x-{index}",
                    view_id=view_id,
                    dimension=AxisDimension.X,
                    side=AxisSide.BOTTOM,
                ),
                AxisGuide(
                    id=f"guide:y-{index}",
                    view_id=view_id,
                    dimension=AxisDimension.Y,
                    side=AxisSide.LEFT,
                ),
            ]
        )

    def set_xlim(self, left: float, right: float) -> tuple[float, float]:
        """Set this axes' x limits and propagate programmatically linked x limits."""
        self.set_view2d(xlim=(left, right))
        return self.view.x_range

    def set_ylim(self, bottom: float, top: float) -> tuple[float, float]:
        """Set this axes' y limits and propagate programmatically linked y limits."""
        self.set_view2d(ylim=(bottom, top))
        return self.view.y_range

    def set_view2d(
        self, *, xlim: tuple[float, float] | None = None, ylim: tuple[float, float] | None = None
    ) -> View2D:
        """Set semantic limits, propagating the figure's linked dimensions."""
        return self.figure.set_limits(self, xlim=xlim, ylim=ylim)

    def sharex(self, other: Axes) -> None:
        """Link programmatic x limits, initially adopting the other axes' limits."""
        self.figure.link_axes(other, self, x=True, y=False)

    def sharey(self, other: Axes) -> None:
        """Link programmatic y limits, initially adopting the other axes' limits."""
        self.figure.link_axes(other, self, x=False, y=True)

    def fit_data(self, *, margin: float = 1.1) -> View2D:
        """Fit finite DATA geometry, including inline transforms, with a span multiplier.

        Screen-space marker sizes and strokes do not enlarge the data bounds.
        Preserve reversed axes and expand degenerate ranges by a small finite span.
        """
        resolved_margin = float(margin)
        if not math.isfinite(resolved_margin) or resolved_margin < 1.0:
            raise ValueError("data fit margin must be finite and at least 1")
        minimum, maximum = _axes2d_data_bounds(self.visuals)
        xlim = _fit_interval(
            float(minimum[0]),
            float(maximum[0]),
            margin=resolved_margin,
            reverse=self.view.x_range[1] < self.view.x_range[0],
        )
        ylim = _fit_interval(
            float(minimum[1]),
            float(maximum[1]),
            margin=resolved_margin,
            reverse=self.view.y_range[1] < self.view.y_range[0],
        )
        return self.set_view2d(xlim=xlim, ylim=ylim)

    def autoscale(self, *, margin: float = 1.1) -> View2D:
        """Explicitly fit the current data once; later visuals leave limits unchanged."""
        return self.fit_data(margin=margin)

    def set_clip_scope(self, scope: ClipScope | str) -> ClipScope:
        """Set attachment-owned rectangular clipping for current and future visuals."""
        resolved = ClipScope(scope)
        self.attachments = [
            replace(attachment, clip_scope=resolved) for attachment in self.attachments
        ]
        self._clip_scope = resolved
        return resolved

    def _attach(self, visual_id: str) -> None:
        visual = next(visual for visual in reversed(self.visuals) if visual.id == visual_id)
        self.attachments.append(
            VisualAttachment(
                visual_id=visual_id,
                panel_id=self.panel.id,
                view_id=(self.view.id if visual.coordinate_space is CoordinateSpace.DATA else None),
                clip_scope=self._clip_scope,
            )
        )

    def get_xlim(self) -> tuple[float, float]:
        """Return the semantic x range for this 2D view."""
        return self.view.x_range

    def get_ylim(self) -> tuple[float, float]:
        """Return the semantic y range for this 2D view."""
        return self.view.y_range

    def set_xlabel(self, text: str | None) -> str | None:
        """Set the semantic x-axis label."""
        self._set_axis_guide(AxisDimension.X, label_text=text)
        return text

    def get_xlabel(self) -> str | None:
        """Return the semantic x-axis label."""
        return self._axis_guide(AxisDimension.X).label_text

    def set_ylabel(self, text: str | None) -> str | None:
        """Set the semantic y-axis label."""
        self._set_axis_guide(AxisDimension.Y, label_text=text)
        return text

    def get_ylabel(self) -> str | None:
        """Return the semantic y-axis label."""
        return self._axis_guide(AxisDimension.Y).label_text

    def set_title(self, text: str | None) -> str | None:
        """Set or clear the semantic panel title."""
        self.panel_text_guides = [
            guide for guide in self.panel_text_guides if guide.role != PanelTextRole.TITLE
        ]
        if text:
            self.panel_text_guides.append(
                PanelTextGuide(
                    id=f"guide:title-{self._index}",
                    panel_id=self.panel.id,
                    role=PanelTextRole.TITLE,
                    text=text,
                )
            )
        return text

    def get_title(self) -> str | None:
        """Return the semantic panel title, if any."""
        for guide in self.panel_text_guides:
            if guide.role == PanelTextRole.TITLE:
                return guide.text
        return None

    def set_xticks(
        self, ticks: npt.ArrayLike, labels: tuple[str, ...] | list[str] | None = None
    ) -> tuple[float, ...]:
        """Set explicit semantic x-axis tick values and optional labels."""
        values = _tick_values(ticks)
        self._set_axis_guide(AxisDimension.X, tick_spec=_explicit_tick_spec(values, labels))
        return values

    def get_xticks(self) -> tuple[float, ...]:
        """Return explicit semantic x-axis ticks, or an empty tuple for non-explicit ticks."""
        spec = self._axis_guide(AxisDimension.X).tick_spec
        return spec.explicit_values if spec.kind == TickSpecKind.EXPLICIT else ()

    def set_yticks(
        self, ticks: npt.ArrayLike, labels: tuple[str, ...] | list[str] | None = None
    ) -> tuple[float, ...]:
        """Set explicit semantic y-axis tick values and optional labels."""
        values = _tick_values(ticks)
        self._set_axis_guide(AxisDimension.Y, tick_spec=_explicit_tick_spec(values, labels))
        return values

    def get_yticks(self) -> tuple[float, ...]:
        """Return explicit semantic y-axis ticks, or an empty tuple for non-explicit ticks."""
        spec = self._axis_guide(AxisDimension.Y).tick_spec
        return spec.explicit_values if spec.kind == TickSpecKind.EXPLICIT else ()

    def grid(self, visible: bool = True, *, axis: str = "both") -> None:
        """Set semantic grid visibility for x, y, or both axis guides."""
        dimensions = _grid_dimensions(axis)
        for dimension in dimensions:
            self._set_axis_guide(dimension, grid_visible=bool(visible))

    def color_scale(
        self,
        *,
        cmap: str | ColorMapId = ColorMapId.VIRIDIS,
        clim: tuple[float, float],
        id: str | None = None,
        description: str | None = None,
    ) -> ColorScale:
        """Create or register a semantic scalar color scale."""
        colormap_id = _colormap_id(cmap)
        scale = ColorScale(
            id=id or _scale_id(colormap_id.value),
            colormap=ColorMapRef(id=colormap_id),
            normalize=LinearNormalize(vmin=float(clim[0]), vmax=float(clim[1])),
            description=description,
        )
        self._register_color_scale(scale)
        return scale

    def colorbar(
        self,
        color_scale: str | ColorScale,
        *,
        label: str = "",
        orientation: str | ColorbarOrientation = ColorbarOrientation.VERTICAL,
        placement: str | ColorbarPlacement | None = None,
        ticks: npt.ArrayLike | None = None,
        tick_labels: tuple[str, ...] | list[str] | None = None,
        linked_visual_ids: tuple[str, ...] | list[str] = (),
        style: ColorbarGuideStyle | None = None,
        ramp_width_px: float | None = None,
        tick_length_px: float | None = None,
        label_gap_px: float | None = None,
        min_length_px: float | None = None,
        length_fraction: float | None = None,
        id: str | None = None,
    ) -> ColorbarGuide:
        """Create semantic colorbar guide intent for a color scale."""
        with self._color_scale_transaction():
            guide = ColorbarGuide(
                id=id or f"guide:colorbar-{self._index}-{len(self.colorbar_guides) + 1}",
                panel_id=self.panel.id,
                color_scale_id=self._color_scale_id(color_scale),
                linked_visual_ids=tuple(linked_visual_ids),
                orientation=_colorbar_orientation(orientation),
                placement=_colorbar_placement(placement),
                label=label,
                ticks=_tick_values(ticks) if ticks is not None else (),
                tick_labels=tuple(tick_labels) if tick_labels is not None else None,
                style=_colorbar_style(
                    style,
                    ramp_width_px=ramp_width_px,
                    tick_length_px=tick_length_px,
                    label_gap_px=label_gap_px,
                    min_length_px=min_length_px,
                    length_fraction=length_fraction,
                ),
            )
            self.colorbar_guides.append(guide)
            return guide

    def scatter(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        *,
        c: npt.ArrayLike | None = None,
        color: npt.ArrayLike | None = None,
        color_scale: str | ColorScale | None = None,
        cmap: str | ColorMapId | None = None,
        clim: tuple[float, float] | None = None,
        alpha: float = 1.0,
        s: npt.ArrayLike | float = 36.0,
        size: npt.ArrayLike | float | None = None,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> PointVisual:
        """Create a protocol point visual from x/y or an ``(N, 2|3)`` array."""
        with self._color_scale_transaction():
            positions = _positions(x, y)
            color_value = c if c is not None else color
            encoding = self._scalar_encoding(
                color_value,
                positions.shape[0],
                slot=ScalarColorSlot.COLOR,
                domain=ScalarColorDomain.ITEM,
                color_scale=color_scale,
                cmap=cmap,
                clim=clim,
                alpha=alpha,
            )
            colors = None if encoding is not None else _colors(color_value, positions.shape[0])
            sizes = _sizes(size if size is not None else s, positions.shape[0])
            visual = PointVisual(
                id=id or _visual_id("points"),
                positions=positions,
                colors=colors,
                sizes=sizes,
                coordinate_space=CoordinateSpace.DATA,
                color_encoding=encoding,
                transform=_visual_transform(transform),
            )
            self.visuals.append(visual)
            self._attach(visual.id)
            return visual

    def pixels(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        *,
        color: npt.ArrayLike | None = None,
        size: npt.ArrayLike | float = 1.0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> PixelVisual:
        """Create screen-aligned square pixels in this 2D DATA view."""
        positions = _positions(x, y)
        if positions.shape[1] != 2:
            raise ValueError("Axes.pixels() positions must have shape (N, 2)")
        visual = PixelVisual(
            id=id or _visual_id("pixels"),
            positions=positions,
            colors=_colors(color, positions.shape[0]),
            pixel_size_px=_sizes(size, positions.shape[0]),
            coordinate_space=CoordinateSpace.DATA,
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def vectors(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        u: npt.ArrayLike,
        v: npt.ArrayLike,
        *,
        color: npt.ArrayLike | None = None,
        width: npt.ArrayLike | float = 1.0,
        scale: float = 1.0,
        anchor: str | VectorAnchor = VectorAnchor.TAIL,
        start_cap: str | VectorCap = VectorCap.BUTT,
        end_cap: str | VectorCap = VectorCap.TRIANGLE_OUT,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> VectorVisual:
        """Create straight 2D DATA-space vectors from x/y anchors and u/v displacements."""
        positions = _positions(x, y)
        displacements = _vector_components((u, v), dimensions=2)
        if positions.shape != displacements.shape:
            raise ValueError("x/y anchors and u/v vectors must have the same length")
        visual = VectorVisual(
            id=id or _visual_id("vectors"),
            positions=positions,
            vectors=displacements,
            colors=_colors(color, positions.shape[0]),
            widths_px=_sizes(width, positions.shape[0]),
            scale=float(scale),
            anchor=_vector_anchor(anchor),
            start_cap=_vector_cap(start_cap),
            end_cap=_vector_cap(end_cap),
            coordinate_space=CoordinateSpace.DATA,
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def primitives(
        self,
        positions: npt.ArrayLike,
        *,
        topology: str | PrimitiveTopology,
        color: npt.ArrayLike | None = None,
        indices: npt.ArrayLike | None = None,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> PrimitiveVisual:
        """Create bounded point, line, or triangle geometry in this 2D DATA view."""
        vertices = _primitive_positions(positions, dimensions=2)
        visual = PrimitiveVisual(
            id=id or _visual_id("primitives"),
            topology=_primitive_topology(topology),
            positions=vertices,
            colors=_colors(color, vertices.shape[0]),
            indices=_primitive_indices(indices),
            coordinate_space=CoordinateSpace.DATA,
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def bar(
        self,
        x: npt.ArrayLike,
        height: npt.ArrayLike,
        *,
        width: npt.ArrayLike = 0.8,
        bottom: npt.ArrayLike = 0,
        color: npt.ArrayLike | None = None,
        id: str | None = None,
    ) -> PrimitiveVisual:
        """Create centered bars as DATA-space triangles; negative heights are supported."""
        return _scientific.bar(self, x, height, width=width, bottom=bottom, color=color, id=id)

    def hist(
        self,
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
        """Compute a NumPy histogram and emit bars, returning values, edges, and visual.

        Cumulative density returns the normalized cumulative weight at each bin.
        Non-finite inputs and zero-total density histograms are rejected.
        """
        return _scientific.hist(
            self,
            x,
            bins=bins,
            range=range,
            weights=weights,
            density=density,
            cumulative=cumulative,
            color=color,
            id=id,
        )

    def fill_between(
        self,
        x: npt.ArrayLike,
        y1: npt.ArrayLike,
        y2: npt.ArrayLike = 0,
        *,
        color: npt.ArrayLike | None = None,
        id: str | None = None,
    ) -> PrimitiveVisual:
        """Fill finite non-crossing curves on a strictly monotonic x grid with triangles."""
        return _scientific.fill_between(self, x, y1, y2, color=color, id=id)

    def axhline(
        self,
        y: float = 0,
        *,
        color: npt.ArrayLike | None = None,
        width: float = 1,
        id: str | None = None,
    ) -> SegmentVisual:
        """Create a horizontal DATA line spanning the current x limits once."""
        left, right = self.get_xlim()
        return self.segments([[left, y]], [[right, y]], color=color, width=width, id=id)

    def axvline(
        self,
        x: float = 0,
        *,
        color: npt.ArrayLike | None = None,
        width: float = 1,
        id: str | None = None,
    ) -> SegmentVisual:
        """Create a vertical DATA line spanning the current y limits once."""
        bottom, top = self.get_ylim()
        return self.segments([[x, bottom]], [[x, top]], color=color, width=width, id=id)

    def axhspan(
        self, ymin: float, ymax: float, *, color: npt.ArrayLike | None = None, id: str | None = None
    ) -> PrimitiveVisual:
        """Create a horizontal DATA band spanning the current x limits once."""
        return self.fill_between(self.get_xlim(), ymax, ymin, color=color, id=id)

    def axvspan(
        self, xmin: float, xmax: float, *, color: npt.ArrayLike | None = None, id: str | None = None
    ) -> PrimitiveVisual:
        """Create a vertical DATA band spanning the current y limits once."""
        bottom, top = self.get_ylim()
        return self.fill_between([xmin, xmax], top, bottom, color=color, id=id)

    def quiver(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike,
        u: npt.ArrayLike,
        v: npt.ArrayLike,
        **kwargs: Any,
    ) -> VectorVisual:
        """Thin alias for :meth:`vectors`; no Matplotlib quiver surface is emulated."""
        return self.vectors(x, y, u, v, **kwargs)

    def markers(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        *,
        shape: str
        | MarkerShape
        | tuple[str | MarkerShape, ...]
        | list[str | MarkerShape] = MarkerShape.DISC,
        fill_color: npt.ArrayLike | None = None,
        color: npt.ArrayLike | None = None,
        color_scale: str | ColorScale | None = None,
        cmap: str | ColorMapId | None = None,
        clim: tuple[float, float] | None = None,
        alpha: float = 1.0,
        s: npt.ArrayLike | float = 36.0,
        size: npt.ArrayLike | float | None = None,
        angle: npt.ArrayLike | float = 0.0,
        stroke_color: npt.ArrayLike | None = None,
        stroke_width: float = 0.0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> MarkerVisual:
        """Create a protocol marker visual from x/y or an ``(N, 2|3)`` array."""
        with self._color_scale_transaction():
            positions = _positions(x, y)
            color_value = fill_color if fill_color is not None else color
            encoding = self._scalar_encoding(
                color_value,
                positions.shape[0],
                slot=ScalarColorSlot.FILL,
                domain=ScalarColorDomain.ITEM,
                color_scale=color_scale,
                cmap=cmap,
                clim=clim,
                alpha=alpha,
            )
            fill_colors = None if encoding is not None else _colors(color_value, positions.shape[0])
            sizes = _sizes(size if size is not None else s, positions.shape[0])
            visual = MarkerVisual(
                id=id or _visual_id("markers"),
                positions=positions,
                shape=_marker_shapes(shape, positions.shape[0]),
                fill_colors=fill_colors,
                sizes=sizes,
                angle=_angles(angle, positions.shape[0]),
                stroke_color=_stroke_color(stroke_color),
                stroke_width=float(stroke_width),
                coordinate_space=CoordinateSpace.DATA,
                fill_color_encoding=encoding,
                transform=_visual_transform(transform),
            )
            self.visuals.append(visual)
            self._attach(visual.id)
            return visual

    def segments(
        self,
        start: npt.ArrayLike,
        end: npt.ArrayLike,
        *,
        color: npt.ArrayLike | None = None,
        width: npt.ArrayLike | float = 1.0,
        cap: str | StrokeCap = StrokeCap.BUTT,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> SegmentVisual:
        """Create a protocol segment visual from start/end ``(N, 2|3)`` arrays."""
        start_positions = _positions(start, None)
        end_positions = _positions(end, None)
        if end_positions.shape != start_positions.shape:
            raise ValueError("segment start and end positions must have the same shape")
        colors = _colors(color, start_positions.shape[0])
        widths = _sizes(width, start_positions.shape[0])
        visual = SegmentVisual(
            id=id or _visual_id("segments"),
            start_positions=start_positions,
            end_positions=end_positions,
            colors=colors,
            widths=widths,
            cap=_stroke_cap(cap),
            coordinate_space=CoordinateSpace.DATA,
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def path(
        self,
        positions: npt.ArrayLike,
        path_lengths: tuple[int, ...] | list[int] | npt.ArrayLike | None = None,
        *,
        color: npt.ArrayLike | None = None,
        width: npt.ArrayLike | float = 1.0,
        cap: str | StrokeCap = StrokeCap.BUTT,
        join: str | StrokeJoin = StrokeJoin.MITER,
        miter_limit: float = 4.0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> PathVisual:
        """Create a protocol open polyline path from ordered ``(N, 2|3)`` vertices."""
        position_array = _positions(positions, None)
        lengths = _path_lengths(path_lengths, position_array.shape[0])
        colors = _colors(color, len(lengths))
        widths = _sizes(width, len(lengths))
        visual = PathVisual(
            id=id or _visual_id("path"),
            positions=position_array,
            path_lengths=lengths,
            colors=colors,
            widths=widths,
            cap=_stroke_cap(cap),
            join=_stroke_join(join),
            miter_limit=float(miter_limit),
            coordinate_space=CoordinateSpace.DATA,
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def plot(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        **kwargs: Any,
    ) -> PathVisual:
        """Create one open polyline path from x/y or an ``(N, 2|3)`` array."""
        return self.path(_positions(x, y), None, **kwargs)

    def text(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None,
        texts: str | tuple[str, ...] | list[str],
        *,
        color: npt.ArrayLike | None = None,
        font_size_px: npt.ArrayLike | float = 13.0,
        font_role: str | FontRole = FontRole.DEFAULT,
        anchor_x: str
        | TextAnchorX
        | tuple[str | TextAnchorX, ...]
        | list[str | TextAnchorX] = TextAnchorX.LEFT,
        anchor_y: str
        | TextAnchorY
        | tuple[str | TextAnchorY, ...]
        | list[str | TextAnchorY] = TextAnchorY.BASELINE,
        rotation_rad: npt.ArrayLike | float = 0.0,
        z_order: int = 0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        id: str | None = None,
    ) -> TextVisual:
        """Create a protocol TextVisual for explicit labels/annotations."""
        positions = _positions(x, y)
        text_values = _text_values(texts, positions.shape[0])
        visual = TextVisual(
            id=id or _visual_id("text"),
            texts=text_values,
            positions=positions,
            coordinate_space=CoordinateSpace.DATA,
            rgba=_text_rgba(color, positions.shape[0]),
            font_size_px=_positive_values(
                font_size_px, positions.shape[0], field_name="font_size_px"
            ),
            font_role=_font_role(font_role),
            anchor_x=_text_anchor_x(anchor_x, positions.shape[0]),
            anchor_y=_text_anchor_y(anchor_y, positions.shape[0]),
            rotation_rad=_angles(rotation_rad, positions.shape[0]),
            z_order=int(z_order),
            transform=_visual_transform(transform),
        )
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def mesh(
        self,
        positions: npt.ArrayLike,
        faces: npt.ArrayLike,
        *,
        color: npt.ArrayLike,
        color_mode: str | MeshColorMode | None = None,
        coordinate_space: str | CoordinateSpace = CoordinateSpace.DATA,
        shading: str | MeshShading = MeshShading.UNLIT_RGBA,
        normal_mode: str | MeshNormalMode | None = None,
        normals: npt.ArrayLike | None = None,
        normal_generation: str | MeshNormalGeneration = MeshNormalGeneration.NONE,
        order: float = 0.0,
        transform: npt.ArrayLike | VisualTransformBinding | None = None,
        texture: npt.ArrayLike | None = None,
        uvs: npt.ArrayLike | None = None,
        texture_filter: str | TextureFilter = TextureFilter.NEAREST,
        id: str | None = None,
    ) -> MeshVisual:
        """Create a protocol MeshVisual for accepted inline triangle meshes."""
        position_array = _positions(positions, None)
        face_array = _faces(faces)
        texture_resource = self._mesh_texture2d_resource(texture, uvs)
        mesh_shading = _mesh_shading(shading)
        mesh_uvs = None if texture_resource is None else _mesh_uvs(uvs, position_array.shape[0])
        if texture_resource is not None and mesh_shading is not MeshShading.UNLIT_RGBA:
            raise ValueError("texture2d_unlit does not accept explicit mesh shading")
        visual = MeshVisual(
            id=id or _visual_id("mesh"),
            positions=position_array,
            faces=face_array,
            coordinate_space=_coordinate_space(coordinate_space),
            color=_mesh_color(color),
            color_mode=_mesh_color_mode(color_mode),
            shading=(MeshShading.TEXTURE2D_UNLIT if texture_resource is not None else mesh_shading),
            normal_mode=_mesh_normal_mode(normal_mode),
            normals=_mesh_normals(normals),
            normal_generation=_mesh_normal_generation(normal_generation),
            texture2d_id=None if texture_resource is None else texture_resource.id,
            uv_mode=MeshUVMode.NONE if texture_resource is None else MeshUVMode.VERTEX,
            uvs=mesh_uvs,
            order=float(order),
            transform=_visual_transform(transform),
            texture_filter=_texture_filter(texture_filter),
        )
        if texture_resource is not None:
            self.figure.texture2d_resources.append(texture_resource)
        self.visuals.append(visual)
        self._attach(visual.id)
        return visual

    def _mesh_texture2d_resource(
        self, texture: npt.ArrayLike | None, uvs: npt.ArrayLike | None
    ) -> Texture2D | None:
        if texture is None and uvs is None:
            return None
        if texture is None or uvs is None:
            raise ValueError("texture and uvs must be supplied together")
        image = np.asarray(texture)
        if image.dtype != np.dtype(np.uint8):
            raise TypeError("texture2d_invalid_resource: texture must have dtype uint8")
        return Texture2D(id=_texture_id("mesh"), image=image)

    @property
    def _index(self) -> int:
        return int(self.panel.id.rsplit(":", maxsplit=1)[1])

    def _axis_guide(self, dimension: AxisDimension) -> AxisGuide:
        for guide in self.axis_guides:
            if guide.dimension == dimension:
                return guide
        raise LookupError(f"missing {dimension.value} axis guide")

    def _set_axis_guide(self, dimension: AxisDimension, **changes: Any) -> None:
        for index, guide in enumerate(self.axis_guides):
            if guide.dimension == dimension:
                self.axis_guides[index] = replace(guide, **changes)
                return
        raise LookupError(f"missing {dimension.value} axis guide")

    def imshow(
        self,
        image: npt.ArrayLike,
        *,
        extent: tuple[float, float, float, float] | None = None,
        origin: str | ImageOrigin = ImageOrigin.UPPER,
        interpolation: str | ImageInterpolation = ImageInterpolation.NEAREST,
        colormap: str | ImageColormap | ColorMapId | None = None,
        cmap: str | ColorMapId | None = None,
        clim: tuple[float, float] | None = None,
        color_scale: str | ColorScale | None = None,
        id: str | None = None,
    ) -> ImageVisual:
        """Create a protocol image visual."""
        with self._color_scale_transaction():
            image_array = np.asarray(image)
            if image_array.dtype == np.dtype(np.float64):
                image_array = image_array.astype(np.float32)
            if extent is None:
                height, width = image_array.shape[:2]
                if _origin(origin) == ImageOrigin.UPPER:
                    extent = (-0.5, width - 0.5, height - 0.5, -0.5)
                else:
                    extent = (-0.5, width - 0.5, -0.5, height - 0.5)
            color_scale_id = self._image_color_scale_id(
                image_array,
                colormap=colormap,
                cmap=cmap,
                clim=clim,
                color_scale=color_scale,
            )
            visual = ImageVisual(
                id=id or _visual_id("image"),
                image=image_array,
                extent=extent,
                coordinate_space=CoordinateSpace.DATA,
                origin=_origin(origin),
                interpolation=_interpolation(interpolation),
                colormap=None if color_scale_id is not None else _colormap(colormap),
                clim=None if color_scale_id is not None else clim,
                color_scale_id=color_scale_id,
            )
            self.visuals.append(visual)
            self._attach(visual.id)
            return visual

    @contextmanager
    def _color_scale_transaction(self) -> Iterator[None]:
        """Register implicit scales only when their visual or guide validates."""
        checkpoint = len(self.figure.color_scale_resources)
        try:
            yield
        except Exception:
            del self.figure.color_scale_resources[checkpoint:]
            raise

    def _register_color_scale(self, scale: ColorScale) -> None:
        for existing in self.figure.color_scale_resources:
            if existing.id == scale.id:
                if existing == scale:
                    return
                raise ValueError(f"color scale id already exists: {scale.id}")
        self.figure.color_scale_resources.append(scale)

    def _color_scale_id(self, color_scale: str | ColorScale) -> str:
        if isinstance(color_scale, ColorScale):
            self._register_color_scale(color_scale)
            return color_scale.id
        for existing in self.figure.color_scale_resources:
            if existing.id == color_scale:
                return color_scale
        raise ValueError(f"unknown color scale id: {color_scale}")

    def _scalar_encoding(
        self,
        values: npt.ArrayLike | None,
        count_: int,
        *,
        slot: ScalarColorSlot,
        domain: ScalarColorDomain,
        color_scale: str | ColorScale | None,
        cmap: str | ColorMapId | None,
        clim: tuple[float, float] | None,
        alpha: float,
    ) -> ScalarColorEncoding | None:
        if color_scale is None and cmap is None:
            return None
        if values is None:
            raise ValueError("scalar color encoding requires scalar values")
        scale_id = self._scalar_color_scale_id(color_scale, cmap=cmap, clim=clim)
        return ScalarColorEncoding(
            slot=slot,
            values=_scalar_values(values, shape=(count_,)),
            color_scale_id=scale_id,
            alpha=float(alpha),
            domain=domain,
        )

    def _scalar_color_scale_id(
        self,
        color_scale: str | ColorScale | None,
        *,
        cmap: str | ColorMapId | None,
        clim: tuple[float, float] | None,
    ) -> str:
        if color_scale is not None:
            if cmap is not None or clim is not None:
                raise ValueError("color_scale is mutually exclusive with cmap/clim")
            return self._color_scale_id(color_scale)
        if cmap is None or clim is None:
            raise ValueError("cmap and clim are required for scalar color encoding")
        scale = self.color_scale(cmap=cmap, clim=clim)
        return scale.id

    def _image_color_scale_id(
        self,
        image: np.ndarray,
        *,
        colormap: str | ImageColormap | ColorMapId | None,
        cmap: str | ColorMapId | None,
        clim: tuple[float, float] | None,
        color_scale: str | ColorScale | None,
    ) -> str | None:
        if image.ndim != 2:
            if color_scale is not None or cmap is not None:
                raise ValueError("color_scale and cmap apply to scalar images only")
            return None
        if color_scale is not None:
            if cmap is not None or _is_s026_colormap(colormap):
                raise ValueError("color_scale is mutually exclusive with cmap")
            return self._color_scale_id(color_scale)
        resolved_cmap = cmap
        if resolved_cmap is None and _is_s026_colormap(colormap):
            resolved_cmap = cast(str | ColorMapId, colormap)
        if resolved_cmap is None:
            return None
        if clim is None:
            raise ValueError("clim is required when using a scalar color scale")
        scale = self.color_scale(cmap=resolved_cmap, clim=clim)
        return scale.id
