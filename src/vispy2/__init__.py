"""High-level scientific plotting producer for GSP."""

from .protocol import (
    Axes,
    Figure,
    affine2d,
    color_scale,
    colorbar,
    imshow,
    markers,
    mesh,
    path,
    plot,
    scatter,
    segments,
    subplots,
    text,
)
from .session import open_session

__version__ = "0.2.0a1"

__all__ = [
    "__version__",
    "Axes",
    "Figure",
    "affine2d",
    "color_scale",
    "colorbar",
    "imshow",
    "markers",
    "mesh",
    "open_session",
    "path",
    "plot",
    "scatter",
    "segments",
    "subplots",
    "text",
]
