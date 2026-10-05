"""Semantic layout and explicitly requested fitting conveniences."""

import numpy as np
import pytest
from gsp.protocol import CanvasSize, NormalizedRenderTargetRect, VisualTransformBinding

import vispy2 as vp
from vispy2.protocol import Axes, Axes3D, Figure, affine2d


def test_protocol_facade_preserves_class_and_helper_identity() -> None:
    assert (Axes, Axes3D, Figure, affine2d) == (vp.Axes, vp.Axes3D, vp.Figure, vp.affine2d)


def test_subplot_grid_mixed_projections_and_row_major_layout() -> None:
    fig, grid = vp.subplots(2, 2, projection=[["2d", "3d"], ["3d", "2d"]])
    assert isinstance(grid, np.ndarray)
    assert grid.shape == (2, 2)
    assert tuple(type(axis) for axis in grid.flat) == (vp.Axes, vp.Axes3D, vp.Axes3D, vp.Axes)
    assert tuple(grid.flat) == tuple(fig.axes)
    assert [placement.allocation_rect for placement in fig.panel_layout().placements] == [
        NormalizedRenderTargetRect(col / 2, row / 2, 0.5, 0.5)
        for row in range(2)
        for col in range(2)
    ]
    assert len(fig.to_scene().panels) == 4


def test_subplot_squeezing_and_default_horizontal_allocations() -> None:
    assert isinstance(vp.subplots()[1], vp.Axes)
    assert isinstance(vp.subplots(projection="3d")[1], vp.Axes3D)
    _, grid = vp.subplots(1, 3)
    assert isinstance(grid, np.ndarray) and grid.shape == (3,)
    _, grid = vp.subplots(squeeze=False)
    assert isinstance(grid, np.ndarray) and grid.shape == (1, 1)
    fig = vp.Figure()
    fig.add_axes()
    fig.add_axes()
    assert [p.allocation_rect for p in fig.panel_layout().placements] == [
        NormalizedRenderTargetRect(0, 0, 0.5, 1),
        NormalizedRenderTargetRect(0.5, 0, 0.5, 1),
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"nrows": 0},
        {"ncols": -1},
        {"nrows": True},
        {"projection": "bad"},
        {"projection": [["2d", "3d"]]},
    ],
)
def test_subplot_invalid_configuration(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        vp.subplots(**kwargs)  # type: ignore[arg-type]


def test_custom_allocation_and_foreign_axes_rejection() -> None:
    fig = vp.Figure()
    rect = NormalizedRenderTargetRect(0.1, 0.2, 0.7, 0.6)
    axes = fig.add_axes(allocation=rect)
    assert fig.to_scene().panel_layout.placements[0].allocation_rect == rect
    assert fig.set_panel_allocation(axes, rect) is rect
    with pytest.raises(ValueError, match="belong"):
        fig.set_panel_allocation(vp.subplots()[1], rect)


def test_fit_data_transforms_segments_vectors_and_ignores_ndc() -> None:
    _, axes = vp.subplots()
    axes.scatter([[0, 0], [2, 1]], transform=[[2, 0, 10], [0, 3, -5], [0, 0, 1]])
    axes.segments([[0, 0]], [[-2, 3]])
    axes.vectors([1], [1], [3], [4])
    axes.mesh(
        [[1000, 1000], [1001, 1000], [1000, 1001]],
        [[0, 1, 2]],
        color=[0, 0, 0, 255],
        coordinate_space="ndc",
    )
    axes.set_ylim(1, -1)
    view = axes.fit_data(margin=1)
    assert view.x_range == (-2, 14)
    assert view.y_range == (5, -5)
    axes.scatter([50], [20])
    assert axes.get_xlim() == (-2, 14)
    axes.autoscale(margin=1)
    assert axes.get_xlim() == (-2, 50)


def test_fit_image_extent_and_degenerate_points() -> None:
    _, axes = vp.subplots()
    axes.imshow(np.zeros((2, 3)), extent=(-3, 5, -7, 9))
    assert axes.fit_data(margin=1).x_range == (-3, 5)
    assert axes.get_ylim() == (-7, 9)
    _, axes = vp.subplots()
    axes.scatter([2], [3])
    axes.fit_data()
    assert axes.get_xlim()[0] < 2 < axes.get_xlim()[1]
    assert axes.get_ylim()[0] < 3 < axes.get_ylim()[1]


@pytest.mark.parametrize("margin", [0.9, float("nan"), float("inf")])
def test_fit_invalid_margin_is_atomic(margin: float) -> None:
    _, axes = vp.subplots()
    axes.scatter([0], [0])
    before = axes.view
    with pytest.raises(ValueError, match="margin"):
        axes.fit_data(margin=margin)
    assert axes.view is before


def test_fit_missing_data_or_unresolved_transform_is_explicit() -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError, match="non-empty DATA"):
        axes.fit_data()
    axes.scatter([0], [0], transform=VisualTransformBinding.from_ref("transform:missing"))
    with pytest.raises(ValueError, match="referenced"):
        axes.fit_data()


