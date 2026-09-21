from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, call

import pytest
from gsp.protocol import CanvasSizePolicy

import vispy2 as vp


def _load_example() -> ModuleType:
    examples = Path(__file__).parents[1] / "examples"
    sys.path.insert(0, str(examples))
    try:
        spec = importlib.util.spec_from_file_location(
            "manual_live_compare",
            examples / "manual_live_compare.py",
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(examples))


@pytest.mark.parametrize(
    "case",
    (
        "priority-2d",
        "scalar-image",
        "perspective-3d",
        "orthographic-3d",
        "flat-lambert",
        "mixed-panels",
        "camera-fit",
        "camera-orbit",
        "camera-pan",
        "camera-zoom",
        "camera-reset",
    ),
)
def test_manual_live_comparison_cases_build_backend_neutral_figures(case: str) -> None:
    module = _load_example()

    figure = module.make_figure(case)

    assert isinstance(figure, vp.Figure)
    assert figure.to_scene().visuals


def test_manual_live_comparison_rejects_unknown_case() -> None:
    module = _load_example()

    with pytest.raises(ValueError, match="unknown comparison case"):
        module.make_figure("unknown")


def test_scalar_image_case_keeps_data_extent_colorbar_and_registration_points() -> None:
    module = _load_example()

    scene = module.make_figure("scalar-image").to_scene()

    image = next(visual for visual in scene.visuals if visual.id == "review:scalar-image")
    assert image.coordinate_space.value == "data"
    assert image.extent == (-3.0, 3.0, -2.0, 2.0)
    assert image.origin.value == "lower"
    assert image.color_scale_id == "review:viridis"
    assert scene.colorbar_guides[0].linked_visual_ids == (image.id,)
    assert any(visual.id == "review:image-registration" for visual in scene.visuals)


def test_mixed_panel_case_preserves_explicit_panel_routing() -> None:
    module = _load_example()

    scene = module.make_figure("mixed-panels").to_scene()

    assert "mixed-panels" in module.CASES
    assert tuple(panel.id for panel in scene.panels) == ("panel:1", "panel:2")
    assert tuple((view.panel_id, view.id) for view in (*scene.views2d, *scene.views3d)) == (
        ("panel:1", "view:1"),
        ("panel:2", "view:2"),
    )
    assert tuple(attachment.panel_id for attachment in scene.attachments) == (
        "panel:1",
        "panel:2",
    )
    assert tuple(
        placement.allocation_rect.width for placement in scene.panel_layout.placements
    ) == (
        0.5,
        0.5,
    )


def test_mixed_panel_case_does_not_use_single_panel_shared_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_example()
    resolve_shared_layout = Mock(side_effect=AssertionError("must not resolve mixed panels"))
    monkeypatch.setattr(module, "resolve_shared_layout", resolve_shared_layout)

    assert module._comparison_layout(module.make_figure("mixed-panels")) is None

    resolve_shared_layout.assert_not_called()


def test_single_panel_3d_case_still_uses_shared_reference_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_example()
    expected = object()
    resolve_shared_layout = Mock(return_value=expected)
    monkeypatch.setattr(module, "resolve_shared_layout", resolve_shared_layout)
    figure = module.make_figure("perspective-3d")

    assert module._comparison_layout(figure) is expected

    resolve_shared_layout.assert_called_once_with(figure)


def test_bounded_datoviz_loop_stops_before_native_reap(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_example()
    monkeypatch.delenv("GSP_TEST", raising=False)
    renderer = Mock()
    renderer.app = object()
    renderer.dvz.dvz_app_should_exit.side_effect = (False, False, True)

    module.run_datoviz_until_close(renderer)

    assert renderer.show.call_args_list == [
        call(frame_count=1),
        call(frame_count=1),
    ]


def test_live_canvas_uses_shared_host_logical_size_and_device_scale() -> None:
    module = _load_example()
    figure = module.make_figure("priority-2d")

    module.configure_live_canvas(figure, 2.0)

    assert figure.canvas_size is not None
    assert figure.canvas_size.policy is CanvasSizePolicy.HOST_LOGICAL_PX
    assert figure.canvas_size.width == 800
    assert figure.canvas_size.height == 600
    assert figure.canvas_size.requested_device_scale == 2.0


@pytest.mark.parametrize("device_scale", (0.0, -1.0, float("nan")))
def test_live_canvas_rejects_invalid_device_scale(device_scale: float) -> None:
    module = _load_example()

    with pytest.raises(ValueError, match="positive and finite"):
        module.configure_live_canvas(module.make_figure("priority-2d"), device_scale)


def test_matplotlib_window_normalization_removes_gui_chrome() -> None:
    module = _load_example()
    renderer = Mock()
    renderer.figure.canvas.device_pixel_ratio = 2.0
    renderer.figure.canvas.get_width_height.side_effect = (
        (800, 636),
        (800, 600),
    )

    module.normalize_matplotlib_window(renderer)

    renderer.figure.canvas.manager.resize.assert_called_once_with(1600, 1128)
    renderer.figure.canvas.flush_events.assert_called_once_with()
    renderer.figure.canvas.draw.assert_called_once_with()
