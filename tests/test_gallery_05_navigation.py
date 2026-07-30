from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
from gsp.protocol import (
    DirectionalLight3D,
    MeshNormalGeneration,
    MeshNormalMode,
    MeshShading,
)


def _gallery_module() -> ModuleType:
    path = Path(__file__).parents[1] / "examples" / "gallery_05_datoviz_navigation.py"
    spec = importlib.util.spec_from_file_location("gallery_05_datoviz_navigation", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeDatoviz:
    def __init__(self, renderer: "_FakeRenderer") -> None:
        self._renderer = renderer

    def dvz_app_should_exit(self, app: object) -> bool:
        assert app == "app"
        return self._renderer.frames >= 3


class _FakeRenderer:
    app = "app"

    def __init__(self, *, interrupt_at: int | None = None) -> None:
        self.frames = 0
        self.interrupt_at = interrupt_at
        self.dvz = _FakeDatoviz(self)

    def show(self, *, frame_count: int) -> None:
        assert frame_count == 1
        self.frames += 1
        if self.frames == self.interrupt_at:
            raise KeyboardInterrupt


def test_live_gallery_pumps_bounded_frames_until_datoviz_exit() -> None:
    module = _gallery_module()
    renderer = _FakeRenderer()

    module._run_interactive_frames(renderer)

    assert renderer.frames == 3


def test_live_gallery_returns_to_python_for_keyboard_interrupt() -> None:
    module = _gallery_module()
    renderer = _FakeRenderer(interrupt_at=2)

    with pytest.raises(KeyboardInterrupt):
        module._run_interactive_frames(renderer)

    assert renderer.frames == 2


def test_live_gallery_rejects_renderer_without_exit_query() -> None:
    module = _gallery_module()
    renderer: Any = object()

    with pytest.raises(RuntimeError, match="dvz_app_should_exit"):
        module._run_interactive_frames(renderer)


def test_live_gallery_emits_strict_flat_lambert_scene() -> None:
    module = _gallery_module()

    scene = module.make_figure().to_scene()

    assert len(scene.visuals) == 1
    mesh = scene.visuals[0]
    assert mesh.shading is MeshShading.FLAT_LAMBERT
    assert mesh.normal_mode is MeshNormalMode.FACE
    assert mesh.normal_generation is MeshNormalGeneration.FACE_FLAT
    assert mesh.normals is None
    assert scene.view3d is not None
    assert scene.view3d.ambient_light_intensity == 0.18
    assert scene.view3d.directional_light == DirectionalLight3D(
        direction_to_light=(-1.0, -1.0, -1.0),
        intensity=0.82,
    )
    assert scene.view3d.revision == 3


def test_live_gallery_matplotlib_raster_has_two_large_face_tones(
    tmp_path: Path,
) -> None:
    pytest.importorskip("gsp_matplotlib")
    image_reader: Any = pytest.importorskip("matplotlib.image")
    module = _gallery_module()
    target = tmp_path / "gallery-05-lit.png"

    with module.vp.open_session(
        "matplotlib", require={"output.file", "visual.mesh"}
    ) as session:
        session.render(module.make_figure().to_scene(), target=target)

    pixels = np.rint(image_reader.imread(target)[..., :3] * 255.0).astype(np.uint8)
    flat_pixels = pixels.reshape(-1, 3)
    counts: dict[tuple[int, int, int], int] = {}
    for color in ((65, 120, 203), (13, 23, 40)):
        delta = np.abs(flat_pixels.astype(np.int16) - np.asarray(color, dtype=np.int16))
        counts[color] = int(np.count_nonzero(np.max(delta, axis=1) <= 1))

    rendered_face_pixels = sum(counts.values())
    assert rendered_face_pixels / len(flat_pixels) >= 0.03, counts
    for color, count in counts.items():
        assert count / rendered_face_pixels >= 0.20, (color, count, rendered_face_pixels)


class _Capabilities:
    metadata: dict[str, object] = {}

    def __init__(self, *, missing: str | None = None) -> None:
        self.missing = missing

    def supports_view3d_capability(self, capability: str) -> bool:
        return capability != self.missing

    def supports_navigation_capability(self, capability: str) -> bool:
        return capability != self.missing


def test_live_gallery_fails_closed_on_missing_flat_lambert_capability() -> None:
    module = _gallery_module()
    missing = "meshvisual.material.flat_lambert.v1"

    with pytest.raises(RuntimeError, match=missing):
        module._validate_capabilities(_Capabilities(missing=missing))


def test_live_gallery_requires_exact_semantic_capabilities() -> None:
    module = _gallery_module()

    assert module.REQUIRED_SESSION_CAPABILITIES == {
        "display.interactive",
        "visual.mesh",
        "meshvisual.positions3d.data.view3d.v1",
        "meshvisual.material.flat_lambert.v1",
        "meshvisual.normal_generation.face_flat.v1",
        "meshvisual.normals.face3d.v1",
        "view3d.light.ambient.v1",
        "view3d.light.directional.v1",
        "view3d.navigation.orbit_pan_zoom.v1",
        "view3d.static.perspective.v1",
    }
