"""Semantic figures and panel layout."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast, overload

import numpy as np
import numpy.typing as npt
from gsp import Scene, PointUpdateSession, BackendCapabilityError
from gsp.updates import prepare_point_update
from gsp.backends import BackendSession
from gsp.protocol import (
    AxisGuide,
    CanvasSize,
    ColorbarGuide,
    ColorScale,
    ExplicitPanelLayoutV1,
    ImageVisual,
    MarkerVisual,
    MeshVisual,
    NormalizedRenderTargetRect,
    Panel,
    PanelPlacement,
    PanelTextGuide,
    PathVisual,
    PixelVisual,
    PointVisual,
    PrimitiveVisual,
    QueryRequest,
    QueryResult,
    ResolvedLayoutSnapshot,
    SegmentVisual,
    SphereVisual,
    Texture2D,
    TextVisual,
    VectorVisual,
    View2D,
    View3D,
    VisualAttachment,
)

from ._axes2d import Axes
from ._axes3d import Axes3D
from .session import require_session


@dataclass(slots=True)
class Figure:
    """Backend-neutral container for semantic producer scene state."""

    axes: list["Axes | Axes3D"] = field(default_factory=list)
    id: str = "figure:main"
    canvas_size: CanvasSize | None = None
    color_scale_resources: list[ColorScale] = field(default_factory=list)
    texture2d_resources: list[Texture2D] = field(default_factory=list)

    _x_links: list[set[str]] = field(default_factory=list, repr=False)
    _y_links: list[set[str]] = field(default_factory=list, repr=False)
    _allocations: dict[str, NormalizedRenderTargetRect] = field(default_factory=dict, repr=False)

    @overload
    def add_axes(
        self,
        *,
        projection: Literal["2d"] = "2d",
        allocation: NormalizedRenderTargetRect | None = None,
    ) -> "Axes": ...

    @overload
    def add_axes(
        self, *, projection: Literal["3d"], allocation: NormalizedRenderTargetRect | None = None
    ) -> "Axes3D": ...

    def add_axes(
        self, *, projection: str = "2d", allocation: NormalizedRenderTargetRect | None = None
    ) -> "Axes | Axes3D":
        """Add one 2D or 3D protocol-producing axes to the figure."""
        if allocation is not None and not isinstance(allocation, NormalizedRenderTargetRect):
            raise TypeError("allocation must be a NormalizedRenderTargetRect")
        if projection == "2d":
            axes: Axes | Axes3D = Axes(figure=self)
        elif projection == "3d":
            axes = Axes3D(figure=self)
        else:
            raise ValueError("projection must be '2d' or '3d'")
        self.axes.append(axes)
        if allocation is not None:
            self.set_panel_allocation(axes, allocation)
        return axes

    def set_panel_allocation(
        self, axes: Axes | Axes3D, allocation: NormalizedRenderTargetRect
    ) -> NormalizedRenderTargetRect:
        """Set one axes' outer allocation in normalized top-left target coordinates."""
        if not any(axes is existing for existing in self.axes):
            raise ValueError("axes must belong to this figure")
        if not isinstance(allocation, NormalizedRenderTargetRect):
            raise TypeError("allocation must be a NormalizedRenderTargetRect")
        self._allocations[axes.panel.id] = allocation
        return allocation

    def link_axes(self, *axes: Axes, x: bool = True, y: bool = True) -> None:
        """Link programmatic 2D limits, initially taking limits from the first axes.

        Links belong to the producer, and do not enable native backend navigation.
        Each axes keeps its own view ID; overlapping groups merge transitively.
        """
        if len(axes) < 2 or len({id(axis) for axis in axes}) != len(axes):
            raise ValueError("link_axes requires at least two distinct axes")
        for axis in axes:
            self._require_axes2d(axis)
        if not x and not y:
            raise ValueError("link_axes requires x=True or y=True")
        ids = {axis.panel.id for axis in axes}
        for enabled, groups in ((x, self._x_links), (y, self._y_links)):
            if enabled:
                merged = set(ids)
                matching = [group for group in groups if group & ids]
                for group in matching:
                    merged.update(group)
                    groups.remove(group)
                groups.append(merged)
        self.set_limits(
            axes[0], xlim=axes[0].get_xlim() if x else None, ylim=axes[0].get_ylim() if y else None
        )

    def _require_axes2d(self, axes: Axes) -> None:
        if not isinstance(axes, Axes) or not any(axes is item for item in self.axes):
            raise ValueError("axes must be a 2D axes belonging to this figure")

    def set_limits(
        self,
        axes: Axes,
        *,
        xlim: tuple[float, float] | None = None,
        ylim: tuple[float, float] | None = None,
    ) -> View2D:
        """Atomically set one axes' limits and propagate its linked dimensions."""
        self._require_axes2d(axes)
        xids = next((group for group in self._x_links if axes.panel.id in group), {axes.panel.id})
        yids = next((group for group in self._y_links if axes.panel.id in group), {axes.panel.id})
        prepared: list[tuple[Axes, View2D]] = []
        for item in self.axes:
            if not isinstance(item, Axes):
                continue
            change_x = xlim is not None and item.panel.id in xids
            change_y = ylim is not None and item.panel.id in yids
            if change_x or change_y:
                prepared.append(
                    (
                        item,
                        replace(
                            item.view,
                            x_range=(float(xlim[0]), float(xlim[1]))
                            if change_x and xlim is not None
                            else item.view.x_range,
                            y_range=(float(ylim[0]), float(ylim[1]))
                            if change_y and ylim is not None
                            else item.view.y_range,
                        ),
                    )
                )
        for item, view in prepared:
            item.view = view
        return axes.view

    def update_point(self, session: PointUpdateSession, visual: PointVisual) -> int:
        """Update a retained point visual and producer state after session success."""
        if not isinstance(session, PointUpdateSession):
            raise BackendCapabilityError("session does not support scene.update.points.v1")
        scene = self.to_scene()
        prepare_point_update(scene, visual)
        revision = session.update_point(visual, scene_id=scene.id)
        for axes in self.axes:
            if not isinstance(axes, Axes):
                continue
            for index, existing in enumerate(axes.visuals):
                if existing.id == visual.id:
                    axes.visuals[index] = visual
                    return revision
        raise AssertionError("validated point visual has no producer owner")

    def visuals(
        self,
    ) -> tuple[
        PointVisual
        | PixelVisual
        | SphereVisual
        | VectorVisual
        | PrimitiveVisual
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

    def panel_layout(self) -> ExplicitPanelLayoutV1:
        """Return custom allocations or the default equal-width horizontal strips."""
        if not self.axes:
            raise ValueError("Figure panel layout requires at least one Axes")
        count = len(self.axes)
        return ExplicitPanelLayoutV1(
            placements=tuple(
                PanelPlacement(
                    panel_id=axes.panel.id,
                    allocation_rect=(
                        self._allocations[axes.panel.id]
                        if axes.panel.id in self._allocations
                        else NormalizedRenderTargetRect(
                            left=index / count,
                            top=0.0,
                            width=(index + 1) / count - index / count,
                            height=1.0,
                        )
                    ),
                )
                for index, axes in enumerate(self.axes)
            )
        )

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
        if not self.axes:
            raise ValueError("Figure.to_scene() requires at least one 2D or 3D Axes")
        scene_id = (
            self.id.replace("figure:", "scene:", 1)
            if self.id.startswith("figure:")
            else f"scene:{self.id}"
        )
        return Scene(
            id=scene_id,
            panels=self.panels(),
            panel_layout=self.panel_layout(),
            visuals=self.visuals(),
            views2d=tuple(axes.view for axes in self.axes if isinstance(axes, Axes)),
            views3d=tuple(axes.view for axes in self.axes if isinstance(axes, Axes3D)),
            attachments=self.attachments(),
            axis_guides=self.axis_guides(),
            panel_text_guides=self.panel_text_guides(),
            color_scales=self.color_scales(),
            colorbar_guides=self.colorbar_guides(),
            textures=self.texture_resources(),
            canvas_size=self.canvas_size,
        )

    def savefig(self, path: str | Path, **kwargs: Any) -> None:
        """Save through an ephemeral Matplotlib provider session."""
        with require_session("matplotlib", extra="matplotlib", require={"output.file"}) as session:
            session.render(self.to_scene(), target=path, **kwargs)

    def resolve_layout(
        self,
        session: BackendSession,
        **kwargs: Any,
    ) -> ResolvedLayoutSnapshot:
        """Render once and return only the backend-neutral resolved layout snapshot."""
        result = session.render(self.to_scene(), **kwargs)
        snapshot = getattr(result, "layout_snapshot", None)
        if not isinstance(snapshot, ResolvedLayoutSnapshot):
            authoritative_snapshot = getattr(result, "authoritative_layout_snapshot", None)
            if callable(authoritative_snapshot):
                snapshot = authoritative_snapshot()
        if not isinstance(snapshot, ResolvedLayoutSnapshot):
            raise RuntimeError(
                f"{session.backend_name!r} did not return a resolved layout snapshot"
            )
        return snapshot

    def display(self, session: BackendSession, **kwargs: Any) -> Any:
        """Display through a caller-owned session without retaining backend state."""
        return session.display(self.to_scene(), **kwargs)

    def query(self, session: BackendSession, request: QueryRequest) -> QueryResult:
        """Query this figure's stable scene through a caller-owned session."""
        scene_id = self.to_scene().id
        return session.query(request, scene_id=scene_id)

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


@overload
def subplots(*, canvas_size: CanvasSize | None = None) -> tuple[Figure, Axes]: ...


@overload
def subplots(
    *, projection: Literal["2d"], canvas_size: CanvasSize | None = None
) -> tuple[Figure, Axes]: ...


@overload
def subplots(
    *, projection: Literal["3d"], canvas_size: CanvasSize | None = None
) -> tuple[Figure, Axes3D]: ...


@overload
def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    projection: str | Sequence[Sequence[str]] = "2d",
    canvas_size: CanvasSize | None = None,
    squeeze: bool = True,
) -> tuple[Figure, Axes | Axes3D | npt.NDArray[np.object_]]: ...


