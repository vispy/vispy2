# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import datoviz as dvz

# Constants
WIDTH = 800
HEIGHT = 600
DEFAULT_SIZE = 10.0


# -------------------------------------------------------------------------------------------------
# Context
# -------------------------------------------------------------------------------------------------

class Context:
    """Encapsulates the application context for managing APP, BATCH, and SCENE."""
    def __init__(self):
        self.app = None
        self.batch = None
        self.scene = None

    def initialize(self):
        """Initialize the APP, BATCH, and SCENE variables."""
        if self.app is None:
            self.app = dvz.app(0)
        if self.batch is None:
            self.batch = dvz.app_batch(self.app)
        if self.scene is None:
            self.scene = dvz.scene(self.batch)

    def destroy(self):
        """Clean up the APP, BATCH, and SCENE variables."""
        if self.scene:
            dvz.scene_destroy(self.scene)
        if self.app:
            dvz.app_destroy(self.app)
        self.app = self.batch = self.scene = None


# -------------------------------------------------------------------------------------------------
# Globlal variable
# -------------------------------------------------------------------------------------------------

# Create a shared context instance.
context = Context()


# -------------------------------------------------------------------------------------------------
# Figure
# -------------------------------------------------------------------------------------------------

class Figure:
    def __init__(self, width=0, height=0):
        context.initialize()  # Ensure APP, BATCH, and SCENE are initialized
        self.width = width or WIDTH
        self.height = height or HEIGHT
        self._figure = dvz.figure(context.scene, self.width, self.height, 0)

    def get_panel(self, **kwargs):
        """Return the default panel for this figure."""
        return Panel(fig=self, **kwargs)


# -------------------------------------------------------------------------------------------------
# Panel
# -------------------------------------------------------------------------------------------------

class Panel:
    def __init__(self, x0=0, y0=0, w=0, h=0, fig=None, _panel=None, interact='panzoom'):
        context.initialize()  # Ensure APP, BATCH, and SCENE are initialized
        self.fig = fig or Figure()
        assert self.fig
        if w == h == 0 and _panel is None:
            _panel = dvz.panel_default(self.fig._figure)
        w = w or self.fig.width
        h = h or self.fig.height
        self._panel = _panel or dvz.panel(self.fig._figure, x0, y0, w, h)
        if interact == 'panzoom':
            self._pz = dvz.panel_panzoom(self._panel)
        elif interact == 'arcball':
            self._arcball = dvz.panel_arcball(self._panel)

    def add_visual(self, visual):
        dvz.panel_visual(self._panel, visual, 0)


# -------------------------------------------------------------------------------------------------
# Axis
# -------------------------------------------------------------------------------------------------

def Axis(fig=None):
    fig = fig or Figure()
    panel = Panel(fig=fig)
    return panel


# -------------------------------------------------------------------------------------------------
# Run
# -------------------------------------------------------------------------------------------------

def run():
    context.initialize()  # Ensure APP, BATCH, and SCENE are initialized
    dvz.scene_run(context.scene, context.app, 0)
    context.destroy()
