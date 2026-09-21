"""Mixed View2D/View3D panels with layout, query, resize, and lifecycle evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import vispy2 as vp
from gsp.protocol import (
    CanvasSize,
    QueryPayload,
    QueryRequest,
    QueryStatus,
    ResolvedLayoutSnapshot,
)


def make_figure() -> vp.Figure:
    figure = vp.Figure(canvas_size=CanvasSize.pixel_exact(800, 600))
    axes2d = figure.add_axes()
    axes3d = figure.add_axes(projection="3d")
    axes2d.scatter(
        [0.0],
        [0.0],
        size=32.0,
        color=[220, 60, 80, 255],
        id="visual:mixed-2d",
    )
    axes2d.set_xlim(-1.0, 1.0)
    axes2d.set_ylim(-1.0, 1.0)
    axes2d.set_title("View2D panel")
    axes3d.mesh(
        [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.5]],
        [[0, 1, 2]],
        color=[60, 120, 220, 255],
        id="visual:mixed-3d",
    )
    axes3d.set_camera(eye=(3.0, 3.0, 3.0), target=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0))
    axes3d.set_title("View3D panel")
    return figure


def _result_layout(result: Any) -> ResolvedLayoutSnapshot:
    snapshot = getattr(result, "layout_snapshot", None)
    if isinstance(snapshot, ResolvedLayoutSnapshot):
        return snapshot
    authoritative = getattr(result, "authoritative_layout_snapshot", None)
    if callable(authoritative):
        snapshot = authoritative()
        if isinstance(snapshot, ResolvedLayoutSnapshot):
            return snapshot
    partial = getattr(result, "resolve_partial_layout_snapshot", None)
    if callable(partial):
        snapshot = partial()
        if isinstance(snapshot, ResolvedLayoutSnapshot):
            return snapshot
    raise RuntimeError("mixed-panel backend did not expose a resolved layout snapshot")


def _rect_values(rect: Any) -> list[float]:
    return [float(rect.x), float(rect.y), float(rect.width), float(rect.height)]


def render(
    backend: str,
    output_dir: str | Path,
    *,
    evidence_dir: str | Path | None = None,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{backend}-gallery-mixed-panels.png"
    figure = make_figure()
    scene = figure.to_scene()
    panel2d_id = scene.views2d[0].panel_id
    required = {"output.file", "query.panel", "visual.points", "visual.mesh"}

    with vp.open_session(backend, require=required) as session:
        figure.canvas_size = CanvasSize.pixel_exact(640, 360)
        warmup = session.render(figure.to_scene())
        warmup_layout = _result_layout(warmup)

        figure.canvas_size = CanvasSize.pixel_exact(800, 600)
        scene = figure.to_scene()
        result = session.render(scene, target=path)
        layout = _result_layout(result)
        point_query = figure.query(
            session,
            QueryRequest(
                id=f"query:{backend}:mixed-2d",
                panel_id=panel2d_id,
                coordinate=(0.0, 0.0),
                requested_payload=(QueryPayload.IDENTITY,),
            ),
        )
        invalid_panel_query = figure.query(
            session,
            QueryRequest(
                id=f"query:{backend}:missing-panel",
                panel_id="panel:missing",
                coordinate=(0.0, 0.0),
                requested_payload=(QueryPayload.IDENTITY,),
            ),
        )
        diagnostics = list(session.diagnostics)
        title_status = session.capabilities.guide_layout_capability.panel_text_title
        layout_diagnostics = list(session.capabilities.layout_capability.diagnostics)

    if invalid_panel_query.status is not QueryStatus.UNSUPPORTED:
        raise RuntimeError(
            f"{backend} missing-panel query must be structured unsupported, "
            f"got {invalid_panel_query.status.value}"
        )
    if point_query.status not in (QueryStatus.HIT, QueryStatus.UNSUPPORTED):
        raise RuntimeError(
            f"{backend} mixed 2D query must be hit or structured unsupported, "
            f"got {point_query.status.value}"
        )
    try:
        session.render(scene)
    except RuntimeError as exc:
        if "closed" not in str(exc):
            raise
    else:
        raise RuntimeError(f"{backend} session accepted a render after context teardown")

    expected_pairs = tuple(
        (panel.id, scene.primary_view_for_panel(panel.id).id) for panel in scene.panels
    )
    resolved_pairs = tuple((panel.panel_id, panel.view_id) for panel in layout.panels)
    if resolved_pairs != expected_pairs:
        raise RuntimeError(
            f"{backend} resolved panel/view identities differ: "
            f"expected={expected_pairs!r}, actual={resolved_pairs!r}"
        )
    if (
        warmup_layout.render_target.framebuffer_width_px,
        warmup_layout.render_target.framebuffer_height_px,
    ) != (640, 360):
        raise RuntimeError(f"{backend} mixed-panel warmup did not resolve to 640x360")
    if (
        layout.render_target.framebuffer_width_px,
        layout.render_target.framebuffer_height_px,
    ) != (800, 600):
        raise RuntimeError(f"{backend} mixed-panel capture did not resolve to 800x600")

    if evidence_dir is not None:
        evidence_path = Path(evidence_dir) / f"{path.stem}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence = {
            "backend": backend,
            "canvas_size": [800, 600],
            "warmup_canvas_size": [640, 360],
            "scene_panels": [panel.id for panel in scene.panels],
            "scene_views": {
                panel.id: scene.primary_view_for_panel(panel.id).id for panel in scene.panels
            },
            "attachments": [
                {
                    "visual_id": attachment.visual_id,
                    "panel_id": attachment.panel_id,
                    "view_id": attachment.view_id,
                }
                for attachment in scene.attachments
            ],
            "allocation_rects": [
                [
                    placement.allocation_rect.left,
                    placement.allocation_rect.top,
                    placement.allocation_rect.width,
                    placement.allocation_rect.height,
                ]
                for placement in scene.panel_layout.placements
            ],
            "resolved_panels": [
                {
                    "panel_id": panel.panel_id,
                    "view_id": panel.view_id,
                    "panel_rect": _rect_values(panel.panel_rect_px),
                    "plot_rect": _rect_values(panel.plot_rect_px),
                }
                for panel in layout.panels
            ],
            "point_query": {
                "request_id": point_query.request_id,
                "status": point_query.status.value,
                "visual_id": point_query.visual_id,
                "diagnostic": point_query.diagnostic,
            },
            "invalid_panel_query": {
                "request_id": invalid_panel_query.request_id,
                "status": invalid_panel_query.status.value,
                "diagnostic": invalid_panel_query.diagnostic,
            },
            "session_teardown": "closed",
            "title_status": title_status,
            "layout_diagnostics": layout_diagnostics,
            "render_diagnostics": diagnostics,
        }
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return path


def main() -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", choices=("matplotlib", "datoviz"))
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    return render(args.backend, args.output_dir, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    print(main())
