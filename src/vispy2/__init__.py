"""High-level scientific plotting producer for GSP."""

from .emission_features import EMISSION_FEATURES, EmissionFeature
from .protocol import (
    Axes,
    Axes3D,
    Figure,
    affine2d,
    color_scale,
    colorbar,
    imshow,
    markers,
    mesh,
    path,
    pixels,
    primitives,
    plot,
    quiver,
    scatter,
    segments,
    subplots,
    text,
    vectors,
)
from .session import open_session

__version__ = "0.2.0a1"

__all__ = [
    "__version__",
    "EMISSION_FEATURES",
    "EmissionFeature",
    "Axes",
    "Axes3D",
    "Figure",
    "affine2d",
    "color_scale",
    "colorbar",
    "imshow",
    "markers",
    "mesh",
    "open_session",
    "path",
    "pixels",
    "primitives",
    "plot",
    "quiver",
    "scatter",
    "segments",
    "subplots",
    "text",
    "vectors",
]
