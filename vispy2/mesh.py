# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import numpy as np
import datoviz as dvz
from .common import Panel, context


# -------------------------------------------------------------------------------------------------
# Mesh
# -------------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self, vertices=None, indices=None, shape=None, colors=None, panel=None, fig=None):
        context.initialize()  # Ensure APP, BATCH, and SCENE are initialized
        if fig and not panel:
            panel = fig.get_panel(interact='arcball')
        self.panel = panel or Panel(fig=fig, interact='arcball')
        flags = dvz.MESH_FLAGS_LIGHTING
        self.visual = dvz.mesh(context.batch, flags)

        # Prepare data.
        if vertices is not None and indices is not None:
            nv, ni = vertices.shape[0], indices.shape[0]
            dvz.mesh_alloc(self.visual, nv, ni)
            dvz.mesh_vertex(self.visual, 0, nv, vertices, 0)
            dvz.mesh_index(self.visual, 0, ni, indices, 0)
        elif shape is not None:
            nv = shape.vertex_count
            ni = shape.index_count
            self.visual = dvz.mesh_shape(context.batch, shape, flags)

        # Set colors.
        if colors is not None:
            # colors = np.clip(colors * 255.0, 0, 255).astype(np.uint8)
            dvz.mesh_color(self.visual, 0, nv, colors, 0)

        self.panel.add_visual(self.visual)
