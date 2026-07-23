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

## Sphere visuals

`Axes3D.spheres(x, y, z, radius=..., color=...)` creates DATA-space `SphereVisual` values.
`radius` accepts one strictly positive DATA-space radius or one radius per sphere; `color` accepts
one RGBA value or one RGBA value per sphere. Camera fitting includes the full
`position - radius` to `position + radius` extent rather than fitting sphere centers alone.

Opening a session for the sphere example requires the provider capability `visual.sphere`.
Datoviz lowers spheres to its public raycast-impostor visual and advertises
`spherevisual.analytic_surface_depth.v1` only when that binding surface is available. Matplotlib
advertises only `spherevisual.v1`: it draws projected circles in far-to-near center-depth order,
and perspective radius projection is a view-plane approximation rather than exact sphere
silhouette or analytic surface depth.

The installed-wheel example `examples/spheres_3d.py` builds perspective and orthographic scenes.
Matplotlib reference captures are checked in under `examples/artifacts`. Native Datoviz capture is
tracked separately by M284 because `capture_png_bytes()` currently aborts after rendering in the
available runtime.

## Vector visuals

`Axes.vectors(x, y, u, v, ...)` and `Axes3D.vectors(x, y, z, u, v, w, ...)` create
straight DATA-space `VectorVisual` values. `scale` and `anchor="tail"|"center"|"head"` resolve
canonical endpoints before backend lowering. Widths are logical canvas pixels; colors and widths
may be uniform or per item. Caps are visual-wide and limited to the GSP `VectorCap` vocabulary.

`Axes.quiver(...)`, `Axes3D.quiver(...)`, and module-level `vispy2.quiver(...)` are thin aliases
over the same semantic record. They deliberately do not emulate Matplotlib's `quiver` keyword
surface.

Datoviz lowering uses public `dvz_vector` dense attributes plus `DvzVectorStyle`, preserving
source item identity. M279 did not produce or qualify a native Datoviz capture; native GUI and
capture qualification remain assigned to M284. Matplotlib uses deterministic line-and-marker-cap
artists: endpoint placement, scale, color, and width are preserved, while head rasterization is
explicitly adapted. Its 3D path projects the canonical endpoints into a 2D overlay rather than
using native Matplotlib 3D axes. Curves, per-item caps, dashes, and backend-native style structures
are outside this API.

The installed-wheel example `examples/vectors_2d_3d.py` builds bounded 2D and perspective 3D
vector fields and writes files through Matplotlib only, after checking the straight-vector,
DATA-space View3D, and triangle-head capabilities. It rejects Datoviz file output until M284
qualifies native capture.

## Primitive visuals

`Axes.primitives(positions, topology=...)`, `Axes3D.primitives(...)`, and module-level
`vispy2.primitives(...)` produce the bounded `PrimitiveVisual` escape hatch. The only topologies
are `point_list`, `line_list`, `line_strip`, `triangle_list`, and `triangle_strip`. Its bounded
fields are an ID, topology, `(N, 2)` or `(N, 3)` real finite DATA-space positions, uniform or
per-public-vertex RGBA colors, optional flat public vertex indices, coordinate space, and the
existing 2D visual transform binding. Optional indices select from the public positions and colors;
topology cardinality is validated on that resolved sequence after indexing.

The API intentionally has no shader, pipeline, material, depth, culling, instancing, slot, or
native-handle parameters. Datoviz lowering uses the public `dvz_primitive` constructor, dense
position and color attributes, and optional public index binding. Matplotlib deterministically
adapts the five topologies to point, line, or triangle collections. Point colors remain
per-vertex; line and triangle colors are the mean of each primitive's vertex RGBA values rather
than interpolated GPU colors. The 3D path projects vertices to a 2D overlay, uses painter ordering
by mean projected depth for triangles, and does not claim native depth-buffer or exact raster
semantics.

The installed-wheel `examples/primitive_topologies.py` gallery includes all five topologies and
both indexed and unindexed inputs. It writes through Matplotlib after checking every primitive
capability and defers native Datoviz capture qualification to M284.

## Text billboards in View3D

`Axes3D.text(x, y, z, texts, ...)` creates screen-facing `TextVisual` billboards anchored at
projected 3D DATA positions. Font size remains in logical pixels as camera distance changes.
Generic sans, serif, and monospace roles, layout-box anchors, display-plane rotation, RGBA color,
and integer `z_order` are semantic. Overlay ordering is stable: higher `z_order` values appear
above lower values, without claiming depth occlusion.

Matplotlib projects each DATA anchor into an axes-fraction overlay and maps generic roles through
its configured font-family aliases. Datoviz public lowering uses retained UTF-8 text, style, and
placement objects; because its public style takes a concrete font pointer rather than a generic
role, the adapter leaves that pointer unset and uses the backend default font. Datoviz coverage in
M281 is limited to lowering and a no-capture smoke path. No native Datoviz PNG was produced or
qualified, and M284 owns native GUI/capture qualification.

Exact fonts, glyph coverage, metrics, shaping, and rasterization vary by backend. Font files,
glyph IDs or atlases, rich text, per-glyph query, raster parity, and strict depth occlusion are not
part of this API. The Matplotlib-only installed-wheel gallery
`examples/text_billboards_3d.py` uses three separated objects and independent sans, serif, and
monospace labels; it rejects Datoviz before creating output or opening a session.

# Pixel visuals

`Axes.pixels(x, y, color=..., size=...)` creates 2D DATA-space screen-aligned squares. `Axes3D.pixels(x, y, z, ...)` creates screen-facing squares anchored at projected 3D DATA positions, and `vispy2.pixels(...)` is the module-level 2D convenience. `size` is a strictly positive logical-pixel width, scalar or per item.

Matplotlib preserves deterministic square shape and logical width in 2D; its 3D path is an explicit projected-square overlay adaptation without strict GPU depth occlusion. The Datoviz adapter uses the public v0.4 `dvz_pixel` visual and its `pixel_size_px` attribute, with exact lowering covered by binding tests; native capture qualification is deferred to the dedicated Datoviz runtime mission.
