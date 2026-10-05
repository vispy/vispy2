"""Qualify new scientific conveniences and grid allocations through both adapters."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
import vispy2 as vp
from gsp.protocol import CanvasSize


def check(backend: str) -> None:
    figure, grid = vp.subplots(2, 2, canvas_size=CanvasSize.pixel_exact(800, 600), squeeze=False)
    for axes in grid.flat:
        axes.axis_guides.clear()
        axes.set_xlim(0, 1)
        axes.set_ylim(0, 1)
    histogram, band, points, spans = grid.flat
    values, edges, _ = histogram.hist(
        [0.1, 0.2, 0.3, 0.7, 0.8], bins=[0, 0.5, 1], color=[255, 0, 0, 255]
    )
    np.testing.assert_array_equal(values, [3, 2])
    np.testing.assert_array_equal(edges, [0, 0.5, 1])
    histogram.set_ylim(0, 4)
    band.fill_between([0, 0.5, 1], [0.25, 0.8, 0.25], color=[0, 0, 255, 255])
    points.scatter([0.5], [0.5], size=28, color=[0, 255, 0, 255])
    spans.axvspan(0.25, 0.75, color=[255, 0, 255, 255])
    spans.axhline(0.5, color=[255, 0, 255, 255], width=3)
    figure.link_axes(band, points, spans, x=True, y=False)
    band.set_xlim(-0.1, 1.1)
    assert band.view.x_range == points.view.x_range == spans.view.x_range
    with vp.open_session("matplotlib") as reference:
        layout = figure.resolve_layout(reference)
    with tempfile.TemporaryDirectory(prefix="vispy2-scientific-grid-") as temporary:
        target = Path(temporary) / "grid.png"
        with vp.open_session(
            backend, require={"output.file", "visual.primitive", "visual.points", "visual.segments"}
        ) as session:
            session.render(figure.to_scene(), layout_snapshot=layout, target=target)
        pixels = np.asarray(Image.open(target).convert("RGB"))
        assert pixels.shape == (600, 800, 3), pixels.shape
        selectors = (
            (True, False, False),
            (False, False, True),
            (False, True, False),
            (True, False, True),
        )
        for axes, selector in zip(grid.flat, selectors, strict=True):
            rectangle = layout.panel(axes.panel.id).plot_rect_px
            x, y = round(rectangle.x), round(rectangle.y)
            width, height = round(rectangle.width), round(rectangle.height)
            panel = pixels[y : y + height, x : x + width].astype(np.int16)
            mask = np.ones(panel.shape[:2], dtype=np.bool_)
            for channel, bright in enumerate(selector):
                mask &= panel[:, :, channel] > 150 if bright else panel[:, :, channel] < 100
            assert np.count_nonzero(mask) > 30, (backend, axes.panel.id)
    print(f"{backend}: 2x2 grid, histogram, filled band, linked ranges, reference spans passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("matplotlib", "datoviz"), required=True)
    check(parser.parse_args().backend)
