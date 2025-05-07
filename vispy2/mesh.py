# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

from .common import Panel, get_app


# -------------------------------------------------------------------------------------------------
# Mesh
# -------------------------------------------------------------------------------------------------


class Mesh:
    def __init__(self, vertices=None, indices=None, shape=None, colors=None, panel=None, fig=None):
        app = get_app()
        if fig and not panel:
            panel = fig.get_panel_3D()
        self.panel = panel or Panel(fig=fig)

        # Prepare data.
        kwargs = dict(
            lighting=True,
            indexed=True,
            light_dir=(+1, -1, -1),
            light_params=(0.5, 0.5, 0.5, 32),
        )
        if vertices is not None and indices is not None:
            self.visual = app.mesh(position=vertices, index=indices, color=colors, **kwargs)

        elif shape is not None:
            self.visual = app.mesh_shape(shape, color=colors, **kwargs)

        self.panel.add(self.visual)
