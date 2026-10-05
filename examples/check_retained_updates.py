"""Wheel qualification: retain resources, move a point, refresh pixels and picking."""

from __future__ import annotations

import argparse
from dataclasses import replace
from io import BytesIO

import numpy as np
from PIL import Image
import vispy2 as vp
from gsp import PointUpdateSession
from gsp.protocol import (
    CanvasSize,
    QueryCoordinateSpace,
    QueryPayload,
    QueryRequest,
    QueryStatus,
    plot_ndc_to_plot_logical_px,
)


def check(backend: str) -> None:
    figure, axes = vp.subplots(canvas_size=CanvasSize.pixel_exact(320, 240))
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    # Consume identical geometry without backend-specific native guide reservations.
    axes.axis_guides.clear()
    point = axes.scatter([0.25], [0.5], size=24, color=[255, 0, 0, 255])
    with vp.open_session("matplotlib") as reference:
        layout = figure.resolve_layout(reference)
    old_xy = plot_ndc_to_plot_logical_px(layout, (-0.5, 0))
    new_xy = plot_ndc_to_plot_logical_px(layout, (0.5, 0))
    with vp.open_session(
        backend, require={"scene.update.points.v1", "visual.points", "query.panel"}
    ) as session:
        assert isinstance(session, PointUpdateSession)
        result = session.render(figure.to_scene(), layout_snapshot=layout)
        # Qualification inspects native identity privately; producer state stays semantic.
        if backend == "matplotlib":
            native = result.figure.axes[0].collections[0]

            def capture() -> bytes:
                stream = BytesIO()
                result.figure.savefig(stream, format="png", dpi=result.figure.dpi)
                return stream.getvalue()

        else:
            native = result.visuals[point.id]
            capture = result.capture_png_bytes
        capture()
        assert session.scene_revision(figure.to_scene().id) == 0
        updated = replace(
            point,
            positions=np.asarray([[0.75, 0.5]], dtype=np.float32),
            colors=np.asarray([[0, 0, 255, 255]], dtype=np.uint8),
            sizes=32,
        )
        assert figure.update_point(session, updated) == 1
        current = (
            result.figure.axes[0].collections[0]
            if backend == "matplotlib"
            else result.visuals[point.id]
        )
        assert current is native
        image = np.asarray(Image.open(BytesIO(capture())).convert("RGB"))
        x, y = (round(value) for value in new_xy)
        assert image[y, x, 2] > 200 and image[y, x, 0] < 50, image[y, x]
        x, y = (round(value) for value in old_xy)
        assert np.max(image[y, x]) - np.min(image[y, x]) < 10, image[y, x]
        for identifier, coordinate, expected in (
            ("query:moved", new_xy, QueryStatus.HIT),
            ("query:vacated", old_xy, QueryStatus.MISS),
        ):
            query = QueryRequest(
                identifier,
                axes.panel.id,
                coordinate,
                coordinate_space=QueryCoordinateSpace.PANEL,
                requested_payload=(QueryPayload.IDENTITY,),
            )
            answer = figure.query(session, query)
            assert answer.status is expected, answer
            if expected is QueryStatus.HIT:
                assert answer.hits[0].visual_id == point.id
        try:
            figure.update_point(
                session,
                replace(
                    updated,
                    positions=np.zeros((2, 2), dtype=np.float32),
                    colors=np.full((2, 4), 255, dtype=np.uint8),
                ),
            )
        except ValueError:
            pass
        else:
            raise AssertionError("point count changes must fail")
        assert session.scene_revision(figure.to_scene().id) == 1
        assert axes.visuals[0] is updated
    print(f"{backend}: retained identity, changed pixels, fresh HIT/MISS, rejected topology passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("matplotlib", "datoviz"), required=True)
    check(parser.parse_args().backend)
