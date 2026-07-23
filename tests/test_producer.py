from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

import gsp
from gsp import BackendUnavailable
from gsp.backends import BackendSession
from gsp.protocol import (
    AxisDimension,
    CoordinateSpace,
    ImageVisual,
    MarkerVisual,
    MeshShading,
    MeshUVMode,
    MeshVisual,
    PathVisual,
    PointVisual,
    SegmentVisual,
    TextVisual,
    TextureFilter,
    TickSpecKind,
)
import vispy2 as vp
import vispy2.session as session_module


def test_subplots_emits_backend_neutral_scene_records() -> None:
    figure, axes = vp.subplots()
    axes.set_xlim(-2.0, 2.0)
    axes.set_ylim(-1.0, 1.0)
    axes.set_xlabel("x")
    axes.set_ylabel("y")
    axes.set_title("scene")
    axes.set_xticks([-2.0, 0.0, 2.0], labels=["left", "zero", "right"])
    axes.grid(True)
    point = axes.scatter([0.0], [0.5], color=[255, 0, 0, 255], id="visual:point")

    scene = figure.to_scene()

    assert isinstance(scene, gsp.Scene)
    assert scene.id == "scene:main"
    assert scene.visuals == (point,)
    assert scene.panels == figure.panels()
    assert scene.attachments == figure.attachments()
    assert scene.view2d is figure.views()[0]
    assert scene.view2d.x_range == (-2.0, 2.0)
    assert len(scene.axis_guides) == 2
    assert scene.axis_guides[0].dimension is AxisDimension.X
    assert scene.axis_guides[0].tick_spec.kind is TickSpecKind.EXPLICIT
    assert scene.panel_text_guides[0].text == "scene"


def test_visual_methods_cover_current_protocol_families() -> None:
    figure, axes = vp.subplots()
    visuals = (
        axes.scatter([0.0], [0.0]),
        axes.markers([0.0], [0.0], shape="square"),
        axes.segments([[0.0, 0.0]], [[1.0, 1.0]]),
        axes.path([[0.0, 0.0], [1.0, 1.0]]),
        axes.imshow(np.zeros((2, 2, 4), dtype=np.uint8)),
        axes.text([0.0], [0.0], "label"),
        axes.mesh(
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
            [[0, 1, 2]],
            color=[255, 255, 255, 255],
        ),
    )
    assert tuple(type(item) for item in visuals) == (
        PointVisual,
        MarkerVisual,
        SegmentVisual,
        PathVisual,
        ImageVisual,
        TextVisual,
        MeshVisual,
    )
    assert figure.to_scene().visuals == visuals


def test_affine_helper_and_visual_convenience_emit_protocol_state() -> None:
    _, axes = vp.subplots()
    matrix = np.array([[1.0, 0.0, 2.0], [0.0, 1.0, -1.0], [0.0, 0.0, 1.0]])
    binding = vp.affine2d(matrix)
    visual = axes.scatter([0.0], [0.0], transform=binding)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.transform is binding
    assert binding.inline is not None
    np.testing.assert_allclose(binding.inline.matrix, matrix)


@pytest.mark.parametrize("filter_mode", ["nearest", "linear"])
def test_textured_mesh_emits_texture_resource_and_filter(filter_mode: str) -> None:
    figure, axes = vp.subplots()
    visual = axes.mesh(
        [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0]],
        [[0, 1, 2], [0, 2, 3]],
        color=[255, 255, 255, 255],
        coordinate_space="ndc",
        texture=np.zeros((2, 2, 4), dtype=np.uint8),
        uvs=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        texture_filter=filter_mode,
    )
    scene = figure.to_scene()
    assert visual.shading is MeshShading.TEXTURE2D_UNLIT
    assert visual.uv_mode is MeshUVMode.VERTEX
    assert visual.texture_filter is TextureFilter(filter_mode)
    assert scene.textures[0].id == visual.texture2d_id


def test_scalar_color_and_colorbar_resources_are_preserved() -> None:
    figure, axes = vp.subplots()
    scale = axes.color_scale(cmap="viridis", clim=(0.0, 1.0), id="scale:main")
    visual = axes.imshow(
        np.array([[0.0, 1.0]], dtype=np.float32),
        color_scale=scale,
        id="visual:image",
    )
    guide = axes.colorbar(scale, label="value", linked_visual_ids=[visual.id])
    scene = figure.to_scene()
    assert scene.color_scales == (scale,)
    assert scene.colorbar_guides == (guide,)
    assert visual.color_scale_id == scale.id


def test_to_scene_rejects_currently_unsupported_multi_axes_layout() -> None:
    figure = vp.Figure()
    figure.add_axes()
    figure.add_axes()
    with pytest.raises(ValueError, match="exactly one"):
        figure.to_scene()


class FakeSession:
    backend_name = "fake"

    def __init__(self) -> None:
        self.scenes: list[gsp.Scene] = []

    def display(self, scene: gsp.Scene, **kwargs: Any) -> tuple[gsp.Scene, dict[str, Any]]:
        self.scenes.append(scene)
        return scene, kwargs


def test_display_uses_caller_owned_session_without_retaining_it() -> None:
    figure, axes = vp.subplots()
    axes.scatter([0.0], [0.0])
    session = FakeSession()
    scene, options = figure.display(cast(BackendSession, session), block=False)
    assert scene is session.scenes[0]
    assert options == {"block": False}
    assert all(getattr(figure, item.name) is not session for item in fields(figure))
    assert all(getattr(axes, item.name) is not session for item in fields(axes))


def test_nonblocking_show_requires_explicit_session() -> None:
    figure, _ = vp.subplots()
    with pytest.raises(ValueError, match="explicit caller-owned session"):
        figure.show(block=False)


def test_savefig_reports_actionable_missing_extra(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise BackendUnavailable("backend 'matplotlib' is not installed")

    monkeypatch.setattr(session_module, "_open_session", unavailable)
    figure, _ = vp.subplots()
    with pytest.raises(RuntimeError, match=r"install vispy2\[matplotlib\]"):
        figure.savefig(tmp_path / "figure.png")
