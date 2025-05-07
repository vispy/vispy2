# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import unittest
from pathlib import Path

from vispy2 import Mesh, Figure, run
import datoviz as dvz


# -------------------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------------------


class TestMesh(unittest.TestCase):
    def test_mesh_brain(self):
        # Path to the brain.obj file.
        CURDIR = Path(__file__).parent
        filepath = (CURDIR / "../data/brain.obj").resolve()

        sc = dvz.ShapeCollection()
        sc.add_obj(filepath)

        # Create a figure and mesh.
        fig = Figure(800, 600)
        Mesh(shape=sc, fig=fig)
        sc.destroy()

        # Run the visualization.
        run()


# -------------------------------------------------------------------------------------------------
# Entry-point
# -------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
