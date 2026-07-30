# VisPy2 user guide

VisPy2 is the high-level plotting producer for GSP. It owns semantic figure, axes, visual, guide,
camera, and lighting state. GSP sessions own backend selection, native resources, display loops,
output, and queries.

## Onboarding

Install the `vispy2` wheel with `gsp-core` and at least one adapter wheel. During the unpublished
bootstrap, Datoviz also needs the compatible checkout selected by `GSP_DATOVIZ_SOURCE`. Confirm
the environment before plotting:

```python
import gsp
import vispy2 as vp

print(vp.__version__)
print([(item.name, item.available) for item in gsp.discover_backends(probe=True)])
```

`vp.subplots()` creates exactly one semantic axes. VisPy2 does not select a backend while you
construct the figure:

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0.0, 1.0], [1.0, 0.0])
scene = figure.to_scene()
```

The resulting `gsp.Scene` is an immutable snapshot. Changing the axes later changes the next
snapshot, not the earlier one.

## 2D plotting

All ordinary 2D positions are in DATA coordinates. RGBA colors use integer channels from 0 to 255;
sizes, widths, and font sizes use logical canvas pixels.

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.plot([0.0, 0.5, 1.0], [0.2, 0.9, 0.4], width=2.0)
axes.scatter([0.0, 1.0], [0.2, 0.4], size=[12.0, 20.0])
axes.markers([0.5], [0.9], shape="diamond", size=18.0)
axes.vectors([0.2], [0.3], [0.4], [0.25])
axes.text([0.5], [0.75], ["two-dimensional"], anchor_x="center")
axes.set_xlim(-0.1, 1.1)
axes.set_ylim(0.0, 1.0)
axes.set_xlabel("distance")
axes.set_ylabel("response")
axes.set_title("Semantic 2D scene")
axes.grid(axis="both")
figure.savefig("plot.png")
```

The visual families are:

| Method | Meaning |
|---|---|
| `scatter` | screen-sized points with uniform, per-item, or scalar-mapped color |
| `markers` | shaped and optionally stroked screen-sized markers |
| `pixels` | screen-aligned square pixels |
| `segments` | independent DATA-space line segments |
| `path`, `plot` | one or more open DATA-space polylines |
| `vectors`, `quiver` | straight displacement vectors with bounded cap styles |
| `primitives` | point-, line-, or triangle-list/strip geometry |
| `text` | explicit DATA-anchored labels |
| `mesh` | indexed triangle mesh, including the bounded texture path |
| `imshow` | scalar or RGBA image with a DATA-space extent |

`quiver` is a thin alias for `vectors`; it does not emulate Matplotlib's keyword surface.
`primitives` is intentionally bounded and exposes no shader, pipeline, material, native handle,
depth, culling, or instancing API. Two-dimensional visuals accept an optional affine transform;
use `vp.affine2d(matrix)` or pass a compatible matrix directly.

## Scalar color and images

Create one semantic color scale and share it between visuals and a colorbar:

```python
import numpy as np
import vispy2 as vp

figure, axes = vp.subplots()
values = np.array([[-1.0, -0.4, 0.2], [0.1, 0.7, 1.0]], dtype=np.float32)
scale = axes.color_scale(
    cmap="viridis",
    clim=(-1.0, 1.0),
    id="scale:temperature",
    description="temperature",
)
image = axes.imshow(
    values,
    extent=(0.0, 3.0, 0.0, 2.0),
    origin="lower",
    interpolation="nearest",
    color_scale=scale,
)
axes.colorbar(
    scale,
    label="temperature",
    linked_visual_ids=[image.id],
)
```

Scalar `scatter` and `markers` colors can use the same `ColorScale`. A scale ID must identify one
consistent scale within the figure. Scalar mapping requires `clim`; RGBA input bypasses scalar
mapping.

Matplotlib is the deterministic reference/publication path for DATA-space images and colorbars.
The qualified Datoviz v0.4 path retains the same DATA extent under View2D, pre-maps the canonical
scalar color scale to RGBA8, uploads it as a sampled field, and composes the linked native
colorbar. Image rendering and image-texel query/readback remain independently capability-gated.

## Guides and view state

Use `set_xlim`, `set_ylim`, or `set_view2d` for semantic ranges. Labels, explicit ticks, grids, and
titles are guide state rather than extra data visuals:

```python
figure, axes = vp.subplots()
axes.plot([0.0, 1.0], [0.0, 1.0])
axes.set_view2d(xlim=(0.0, 1.0), ylim=(0.0, 1.0), clip=True)
axes.set_xticks([0.0, 0.5, 1.0], ["low", "middle", "high"])
axes.set_yticks([0.0, 1.0])
axes.grid(True, axis="y")
axes.set_title("Guides remain semantic")
```

Providers may differ in fonts, metrics, antialiasing, and guide layout. Unsupported guide paths
must be diagnosed rather than silently advertised.

## 3D plotting, camera, and lighting

