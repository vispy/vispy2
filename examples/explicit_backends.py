"""Render one VisPy2 figure through explicit GSP providers."""

from pathlib import Path

import vispy2 as vp


figure, axes = vp.subplots()
axes.set_xlim(-1.0, 1.0)
axes.set_ylim(-1.0, 1.0)
axes.scatter([-0.5, 0.0, 0.5], [0.0, 0.5, -0.25], size=[18.0, 30.0, 24.0])


def save_matplotlib(path: str | Path) -> None:
    """Use the one-shot Matplotlib convenience."""
    figure.savefig(path)


def show_datoviz() -> None:
    """Keep an interactive Datoviz session explicitly owned by the caller."""
    with vp.open_session("datoviz", require={"visual.points"}) as session:
        figure.display(session, block=True, frame_count=2)
