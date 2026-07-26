"""Shared resolved-layout and projection evidence for galleries 2--4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import vispy2 as vp
from gsp.protocol import (
    PerspectiveProjection3D,
    ResolvedLayoutSnapshot,
    panel_ndc_to_plot_logical_px,
    project_view3d_data_point,
    resolve_view3d_projection_snapshot,
)


def resolve_shared_layout(figure: vp.Figure) -> ResolvedLayoutSnapshot:
    """Resolve the publication layout once without exposing a backend render object."""
    with vp.open_session("matplotlib", require={"output.file"}) as session:
        return figure.resolve_layout(session)


def render_with_shared_layout(
    figure: vp.Figure,
    backend: str,
    target: Path,
    *,
    anchor_points: Iterable[tuple[float, float, float]],
    evidence_path: Path | None,
) -> None:
    """Render through one consumed layout and optionally record strict evidence."""
    layout = resolve_shared_layout(figure)
    required = _required_capabilities(figure)
    with vp.open_session(backend, require=required) as session:
        _validate_view3d_capabilities(figure, backend, session.capabilities)
        result = session.render(
            figure.to_scene(),
            layout_snapshot=layout,
            target=target,
        )
        if evidence_path is not None:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text(
                json.dumps(
                    _render_evidence(
                        figure,
                        backend,
                        layout,
                        result,
                        anchor_points=tuple(anchor_points),
                        title_status=session.capabilities.guide_layout_capability.panel_text_title,
                        layout_diagnostics=session.capabilities.layout_capability.diagnostics,
                        render_diagnostics=session.diagnostics,
                    ),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )


def _required_capabilities(figure: vp.Figure) -> set[str]:
    names = {type(visual).__name__ for visual in figure.visuals()}
    mapping = {
        "MeshVisual": "visual.mesh",
        "PixelVisual": "visual.pixels",
        "PrimitiveVisual": "visual.primitive",
        "SphereVisual": "visual.sphere",
        "TextVisual": "visual.text",
        "VectorVisual": "visual.vector",
    }
    return {"output.file", *(mapping[name] for name in names if name in mapping)}


def _validate_view3d_capabilities(
    figure: vp.Figure,
    backend: str,
    capabilities: Any,
) -> None:
    scene = figure.to_scene()
    if scene.view3d is None:
        raise RuntimeError("shared gallery layout requires a View3D")
    required = _required_view3d_capabilities(figure)
    for capability in sorted(required):
        if not capabilities.supports_view3d_capability(capability):
            raise RuntimeError(f"{backend} does not advertise {capability}")


def _required_view3d_capabilities(figure: vp.Figure) -> set[str]:
    scene = figure.to_scene()
    if scene.view3d is None:
        raise RuntimeError("shared gallery layout requires a View3D")
    required = {
        (
            "view3d.static.perspective.v1"
            if isinstance(scene.view3d.projection, PerspectiveProjection3D)
            else "view3d.static.orthographic.v1"
        )
    }
    names = {type(visual).__name__ for visual in scene.visuals}
    mapping = {
        "MeshVisual": "meshvisual.positions3d.data.view3d.v1",
        "PixelVisual": "pixelvisual.positions3d.data.view3d.v1",
        "PrimitiveVisual": "primitivevisual.v1",
        "SphereVisual": "spherevisual.v1",
        "TextVisual": "textvisual.billboard3d.v1",
        "VectorVisual": "vectorvisual.positions3d.data.view3d.v1",
    }
    required.update(mapping[name] for name in names if name in mapping)
    if "PrimitiveVisual" in names:
        required.update(
            {
                "primitivevisual.indexed.v1",
                "primitivevisual.triangle_strip",
            }
        )
    return required


def _render_evidence(
    figure: vp.Figure,
    backend: str,
    layout: ResolvedLayoutSnapshot,
    result: Any,
    *,
    anchor_points: tuple[tuple[float, float, float], ...],
    title_status: str,
    layout_diagnostics: tuple[str, ...],
    render_diagnostics: tuple[str, ...],
) -> dict[str, Any]:
    scene = figure.to_scene()
    if scene.view3d is None:
        raise RuntimeError("shared gallery evidence requires a View3D")
    projection = resolve_view3d_projection_snapshot(
        scene.view3d,
        layout_snapshot=layout,
    )
    aspect = projection.aspect_ratio
    anchors = []
    for point in anchor_points:
        ndc = project_view3d_data_point(
            scene.view3d,
            point,
            aspect_ratio=aspect,
        )
        pixel = panel_ndc_to_plot_logical_px(layout, (ndc[0], ndc[1]))
        anchors.append(
            {
                "data": list(point),
                "ndc": list(ndc),
                "logical_pixel": list(pixel),
            }
        )
    return {
        "backend": backend,
        "canvas_size": [
            layout.render_target.framebuffer_width_px,
            layout.render_target.framebuffer_height_px,
        ],
        "panel_rect": _rect_values(layout.panel_rect_px),
        "plot_rect": _rect_values(layout.plot_rect_px),
        "layout_snapshot_id": layout.snapshot_id,
        "projection_snapshot_id": projection.view_projection_snapshot_id,
        "projection_kind": projection.projection_kind.value,
        "effective_perspective_aspect": (
            aspect
            if isinstance(scene.view3d.projection, PerspectiveProjection3D)
            else None
        ),
        "authored_perspective_aspect": (
            scene.view3d.projection.aspect_ratio
            if isinstance(scene.view3d.projection, PerspectiveProjection3D)
            else None
        ),
        "projected_anchors": anchors,
        "backend_projection_snapshot_id": _backend_projection_snapshot_id(
            backend, result, layout
        ),
        "title_status": title_status,
        "layout_diagnostics": list(layout_diagnostics),
        "render_diagnostics": list(render_diagnostics),
    }


def _backend_projection_snapshot_id(
    backend: str,
    result: Any,
    layout: ResolvedLayoutSnapshot,
) -> str | None:
    projection = getattr(result, "view3d_projection_snapshot", None)
    if projection is not None:
        return str(projection.view_projection_snapshot_id)
    readback = getattr(result, "resolve_retained_view3d_state_snapshot", None)
    if backend == "datoviz" and callable(readback):
        state = readback(layout_snapshot_id=layout.snapshot_id)
        return str(state["view_projection_snapshot_id"])
    return None


def _rect_values(rect: Any) -> list[float]:
    return [float(rect.x), float(rect.y), float(rect.width), float(rect.height)]
