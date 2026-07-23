"""VisPy2 producer API for backend-neutral GSP scenes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import count
import math
from pathlib import Path
from typing import Any, Literal, SupportsFloat, cast, overload

import numpy as np
import numpy.typing as npt

from gsp import Scene
from gsp.backends import BackendSession
from gsp.protocol import (
    AxisDimension,
    AxisGuide,
    AxisSide,
    ColorMapId,
    ColorMapRef,
    ColorScale,
    ColorbarGuide,
    ColorbarGuideStyle,
    ColorbarOrientation,
    ColorbarPlacement,
    Camera3D,
    CoordinateSpace,
    FontRole,
    ImageColormap,
    ImageInterpolation,
    ImageOrigin,
    ImageVisual,
    LinearNormalize,
    MeshColorMode,
    MeshNormalGeneration,
    MeshNormalMode,
    MeshShading,
    MeshUVMode,
    MeshVisual,
    MarkerShape,
    MarkerVisual,
    Orbit3DPayload,
    OrthographicProjection3D,
    Panel,
    Pan3DPayload,
    PanelTextGuide,
    PanelTextRole,
    PathVisual,
    PerspectiveProjection3D,
    PixelVisual,
    PointVisual,
    Projection3D,
    ScalarColorDomain,
    ScalarColorEncoding,
    ScalarColorSlot,
    SegmentVisual,
    StrokeCap,
    StrokeJoin,
    TextAnchorX,
    TextAnchorY,
    TextVisual,
    TickSpec,
    TickSpecKind,
    Texture2D,
    TextureFilter,
    View2D,
    View3D,
    VisualAttachment,
    VisualTransformBinding,
    Zoom3DPayload,
    orbit_view3d,
    pan_view3d,
    zoom_view3d,
)

from .session import require_session


_visual_counter = count(1)
_scale_counter = count(1)
_texture_counter = count(1)


@dataclass(slots=True)
class Figure:
    """Backend-neutral container for semantic producer scene state."""

    axes: list["Axes | Axes3D"] = field(default_factory=list)
    id: str = "figure:main"
    color_scale_resources: list[ColorScale] = field(default_factory=list)
    texture2d_resources: list[Texture2D] = field(default_factory=list)

    @overload
    def add_axes(self, *, projection: Literal["2d"] = "2d") -> "Axes": ...

    @overload
    def add_axes(self, *, projection: Literal["3d"]) -> "Axes3D": ...

    def add_axes(self, *, projection: str = "2d") -> "Axes | Axes3D":
        """Add one 2D or 3D protocol-producing axes to the figure."""
        if projection == "2d":
            axes: Axes | Axes3D = Axes(figure=self)
        elif projection == "3d":
            axes = Axes3D(figure=self)
        else:
            raise ValueError("projection must be '2d' or '3d'")
        self.axes.append(axes)
        return axes

    def visuals(
        self,
    ) -> tuple[
        PointVisual
        | PixelVisual
        | MarkerVisual
        | SegmentVisual
        | PathVisual
        | MeshVisual
        | ImageVisual
        | TextVisual,
        ...,
    ]:
        """Return protocol visuals in creation order."""
        return tuple(visual for axes in self.axes for visual in axes.visuals)

    def panels(self) -> tuple[Panel, ...]:
        """Return semantic panels without expanding guide visuals."""
        return tuple(axes.panel for axes in self.axes)

    def views(self) -> tuple[View2D | View3D, ...]:
        """Return semantic views without expanding guide visuals."""
        return tuple(axes.view for axes in self.axes)

    def attachments(self) -> tuple[VisualAttachment, ...]:
        """Return data visual attachments to panels/views."""
        return tuple(attachment for axes in self.axes for attachment in axes.attachments)

    def axis_guides(self) -> tuple[AxisGuide, ...]:
        """Return semantic axis guide intent without expanding guide visuals."""
        return tuple(guide for axes in self.axes for guide in axes.axis_guides)

    def panel_text_guides(self) -> tuple[PanelTextGuide, ...]:
        """Return semantic panel text guide intent without expanding guide visuals."""
        return tuple(guide for axes in self.axes for guide in axes.panel_text_guides)

    def color_scales(self) -> tuple[ColorScale, ...]:
        """Return semantic scalar color scale resources."""
        return tuple(self.color_scale_resources)

    def texture_resources(self) -> tuple[Texture2D, ...]:
        """Return semantic Texture2D resources."""
        return tuple(self.texture2d_resources)

    def colorbar_guides(self) -> tuple[ColorbarGuide, ...]:
        """Return semantic colorbar guide intent."""
        return tuple(guide for axes in self.axes for guide in axes.colorbar_guides)

    def to_scene(self) -> Scene:
        """Freeze current semantic producer state into one immutable GSP scene."""
        if len(self.axes) != 1:
            raise ValueError("Figure.to_scene() requires exactly one 2D or 3D Axes")
        axes = self.axes[0]
        scene_id = (
            self.id.replace("figure:", "scene:", 1)
            if self.id.startswith("figure:")
            else f"scene:{self.id}"
        )
        return Scene(
            id=scene_id,
            visuals=self.visuals(),
            panels=self.panels(),
            view2d=axes.view if isinstance(axes, Axes) else None,
            view3d=axes.view if isinstance(axes, Axes3D) else None,
            attachments=self.attachments(),
            axis_guides=self.axis_guides(),
            panel_text_guides=self.panel_text_guides(),
            color_scales=self.color_scales(),
            colorbar_guides=self.colorbar_guides(),
            textures=self.texture_resources(),
        )

    def savefig(self, path: str | Path, **kwargs: Any) -> None:
        """Save through an ephemeral Matplotlib provider session."""
        with require_session("matplotlib", extra="matplotlib", require={"output.file"}) as session:
            session.render(self.to_scene(), target=path, **kwargs)

    def display(self, session: BackendSession, **kwargs: Any) -> Any:
        """Display through a caller-owned session without retaining backend state."""
        return session.display(self.to_scene(), **kwargs)

    def show(
        self,
        *,
        session: BackendSession | None = None,
        block: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Show with Matplotlib, or use an explicit caller-owned session."""
        if session is not None:
            return self.display(session, block=block, **kwargs)
        if not block:
            raise ValueError("non-blocking show requires an explicit caller-owned session")
        with require_session("matplotlib", extra="matplotlib") as owned_session:
            result = owned_session.display(self.to_scene(), **kwargs)
            owned_session.run()
            return result


