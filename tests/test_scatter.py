# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import unittest

import numpy as np

from vispy2 import Scatter, Figure, run


# -------------------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------------------

class TestScatter(unittest.TestCase):
    def test_scatter_1(self):
        n = 10_000
        x = np.random.normal(size=n, scale=.25)
        y = np.random.normal(size=n, scale=.25)
        size = np.random.uniform(size=(n,), low=10, high=30)
        color = np.random.uniform(size=(n, 4), low=.25, high=.95)

        fig = Figure(800, 600)
        Scatter(x, y, s=size, c=color, fig=fig)
        run()


# -------------------------------------------------------------------------------------------------
# Entry-point
# -------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
