"""Numerical and geometry contracts for bounded scientific conveniences."""

import numpy as np
import pytest
from gsp.protocol import CoordinateSpace, PrimitiveTopology

import vispy2 as vp


def _triangle_area(vertices: np.ndarray) -> float:  # type: ignore[type-arg]
    triangles = vertices.reshape(-1, 3, 2).astype(np.float64)
    sides = triangles[:, 1:] - triangles[:, :1]
    return float(
        np.sum(np.abs(sides[:, 0, 0] * sides[:, 1, 1] - sides[:, 0, 1] * sides[:, 1, 0])) / 2
    )


def test_bar_geometry_negative_heights_widths_and_per_bar_colors() -> None:
    fig, axes = vp.subplots()
    visual = axes.bar(
        [2, 5],
        [3, -2],
        width=[1, 2],
        bottom=[1, 4],
        color=[[255, 0, 0, 255], [0, 0, 255, 255]],
        id="visual:bars",
    )
    assert visual.topology is PrimitiveTopology.TRIANGLE_LIST
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.positions.shape == (12, 2)
    np.testing.assert_array_equal(
        visual.positions[:6], [[1.5, 1], [2.5, 1], [2.5, 4], [1.5, 1], [2.5, 4], [1.5, 4]]
    )
    np.testing.assert_array_equal(visual.positions[6:8], [[4, 4], [6, 4]])
    np.testing.assert_array_equal(visual.colors[:6], np.tile([255, 0, 0, 255], (6, 1)))
    assert _triangle_area(visual.positions) == 7
    assert fig.to_scene().visuals == (visual,)


@pytest.mark.parametrize(
    "kwargs", [{"width": 0}, {"width": [-1, 2]}, {"height": [1]}, {"bottom": float("nan")}]
)
def test_bar_rejects_invalid_geometry_before_append(kwargs: dict[str, object]) -> None:
    _, axes = vp.subplots()
    arguments: dict[str, object] = {"height": [1, 2], **kwargs}
    with pytest.raises(ValueError):
        axes.bar([0, 1], **arguments)  # type: ignore[arg-type]
    assert not axes.visuals


@pytest.mark.parametrize(
    "density,cumulative", [(False, False), (True, False), (False, True), (True, True)]
)
def test_histogram_nonuniform_edges_weighted_statistics(density: bool, cumulative: bool) -> None:
    _, axes = vp.subplots()
    samples = [0.2, 0.8, 1.5, 2.2, 3.0]
    weights = [1, 2, 3, 4, 5]
    values, edges, visual = axes.hist(
        samples, bins=[0, 1, 3, 5], weights=weights, density=density, cumulative=cumulative
    )
    expected = np.asarray([3, 7, 5], dtype=float)
    if cumulative:
        expected = expected.cumsum()
        if density:
            expected /= 15
    elif density:
        expected /= 15 * np.diff(edges)
    np.testing.assert_allclose(values, expected)
    np.testing.assert_array_equal(edges, [0, 1, 3, 5])
    assert visual.positions.shape == (18, 2)
    if density and not cumulative:
        assert np.sum(values * np.diff(edges)) == pytest.approx(1)
        assert _triangle_area(visual.positions) == pytest.approx(1)


def test_histogram_integer_bins_range_and_zero_count_bins() -> None:
    _, axes = vp.subplots()
    counts, edges, visual = axes.hist([0.2, 0.4, 1.2, 4], bins=3, range=(0, 3))
    np.testing.assert_array_equal(counts, [2, 1, 0])
    np.testing.assert_array_equal(edges, [0, 1, 2, 3])
    assert len(visual.positions) == 18


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bins": 0},
        {"bins": [0, 1, 1]},
        {"weights": [1]},
        {"range": (1, 0)},
        {"density": True, "weights": [0, 0]},
    ],
)
def test_histogram_rejects_ambiguous_statistics(kwargs: dict[str, object]) -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError):
        axes.hist([0.2, 0.8], **kwargs)  # type: ignore[arg-type]
    assert not axes.visuals


@pytest.mark.parametrize("reverse", [False, True])
def test_fill_between_trapezoids_have_expected_area(reverse: bool) -> None:
    _, axes = vp.subplots()
    x, y = np.array([0, 1, 3]), np.array([1, 2, 4])
    if reverse:
        x, y = x[::-1], y[::-1]
    visual = axes.fill_between(x, y, 0)
    assert _triangle_area(visual.positions) == pytest.approx(7.5)
    assert visual.positions.shape == (12, 2)


@pytest.mark.parametrize(
    "x,y1,y2",
    [
        ([0, 0], [1, 2], 0),
        ([0, 2, 1], [1, 2, 3], 0),
        ([0, 1], [1, -1], 0),
        ([0, 1], [1, float("nan")], 0),
        ([0], [1], 0),
    ],
)
def test_fill_between_rejects_crossings_and_nonmonotonic_data(
    x: list[float], y1: list[float], y2: float
) -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError):
        axes.fill_between(x, y1, y2)
    assert not axes.visuals


def test_lines_and_spans_capture_current_ranges() -> None:
    _, axes = vp.subplots()
    axes.set_view2d(xlim=(10, 20), ylim=(-3, 7))
    horizontal = axes.axhline(2)
    vertical = axes.axvline(12)
    hspan = axes.axhspan(1, 3)
    vspan = axes.axvspan(12, 15)
    np.testing.assert_array_equal(horizontal.start_positions, [[10, 2]])
    np.testing.assert_array_equal(horizontal.end_positions, [[20, 2]])
    np.testing.assert_array_equal(vertical.start_positions, [[12, -3]])
    np.testing.assert_array_equal(vertical.end_positions, [[12, 7]])
    assert _triangle_area(hspan.positions) == 20
    assert _triangle_area(vspan.positions) == 30
    axes.set_xlim(0, 100)
    np.testing.assert_array_equal(horizontal.end_positions, [[20, 2]])


def test_scientific_visuals_render_through_matplotlib() -> None:
    pytest.importorskip("gsp_matplotlib")
    fig, axes = vp.subplots()
    axes.hist([1, 2, 2, 3], bins=[0, 1, 2, 3, 4], color=[120, 160, 220, 255])
    axes.fill_between([0, 2, 4], [1, 2, 1], color=[220, 120, 80, 128])
    axes.axhline(1)
    axes.fit_data()
    with vp.open_session("matplotlib", require={"visual.primitive", "visual.segments"}) as session:
        snapshot = fig.resolve_layout(session)
    assert len(snapshot.panels) == 1


def test_fill_between_equal_endpoints_omits_zero_area_triangles() -> None:
    _, axes = vp.subplots()
    visual = axes.fill_between([0, 1, 2], [0, 1, 0], 0)
    assert visual.positions.shape == (6, 2)
    assert _triangle_area(visual.positions) == 1
    before = len(axes.visuals)
    with pytest.raises(ValueError, match="non-zero area"):
        axes.fill_between([0, 1], [2, 2], [2, 2])
    assert len(axes.visuals) == before
