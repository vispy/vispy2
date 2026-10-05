"""Review builders remain semantic; native loops preserve update/close ordering."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from gsp.protocol import CoordinateSpace, MeshShading


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "examples"))
    return importlib.import_module("review_live")


@pytest.mark.parametrize(
    "case",
    (
        "points-markers",
        "strokes",
        "primitives-pixels",
        "scientific-grid",
        "layout-links",
        "transforms",
        "textures",
        "retained-updates",
        "mesh-pick",
    ),
)
def test_builders_emit_attached_scenes(review, case):
    scene = review.make_figure(case).to_scene()
    assert scene.visuals
    assert {a.visual_id for a in scene.attachments} == {v.id for v in scene.visuals}
    if case == "scientific-grid":
        assert len(scene.panels) == 4
        assert all(g.grid_visible for g in scene.axis_guides)
    if case == "mesh-pick":
        assert len(scene.views3d) == 1


def test_transforms_and_texture_are_authored_not_baked(review):
    scene = review.make_figure("transforms").to_scene()
    meshes = scene.visuals[:2]
    assert [v.coordinate_space for v in meshes] == [CoordinateSpace.DATA, CoordinateSpace.NDC]
    assert all(v.transform.inline is not None for v in meshes)
    np.testing.assert_array_equal(meshes[0].positions, meshes[1].positions)
    scene = review.make_figure("textures").to_scene()
    mesh = scene.visuals[0]
    assert mesh.shading is MeshShading.TEXTURE2D_UNLIT
    assert mesh.texture2d_id == scene.textures[0].id
    assert mesh.uvs.shape == (4, 2)


def test_linked_limits_propagate_with_distinct_views(review):
    figure = review.make_figure("layout-links")
    a, b = figure.axes
    assert a.view.id != b.view.id
    a.set_xlim(-0.5, 0.5)
    assert b.get_xlim() == (-0.5, 0.5)


@pytest.mark.parametrize("failure", (None, KeyboardInterrupt, RuntimeError))
def test_matplotlib_timer_stops_before_session_unwinds(review, failure):
    events = []

    class Timer:
        def add_callback(self, callback):
            self.callback = callback

        def start(self):
            events.append("start")

        def stop(self):
            events.append("stop")

    timer = Timer()

    def run():
        events.append("run")
        timer.callback()
        if failure:
            raise failure()

    renderer = SimpleNamespace(
        figure=SimpleNamespace(
            canvas=SimpleNamespace(
                new_timer=lambda **kwargs: timer,
            )
        )
    )
    session = SimpleNamespace(run=run)
    if failure:
        with pytest.raises(failure):
            review._animate_matplotlib(session, renderer, lambda: events.append("update"))
    else:
        review._animate_matplotlib(session, renderer, lambda: events.append("update"))
    assert events == ["start", "run", "update", "stop"]


def test_datoviz_updates_inside_bounded_loop_and_checks_close(review, monkeypatch):
    monkeypatch.delenv("GSP_TEST", raising=False)
    events = []
    ticks = iter((0.0, 0.1, 0.2))
    monkeypatch.setattr(review.time, "monotonic", lambda: next(ticks))

    class Renderer:
        app = "app"
        frames = 0

        def show(self, *, frame_count):
            assert frame_count == 1
            events.append("frame")
            self.frames += 1

        def should_exit(self, app):
            assert app == "app"
            events.append("close-check")
            return self.frames == 3

    renderer = Renderer()
    renderer.dvz = SimpleNamespace(dvz_app_should_exit=renderer.should_exit)
    review._animate_datoviz(renderer, lambda: events.append("update"))
    assert events == ["close-check", "update", "frame"] * 3 + ["close-check"]


def test_datoviz_interrupt_returns_control_before_cleanup(review, monkeypatch):
    monkeypatch.delenv("GSP_TEST", raising=False)

    def show(**kwargs):
        raise KeyboardInterrupt()

    renderer = SimpleNamespace(
        app="app",
        show=show,
        dvz=SimpleNamespace(
            dvz_app_should_exit=lambda app: False,
        ),
    )
    with pytest.raises(KeyboardInterrupt):
        review._animate_datoviz(renderer, lambda: None)


@pytest.mark.parametrize(
    "case",
    (
        "points-markers",
        "strokes",
        "primitives-pixels",
        "scientific-grid",
        "layout-links",
        "transforms",
        "textures",
        "retained-updates",
        "mesh-pick",
    ),
)
def test_headless_matplotlib_captures_and_checks(review, case, tmp_path, capsys):
    review.run(case, "matplotlib", headless=True, capture_dir=tmp_path)
    output = capsys.readouterr().out
    assert f"HEADLESS_OK matplotlib {case}" in output
    assert (tmp_path / f"{case}-matplotlib.png").is_file()
    if case == "retained-updates":
        initial = (tmp_path / f"{case}-matplotlib.png").read_bytes()
        changed = (tmp_path / f"{case}-matplotlib-updated.png").read_bytes()
        assert initial != changed
        assert "revision=1" in output
        assert "expected miss" in output
    if case in {"textures", "mesh-pick"}:
        assert "UNSUPPORTED:" in output
