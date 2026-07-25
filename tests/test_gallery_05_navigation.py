from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


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