@dataclass(slots=True)
class Axes:
    """Axes-like producer that appends GSP visuals, guides, and resources."""

    figure: Figure
    visuals: list[
        PointVisual
        | PixelVisual
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

    def __post_init__(self) -> None:
        index = len(self.figure.axes) + 1
        panel_id = f"panel:{index}"
        view_id = f"view:{index}"
        self.panel = Panel(id=panel_id, figure_id=self.figure.id)
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
        """Set the semantic x range for this 2D view."""
        self.view = View2D(
            id=self.view.id,
            panel_id=self.view.panel_id,
            x_range=(float(left), float(right)),
            y_range=self.view.y_range,
            aspect_policy=self.view.aspect_policy,
        )
        return self.view.x_range

    def set_ylim(self, bottom: float, top: float) -> tuple[float, float]:
        """Set the semantic y range for this 2D view."""
        self.view = View2D(
            id=self.view.id,
            panel_id=self.view.panel_id,
            x_range=self.view.x_range,
            y_range=(float(bottom), float(top)),
            aspect_policy=self.view.aspect_policy,
        )
        return self.view.y_range

    def set_view2d(
        self,
        *,
        xlim: tuple[float, float] | None = None,
        ylim: tuple[float, float] | None = None,
        clip: bool | None = None,
    ) -> View2D:
        """Set deterministic S027 View2D state."""
        next_xlim = self.view.xlim if xlim is None else (float(xlim[0]), float(xlim[1]))
        next_ylim = self.view.ylim if ylim is None else (float(ylim[0]), float(ylim[1]))
        self.view = View2D(
            id=self.view.id,
            panel_id=self.view.panel_id,
            x_range=next_xlim,
            y_range=next_ylim,
            aspect_policy=self.view.aspect_policy,
            kind=self.view.kind,
            clip=self.view.clip if clip is None else bool(clip),
        )
        return self.view

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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(
                visual_id=visual.id,
                panel_id=self.panel.id,
                view_id=self.view.id,
            )
        )
        return visual

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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
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
        self.attachments.append(
            VisualAttachment(visual_id=visual.id, panel_id=self.panel.id, view_id=self.view.id)
        )
        return visual

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


