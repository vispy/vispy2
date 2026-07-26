from __future__ import annotations

from pathlib import Path
import runpy
from typing import Any, Callable, cast

import pytest

import vispy2 as vp


EXAMPLES = Path(__file__).parents[1] / "examples"


def _load(name: str) -> dict[str, Any]:
    return runpy.run_path(str(EXAMPLES / name))


def test_galleries_2_to_4_preserve_all_required_view3d_capability_assertions() -> None:
    shared = _load("gallery_shared_layout.py")
    required_capabilities = cast(
        Callable[[vp.Figure], set[str]],
        shared["_required_view3d_capabilities"],
    )
    figures = (
        cast(Callable[[], vp.Figure], _load("gallery_02_perspective_3d.py")["make_figure"])(),
        cast(Callable[[], vp.Figure], _load("gallery_03_orthographic_3d.py")["make_figure"])(),
        cast(
            Callable[[], tuple[vp.Figure, vp.Axes3D]],
            _load("gallery_04_camera_sequence.py")["make_figure"],
        )()[0],
    )

    asserted = set().union(*(required_capabilities(figure) for figure in figures))

    assert asserted >= {
        "view3d.static.perspective.v1",
        "view3d.static.orthographic.v1",
        "meshvisual.positions3d.data.view3d.v1",
        "pixelvisual.positions3d.data.view3d.v1",
        "spherevisual.v1",
        "vectorvisual.positions3d.data.view3d.v1",
        "textvisual.billboard3d.v1",
        "primitivevisual.v1",
        "primitivevisual.indexed.v1",
        "primitivevisual.triangle_strip",
    }


def test_gallery_manifest_provenance_is_portable_and_schema_2() -> None:
    validator = _load("validate_gallery.py")
    logical_import_path = cast(
        Callable[[Path, str], str],
        validator["_logical_import_path"],
    )
    assert_manifest_schema = cast(
        Callable[[dict[str, object]], None],
        validator["_assert_manifest_schema"],
    )
    runtime_description = cast(Callable[[], str], validator["_runtime_description"])

    assert logical_import_path(
        Path("/private/tmp/wheel-env/lib/python3.13/site-packages/gsp/__init__.py"),
        "gsp",
    ) == "isolated-wheel-site/gsp/__init__.py"
    assert logical_import_path(
        Path("/private/tmp/wheel-env/lib/python3.13/site-packages/vispy2/__init__.py"),
        "vispy2",
    ) == "isolated-wheel-site/vispy2/__init__.py"
    runtime = runtime_description()
    assert runtime.startswith("CPython ")
    assert not Path(runtime).is_absolute()

    manifest: dict[str, object] = {
        "schema": 2,
        "provenance": {
            "python": runtime,
            "gsp_import": "isolated-wheel-site/gsp/__init__.py",
            "vispy2_import": "isolated-wheel-site/vispy2/__init__.py",
        },
    }
    assert_manifest_schema(manifest)
    with pytest.raises(RuntimeError, match="absolute path"):
        assert_manifest_schema(
            {
                **manifest,
                "provenance": {"python": "/private/tmp/wheel-env/bin/python"},
            }
        )
    with pytest.raises(RuntimeError, match="absolute path"):
        assert_manifest_schema(
            {
                **manifest,
                "provenance": {"python": r"C:\wheel-env\python.exe"},
            }
        )
