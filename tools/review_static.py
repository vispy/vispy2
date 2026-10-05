"""Capture an existing live comparison case without starting a GUI event loop."""

from __future__ import annotations

import argparse
from pathlib import Path

from manual_live_compare import CASES, make_figure
from gsp.protocol import CanvasSize
from PIL import Image
import vispy2 as vp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--backend", choices=("matplotlib", "datoviz"), required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    args = parser.parse_args()
    figure = make_figure(args.case)
    figure.canvas_size = CanvasSize.pixel_exact(800, 600)
    args.capture_dir.mkdir(parents=True, exist_ok=True)
    target = args.capture_dir / f"{args.backend}-{args.case}.png"
    with vp.open_session(args.backend, require={"output.file"}) as session:
        session.render(figure.to_scene(), target=target)
        for diagnostic in session.diagnostics:
            print(f"Adaptation: {diagnostic}")
    with Image.open(target) as image:
        if image.size != (800, 600):
            raise RuntimeError(f"unexpected capture dimensions {image.size}")
    print(f"Capture checked: {target}. Human visual review is still pending.")


if __name__ == "__main__":
    main()
