from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

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
        "perspective-3d",
        "orthographic-3d",
        "flat-lambert",
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
