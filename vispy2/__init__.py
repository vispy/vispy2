# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import numpy as np
import datoviz as dvz


# -------------------------------------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------------------------------------

__version__ = '2.0.0-dev'
WIDTH = 800
HEIGHT = 600
DEFAULT_SIZE = 10.0

APP = None
BATCH = None
SCENE = None


# -------------------------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------------------------

def figure(width=0, height=0):
    global APP, BATCH, SCENE
    APP = APP or dvz.app(0)
    BATCH = BATCH or dvz.app_batch(APP)
    SCENE = SCENE or dvz.scene(BATCH)

    width = width or WIDTH
    height = height or HEIGHT

    fig = dvz.figure(SCENE, width, height, 0)

    return fig


def axis(fig=None):
    fig = fig or figure()
    panel = dvz.panel_default(fig)
    return panel


def scatter(x, y, s=None, c=None, ax=None):
    x = np.asarray(x)
    y = np.asarray(y)

    panel = ax or axis()

    pz = dvz.panel_panzoom(panel)

    # Visual creation.
    visual = dvz.point(BATCH, 0)

    # Visual allocation.
    n = min(x.shape[0], y.shape[0])
    dvz.point_alloc(visual, n)

    pos = np.zeros((n, 3), np.float32)
    pos[:, 0] = x
    pos[:, 1] = y
    dvz.point_position(visual, 0, n, pos, 0)

    c = np.asarray(c) if c is not None else np.ones((n, 4), dtype=np.float32)
    color = np.clip(c * 255.0, 0, 255).astype(np.uint8)
    dvz.point_color(visual, 0, n, color, 0)

    size = s.astype(np.float32) if s is not None else np.full(n, DEFAULT_SIZE, dtype=np.float32)
    dvz.point_size(visual, 0, n, size, 0)

    dvz.panel_visual(panel, visual, 0)


def run():
    dvz.scene_run(SCENE, APP, 0)
    dvz.scene_destroy(SCENE)
    dvz.app_destroy(APP)
