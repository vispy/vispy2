import inspect
from collections.abc import Callable
from pathlib import Path
import runpy
from typing import cast

import pytest

from gsp.protocol import CoordinateSpace, FontRole, TextAnchorX, TextAnchorY, TextVisual

import vispy2 as vp


def test_axes3d_billboard_public_fields() -> None:
    figure, axes = vp.subplots(projection="3d")
    visual = axes.text(
        [0, 1],
        [0, 0],
        [0, 1],
        ["ASCII", "Δ café"],
        font_role="monospace",
        anchor_x=["left", "right"],
        anchor_y=["top", "bottom"],
        rotation_rad=[0.0, 0.5],
    )

    assert isinstance(visual, TextVisual)
    assert visual.coordinate_space is CoordinateSpace.DATA
    assert visual.font_role is FontRole.MONOSPACE
    assert visual.anchor_x_values() == (TextAnchorX.LEFT, TextAnchorX.RIGHT)
    assert visual.anchor_y_values() == (TextAnchorY.TOP, TextAnchorY.BOTTOM)
    assert figure.to_scene().visuals == (visual,)


def test_installed_wheel_billboard_example_writes_matplotlib_artifact(
    tmp_path: Path,
) -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "text_billboards_3d.py"))
    render_backend = cast(Callable[[str, Path], Path], example["render_backend"])

    artifact = render_backend("matplotlib", tmp_path)

    assert artifact.name == "matplotlib-text-billboards3d.png"
    assert artifact.stat().st_size > 0


def test_billboard_example_rejects_unqualified_datoviz_capture(tmp_path: Path) -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "text_billboards_3d.py"))
    render_backend = cast(Callable[[str, Path], Path], example["render_backend"])
    output = tmp_path / "unqualified-datoviz"

    with pytest.raises(ValueError, match="Matplotlib file output only"):
        render_backend("datoviz", output)
    assert not output.exists()


def test_axes3d_text_signature_has_no_low_level_text_or_backend_escape() -> None:
    forbidden = {
        "glyph",
        "atlas",
        "font_file",
        "font_path",
        "rich_text",
        "shaping",
        "native_handle",
        "backend",
        "backend_options",
    }
    assert forbidden.isdisjoint(inspect.signature(vp.Axes3D.text).parameters)


def test_billboard_gallery_uses_separate_font_roles_and_overlay_layers() -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "text_billboards_3d.py"))
    make_figure = cast(Callable[[], vp.Figure], example["make_figure"])
    labels = tuple(
        visual for visual in make_figure().to_scene().visuals if isinstance(visual, TextVisual)
    )

    assert tuple(label.font_role for label in labels) == (
        FontRole.SANS,
        FontRole.SERIF,
        FontRole.MONOSPACE,
    )
    assert tuple(label.z_order for label in labels) == (-1, 0, 1)
    assert tuple(float(label.positions[0, 0]) for label in labels) == pytest.approx(
        (-2.2, 0.0, 2.0)
    )
