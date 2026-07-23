# VisPy2 user guide

VisPy2 is the high-level plotting producer for GSP. It owns semantic figure, axes, visual, guide,
and camera state. GSP sessions own backend selection, native resources, display loops, output,
and queries.

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

## 2D plotting

Create one figure and one axes, add semantic visuals, then use Matplotlib's one-shot file
convenience or an explicit session:

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0.0, 1.0], [1.0, 0.0], size=[12.0, 20.0])
axes.vectors([0.0], [0.0], [0.6], [0.4])
axes.text([0.5], [0.8], ["two-dimensional"])
axes.set_xlim(-0.2, 1.2)
axes.set_ylim(-0.2, 1.2)
figure.savefig("plot.png")
```

The priority 2D methods are `scatter`, `markers`, `pixels`, `vectors`, `primitives`, and `text`.
Positions are DATA-space unless documented otherwise. Sizes and widths are logical canvas pixels.
Colors are RGBA8. The bounded primitive escape hatch accepts point-list, line-list, line-strip,
triangle-list, and triangle-strip topologies; it does not expose shaders or pipelines.

## 3D plotting and camera

Request `projection="3d"` and add DATA-space visuals:

```python
import vispy2 as vp

figure, axes = vp.subplots(projection="3d")
axes.mesh(
    [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.5]],
    [[0, 1, 2]],
    color=[70, 130, 220, 255],
)
axes.spheres([0.0], [0.0], [0.8], radius=0.25)
axes.fit_camera(margin=1.2)
figure.savefig("scene.png")
```

`set_camera`, `set_perspective`, `set_orthographic`, `fit_camera`, `orbit`, `pan`, `zoom`, and
`reset_camera` update canonical semantic View3D state. They do not retain backend objects.
Programmatic camera captures work with both qualified backends. If actions follow a tight fit,
set a safe near/far interval after fitting, as gallery 4 demonstrates.

Supported priority 3D visuals are mesh, sphere, vector, primitive, pixel, and billboard text.
Matplotlib projects several families into deterministic 2D artists. Datoviz uses retained
DATA-space paths where its probed capabilities prove them. Check both the ordinary visual
capability and every required versioned View3D capability before rendering.

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
`UNSUPPORTED`; comprehensive 3D picking, occlusion picking, and per-glyph query are future work.

## Capabilities and limitations

Use ordinary requirements when opening a session and versioned checks for View3D semantics:

```python
with vp.open_session("datoviz", require={"output.file", "visual.mesh"}) as session:
    required = "view3d.static.perspective.v1"
    if not session.capabilities.supports_view3d_capability(required):
        raise RuntimeError(f"missing {required}")
```

The block is executable when `vp`, the provider, and the Datoviz runtime are available.
Matplotlib is the deterministic reference/publication path, but its projected spheres, vectors,
primitives, pixels, and billboards are documented adaptations. Datoviz is the flagship GPU path,
but capability availability depends on the installed v0.4 binding. Native titles, guides, fonts,
text metrics, antialiasing, and raster sizes differ. Live Datoviz View3D navigation is
experimental and requires opt-in plus human review.

See the [gallery](gallery.md), [capability matrix](capability-matrix.md), and
[producer/backend boundary](producer-and-backends.md) for exact evidence.
