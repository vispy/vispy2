"""Producer-owned linked limits and retained point replacement forwarding."""

from dataclasses import replace

import numpy as np
import pytest
from gsp import BackendCapabilityError
from gsp.protocol import PointVisual

import vispy2 as vp


def test_linked_dimensions_merge_transitively_keep_distinct_views() -> None:
    fig = vp.Figure()
    a, b, c = [fig.add_axes() for _ in range(3)]
    a.set_view2d(xlim=(10, 20), ylim=(30, 40))
    fig.link_axes(a, b, x=True, y=False)
    fig.link_axes(b, c, x=True, y=False)
    assert b.get_xlim() == c.get_xlim() == (10, 20)
    c.set_view2d(xlim=(5, -5), ylim=(9, 10))
    assert a.get_xlim() == b.get_xlim() == (5, -5)
    assert a.get_ylim() == (30, 40)
    assert b.get_ylim() == (-1, 1)
    assert len({view.id for view in fig.to_scene().views2d}) == 3
    assert len({id(axis.view) for axis in (a, b, c)}) == 3


def test_share_helpers_and_fit_propagation() -> None:
    fig = vp.Figure()
    a, b = fig.add_axes(), fig.add_axes()
    a.set_view2d(xlim=(10, 20), ylim=(30, 40))
    b.sharex(a)
    b.sharey(a)
    b.scatter([100, 200], [300, 400])
    b.fit_data(margin=1)
    assert a.get_xlim() == b.get_xlim() == (100, 200)
    assert a.get_ylim() == b.get_ylim() == (300, 400)
    fig.set_limits(a, xlim=(1, 2), ylim=(3, 4))
    assert b.get_xlim() == (1, 2)


def test_linked_limits_failure_does_not_partially_mutate() -> None:
    fig = vp.Figure()
    a, b = fig.add_axes(), fig.add_axes()
    fig.link_axes(a, b)
    before = (a.view, b.view)
    with pytest.raises(ValueError):
        a.set_view2d(xlim=(10, 20), ylim=(2, 2))
    assert (a.view, b.view) == before
    with pytest.raises(ValueError, match="distinct"):
        fig.link_axes(a, a)
    with pytest.raises(ValueError, match="belonging"):
        a.sharex(vp.subplots()[1])
    with pytest.raises(ValueError, match="2D"):
        fig.link_axes(a, fig.add_axes(projection="3d"))  # type: ignore[arg-type]


class UpdateSession:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[PointVisual, str | None]] = []
        self.fail = fail

    def update_point(self, visual: PointVisual, *, scene_id: str | None = None) -> int:
        self.calls.append((visual, scene_id))
        if self.fail:
            raise RuntimeError("renderer failed")
        return 7

    def scene_revision(self, scene_id: str | None = None) -> int:
        return 7


def test_point_update_forwards_stable_scene_id_and_replaces_after_success() -> None:
    fig, axes = vp.subplots()
    fig.id = "figure:updates"
    point = axes.scatter([0, 1], [2, 3])
    snapshot = fig.to_scene()
    updated = replace(point, positions=np.array([[4, 5], [6, 7]], dtype=np.float32))
    session = UpdateSession()
    assert fig.update_point(session, updated) == 7
    assert session.calls == [(updated, "scene:updates")]
    assert fig.to_scene().visuals[0] is updated
    assert snapshot.visuals[0] is point
    assert len(axes.attachments) == 1


def test_point_update_failure_and_invalid_topology_leave_producer_unchanged() -> None:
    fig, axes = vp.subplots()
    point = axes.scatter([0], [1])
    updated = replace(point, positions=np.array([[2, 3]], dtype=np.float32))
    with pytest.raises(RuntimeError, match="renderer failed"):
        fig.update_point(UpdateSession(fail=True), updated)
    assert axes.visuals == [point]
    session = UpdateSession()
    changed_count = replace(
        point,
        positions=np.array([[2, 3], [4, 5]], dtype=np.float32),
        sizes=3,
        colors=np.tile([0, 0, 0, 255], (2, 1)).astype(np.uint8),
    )
    with pytest.raises(ValueError, match="point count"):
        fig.update_point(session, changed_count)
    assert not session.calls
    with pytest.raises(BackendCapabilityError, match="scene.update.points.v1"):
        fig.update_point(object(), updated)  # type: ignore[arg-type]


