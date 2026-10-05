"""Qualify bounded native single-mesh FACE identity and fresh HIT/MISS results."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json

from gsp import MeshPickSession
from gsp.protocol import (
    CanvasSize,
    QueryStatus,
    View3DMeshTrianglePickPayload,
    View3DMeshTrianglePickRequest,
    plot_ndc_to_plot_logical_px,
)
import vispy2 as vp


def check(backend: str = "datoviz") -> None:
    if backend != "datoviz":
        raise ValueError("single-mesh native FACE qualification requires Datoviz")
    figure, axes = vp.subplots(projection="3d", canvas_size=CanvasSize.pixel_exact(320, 240))
    mesh = axes.mesh(
        [[-0.5, -0.5, 0.0], [0.5, -0.5, 0.0], [0.0, 0.5, 0.0]],
        [[0, 1, 2]],
        color=[255, 255, 255, 255],
        id="visual:mesh-pick",
    )
    axes.set_camera(eye=(0.0, 0.0, 1.0), target=(0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    axes.set_orthographic(xlim=(-1.0, 1.0), ylim=(-1.0, 1.0), near=0.0, far=2.0)
    with vp.open_session("matplotlib") as reference:
        layout = figure.resolve_layout(reference)
    records = []
    with vp.open_session(backend, require={"query.mesh.single.v1"}) as session:
        assert isinstance(session, MeshPickSession)
        result = session.render(figure.to_scene(), layout_snapshot=layout)
        # Force a native frame before querying, using capture solely for qualification.
        assert result.capture_png_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        for name, ndc, expected in (
            ("hit", (0.0, 0.0), QueryStatus.HIT),
            ("miss", (0.8, 0.8), QueryStatus.MISS),
        ):
            request = View3DMeshTrianglePickRequest(
                axes.view.id,
                plot_ndc_to_plot_logical_px(layout, ndc),
                panel_id=axes.panel.id,
                expected_layout_snapshot_id=layout.snapshot_id,
            )
            answer = session.pick_mesh(request)
            assert answer.status is expected, answer
            payload = answer.extension_payload
            assert isinstance(payload, View3DMeshTrianglePickPayload)
            assert payload.pick_scene_snapshot_id is not None
            if expected is QueryStatus.HIT:
                assert answer.visual_id == mesh.id
                assert payload.primitive_index == 0
            else:
                assert answer.visual_id is None and not answer.hits
                assert payload.primitive_index is None
            records.append(
                {
                    "case": name,
                    "status": answer.status.value,
                    "visual_id": answer.visual_id,
                    "primitive_index": payload.primitive_index,
                    "pick_scene_snapshot_id": payload.pick_scene_snapshot_id,
                }
            )
        stale = session.pick_mesh(
            replace(request, expected_pick_scene_snapshot_id="pick-scene:old")
        )
        assert stale.status is QueryStatus.STALE, stale
        assert stale.diagnostic == "pick.stale.pick_scene_snapshot", stale
        records.append(
            {"case": "stale", "status": stale.status.value, "diagnostic": stale.diagnostic}
        )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("datoviz",), default="datoviz")
    check(parser.parse_args().backend)
