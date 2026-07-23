"""Gallery 5: experimental live Datoviz View3D navigation.

Controls: left-drag orbits, right-drag pans, wheel zooms, and double-click
resets the construction camera. Close the window to release the session;
Ctrl-C is the terminal fallback. The backend advertises this path only after
explicit experimental opt-in and its binding/lifecycle checks pass.
"""

from __future__ import annotations

import os

import numpy as np

import vispy2 as vp
from gsp.protocol import VIEW3D_NAVIGATION_ORBIT_PAN_ZOOM_CAPABILITY


def main() -> None:
    if os.environ.get("GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV") != "1":
        raise RuntimeError(
            "live View3D navigation is unadvertised; set "
            "GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=1 only for the isolated "
            "manual-review run"
        )
    figure, axes = vp.subplots(projection="3d")
    axes.mesh(
        np.asarray([[-1, -1, 0], [1, -1, 0], [0, 1, 0.5], [0, 0, 1.5]], dtype=np.float32),
        np.asarray([[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]], dtype=np.uint32),
        color=[70, 130, 220, 255],
    )
    axes.fit_camera()
    axes.set_title("Datoviz live camera: left orbit, right pan, wheel zoom")
    with vp.open_session("datoviz", require={"display.interactive", "visual.mesh"}) as session:
        if not session.capabilities.supports_navigation_capability(
            VIEW3D_NAVIGATION_ORBIT_PAN_ZOOM_CAPABILITY
        ):
            diagnostic = session.capabilities.metadata.get(
                "datoviz_view3d_navigation_diagnostics",
                "installed binding did not qualify",
            )
            raise RuntimeError(f"live View3D navigation unavailable: {diagnostic}")
        # A high bound keeps the public session loop live; closing the window ends it early.
        figure.display(session, block=True, frame_count=1_000_000)


if __name__ == "__main__":
    main()