def test_figure_point_update_executes_through_matplotlib_extension() -> None:
    pytest.importorskip("gsp_matplotlib")
    from gsp import PointUpdateSession

    fig, axes = vp.subplots()
    point = axes.scatter([0, 1], [1, 0])
    updated = replace(point, positions=np.array([[0.25, 0.5], [0.5, 0.25]], dtype=np.float32))
    with vp.open_session("matplotlib", require={"scene.update.points.v1"}) as session:
        assert isinstance(session, PointUpdateSession)
        session.render(fig.to_scene())
        assert fig.update_point(session, updated) == 1
        assert session.scene_revision("scene:main") == 1
    assert axes.visuals[0] is updated


@pytest.mark.parametrize(
    "method", ["scatter-shape", "scatter-size", "markers", "image", "colorbar"]
)
def test_invalid_scalar_visual_or_guide_does_not_register_color_scale(method: str) -> None:
    from gsp.protocol import ColorScale, ColorMapRef, ColorMapId, LinearNormalize

    fig, axes = vp.subplots()
    original = axes.color_scale(clim=(0, 1), id="scale:existing")
    with pytest.raises((TypeError, ValueError)):
        if method == "scatter-shape":
            axes.scatter([0, 1], [0, 1], c=[0], cmap="viridis", clim=(0, 1))
        elif method == "scatter-size":
            axes.scatter([0, 1], [0, 1], c=[0, 1], cmap="viridis", clim=(0, 1), size=[1])
        elif method == "markers":
            axes.markers([0], [0], color=[0], cmap="viridis", clim=(0, 1), shape="invalid")
        elif method == "image":
            axes.imshow(np.zeros((2, 2)), cmap="viridis", clim=(0, 1), origin="invalid")
        else:
            scale = ColorScale(
                id="scale:new",
                colormap=ColorMapRef(ColorMapId.VIRIDIS),
                normalize=LinearNormalize(vmin=0, vmax=1),
            )
            axes.colorbar(scale, ramp_width_px=-1)
    assert fig.color_scale_resources == [original]
    assert not axes.visuals and not axes.attachments and not axes.colorbar_guides


def test_scalar_updates_keep_bindings_and_own_values_after_success() -> None:
    pytest.importorskip("gsp_matplotlib")
    from gsp import PointUpdateSession

    fig, axes = vp.subplots()
    scale = axes.color_scale(clim=(0, 1), id="scale:points")
    point = axes.scatter([0, 1], [1, 0], c=[0, 1], color_scale=scale)
    original_snapshot = fig.to_scene()
    assert point.color_encoding is not None
    values = np.array([0.75, 0.25], dtype=np.float32)
    encoding = replace(point.color_encoding, values=values, alpha=0.5)
    updated = replace(point, color_encoding=encoding, sizes=20)
    with vp.open_session("matplotlib", require={"scene.update.points.v1"}) as session:
        assert isinstance(session, PointUpdateSession)
        session.render(original_snapshot)
        assert fig.update_point(session, updated) == 1
        values[:] = 99
        assert session.scene_revision("scene:main") == 1
        assert axes.visuals[0] is updated
        np.testing.assert_array_equal(updated.color_encoding.values, [0.75, 0.25])
        other = axes.color_scale(clim=(0, 1), id="scale:other")
        rebound = replace(updated, color_encoding=replace(encoding, color_scale_id=other.id))
        with pytest.raises(ValueError, match="scalar color binding"):
            fig.update_point(session, rebound)
        assert session.scene_revision("scene:main") == 1
        assert axes.visuals[0] is updated
    np.testing.assert_array_equal(original_snapshot.visuals[0].color_encoding.values, [0, 1])


def test_update_selects_figure_scene_not_sessions_latest_scene() -> None:
    pytest.importorskip("gsp_matplotlib")
    from gsp import PointUpdateSession
    from gsp.protocol import QueryCoordinateSpace, QueryRequest

    first, a = vp.subplots()
    second, b = vp.subplots()
    first.id, second.id = "figure:first", "figure:second"
    p = a.scatter([-0.5], [0], id="visual:common")
    b.scatter([-0.5], [0], id="visual:common")
    update = replace(p, positions=np.array([[0.5, 0]], dtype=np.float32))
    request = QueryRequest(
        id="query:point",
        panel_id=a.panel.id,
        coordinate=(0.5, 0),
        coordinate_space=QueryCoordinateSpace.DATA,
    )
    with vp.open_session(
        "matplotlib", require={"scene.update.points.v1", "query.panel"}
    ) as session:
        assert isinstance(session, PointUpdateSession)
        session.render(first.to_scene())
        session.render(second.to_scene())
        assert first.update_point(session, update) == 1
        assert session.scene_revision("scene:first") == 1
        assert session.scene_revision("scene:second") == 0
        assert first.query(session, request).hit
        assert not second.query(session, request).hit
    assert a.visuals[0] is update
    np.testing.assert_array_equal(b.visuals[0].positions, [[-0.5, 0]])
