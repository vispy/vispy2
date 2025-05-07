# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import datoviz as dvz

# Constants
WIDTH = 800
HEIGHT = 600
DEFAULT_SIZE = 10.0


# -------------------------------------------------------------------------------------------------
# Globlal variable
# -------------------------------------------------------------------------------------------------

APP = None


def get_app():
    if APP is None:
        globals()["APP"] = dvz.App()
    return globals()["APP"]


# -------------------------------------------------------------------------------------------------
# Figure
# -------------------------------------------------------------------------------------------------


class Figure:
    def __init__(self, width=0, height=0):
        self.width = width or WIDTH
        self.height = height or HEIGHT
        app = get_app()
        self._figure = app.figure(self.width, self.height)

    def get_panel_2D(self, **kwargs):
        dvz_panel = self._figure.panel(**kwargs)
        dvz_panel.panzoom()
        return Panel(dvz_panel)

    def get_panel_3D(self, **kwargs):
        dvz_panel = self._figure.panel(**kwargs)
        dvz_panel.arcball()
        return Panel(dvz_panel)


# -------------------------------------------------------------------------------------------------
# Panel
# -------------------------------------------------------------------------------------------------


class Panel:
    _panel = None

    def __init__(self, panel):
        self._panel = panel

    def add(self, visual):
        self._panel.add(visual)


# -------------------------------------------------------------------------------------------------
# Run
# -------------------------------------------------------------------------------------------------


def run():
    app = get_app()
    app.run()
    app.destroy()
