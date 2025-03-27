import numpy as np
import datoviz as dvz
from .common import Panel, DEFAULT_SIZE, context


class Scatter:
    def __init__(self, x, y, s=None, c=None, panel=None, fig=None):
        context.initialize()  # Ensure APP, BATCH, and SCENE are initialized
        assert context.batch
        if fig and not panel:
            panel = fig.get_panel()
        self.panel = panel or Panel(fig=fig)
        self.visual = dvz.point(context.batch, 0)

        # Prepare data.
        x, y = np.asarray(x), np.asarray(y)
        n = min(x.shape[0], y.shape[0])
        dvz.point_alloc(self.visual, n)

        # Set positions.
        pos = np.zeros((n, 3), np.float32)
        pos[:, 0], pos[:, 1] = x, y
        dvz.point_position(self.visual, 0, n, pos, 0)

        # Set colors.
        c = np.asarray(c) if c is not None else np.ones((n, 4), dtype=np.float32)
        color = np.clip(c * 255.0, 0, 255).astype(np.uint8)
        dvz.point_color(self.visual, 0, n, color, 0)

        # Set sizes.
        size = s.astype(np.float32) if s is not None else np.full(n, DEFAULT_SIZE, dtype=np.float32)
        dvz.point_size(self.visual, 0, n, size, 0)

        self.panel.add_visual(self.visual)