Request `projection="3d"` and add DATA-space visuals:

```python
import vispy2 as vp

figure, axes = vp.subplots(projection="3d")
axes.mesh(
    [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.5]],
    [[0, 1, 2]],
    color=[70, 130, 220, 255],
)
axes.spheres([0.0], [0.0], [0.8], radius=0.25, color=[230, 57, 70, 255])
axes.vectors([0.0], [0.0], [0.0], [0.4], [0.2], [0.6])
axes.text([0.0], [0.0], [1.1], ["DATA-space anchor"])
axes.fit_camera(margin=1.2)
figure.savefig("scene.png")
```

Supported 3D families are mesh, sphere, vector, primitive, pixel, and screen-facing billboard
text. Matplotlib projects several families into deterministic 2D artists. Datoviz uses retained
DATA-space paths where its probed capabilities prove them.

`set_camera`, `set_perspective`, `set_orthographic`, `fit_camera`, `orbit`, `pan`, `zoom`, and
`reset_camera` update canonical semantic `View3D` state. They retain no backend objects.
Programmatic camera states work with both qualified backends. `fit_camera` includes sphere radii,
vector endpoints, and other finite DATA-space bounds.

Flat-Lambert lighting is an explicit, narrow semantic path:

```python
figure, axes = vp.subplots(projection="3d")
axes.mesh(
    [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.8]],
    [[0, 1, 2]],
    color=[70, 130, 220, 255],
    shading="flat_lambert",
    normal_mode="face",
    normal_generation="face_flat",
)
axes.set_lighting(
    ambient_light_intensity=0.2,
    direction_to_light=(-1.0, -1.0, -1.0),
    directional_light_intensity=0.8,
)
axes.fit_camera()
```

This contract has one scalar ambient term and one optional white directional light. Check every
required versioned mesh, normal, lighting, and View3D capability before using a strict backend
path. Textures and explicit lighting are mutually exclusive in the current mesh contract.

## Output and session ownership

`Figure.savefig()` and blocking `Figure.show()` are Matplotlib one-shot conveniences. They create
and close a session internally:

```python
figure, axes = vp.subplots()
axes.scatter([0.0], [0.0])
figure.savefig("point.png")
```

Use an explicit caller-owned session for Datoviz, backend selection, non-blocking display, layout
queries, or interactive lifecycle control:

```python
with vp.open_session("datoviz", require={"visual.points"}) as session:
    figure.display(session, block=False)
    session.run()
```

The context manager owns cleanup. `Figure`, `Axes`, and `Scene` never retain the session or native
renderer. Calling `figure.show(block=False)` without an explicit session is an error.

## Queries

Keep one caller-owned session open for the render/query sequence:

```python
import vispy2 as vp
from gsp.protocol import QueryPayload, QueryRequest

figure, axes = vp.subplots()
axes.scatter([0.0], [0.0], size=20.0)
request = QueryRequest(
    id="query:point",
    panel_id=axes.panel.id,
    coordinate=(0.0, 0.0),
    requested_payload=(QueryPayload.IDENTITY,),
)
with vp.open_session("matplotlib", require={"query.panel", "visual.points"}) as session:
    figure.display(session, block=False)
    result = figure.query(session, request)
print(result.status, result.hits)
```

`Figure.query` neither creates nor closes a session. Redisplay after changing figure state.
Point identity is the qualified public path. Unsupported families return structured
`UNSUPPORTED`; lifecycle errors remain exceptions. Comprehensive 3D picking, occlusion picking,
sphere/vector item picking, and per-glyph query are outside the current release scope.

## Capabilities and limitations

Ordinary capabilities describe provider surfaces such as `visual.mesh` and `output.file`.
Versioned capabilities prove stricter semantic paths:

```python
with vp.open_session("datoviz", require={"output.file", "visual.mesh"}) as session:
    required = "view3d.static.perspective.v1"
    if not session.capabilities.supports_view3d_capability(required):
        raise RuntimeError(f"missing {required}")
```

The block is executable when `vp`, the provider, and the Datoviz runtime are available.
Matplotlib is the deterministic reference/publication path, with documented 3D projection,
depth, sphere, font, and raster adaptations. Datoviz is the flagship GPU path, but capabilities
depend on the installed binding.

Current product boundaries:

- `Figure.to_scene()` requires exactly one 2D or 3D axes;
- VisPy2 produces semantic snapshots and imports no concrete adapter;
- DATA-space `imshow` and linked colorbars require the qualified Datoviz retained-image binding;
- live Datoviz View3D navigation is experimental, opt-in, and caller-owned;
- fonts, text metrics, antialiasing, raster sizes, and some guide behavior vary by backend;
- unsupported behavior must fail through capabilities, diagnostics, or structured query results.

See the [API reference](api-reference.md), [gallery](gallery.md),
[capability matrix](capability-matrix.md), and
[producer/backend boundary](producer-and-backends.md) for exact contracts and evidence.