@dataclass(slots=True)
class Axes3D:
    """Backend-neutral producer for one static GSP View3D."""

    figure: Figure
    visuals: list[MeshVisual | PixelVisual] = field(default_factory=list)
    panel: Panel = field(init=False)
    view: View3D = field(init=False)
    attachments: list[VisualAttachment] = field(default_factory=list)
    axis_guides: list[AxisGuide] = field(default_factory=list)
    panel_text_guides: list[PanelTextGuide] = field(default_factory=list)
    colorbar_guides: list[ColorbarGuide] = field(default_factory=list)
    _home_view: View3D = field(init=False, repr=False)

    def __post_init__(self) -> None:
        index = len(self.figure.axes) + 1
        panel_id = f"panel:{index}"
        self.panel = Panel(id=panel_id, figure_id=self.figure.id)
        self.view = View3D(
            id=f"view:{index}",
            panel_id=panel_id,
            camera=Camera3D(
                eye=(3.0, 3.0, 3.0),
                target=(0.0, 0.0, 0.0),
                up=(0.0, 0.0, 1.0),
            ),
            projection=PerspectiveProjection3D(
                fov_y_degrees=45.0,
                near_far=(0.1, 1000.0),
            ),
        )
        self._home_view = self.view

    def set_camera(
        self,
        *,
        eye: npt.ArrayLike,
        target: npt.ArrayLike,
        up: npt.ArrayLike,
    ) -> Camera3D:
        """Replace the semantic camera and increment the View3D revision."""
        camera = Camera3D(
            eye=_float3(eye, field_name="eye"),
            target=_float3(target, field_name="target"),
            up=_float3(up, field_name="up"),
        )
        self.view = replace(
            self.view,
            camera=camera,
            revision=self.view.revision + 1,
        )
        return camera

    def get_camera(self) -> Camera3D:
        """Return the current semantic camera."""
        return self.view.camera

    def set_perspective(
        self,
        *,
        fov_y_degrees: float = 45.0,
        near: float = 0.1,
        far: float = 1000.0,
        aspect_ratio: float | None = None,
    ) -> PerspectiveProjection3D:
        """Set a perspective projection and increment the View3D revision."""
        projection = PerspectiveProjection3D(
            fov_y_degrees=float(fov_y_degrees),
            near_far=(float(near), float(far)),
            aspect_ratio=None if aspect_ratio is None else float(aspect_ratio),
        )
        self.view = replace(
            self.view,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return projection

    def set_orthographic(
        self,
        *,
        xlim: tuple[float, float] = (-1.0, 1.0),
        ylim: tuple[float, float] = (-1.0, 1.0),
        near: float = 0.0,
        far: float = 1000.0,
    ) -> OrthographicProjection3D:
        """Set an orthographic projection and increment the View3D revision."""
        projection = OrthographicProjection3D(
            xlim=(float(xlim[0]), float(xlim[1])),
            ylim=(float(ylim[0]), float(ylim[1])),
            near_far=(float(near), float(far)),
        )
        self.view = replace(
            self.view,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return projection

    def get_projection(self) -> Projection3D:
        """Return the current semantic projection."""
        return self.view.projection

    def orbit(self, *, yaw_radians: float, pitch_radians: float) -> View3D:
        """Orbit with the accepted GSP reducer."""
        self.view = orbit_view3d(
            self.view,
            Orbit3DPayload(
                delta_yaw_radians=float(yaw_radians),
                delta_pitch_radians=float(pitch_radians),
            ),
        )
        return self.view

    def pan(self, *, right: float, up: float) -> View3D:
        """Pan with the accepted GSP reducer."""
        self.view = pan_view3d(
            self.view,
            Pan3DPayload(
                delta_view_right=float(right),
                delta_view_up=float(up),
            ),
        )
        return self.view

    def zoom(
        self,
        scale: float,
        *,
        anchor_ndc: tuple[float, float] | None = None,
    ) -> View3D:
        """Zoom with the accepted GSP reducer."""
        anchor = None if anchor_ndc is None else (float(anchor_ndc[0]), float(anchor_ndc[1]))
        self.view = zoom_view3d(
            self.view,
            Zoom3DPayload(
                scale=float(scale),
                anchor_panel_ndc_xy=anchor,
            ),
        )
        return self.view

    def reset_camera(self) -> View3D:
        """Restore the camera and projection from axes construction."""
        self.view = replace(
            self._home_view,
            revision=self.view.revision + 1,
        )
        return self.view

    def fit_camera(self, *, margin: float = 1.1) -> View3D:
        """Fit the current camera/projection to finite DATA-space 3D bounds."""
        resolved_margin = float(margin)
        if not math.isfinite(resolved_margin) or resolved_margin < 1.0:
            raise ValueError("camera fit margin must be finite and at least 1")
        bounds = _axes3d_data_bounds(self.visuals)
        camera: Camera3D
        projection: Projection3D
        if isinstance(self.view.projection, PerspectiveProjection3D):
            camera, projection = _fit_perspective_camera(
                self.view,
                bounds,
                margin=resolved_margin,
            )
        else:
            camera, projection = _fit_orthographic_camera(
                self.view,
                bounds,
                margin=resolved_margin,
            )
        self.view = replace(
            self.view,
            camera=camera,
            projection=projection,
            revision=self.view.revision + 1,
        )
        return self.view

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
        """Create a 3D protocol mesh attached to this View3D."""
        position_array = _positions(positions, None)
        if position_array.shape[1] != 3:
            raise ValueError("Axes3D.mesh() positions must have shape (N, 3)")
        if transform is not None:
            raise ValueError("Axes3D.mesh() transforms are not supported in this static 3D slice")
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
            transform=None,
            texture_filter=_texture_filter(texture_filter),
        )
        if texture_resource is not None:
            self.figure.texture2d_resources.append(texture_resource)
        self.visuals.append(visual)
        self.attachments.append(
            VisualAttachment(
                visual_id=visual.id,
                panel_id=self.panel.id,
                view_id=self.view.id,
            )
        )
        return visual

    def pixels(
        self,
        x: npt.ArrayLike,
        y: npt.ArrayLike | None = None,
        z: npt.ArrayLike | None = None,
        *,
        color: npt.ArrayLike | None = None,
        size: npt.ArrayLike | float = 1.0,
        id: str | None = None,
    ) -> PixelVisual:
        """Create projected square pixels anchored in 3D DATA space."""
        positions = _positions3d(x, y, z)
        visual = PixelVisual(
            id=id or _visual_id("pixels"),
            positions=positions,
            colors=_colors(color, positions.shape[0]),
            pixel_size_px=_sizes(size, positions.shape[0]),
            coordinate_space=CoordinateSpace.DATA,
        )
        self.visuals.append(visual)
        self.attachments.append(
            VisualAttachment(
                visual_id=visual.id,
                panel_id=self.panel.id,
                view_id=self.view.id,
            )
        )
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


@overload
def subplots() -> tuple[Figure, Axes]: ...


@overload
def subplots(*, projection: Literal["2d"]) -> tuple[Figure, Axes]: ...


@overload
def subplots(*, projection: Literal["3d"]) -> tuple[Figure, Axes3D]: ...


def subplots(*, projection: str = "2d") -> tuple[Figure, Axes | Axes3D]:
    """Create a one-axes 2D or 3D GSP VisPy2 protocol figure."""
    fig = Figure()
    if projection == "2d":
        ax: Axes | Axes3D = fig.add_axes(projection="2d")
    elif projection == "3d":
        ax = fig.add_axes(projection="3d")
    else:
        raise ValueError("projection must be '2d' or '3d'")
    return fig, ax


def affine2d(matrix: npt.ArrayLike) -> VisualTransformBinding:
    """Create an inline S027 affine 2D visual transform binding."""
    return VisualTransformBinding.inline_affine(_affine_matrix(matrix))


def scatter(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> PointVisual:
    """Create a point visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.scatter(x, y, **kwargs)


def pixels(x: npt.ArrayLike, y: npt.ArrayLike | None = None, **kwargs: Any) -> PixelVisual:
    """Create a pixel visual in a temporary one-axes figure."""
    _, ax = subplots()
    return ax.pixels(x, y, **kwargs)


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


def _float3(value: npt.ArrayLike, *, field_name: str) -> tuple[float, float, float]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3,):
        raise ValueError(f"{field_name} must contain exactly three values")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} values must be finite")
    return (float(array[0]), float(array[1]), float(array[2]))


def _axes3d_data_bounds(
    visuals: list[MeshVisual | PixelVisual],
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    position_arrays = [
        np.asarray(visual.positions, dtype=np.float64)
        for visual in visuals
        if visual.coordinate_space is CoordinateSpace.DATA and visual.positions.shape[1] == 3
    ]
    if not position_arrays:
        raise ValueError("fit_camera() requires at least one DATA-space 3D visual")
    positions = np.concatenate(position_arrays, axis=0)
    if positions.size == 0 or not np.all(np.isfinite(positions)):
        raise ValueError("fit_camera() requires finite non-empty DATA-space bounds")
    return np.min(positions, axis=0), np.max(positions, axis=0)


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


def _positions3d(
    x: npt.ArrayLike,
    y: npt.ArrayLike | None,
    z: npt.ArrayLike | None,
) -> npt.NDArray[np.float32]:
    if y is None and z is None:
        positions = _positions(x, None)
        if positions.shape[1] != 3:
            raise ValueError(
                "Axes3D.pixels() requires x/y/z arrays or an array with shape (N, 3)"
            )
        return positions
    if y is None or z is None:
        raise ValueError("Axes3D.pixels() requires both y and z")
    arrays = tuple(np.asarray(value, dtype=np.float32) for value in (x, y, z))
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("x, y, and z must be one-dimensional")
    if len({array.shape[0] for array in arrays}) != 1:
        raise ValueError("x, y, and z must have the same length")
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