def test_producer_arrays_are_owned_by_semantic_snapshot() -> None:
    fig, axes = vp.subplots()
    positions = np.array([[1, 2], [3, 4]], dtype=np.float32)
    transform = np.eye(3)
    visual = axes.scatter(positions, transform=transform)
    scene = fig.to_scene()
    positions[:] = 99
    transform[0, 2] = 99
    np.testing.assert_array_equal(scene.visuals[0].positions, [[1, 2], [3, 4]])
    assert visual.transform is not None and visual.transform.inline is not None
    np.testing.assert_array_equal(visual.transform.inline.matrix, np.eye(3))
    with pytest.raises(ValueError):
        scene.visuals[0].positions.setflags(write=True)


def test_grid_and_fit_render_with_matplotlib() -> None:
    pytest.importorskip("gsp_matplotlib")
    fig, grid = vp.subplots(2, 2, canvas_size=CanvasSize.pixel_exact(640, 480))
    assert isinstance(grid, np.ndarray)
    for index, axes in enumerate(grid.flat):
        axes.plot([10, 20], [index, index + 1])
        axes.fit_data()
    with vp.open_session("matplotlib", require={"visual.paths"}) as session:
        layout = fig.resolve_layout(session)
    assert len(layout.panels) == 4
    first, second, third, _ = layout.panels
    assert first.panel_rect_px.x < second.panel_rect_px.x
    assert first.panel_rect_px.y < third.panel_rect_px.y


@pytest.mark.parametrize("count", [9, 12, 20, 93])
def test_horizontal_strip_boundaries_do_not_overlap_due_to_rounding(count: int) -> None:
    fig = vp.Figure()
    for _ in range(count):
        fig.add_axes()
    placements = fig.to_scene().panel_layout.placements
    for left, right in zip(placements, placements[1:]):
        assert left.allocation_rect.left + left.allocation_rect.width == right.allocation_rect.left
    assert placements[-1].allocation_rect.left + placements[-1].allocation_rect.width == 1


def test_explicit_grid_does_not_construct_unused_default_rectangles() -> None:
    fig, grid = vp.subplots(1, 93)
    assert isinstance(grid, np.ndarray) and grid.shape == (93,)
    assert len(fig.to_scene().panel_layout.placements) == 93


def test_invalid_add_axes_and_allocations_do_not_change_figure() -> None:
    fig, axes = vp.subplots()
    original = fig.to_scene()
    with pytest.raises(ValueError):
        fig.add_axes(projection="invalid")  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        fig.add_axes(allocation=(0, 0, 1, 1))  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        fig.set_panel_allocation(axes, (0, 0, 1, 1))  # type: ignore[arg-type]
    assert fig.to_scene() == original


@pytest.mark.parametrize("xlim,ylim", [((float("nan"), 1), (0, 1)), ((0, 1), (0, float("inf")))])
def test_nonfinite_linked_fit_and_limits_are_atomic(
    xlim: tuple[float, float], ylim: tuple[float, float]
) -> None:
    fig = vp.Figure()
    a, b = fig.add_axes(), fig.add_axes()
    fig.link_axes(a, b)
    before = (a.view, b.view)
    with pytest.raises(ValueError):
        fig.set_limits(a, xlim=xlim, ylim=ylim)
    assert (a.view, b.view) == before


def test_fit_overflow_keeps_all_linked_limits_unchanged() -> None:
    fig = vp.Figure()
    a, b = fig.add_axes(), fig.add_axes()
    fig.link_axes(a, b)
    a.scatter([-2, 2], [-2, 2])
    before = (a.view, b.view)
    with pytest.raises(ValueError):
        a.fit_data(margin=np.finfo(np.float64).max)
    assert (a.view, b.view) == before
