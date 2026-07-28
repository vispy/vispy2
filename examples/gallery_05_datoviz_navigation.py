"""Gallery 5: experimental live Datoviz flat-Lambert View3D navigation.

Controls: left-drag orbits, right-drag pans, wheel zooms, and double-click
resets the construction camera. Close the window to release the session;
Ctrl-C is the terminal fallback. The backend advertises this path only after
explicit experimental opt-in and its binding/lifecycle checks pass. The mesh
uses generated face normals, one scalar ambient term, and one white
directional light from the backend-neutral GSP lighting contract.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

import vispy2 as vp
from gsp.protocol import (
    MESH3D_DATA_VIEW3D_CAPABILITY,
    MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
    MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
    MESH_NORMALS_FACE3D_CAPABILITY,
    VIEW3D_LIGHT_AMBIENT_CAPABILITY,
    VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
    VIEW3D_NAVIGATION_ORBIT_PAN_ZOOM_CAPABILITY,
    VIEW3D_STATIC_PERSPECTIVE_CAPABILITY,
)


REQUIRED_VIEW3D_CAPABILITIES = frozenset(
    {
        MESH3D_DATA_VIEW3D_CAPABILITY,
        MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
        MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
        MESH_NORMALS_FACE3D_CAPABILITY,
        VIEW3D_LIGHT_AMBIENT_CAPABILITY,
        VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
        VIEW3D_STATIC_PERSPECTIVE_CAPABILITY,
    }
)
REQUIRED_SESSION_CAPABILITIES = frozenset(
    {
        "display.interactive",
        "visual.mesh",
        *REQUIRED_VIEW3D_CAPABILITIES,
        VIEW3D_NAVIGATION_ORBIT_PAN_ZOOM_CAPABILITY,
    }
)


def _run_interactive_frames(renderer: Any) -> None:
    """Pump bounded native frames so Python can dispatch ``SIGINT``.

    Datoviz's zero-frame convention and a very large frame count both keep
    control inside one native call. Running one frame at a time returns to
    Python frequently, while the public app-exit query preserves the normal
    close-window path.
    """
    show = getattr(renderer, "show", None)
    dvz = getattr(renderer, "dvz", None)
    should_exit = getattr(dvz, "dvz_app_should_exit", None)
    if not callable(show) or not callable(should_exit):
        raise RuntimeError(
            "live View3D navigation requires bounded frame pumping and "
            "dvz_app_should_exit()"
        )

    while True:
        show(frame_count=1)
        if should_exit(renderer.app):
            return


def make_figure() -> vp.Figure:
    """Build the strict flat-Lambert scene without creating backend resources."""
    figure, axes = vp.subplots(projection="3d")
    axes.mesh(
        np.asarray([[-1, -1, 0], [1, -1, 0], [0, 1, 0.5], [0, 0, 1.5]], dtype=np.float32),
        np.asarray([[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]], dtype=np.uint32),
        color=[70, 130, 220, 255],
        shading="flat_lambert",
        normal_mode="face",
        normal_generation="face_flat",
    )
    axes.set_lighting(
        ambient_light_intensity=0.18,
        direction_to_light=(-1.0, -1.0, -1.0),
        directional_light_intensity=0.82,
    )
    axes.fit_camera()
    axes.orbit(yaw_radians=0.35, pitch_radians=-0.20)
    axes.set_title("Datoviz live camera: left orbit, right pan, wheel zoom")
    return figure


def _validate_capabilities(capabilities: Any) -> None:
    for capability in sorted(REQUIRED_VIEW3D_CAPABILITIES):
        if not capabilities.supports_view3d_capability(capability):
            raise RuntimeError(
                "live flat-Lambert View3D navigation unavailable: "
                f"Datoviz does not advertise {capability}"
            )
    if not capabilities.supports_navigation_capability(
        VIEW3D_NAVIGATION_ORBIT_PAN_ZOOM_CAPABILITY
    ):
        diagnostic = capabilities.metadata.get(
            "datoviz_view3d_navigation_diagnostics",
            "installed binding did not qualify",
        )
        raise RuntimeError(f"live View3D navigation unavailable: {diagnostic}")


def main() -> None:
    if os.environ.get("GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV") != "1":
        raise RuntimeError(
            "live View3D navigation is unadvertised; set "
            "GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=1 only for the isolated "
            "manual-review run"
        )
    figure = make_figure()
    try:
        with vp.open_session("datoviz", require=REQUIRED_SESSION_CAPABILITIES) as session:
            _validate_capabilities(session.capabilities)
            renderer = figure.display(session, block=False)
            _run_interactive_frames(renderer)
    except KeyboardInterrupt:
        # The session context has already released native resources.
        print("Datoviz live review interrupted; session closed.")


if __name__ == "__main__":
    main()
