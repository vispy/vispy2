# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import unittest
from pathlib import Path

import numpy as np
from vispy2 import Mesh, Figure, run
import datoviz as dvz
from datoviz import S_


# -------------------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------------------

class TestMesh(unittest.TestCase):
    def test_mesh_brain(self):
        # Path to the brain.obj file.
        CURDIR = Path(__file__).parent
        filepath = (CURDIR / "../data/brain.obj").resolve()

        # Load the .OBJ mesh file.
        shape = dvz.shape_obj(S_(filepath))
        nv = shape.vertex_count
        ni = shape.index_count

        # Create artificial colors.
        t = np.linspace(0, 1, nv).astype(np.float32)
        colors = np.empty((nv, 4), dtype=np.uint8)
        dvz.colormap_array(dvz.CMAP_COOLWARM, nv, t, 0, 1, colors)

        # Create a figure and mesh.
        fig = Figure(800, 600)
        Mesh(shape=shape, colors=colors, fig=fig)

        # Run the visualization.
        run()


# -------------------------------------------------------------------------------------------------
# Entry-point
# -------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
