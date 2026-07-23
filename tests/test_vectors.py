from pathlib import Path
import runpy
from typing import Callable, cast

import numpy as np
import pytest

import vispy2 as vp
from gsp.protocol import (
    CoordinateSpace,
    VectorAnchor,
    VectorCap,
    VectorVisual,
)


def test_axes_vectors_emits_attached_2d_semantic_visual() -> None:
    figure, axes = vp.subplots()
    visual = axes.vectors(
        [0.0, 1.0],
        [1.0, 0.0],
        [2.0, 0.0],
        [0.0, -1.0],
        color=[[255, 0, 0, 255], [0, 0, 255, 128]],
        width=[2.0, 4.0],
        scale=0.5,
        anchor="center",
        start_cap="round",
        end_cap="triangle_out",
        id="vector:producer-2d",
    )

    assert isinstance(visual, VectorVisual)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.anchor is VectorAnchor.CENTER
    assert visual.start_cap is VectorCap.ROUND
    assert visual.end_cap is VectorCap.TRIANGLE_OUT
    np.testing.assert_array_equal(visual.width_values(), [2.0, 4.0])
    tails, heads = visual.endpoint_values()
    np.testing.assert_allclose(tails, [[-0.5, 1.0], [1.0, 0.25]])
    np.testing.assert_allclose(heads, [[0.5, 1.0], [1.0, -0.25]])
    scene = figure.to_scene()
    assert scene.visuals == (visual,)
    assert scene.attachments[0].visual_id == visual.id


def test_axes3d_vectors_and_camera_fit_include_resolved_endpoints() -> None:
    _, axes = vp.subplots(projection="3d")
    visual = axes.vectors(
        [-4.0, 2.0],
        [0.0, 0.0],
        [0.0, 0.0],
        [2.0, 4.0],
        [0.0, 0.0],
        [0.0, 0.0],
        scale=2.0,
        anchor="tail",
    )
    fitted = axes.fit_camera()

    assert visual.positions.shape == (2, 3)
    assert fitted.camera.target == pytest.approx((3.0, 0.0, 0.0))


def test_axes3d_quiver_emits_attached_vector_visual() -> None:
    figure, axes = vp.subplots(projection="3d")
    visual = axes.quiver(
        [0.0],
        [1.0],
        [2.0],
        [1.0],
        [0.0],
        [-1.0],
        scale=2.0,
        anchor="head",
        end_cap="round",
        id="vector:quiver-3d",
    )

    assert isinstance(visual, VectorVisual)
    assert visual.positions.shape == (1, 3)
    assert visual.anchor is VectorAnchor.HEAD
    tails, heads = visual.endpoint_values()
    np.testing.assert_allclose(tails, [[-2.0, 1.0, 4.0]])
    np.testing.assert_allclose(heads, [[0.0, 1.0, 2.0]])
    scene = figure.to_scene()
    assert scene.visuals == (visual,)
    assert scene.attachments[0].visual_id == visual.id
    assert scene.attachments[0].view_id == axes.view.id


def test_quiver_aliases_are_bounded_vector_conveniences() -> None:
    figure, axes = vp.subplots()
    method_visual = axes.quiver([0.0], [0.0], [1.0], [2.0])
    module_visual = vp.quiver([0.0], [0.0], [1.0], [2.0])
    direct_visual = vp.vectors([0.0], [0.0], [1.0], [2.0])

    assert isinstance(method_visual, VectorVisual)
    assert isinstance(module_visual, VectorVisual)
    assert isinstance(direct_visual, VectorVisual)
    assert figure.to_scene().visuals == (method_visual,)
    with pytest.raises(TypeError):
        vp.quiver([0.0], [0.0], [1.0], [2.0], angles="xy")


def test_vectors_reject_shape_zero_and_nonfinite_inputs() -> None:
    _, axes = vp.subplots()
    with pytest.raises(ValueError, match="same length"):
        axes.vectors([0.0], [0.0], [1.0, 2.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="nonzero"):
        axes.vectors([0.0], [0.0], [0.0], [0.0])
    with pytest.raises(ValueError, match="finite"):
        axes.vectors([0.0], [0.0], [np.nan], [1.0])
    with pytest.raises(ValueError, match="positive"):
        axes.vectors([0.0], [0.0], [1.0], [1.0], width=0.0)


def test_vector_file_output_example_rejects_unqualified_datoviz_capture(
    tmp_path: Path,
) -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "vectors_2d_3d.py"))
    render_backend = cast(
        Callable[[str, Path], tuple[Path, Path]],
        example["render_backend"],
    )
    output = tmp_path / "unqualified-datoviz"
    with pytest.raises(ValueError, match="Matplotlib file output only"):
        render_backend("datoviz", output)
    assert not output.exists()