def subplots(
    nrows: int = 1,
    ncols: int = 1,
    *,
    projection: str | Sequence[Sequence[str]] = "2d",
    canvas_size: CanvasSize | None = None,
    squeeze: bool = True,
) -> tuple[Figure, Axes | Axes3D | npt.NDArray[np.object_]]:
    """Create a row-major subplot grid, squeezing singleton dimensions by default.

    Projection may be one string for all cells or a rectangular nested sequence.
    A single subplot returns an axes; ``squeeze=False`` always returns a 2D array.
    """
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 1
        for value in (nrows, ncols)
    ):
        raise ValueError("nrows and ncols must be positive integers")
    projections = (
        np.full((nrows, ncols), projection)
        if isinstance(projection, str)
        else np.asarray(projection)
    )
    if projections.shape != (nrows, ncols) or not np.all(np.isin(projections, ("2d", "3d"))):
        raise ValueError("projection must be '2d', '3d', or a matching grid of those values")
    fig = Figure(canvas_size=canvas_size)
    grid = np.empty((nrows, ncols), dtype=object)
    for row in range(nrows):
        for col in range(ncols):
            allocation = NormalizedRenderTargetRect(
                left=col / ncols,
                top=row / nrows,
                width=(col + 1) / ncols - col / ncols,
                height=(row + 1) / nrows - row / nrows,
            )
            if projections[row, col] == "2d":
                grid[row, col] = fig.add_axes(projection="2d", allocation=allocation)
            else:
                grid[row, col] = fig.add_axes(projection="3d", allocation=allocation)
    if squeeze and nrows == ncols == 1:
        return fig, cast(Axes | Axes3D, grid[0, 0])
    return fig, np.squeeze(grid) if squeeze else grid
