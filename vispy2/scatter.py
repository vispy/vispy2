import numpy as np
from .common import Panel, DEFAULT_SIZE, get_app


class Scatter:
    def __init__(self, x, y, s=None, c=None, panel=None, fig=None):
        app = get_app()
        if fig and not panel:
            panel = fig.get_panel_2D()
        self.panel = panel or Panel(fig=fig)

        # Prepare data.
        x, y = np.asarray(x), np.asarray(y)
        n = min(x.shape[0], y.shape[0])

        # Position.
        pos = np.zeros((n, 3), np.float32)
        pos[:, 0], pos[:, 1] = x, y

        # Color.
        c = np.asarray(c) if c is not None else np.ones((n, 4), dtype=np.float32)
        color = np.clip(c * 255.0, 0, 255).astype(np.uint8)

        # Size.
        size = s if s is not None else np.full(n, DEFAULT_SIZE)

        self.visual = app.point(
            position=pos,
            color=color,
            size=size,
        )
        self.panel.add(self.visual)
