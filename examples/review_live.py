"""Backend-neutral scenes and bounded/live execution for the guided review tour.

Run one case with --backend matplotlib|datoviz. --headless renders and validates
PNG captures without opening windows. Importing this module creates no graphics.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy as np
from gsp import MeshPickSession, PointUpdateSession
from gsp.protocol import (
    QueryCoordinateSpace,
    QueryPayload,
    QueryRequest,
    View3DMeshTrianglePickRequest,
    plot_ndc_to_plot_logical_px,
)
from manual_live_compare import (
    BACKENDS,
    _review_device_scale,
    configure_live_canvas,
    normalize_matplotlib_window,
    run_datoviz_until_close,
)

import vispy2 as vp

CASES = (
    "points-markers",
    "strokes",
    "primitives-pixels",
    "scientific-grid",
    "layout-links",
    "transforms",
    "textures",
    "retained-updates",
    "mesh-pick",
)
BLUE = (35, 110, 225, 255)
ORANGE = (235, 110, 35, 255)


def _axes(title: str) -> tuple[vp.Figure, vp.Axes]:
    figure, axes = vp.subplots()
    axes.set_xlim(-1, 1)
    axes.set_ylim(-1, 1)
    axes.set_title(title)
    return figure, axes


def make_figure(case: str) -> vp.Figure:
    """Author semantic scenes using public producer methods only."""
    if case not in CASES:
        raise ValueError(f"unknown review case: {case!r}")
    figure, axes = _axes(case.replace("-", " "))
    if case == "points-markers":
        x = np.linspace(-0.75, 0.75, 5)
        axes.scatter(x, np.full(5, 0.45), size=[8, 14, 20, 26, 32], color=BLUE)
        axes.markers(
            x,
            np.zeros(5),
            shape=["disc", "square", "triangle", "diamond", "cross"],
            size=30,
            color=ORANGE,
            stroke_color=(30, 30, 30, 255),
            stroke_width=2,
        )
        axes.text([-0.85], [-0.55], "Pixel-sized markers; pan/zoom to compare", color=BLUE)
    elif case == "strokes":
        for index, cap in enumerate(("butt", "round", "square")):
            y = 0.7 - index * 0.5
            axes.segments([[-0.85, y]], [[-0.25, y]], width=15, color=BLUE, cap=cap)
            axes.path(
                [[0, y - 0.15], [0.3, y + 0.12], [0.65, y - 0.15]],
                width=12,
                color=ORANGE,
                cap=cap,
                join=("miter", "round", "bevel")[index],
            )
            axes.text([-0.9], [y - 0.23], cap, font_size_px=14)
    elif case == "primitives-pixels":
        axes.primitives(
            [[-0.8, -0.6], [-0.1, -0.6], [-0.45, 0.6]], topology="triangle_list", color=BLUE
        )
        axes.primitives([[0, -0.5], [0.8, 0.5]], topology="line_list", color=ORANGE)
        axes.pixels([0.1, 0.4, 0.7], [0.6, 0.6, 0.6], size=[4, 12, 24], color=BLUE)
    elif case == "scientific-grid":
        figure, grid = vp.subplots(2, 2)
        x = np.linspace(-2, 2, 40)
        a, b, c, d = grid.flat
        a.fill_between(x, np.sin(x) + 0.25, np.sin(x) - 0.25, color=(35, 110, 225, 100))
        a.plot(x, np.sin(x), color=BLUE, width=3)
        a.set_title("curve + uncertainty band")
        b.bar([-1, 0, 1], [1, -0.5, 1.5], color=ORANGE)
        b.set_title("positive / negative bars")
        c.hist(np.random.default_rng(42).normal(size=200), bins=12, color=BLUE)
        c.set_title("deterministic histogram")
        d.quiver([-1, 0, 1], [0, 0, 0], [0.3, 0.3, 0.3], [0.5, -0.5, 0.5], color=ORANGE)
        d.set_xlim(-1.5, 1.5)
        d.set_ylim(-1, 1)
        d.set_title("vector glyphs")
        for axis in (a, b, c):
            axis.fit_data()
        for axis in grid.flat:
            axis.grid()
            axis.set_xlabel("x")
            axis.set_ylabel("value")
    elif case == "layout-links":
        figure, grid = vp.subplots(1, 2)
        a, b = grid
        x = np.linspace(-3, 3, 80)
        a.plot(x, np.sin(x), color=BLUE)
        b.plot(x, np.cos(x), color=ORANGE)
        b.sharex(a)
        a.set_xlim(-2, 2)
        for axis, label in ((a, "sine"), (b, "cosine")):
            axis.set_ylim(-1.2, 1.2)
            axis.set_title(label + ": linked authored x limits")
            axis.set_xticks([-2, 0, 2], ["left", "zero", "right"])
            axis.grid()
        print(
            "Linked programmatic limits propagated to both axes; native navigation is backend-local.",
            flush=True,
        )
    elif case == "transforms":
        triangle = np.array([[-0.2, -0.2], [0.2, -0.2], [0, 0.2]], dtype=np.float32)
        axes.mesh(
            triangle,
            [[0, 1, 2]],
            color=BLUE,
            transform=vp.affine2d([[1, 0.4, -0.45], [0, 1, 0.1], [0, 0, 1]]),
        )
        axes.mesh(
            triangle,
            [[0, 1, 2]],
            color=ORANGE,
            coordinate_space="ndc",
            transform=vp.affine2d([[1.2, 0, 0.45], [0, 1.2, 0.1], [0, 0, 1]]),
        )
        axes.text([-0.9], [-0.65], "Blue: DATA shear. Orange: NDC scale + translation.")
    elif case == "textures":
        texture = np.array(
            [[[255, 40, 40, 255], [40, 220, 40, 255]], [[40, 40, 255, 255], [255, 220, 40, 255]]],
            dtype=np.uint8,
        )
        axes.mesh(
            [[-0.8, -0.8], [0.8, -0.8], [0.8, 0.8], [-0.8, 0.8]],
            [[0, 1, 2], [0, 2, 3]],
            color=(255, 255, 255, 255),
            texture=texture,
            uvs=[[0, 0], [1, 0], [1, 1], [0, 1]],
            texture_filter="nearest",
            id="review:textured-mesh",
        )
    elif case == "retained-updates":
        axes.scatter([-0.65, 0, 0.65], [0, 0, 0], size=24, color=BLUE, id="review:moving-points")
    elif case == "mesh-pick":
        figure, axes3d = vp.subplots(projection="3d")
        axes3d.mesh(
            [[-1, -1, 0], [1, -1, 0], [0, 1, 0]], [[0, 1, 2]], color=BLUE, id="review:pick-triangle"
        )
        axes3d.set_camera(eye=[0, 0, 4], target=[0, 0, 0], up=[0, 1, 0])
        axes3d.set_perspective(near=0.1, far=10)
    return figure


def _update(figure: vp.Figure, session: PointUpdateSession, phase: float) -> None:
    point = figure.axes[0].visuals[0]
    positions = np.array([[-0.65, 0], [0, 0], [0.65, 0]], dtype=np.float32)
    positions[:, 1] = 0.5 * np.sin(phase + np.arange(3))
    figure.update_point(session, replace(point, positions=positions))


def _query_evidence(figure: vp.Figure, session: object, layout: object) -> None:
    axes = figure.axes[0]
    point = axes.visuals[0]
    data_coordinate = tuple(float(value) for value in point.positions[0])
    panel_query = session.backend_name == "datoviz"
    coordinate = (
        plot_ndc_to_plot_logical_px(layout, data_coordinate) if panel_query else data_coordinate
    )
    result = figure.query(
        session,
        QueryRequest(
            id="review:point-query",
            panel_id=axes.panel.id,
            coordinate=coordinate,
            coordinate_space=(
                QueryCoordinateSpace.PANEL if panel_query else QueryCoordinateSpace.DATA
            ),
            requested_payload=(QueryPayload.IDENTITY,),
        ),
    )
    print(
        f"Retained panel query for moved point {data_coordinate} at {coordinate}: {result.status.value}; "
        f"visual={result.visual_id}, revision={session.scene_revision(figure.to_scene().id)}",
        flush=True,
    )
    if not result.hit or result.visual_id != point.id:
        raise RuntimeError("retained query did not find the updated point")
    old_data = (-0.65, 0.0)
    old_coordinate = plot_ndc_to_plot_logical_px(layout, old_data) if panel_query else old_data
    vacated = figure.query(
        session,
        QueryRequest(
            id="review:vacated-query",
            panel_id=axes.panel.id,
            coordinate=old_coordinate,
            coordinate_space=(
                QueryCoordinateSpace.PANEL if panel_query else QueryCoordinateSpace.DATA
            ),
            requested_payload=(QueryPayload.IDENTITY,),
        ),
    )
    print(f"Vacated point location: {vacated.status.value} (expected miss).", flush=True)
    if vacated.status.value != "miss":
        raise RuntimeError("retained query still found the vacated point")


def _animate_matplotlib(session: object, renderer: object, update: Callable[[], None]) -> None:
    """Own the timer until the native GUI loop returns, including failures."""
    timer = renderer.figure.canvas.new_timer(interval=80)
    timer.add_callback(update)
    timer.start()
    try:
        session.run()
    finally:
        timer.stop()


def _animate_datoviz(renderer: object, update: Callable[[], None]) -> None:
    """Return to Python between native frames and observe close before cleanup."""
    if not callable(getattr(renderer, "show", None)) or not callable(
        getattr(getattr(renderer, "dvz", None), "dvz_app_should_exit", None)
    ):
        raise RuntimeError("Datoviz animation requires bounded frames and exit queries")
    if renderer.app is None:
        renderer.show(frame_count=1)
    last_update = -math.inf
    while not renderer.dvz.dvz_app_should_exit(renderer.app):
        now = time.monotonic()
        if now - last_update >= 0.08:
            update()
            last_update = now
        renderer.show(frame_count=1)
        if os.environ.get("GSP_TEST") == "True":
            break


def _capture(renderer: object, backend: str) -> bytes:
    if backend == "datoviz":
        return renderer.capture_png_bytes()
    stream = io.BytesIO()
    renderer.figure.savefig(stream, format="png")
    return stream.getvalue()


def _check_capture(data: bytes) -> None:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        pixels = np.asarray(image.convert("RGB"))
        if image.width < 100 or image.height < 100 or np.ptp(pixels) < 20:
            raise RuntimeError("review capture is empty or unexpectedly small")


def _pick_evidence(figure: vp.Figure, session: object, renderer: object, backend: str) -> None:
    if (
        backend != "datoviz"
        or not isinstance(session, MeshPickSession)
        or not (session.capabilities.supports_extension("query.mesh.single.v1"))
    ):
        print(
            "UNSUPPORTED: native single-mesh picking requires Datoviz query.mesh.single.v1.",
            flush=True,
        )
        return
    snapshot = getattr(renderer, "layout_snapshot", None)
    if snapshot is None:
        snapshot = renderer.authoritative_layout_snapshot()
    panel = snapshot.only_panel()
    rect = panel.plot_rect_px
    allocation = panel.panel_rect_px
    # Native request coordinates are panel-local logical pixels.
    xy = (rect.x + rect.width / 2 - allocation.x, rect.y + rect.height / 2 - allocation.y)
    result = session.pick_mesh(
        View3DMeshTrianglePickRequest(
            figure.axes[0].view.id,
            xy,
            panel_id=figure.axes[0].panel.id,
        ),
        scene_id=figure.to_scene().id,
    )
    print(
        f"Native mesh pick at panel center {xy}: {result.status.value}; "
        f"visual={result.visual_id}; payload={result.extension_payload}",
        flush=True,
    )
    if result.diagnostic:
        print(f"Mesh pick diagnostic: {result.diagnostic}", flush=True)
    if not result.hit or result.visual_id != "review:pick-triangle":
        raise RuntimeError("native mesh pick did not find the center triangle")


def run(
    case: str, backend: str, *, headless: bool = False, capture_dir: Path | None = None
) -> None:
    if headless and backend == "matplotlib":
        import matplotlib

        matplotlib.use("Agg", force=True)
    figure = make_figure(case)
    if case == "textures" and backend == "matplotlib":
        print(
            "UNSUPPORTED: meshvisual_material_texture2d_unlit_unsupported: Matplotlib mesh "
            "texture sampling. Showing the source RGBA image as an explicit reference.",
            flush=True,
        )
        texture = figure.texture_resources()[0].image
        figure, axes = _axes("texture source image reference (mesh sampling unsupported)")
        axes.imshow(texture, extent=(-0.8, 0.8, -0.8, 0.8), origin="lower")
    configure_live_canvas(figure, 1.0 if headless else _review_device_scale())
    layout = None
    if case == "retained-updates":
        figure.axes[0].axis_guides.clear()
        figure.axes[0].panel_text_guides.clear()
    if case in {"retained-updates", "mesh-pick"}:
        with vp.open_session("matplotlib") as reference:
            layout = figure.resolve_layout(reference)
    required = {"scene.update.points.v1", "query.panel"} if case == "retained-updates" else set()
    with vp.open_session(backend, require=required) as session:
        if headless:
            with tempfile.TemporaryDirectory(prefix="vispy2-review-") as directory:
                target = Path(directory) / "initial.png"
                renderer = session.render(figure.to_scene(), target=target, layout_snapshot=layout)
                initial = target.read_bytes()
            _check_capture(initial)
            if capture_dir is not None:
                capture_dir.mkdir(parents=True, exist_ok=True)
                (capture_dir / f"{case}-{backend}.png").write_bytes(initial)
        else:
            renderer = figure.display(session, block=False, layout_snapshot=layout)
            if backend == "matplotlib":
                normalize_matplotlib_window(renderer)
                renderer.figure.canvas.draw()
            else:
                renderer.show(frame_count=1)
        for diagnostic in session.diagnostics:
            print(f"Backend diagnostic: {diagnostic}", flush=True)
        if case == "mesh-pick":
            _pick_evidence(figure, session, renderer, backend)
        print(f"REVIEW_READY {backend} {case}", flush=True)
        if case == "retained-updates":
            if not isinstance(session, PointUpdateSession):
                raise RuntimeError(
                    "backend advertised retained updates without its public interface"
                )
            if headless:
                native = (
                    renderer.figure.axes[0].collections[0]
                    if backend == "matplotlib"
                    else renderer.visuals[figure.axes[0].visuals[0].id]
                )
                _update(figure, session, 1.0)
                current = (
                    renderer.figure.axes[0].collections[0]
                    if backend == "matplotlib"
                    else renderer.visuals[figure.axes[0].visuals[0].id]
                )
                if current is not native or session.scene_revision(figure.to_scene().id) != 1:
                    raise RuntimeError(
                        "retained update recreated its resource or lost its revision"
                    )
                _query_evidence(figure, session, layout)
                changed = _capture(renderer, backend)
                _check_capture(changed)
                if capture_dir is not None:
                    (capture_dir / f"{case}-{backend}-updated.png").write_bytes(changed)
                if changed == initial:
                    raise RuntimeError("retained update did not change the capture")
            else:
                _update(figure, session, 1.0)
                _query_evidence(figure, session, layout)
                start = time.monotonic()

                def update() -> None:
                    _update(figure, session, (time.monotonic() - start) * 2)

                if backend == "matplotlib":
                    _animate_matplotlib(session, renderer, update)
                else:
                    _animate_datoviz(renderer, update)
        elif not headless:
            if backend == "datoviz":
                run_datoviz_until_close(renderer)
            else:
                session.run()
        if headless:
            print(
                f"HEADLESS_OK {backend} {case}: nonempty capture and semantic checks passed.",
                flush=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--backend", choices=BACKENDS, required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--capture-dir", type=Path)
    args = parser.parse_args()
    try:
        run(args.case, args.backend, headless=args.headless, capture_dir=args.capture_dir)
    except KeyboardInterrupt:
        print(f"{args.backend}: review window closed cleanly.", flush=True)


if __name__ == "__main__":
    main()
