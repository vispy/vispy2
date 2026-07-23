from __future__ import annotations

import inspect
from pathlib import Path
import runpy
from typing import Callable, cast

import numpy as np
import pytest

import vispy2 as vp
from gsp.protocol import CoordinateSpace, PrimitiveTopology, PrimitiveVisual


@pytest.mark.parametrize(
    ("topology", "positions"),
    [
        ("point_list", [[0.0, 0.0]]),
        ("line_list", [[0.0, 0.0], [1.0, 1.0]]),
        ("line_strip", [[0.0, 0.0], [1.0, 1.0]]),
        ("triangle_list", [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
        ("triangle_strip", [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]),
    ],
)
def test_axes_primitives_emits_every_attached_2d_topology(
    topology: str, positions: list[list[float]]
) -> None:
    figure, axes = vp.subplots()
    visual = axes.primitives(
        positions,
        topology=topology,
        color=np.tile([255, 0, 0, 255], (len(positions), 1)),
        indices=np.arange(len(positions), dtype=np.uint16),
        id=f"primitive:{topology}",
    )
    assert isinstance(visual, PrimitiveVisual)
    assert visual.topology is PrimitiveTopology(topology)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert figure.to_scene().visuals == (visual,)
    assert figure.to_scene().attachments[0].view_id == axes.view.id


def test_axes3d_primitives_and_camera_fit_include_geometry_bounds() -> None:
    figure, axes = vp.subplots(projection="3d")
    visual = axes.primitives(
        [[-4.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 3.0, 1.0]],
        topology="triangle_list",
        color=[
            [255, 0, 0, 255],
            [0, 255, 0, 255],
            [0, 0, 255, 255],
        ],
    )
    fitted = axes.fit_camera()
    assert visual.positions.shape == (3, 3)
    assert fitted.camera.target == pytest.approx((-1.0, 1.5, 0.5))
    assert figure.to_scene().view3d is fitted


def test_module_primitives_is_bounded_2d_convenience() -> None:
    visual = vp.primitives(
        [[0.0, 0.0], [1.0, 1.0]],
        topology="line_list",
        color=[255, 255, 255, 255],
    )
    assert isinstance(visual, PrimitiveVisual)


def test_primitive_producers_reject_dimensions_topology_indices_and_colors() -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError, match=r"shape \(N, 2\)"):
        axes.primitives([[0.0, 0.0, 0.0]], topology="point_list")
    with pytest.raises(ValueError, match="unsupported primitive topology"):
        axes.primitives([[0.0, 0.0]], topology="triangle_fan")
    with pytest.raises(TypeError, match="noninteger_index"):
        axes.primitives(
            [[0.0, 0.0], [1.0, 1.0]],
            topology="line_list",
            indices=[0.0, 1.0],
        )
    with pytest.raises(ValueError, match="color"):
        axes.primitives(
            [[0.0, 0.0], [1.0, 1.0]],
            topology="line_list",
            color=[[255, 0, 0, 255]],
        )


@pytest.mark.parametrize(
    "positions",
    [
        np.array([[True, False]], dtype=np.bool_),
        np.array([[1.0 + 2.0j, 3.0 + 0.0j]], dtype=np.complex64),
        np.array([[1.0, 2.0]], dtype=object),
    ],
)
def test_primitive_positions_reject_non_real_numeric_dtypes(
    positions: np.ndarray,
) -> None:
    _, axes = vp.subplots()
    with pytest.raises(TypeError, match="real integer or floating dtype"):
        axes.primitives(positions, topology="point_list")


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
def test_primitive_positions_reject_nonfinite_values_before_cast(invalid: float) -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError, match="positions must be finite"):
        axes.primitives([[invalid, 0.0]], topology="point_list")


def test_primitive_positions_reject_float32_overflow_and_accept_real_integers() -> None:
    _, axes = vp.subplots()
    overflow = np.array([[float(np.finfo(np.float32).max) * 2.0, 0.0]])
    with pytest.raises(ValueError, match="representable as float32"):
        axes.primitives(overflow, topology="point_list")

    visual = axes.primitives(
        np.array([[1, -2], [3, 4]], dtype=np.int64),
        topology="line_list",
    )
    assert visual.positions.dtype == np.dtype(np.float32)
    np.testing.assert_array_equal(visual.positions, [[1.0, -2.0], [3.0, 4.0]])


def test_primitive_public_signatures_have_no_raw_gpu_keywords() -> None:
    forbidden = {
        "shader",
        "pipeline",
        "slot",
        "material",
        "depth",
        "culling",
        "instance",
        "native_handle",
    }
    primitive_producers = (vp.primitives, vp.Axes.primitives, vp.Axes3D.primitives)
    for callable_ in primitive_producers:
        assert forbidden.isdisjoint(inspect.signature(callable_).parameters)


def test_primitive_topology_gallery_file_output_is_matplotlib_only(
    tmp_path: Path,
) -> None:
    example = runpy.run_path(
        str(Path(__file__).parents[1] / "examples" / "primitive_topologies.py")
    )
    render_backend = cast(
        Callable[[str, Path], Path],
        example["render_backend"],
    )
    output = tmp_path / "unqualified-datoviz"
    with pytest.raises(ValueError, match="Matplotlib file output only"):
        render_backend("datoviz", output)
    assert not output.exists()
