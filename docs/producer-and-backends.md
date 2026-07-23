# Producer and backend boundary

VisPy2 builds typed, backend-neutral `gsp.Scene` snapshots. A `Figure` and its `Axes` never retain a
Matplotlib figure, a Datoviz handle, an open session, or backend capability state.

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0, 1], [1, 0])
scene = figure.to_scene()
```

Backend packages register providers in the `gsp.backends` entry-point group. Discovering metadata
is lazy; probing or opening a session performs dependency and API checks. Selection is explicit:

```python
import gsp

print(gsp.discover_backends())
print(gsp.discover_backends(probe=True))

with gsp.open_session("datoviz", require={"visual.points"}) as session:
    figure.display(session, block=True, frame_count=2)
```

`Figure.savefig()` and blocking `Figure.show()` are deliberate one-shot conveniences that open and
close a Matplotlib session. Install `vispy2[matplotlib]` for those methods. Non-blocking or
interactive execution requires a caller-owned session so its lifecycle remains explicit.

The current `Scene` execution boundary requires exactly one `Axes` or `Axes3D`;
`Figure.to_scene()` rejects empty, mixed, and multi-axes figures instead of silently discarding
views.

## Static View3D and camera

Use `projection="3d"` to create an `Axes3D`. It owns semantic camera and projection state only:

```python
figure, axes = vp.subplots(projection="3d")
axes.mesh(
    [[-1, -1, 0], [1, -1, 0], [0, 1, 0]],
    [[0, 1, 2]],
    color=[70, 130, 220, 255],
)
axes.fit_camera()
scene = figure.to_scene()
```

`set_camera()`, `set_perspective()`, `set_orthographic()`, `orbit()`, `pan()`, `zoom()`,
`reset_camera()`, and `fit_camera()` each update canonical `View3D` state and increment its
revision. Orbit, pan, and zoom use the GSP reducers; they do not retain a backend or claim live
backend navigation support.

Perspective fitting preserves view direction, targets the DATA bounds center, contains the
bounding sphere at the limiting vertical/horizontal field of view, and resolves positive
near/far planes. Orthographic fitting projects all bounds corners into the camera basis, preserves
reversed x/y limits, and resolves a non-degenerate depth range. The margin must be finite and at
least one. Fitting without a finite DATA-space 3D visual is an explicit error.
`Axes3D.mesh()` requires `(N, 3)` positions; visual transforms are explicitly rejected in this
static slice because a 3D transform model is outside M275.

Static mesh rendering requires:

- `meshvisual.positions3d.data.view3d.v1`;
- `view3d.static.perspective.v1` or `view3d.static.orthographic.v1`;
- the backend's ordinary `visual.mesh` surface.

Matplotlib provides deterministic reference rendering with its documented 3D depth adaptation.
Datoviz uses the public v0.4 View3D binding and advertises strict retained DATA-space/depth behavior
only when the installed binding proves those capabilities. Unsupported projections and mesh
behavior must be surfaced by capability checks or backend diagnostics; VisPy2 does not silently
adapt them.

The installed-wheel example `examples/static_mesh3d.py` builds both projections and captures PNGs
through either backend.
# Pixel visuals

`Axes.pixels(x, y, color=..., size=...)` creates 2D DATA-space screen-aligned squares. `Axes3D.pixels(x, y, z, ...)` creates screen-facing squares anchored at projected 3D DATA positions, and `vispy2.pixels(...)` is the module-level 2D convenience. `size` is a strictly positive logical-pixel width, scalar or per item.

Matplotlib preserves deterministic square shape and logical width in 2D; its 3D path is an explicit projected-square overlay adaptation without strict GPU depth occlusion. The Datoviz adapter uses the public v0.4 `dvz_pixel` visual and its `pixel_size_px` attribute, with exact lowering covered by binding tests; native capture qualification is deferred to the dedicated Datoviz runtime mission.
