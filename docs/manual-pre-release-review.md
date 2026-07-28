# VisPy2 manual pre-release review workbook

This is the linear, human-in-the-loop review for the first experimental VisPy2/GSP release. Read
it from beginning to end. Run the exercises, inspect the results, and write observations directly
into a copy of this file or a separate review note. This workbook does not authorize version
changes, tags, uploads, or a release.

The review covers:

- the public VisPy2 plotting API;
- the backend-neutral GSP scene/session boundary;
- the Matplotlib reference and publication path;
- the Datoviz retained GPU path;
- documented adaptations, experimental behavior, and unsupported behavior;
- enough implementation structure to assess whether the public claims are honest.

The implementation baselines when this workbook was written were GSP `fd20c94`, VisPy2 `c51ca4c`,
and Datoviz `b45d692e4`. Record the exact commits you actually review in section 1.

## Review rules

Use these severities consistently:

| Severity | Meaning |
|---|---|
| **BLOCKER** | Crash, hang, wrong scientific data, resource leak, capability lie, silent semantic loss, or unusable core API |
| **BUG** | Incorrect bounded behavior with a practical workaround |
| **DOC** | Behavior is coherent, but the public explanation or example is missing or misleading |
| **ADAPTATION** | Expected backend-specific realization that is explicitly disclosed |
| **DEFERRED** | Useful feature that is honestly unsupported for this experimental release |
| **PREFERENCE** | Naming, aesthetics, or ergonomics worth discussing but not objectively incorrect |

Do not demand pixel identity between backends. Do demand the same semantic scene, coherent geometry,
truthful capabilities, a usable live Matplotlib reference, and fail-closed Datoviz behavior.

For each finding, record:

| ID | Section | Backend | Expected | Observed | Severity | Evidence |
|---|---|---|---|---|---|---|
| R-001 |  |  |  |  |  |  |

Stop the release review and report immediately if a native process crashes or hangs, an advertised
capability fails, data are placed incorrectly, or unsupported behavior silently falls back.

## 1. Prepare one terminal and launch paired windows

Use one terminal in the VisPy2 repository. The examples below assume GSP and Datoviz are sibling
checkouts named `gsp` and `datoviz`.

Run this setup once:

```console
cd /path/to/vispy2
export VISPY2_REVIEW_OUTPUT="$(mktemp -d "${TMPDIR:-/tmp}/vispy2-review.XXXXXX")"
export VISPY2_REVIEW_PYTHON="$(cd ../gsp && pwd)/.venv/bin/python"
export GSP_DATOVIZ_SOURCE="$(cd ../datoviz && pwd)"
export PYTHONPATH="src:../gsp/packages/gsp-core/src:../gsp/packages/gsp-matplotlib/src:../gsp/packages/gsp-datoviz/src:../datoviz"
echo "review output: $VISPY2_REVIEW_OUTPUT"
```

The output directory is used only by the optional automated wheel qualification near the end. You
do not need to open or review its PNG files.

Record exact repository state:

```console
git status --short --branch
git rev-parse HEAD
git -C ../gsp status --short --branch
git -C ../gsp rev-parse HEAD
git -C ../datoviz status --short --branch
git -C ../datoviz rev-parse HEAD
"$VISPY2_REVIEW_PYTHON" --version
```

Expected:

- VisPy2 and GSP are clean.
- Datoviz may contain unrelated owner files, but no review command should modify them.
- Python is 3.13.
- Record all three commit hashes below.

| Component | Reviewed commit | Worktree note |
|---|---|---|
| VisPy2 |  |  |
| GSP |  |  |
| Datoviz |  |  |
| Python |  |  |

Make sure the terminal is configured for real GUI windows:

```console
unset MPLBACKEND
unset GSP_TEST
```

The primary human-review command opens matching Matplotlib and Datoviz windows concurrently from
this one terminal:

```console
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py all
```

The runner visits these cases in order: priority 2D, perspective 3D, orthographic 3D, flat
Lambert, then camera fit/orbit/pan/zoom/reset. For each case it:

1. starts one isolated child process per backend;
2. opens both live windows at the same time;
3. applies the same resolved plot viewport to both 3D windows;
4. waits while you move the windows side by side and inspect them;
5. continues only after you close both windows.

To repeat only one case:

```console
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py priority-2d
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py perspective-3d
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py orthographic-3d
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py flat-lambert
"$VISPY2_REVIEW_PYTHON" examples/manual_live_compare.py camera-pan
```

Use terminal `Ctrl-C` to terminate both children if either window cannot be closed. Backend
selection is explicit inside each child: one calls `open_session("matplotlib")`, the other calls
`open_session("datoviz")`. The two GUI event loops never share one process.

After the paired visual pass, start IPython in the same terminal for the API-oriented sections:

```console
"$VISPY2_REVIEW_PYTHON" -m IPython
```

If IPython is missing, install it into this development environment only, then retry:

```console
uv pip install --python "$VISPY2_REVIEW_PYTHON" "ipython>=9,<10"
```

The guaranteed fallback is the ordinary interpreter:

```console
"$VISPY2_REVIEW_PYTHON" -i
```

Every Matplotlib `figure.show()` call blocks until you close its window. Every Datoviz block calls
`session.run()` and likewise returns only after you close the native window. Keep the window open
for as long as you need; close it to continue linearly.

**Checkpoint**

- [ ] Exact commits and Python version recorded.
- [ ] One `manual_live_compare.py` case opened both backend windows concurrently.
- [ ] The terminal imports the current VisPy2 source.
- [ ] Review output is outside every repository.

## 2. Inspect the public API before plotting

Paste this complete block into IPython:

```python
from importlib.util import find_spec
import inspect
import sys

import gsp
import vispy2 as vp

print("python:", sys.version)
print("vispy2:", vp.__version__)
print("public exports:", vp.__all__)

for public_type in (vp.Figure, vp.Axes, vp.Axes3D):
    print(f"\n{public_type.__name__}")
    for name, member in inspect.getmembers(public_type):
        if name.startswith("_") or not callable(member):
            continue
        try:
            signature = inspect.signature(member)
        except (TypeError, ValueError):
            continue
        print(f"  {name}{signature}")

print("\nbackend packages are optional:")
print("  matplotlib adapter:", find_spec("gsp_matplotlib") is not None)
print("  datoviz adapter:", find_spec("gsp_datoviz") is not None)
print("  datoviz runtime:", find_spec("datoviz") is not None)
print("\ninstalled metadata:", gsp.discover_backends())
```

Expected:

- the main vocabulary is `Figure`, `Axes`, `Axes3D`, plotting functions, and `open_session`;
- `Axes` owns 2D semantic state and `Axes3D` owns 3D camera/lighting state;
- concrete backends are optional packages rather than VisPy2 imports;
- discovery lists Matplotlib and Datoviz without opening a native window.

Review questions:

- [ ] Can you find the likely method for each visual without reading source?
- [ ] Are 2D and 3D names consistent?
- [ ] Are `vectors` and `quiver` clearly aliases rather than Matplotlib keyword emulation?
- [ ] Is explicit session ownership understandable?
- [ ] Do any signatures expose backend handles, shaders, pipelines, or native objects?
- [ ] Are any defaults surprising enough to be a bug or documentation problem?

Notes:

| Topic | Observation | Severity |
|---|---|---|
| Naming |  |  |
| Defaults |  |  |
| Return values |  |  |
| Discoverability |  |  |

## 3. Build and inspect a complete 2D semantic figure

Goal: exercise the priority 2D visual vocabulary and guides through public VisPy2 methods in a live
Matplotlib window.

Paste into IPython:

```python
import vispy2 as vp
from gsp.protocol import CanvasSize

figure, axes = vp.subplots(canvas_size=CanvasSize.pixel_exact(800, 600))

axes.scatter(
    [-1.7, -1.3, -0.9],
    [1.0, 1.25, 0.9],
    size=[14.0, 24.0, 18.0],
    color=[31, 119, 180, 255],
    id="review:points",
)
axes.markers(
    [-1.7, -1.3, -0.9],
    [0.25, 0.5, 0.15],
    shape=["disc", "square", "triangle"],
    size=26.0,
    color=[214, 39, 40, 255],
    id="review:markers",
)
axes.pixels(
    [-1.7, -1.3, -0.9],
    [-0.7, -0.55, -0.8],
    size=[5.0, 10.0, 15.0],
    color=[44, 160, 44, 255],
    id="review:pixels",
)
axes.segments(
    [[-0.25, 1.15], [0.25, 1.15]],
    [[0.05, 0.75], [0.55, 0.75]],
    width=[2.0, 5.0],
    color=[[23, 190, 207, 255], [23, 190, 207, 255]],
    id="review:segments",
)
axes.path(
    [[-0.25, 0.3], [0.05, 0.5], [0.35, 0.1], [0.65, 0.35]],
    color=[127, 127, 127, 255],
    width=3.0,
    join="round",
    id="review:path",
)
axes.vectors(
    [0.95, 1.35, 1.75],
    [1.0, 1.0, 1.0],
    [0.25, -0.15, 0.2],
    [0.35, 0.4, -0.35],
    width=2.5,
    color=[148, 103, 189, 255],
    id="review:vectors",
)
axes.primitives(
    [[0.85, -0.75], [1.35, 0.0], [1.85, -0.75]],
    topology="triangle_list",
    color=[
        [255, 127, 14, 255],
        [255, 187, 120, 255],
        [255, 127, 14, 255],
    ],
    id="review:primitive",
)
axes.text(
    [0.75],
    [-1.0],
    ["semantic 2D"],
    font_size_px=16.0,
    color=[35, 35, 35, 255],
    id="review:text",
)
axes.set_xlim(-2.0, 2.1)
axes.set_ylim(-1.25, 1.55)
axes.set_xticks([-2.0, -1.0, 0.0, 1.0, 2.0])
axes.set_yticks([-1.0, 0.0, 1.0])
axes.set_xlabel("semantic x")
axes.set_ylabel("semantic y")
axes.set_title("Manual review: priority 2D")
axes.grid(True)

scene = figure.to_scene()
print("visual types:", [type(visual).__name__ for visual in scene.visuals])
print("visual ids:", [visual.id for visual in scene.visuals])
print("view:", scene.view2d)

print("Close the Matplotlib window to continue.")
figure.show()
```

Inspect the live window. Expected:

- all eight visual groups are present and separated;
- square/triangle/disc markers differ;
- pixel sizes increase from left to right;
- vectors preserve direction;
- path and segment widths are legible;
- the primitive forms one triangle;
- labels, title, grid, ticks, and axes are coherent;
- the live canvas is 800×600 logical pixels in the qualified environment.

Review:

- [ ] Positions match the supplied data.
- [ ] Relative logical sizes and widths are credible.
- [ ] Colors and alpha are unsurprising.
- [ ] Guide layout leaves enough plot area.
- [ ] IDs and scene ordering are understandable.
- [ ] Invalid or ambiguous API choices found: ______________________________

## 4. Review scalar images, color mapping, and a colorbar

Paste into IPython:

```python
import numpy as np
import vispy2 as vp
from gsp.protocol import CanvasSize

values = np.linspace(-1.0, 1.0, 20 * 30, dtype=np.float32).reshape(20, 30)
values += 0.35 * np.sin(np.linspace(0.0, 4.0 * np.pi, 30, dtype=np.float32))[None, :]

figure, axes = vp.subplots(canvas_size=CanvasSize.pixel_exact(800, 600))
scale = axes.color_scale(
    cmap="viridis",
    clim=(-1.35, 1.35),
    id="review:viridis",
    description="manual scalar-field scale",
)
image = axes.imshow(
    values,
    extent=(-3.0, 3.0, -2.0, 2.0),
    origin="lower",
    interpolation="nearest",
    color_scale=scale,
    id="review:scalar-image",
)
axes.colorbar(
    scale,
    label="value",
    ticks=[-1.0, 0.0, 1.0],
    tick_labels=["low", "zero", "high"],
    linked_visual_ids=[image.id],
)
axes.set_xlabel("x")
axes.set_ylabel("y")
axes.set_title("Manual review: scalar image")

scene = figure.to_scene()
print("color scales:", scene.color_scales)
print("colorbars:", scene.colorbar_guides)
print("Close the Matplotlib window to continue.")
figure.show()
```

Expected:

- the field uses the full viridis ramp;
- lower-origin orientation is visually testable;
- nearest interpolation preserves discrete cells;
- colorbar ticks and labels correspond to the declared `clim`;
- the scene contains a shared color-scale resource rather than baked backend colors.

Review:

- [ ] Origin and extent are correct.
- [ ] `clim` and colorbar communicate the same numeric mapping.
- [ ] The API makes shared color scales understandable.
- [ ] Nearest interpolation is visually distinct.
- [ ] Missing review case or confusing behavior: ___________________________

## 5. Build the priority 3D scene and flat-Lambert mesh

Goal: review all priority 3D visual families, camera fitting, and the deliberately narrow
ambient-plus-one-directional-light contract.

Paste into IPython:

```python
import numpy as np
import vispy2 as vp
from gsp.protocol import CanvasSize

figure, axes = vp.subplots(
    projection="3d",
    canvas_size=CanvasSize.pixel_exact(800, 600),
)

positions = np.asarray(
    [[-1.4, -0.8, -0.4], [0.0, -0.8, -0.4], [-0.7, 0.6, 0.0], [-0.7, -0.1, 1.1]],
    dtype=np.float32,
)
faces = np.asarray(
    [[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]],
    dtype=np.uint32,
)
axes.mesh(
    positions,
    faces,
    color=[70, 130, 220, 255],
    shading="flat_lambert",
    normal_mode="face",
    normal_generation="face_flat",
    id="review:lit-mesh",
)
axes.set_lighting(
    ambient_light_intensity=0.18,
    direction_to_light=(-1.0, -1.0, -1.0),
    directional_light_intensity=0.82,
)
axes.spheres(
    [0.45, 1.25],
    [-0.2, 0.3],
    [0.0, 0.35],
    radius=[0.35, 0.22],
    color=[[230, 57, 70, 255], [42, 157, 143, 255]],
    id="review:spheres",
)
axes.vectors(
    [-1.15, 0.4, 1.25],
    [0.75, 0.8, 0.3],
    [0.1, 0.0, 0.35],
    [0.0, 0.35, 0.25],
    [0.35, 0.25, -0.2],
    [0.55, 0.45, 0.35],
    width=3.0,
    color=[244, 162, 97, 255],
    id="review:vectors-3d",
)
axes.primitives(
    [[0.4, -0.9, 0.1], [0.95, -0.45, 0.4], [1.45, -0.9, 0.7]],
    topology="triangle_list",
    color=[102, 51, 153, 255],
    id="review:primitive-3d",
)
axes.pixels(
    [-1.15, -0.8, -0.45],
    [0.9, 1.0, 0.9],
    [1.2, 1.25, 1.3],
    size=[7.0, 12.0, 17.0],
    color=[255, 215, 0, 255],
    id="review:pixels-3d",
)
axes.text(
    [-0.7, 0.85],
    [-0.2, 0.2],
    [1.45, 1.15],
    ["lit mesh", "3D scene"],
    font_size_px=16.0,
    color=[25, 25, 25, 255],
    anchor_x="center",
    anchor_y="bottom",
    id="review:billboards",
)
axes.set_camera(
    eye=(4.0, -7.0, 3.8),
    target=(0.0, 0.0, 0.3),
    up=(0.0, 0.0, 1.0),
)
axes.set_perspective(fov_y_degrees=42.0, near=0.1, far=100.0)
axes.fit_camera(margin=1.2)
axes.orbit(yaw_radians=0.25, pitch_radians=-0.12)
axes.set_title("Manual review: perspective 3D")

scene = figure.to_scene()
print("visual types:", [type(visual).__name__ for visual in scene.visuals])
print("camera:", scene.view3d.camera)
print("projection:", scene.view3d.projection)
print("lighting:", scene.view3d.ambient_light_intensity, scene.view3d.directional_light)

print("Close the Matplotlib window to continue.")
figure.show()
```

Expected Matplotlib behavior:

- mesh faces have flat, distinct light intensities;
- spheres are flat projected circles with adapted center-depth ordering;
- vectors, pixels, primitive geometry, and text are deterministic projected adaptations;
- text remains screen-facing and legible;
- the camera contains the whole scene.

Expected Datoviz differences, reviewed later:

- spheres are natively shaded analytic impostors;
- retained mesh and supported visuals use native GPU depth/rasterization;
- font metrics, vector heads, billboard placement, and antialiasing may differ;
- these are not bugs unless data placement or advertised semantics are lost.

Review:

- [ ] All six 3D families are visible and correctly associated.
- [ ] Mesh lighting communicates 3D shape.
- [ ] The fitted scale is sensible and nothing is clipped.
- [ ] Billboard size is readable.
- [ ] Adapted Matplotlib depth/order limitations are acceptable.
- [ ] API concern or missing first-release visual: _________________________

## 6. Review orthographic projection and camera transitions

Paste this independent block into IPython:

```python
import numpy as np
import vispy2 as vp
from gsp.protocol import CanvasSize

figure, axes = vp.subplots(
    projection="3d",
    canvas_size=CanvasSize.pixel_exact(800, 600),
)
axes.mesh(
    np.asarray(
        [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 0.4], [0.0, 0.0, 1.5]],
        dtype=np.float32,
    ),
    np.asarray([[0, 1, 2], [0, 3, 1], [1, 3, 2], [2, 3, 0]], dtype=np.uint32),
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
axes.set_camera(
    eye=(3.5, -6.0, 3.5),
    target=(0.0, 0.0, 0.35),
    up=(0.0, 0.0, 1.0),
)
axes.set_orthographic(near=0.0, far=100.0)
axes.fit_camera(margin=1.2)

states = {}
states["fit"] = axes.view
print("fit:", states["fit"].camera)
figure.show()

states["orbit"] = axes.orbit(yaw_radians=0.35, pitch_radians=-0.15)
print("orbit:", states["orbit"].camera)
figure.show()

states["pan"] = axes.pan(right=0.18, up=-0.08)
print("pan:", states["pan"].camera)
figure.show()

states["zoom"] = axes.zoom(1.25)
print("zoom:", states["zoom"].camera)
figure.show()

states["reset"] = axes.reset_camera()
print("reset:", states["reset"].camera)
figure.show()

for name, view in states.items():
    print(name, "revision=", view.revision, "camera=", view.camera)
    print("  lighting=", view.ambient_light_intensity, view.directional_light)
```

Expected:

- five live windows appear sequentially and are visually distinct;
- orbit changes viewing direction, pan changes target, and zoom changes scale;
- reset restores the construction camera/projection rather than erasing lighting;
- revision increases monotonically;
- every state preserves the ambient and directional light.

Review:

- [ ] Orthographic geometry has no unintended perspective shrinkage.
- [ ] Fit, orbit, pan, and zoom each do what their names imply.
- [ ] Reset behavior is what you would expect as an API user.
- [ ] Lighting survives all transitions.
- [ ] Camera API improvement request: ______________________________________

## 7. Review backend discovery and truthful capabilities

Paste into IPython:

```python
import gsp

ordinary_required = {"visual.mesh"}
versioned_required = {
    "meshvisual.positions3d.data.view3d.v1",
    "view3d.static.perspective.v1",
}

for info in gsp.discover_backends(probe=True):
    print(f"\nbackend={info.name!r} installed={info.installed} available={info.available}")
    print("diagnostics:", info.diagnostics)
    print("missing ordinary:", sorted(ordinary_required - info.capabilities))
    print("missing versioned:", sorted(versioned_required - info.capabilities))

    if not info.available:
        continue
    with gsp.open_session(info.name, require=ordinary_required) as session:
        snapshot = session.capabilities
        print("snapshot:", snapshot.snapshot_id)
        for capability in sorted(versioned_required):
            print(capability, snapshot.supports_view3d_capability(capability))

with gsp.open_session(
    prefer=("datoviz", "matplotlib"),
    require=ordinary_required,
) as selected:
    print("\nordered selection:", selected.backend_name)
```

Expected:

- discovery is lazy and provides useful availability diagnostics;
- ordered selection chooses the first eligible backend, not an arbitrary plugin;
- ordinary provider capabilities and typed/versioned snapshot checks are both visible;
- no renderer is created merely to inspect metadata;
- unavailable or incomplete Datoviz bindings fail closed.

Review:

- [ ] The difference between ordinary and versioned capabilities is understandable.
- [ ] Diagnostics are specific enough to act on.
- [ ] Selection is explicit and predictable.
- [ ] Capability wording matches actual backend behavior.
- [ ] Suspicious or overstated capability: __________________________________

Optional shortcut:

```console
"$VISPY2_REVIEW_PYTHON" examples/gallery_06_capabilities.py
```

## 8. Review explicit session ownership

Paste into IPython:

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0.0, 1.0], [1.0, 0.0], size=[18.0, 28.0])
axes.set_title("Caller-owned session")

with vp.open_session(
    "matplotlib",
    require={"visual.points"},
) as session:
    print("opened:", session.backend_name)
    result = figure.display(session, block=False)
    print("display result:", type(result).__name__)
    print("session diagnostics:", session.diagnostics)
    print("Close the Matplotlib window to leave the session.")
    session.run()

print("session context exited")
```

Expected:

- VisPy2 owns semantic state;
- the caller owns the session lifetime;
- the adapter owns native resources and releases them on context exit;
- `Figure.show()` is the simple blocking Matplotlib path, while explicit sessions support
  capabilities, queries, controlled display lifetime, and Datoviz.

Review:

- [ ] Ownership is understandable without reading implementation.
- [ ] Context-manager cleanup feels sufficient.
- [ ] No backend object leaks into `Figure`, `Axes`, or the scene.
- [ ] Session ergonomics concern: ___________________________________________

## 9. Review supported and unsupported queries

Paste into IPython:

```python
import vispy2 as vp
from gsp.protocol import QueryPayload, QueryRequest, QueryStatus

point_figure, point_axes = vp.subplots()
point_axes.scatter(
    [0.0],
    [0.0],
    size=24.0,
    color=[31, 119, 180, 255],
    id="review:query-point",
)
point_request = QueryRequest(
    id="review:point-query",
    panel_id=point_axes.panel.id,
    coordinate=(0.0, 0.0),
    requested_payload=(QueryPayload.IDENTITY,),
)
with vp.open_session(
    "matplotlib",
    require={"query.panel", "visual.points"},
) as session:
    point_figure.display(session, block=False)
    point_result = point_figure.query(session, point_request)
    print("point:", point_result.status, point_result.hits)
    print("Close the live point-query window to continue.")
    session.run()

assert point_result.status is QueryStatus.HIT

sphere_figure, sphere_axes = vp.subplots(projection="3d")
sphere_axes.spheres(
    [0.0],
    [0.0],
    [0.0],
    radius=0.5,
    color=[230, 57, 70, 255],
)
sphere_request = QueryRequest(
    id="review:sphere-query",
    panel_id=sphere_axes.panel.id,
    coordinate=(0.0, 0.0),
    requested_payload=(QueryPayload.IDENTITY,),
)
with vp.open_session(
    "matplotlib",
    require={"query.panel", "visual.sphere"},
) as session:
    sphere_figure.display(session, block=False)
    sphere_result = sphere_figure.query(session, sphere_request)
    print("sphere:", sphere_result.status, sphere_result.diagnostic)
    print("Close the live sphere window to continue.")
    session.run()

assert sphere_result.status is QueryStatus.UNSUPPORTED
```

Expected:

- the rendered point returns `HIT` with caller identity preserved;
- the unproven sphere/3D query returns structured `UNSUPPORTED`, not a fabricated miss or exception;
- the same caller-owned session is used for display and query;
- comprehensive picking is explicitly outside this first release.

Review:

- [ ] The supported point result is sufficient and correctly structured.
- [ ] Unsupported behavior is honest and actionable.
- [ ] The display-before-query lifecycle is clear.
- [ ] Query API concern or essential missing first-release case: __________________

Optional shortcut:

```console
"$VISPY2_REVIEW_PYTHON" examples/gallery_07_queries.py
```

## 10. Run one isolated native Datoviz 2D case

Exit IPython with `Ctrl-D`. In the same terminal, start a fresh ordinary Python process:

```console
"$VISPY2_REVIEW_PYTHON"
```

Paste this complete block, inspect and close the live window, then press `Ctrl-D`:

```python
import vispy2 as vp
from gsp.protocol import CanvasSize

figure, axes = vp.subplots(canvas_size=CanvasSize.pixel_exact(800, 600))
axes.scatter(
    [-1.0, -0.4, 0.2],
    [0.8, 1.1, 0.75],
    size=[14.0, 24.0, 18.0],
    color=[31, 119, 180, 255],
)
axes.markers(
    [-1.0, -0.4, 0.2],
    [0.0, 0.25, -0.1],
    shape=["disc", "square", "triangle"],
    size=26.0,
    color=[214, 39, 40, 255],
)
axes.pixels(
    [-1.0, -0.4, 0.2],
    [-0.7, -0.55, -0.8],
    size=[5.0, 10.0, 15.0],
    color=[44, 160, 44, 255],
)
axes.segments(
    [[-0.15, 1.15], [0.25, 1.15]],
    [[0.05, 0.75], [0.45, 0.75]],
    width=[2.0, 5.0],
    color=[23, 190, 207, 255],
)
axes.path(
    [[-0.15, 0.3], [0.1, 0.5], [0.35, 0.1], [0.6, 0.35]],
    color=[127, 127, 127, 255],
    width=3.0,
    join="round",
)
axes.vectors(
    [0.75, 1.2],
    [0.8, 0.8],
    [0.25, -0.2],
    [0.35, 0.4],
    width=2.5,
    color=[148, 103, 189, 255],
)
axes.primitives(
    [[0.65, -0.75], [1.05, -0.15], [1.45, -0.75]],
    topology="triangle_list",
    color=[255, 127, 14, 255],
)
axes.text(
    [0.75],
    [-0.8],
    ["Datoviz 2D"],
    font_size_px=16.0,
    color=[35, 35, 35, 255],
)
axes.set_xlim(-1.4, 1.5)
axes.set_ylim(-1.1, 1.4)
axes.grid(True)
axes.set_title("Manual Datoviz 2D")

with vp.open_session(
    "datoviz",
    require={
        "visual.points",
        "visual.markers",
        "visual.paths",
        "visual.pixels",
        "visual.primitive",
        "visual.segments",
        "visual.vector",
        "visual.text",
    },
) as session:
    figure.display(session, block=False)
    print("Inspect the live Datoviz window; close it to continue.")
    session.run()
```

Expected:

- a live 800×600 Datoviz window opens and remains until you close it;
- positions, relative sizes, vector direction, and text association match the semantic input;
- rasterization, font metrics, vector caps, and guides may differ from Matplotlib;
- the qualified Datoviz binding has no public panel-title renderer, so a missing title is an
  explicitly unsupported guide path rather than silent title support;
- the process exits cleanly after `Ctrl-D`.

Review:

- [ ] The live scene is complete.
- [ ] Data placement matches Matplotlib.
- [ ] Differences are documented adaptations rather than semantic loss.
- [ ] Process exits without crash or hang.
- [ ] Datoviz 2D finding: _________________________________________________

Current high-level image boundary: section 4 is Matplotlib-only. VisPy2 `imshow()` currently emits
a DATA-space `ImageVisual`, while the qualified Datoviz v0.4 image lowering accepts only NDC-space
image extents. Therefore there is no honest live Datoviz window for the same public high-level
scalar-image example yet. Record whether this is acceptable as **DEFERRED** for the experimental
release or a release-blocking API/backend coverage gap; do not substitute an old PNG.

## 11. Run one isolated native Datoviz 3D and lighting case

After the previous process exits, start another fresh ordinary Python process in the same terminal:

```console
"$VISPY2_REVIEW_PYTHON"
```

Paste this block, inspect and close the live window, then press `Ctrl-D`:

```python
import numpy as np
import vispy2 as vp
from gsp.protocol import (
    CanvasSize,
    MESH3D_DATA_VIEW3D_CAPABILITY,
    MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
    MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
    MESH_NORMALS_FACE3D_CAPABILITY,
    VIEW3D_LIGHT_AMBIENT_CAPABILITY,
    VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
    VIEW3D_STATIC_PERSPECTIVE_CAPABILITY,
)

figure, axes = vp.subplots(
    projection="3d",
    canvas_size=CanvasSize.pixel_exact(800, 600),
)
axes.mesh(
    np.asarray(
        [[-1.4, -0.8, -0.4], [0.0, -0.8, -0.4], [-0.7, 0.6, 0.0], [-0.7, -0.1, 1.1]],
        dtype=np.float32,
    ),
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
axes.spheres(
    [0.45, 1.25],
    [-0.2, 0.3],
    [0.0, 0.35],
    radius=[0.35, 0.22],
    color=[[230, 57, 70, 255], [42, 157, 143, 255]],
)
axes.vectors(
    [-1.15, 0.4, 1.25],
    [0.75, 0.8, 0.3],
    [0.1, 0.0, 0.35],
    [0.0, 0.35, 0.25],
    [0.35, 0.25, -0.2],
    [0.55, 0.45, 0.35],
    width=3.0,
    color=[244, 162, 97, 255],
)
axes.primitives(
    [[0.4, -0.9, 0.1], [0.95, -0.45, 0.4], [1.45, -0.9, 0.7]],
    topology="triangle_list",
    color=[102, 51, 153, 255],
)
axes.pixels(
    [-1.15, -0.8, -0.45],
    [0.9, 1.0, 0.9],
    [1.2, 1.25, 1.3],
    size=[7.0, 12.0, 17.0],
    color=[255, 215, 0, 255],
)
axes.text(
    [-0.7, 0.85],
    [-0.2, 0.2],
    [1.45, 1.15],
    ["lit mesh", "3D scene"],
    font_size_px=16.0,
    color=[25, 25, 25, 255],
    anchor_x="center",
    anchor_y="bottom",
)
axes.set_camera(
    eye=(4.0, -7.0, 3.8),
    target=(0.0, 0.0, 0.3),
    up=(0.0, 0.0, 1.0),
)
axes.set_perspective(fov_y_degrees=42.0, near=0.1, far=100.0)
axes.fit_camera(margin=1.2)
axes.orbit(yaw_radians=0.25, pitch_radians=-0.12)

required_view3d = {
    MESH3D_DATA_VIEW3D_CAPABILITY,
    MESH_MATERIAL_FLAT_LAMBERT_CAPABILITY,
    MESH_NORMAL_GENERATION_FACE_FLAT_CAPABILITY,
    MESH_NORMALS_FACE3D_CAPABILITY,
    VIEW3D_LIGHT_AMBIENT_CAPABILITY,
    VIEW3D_LIGHT_DIRECTIONAL_CAPABILITY,
    VIEW3D_STATIC_PERSPECTIVE_CAPABILITY,
}
with vp.open_session(
    "datoviz",
    require={
        "visual.mesh",
        "visual.pixels",
        "visual.primitive",
        "visual.sphere",
        "visual.text",
        "visual.vector",
        *required_view3d,
    },
) as session:
    for capability in sorted(required_view3d):
        if not session.capabilities.supports_view3d_capability(capability):
            raise RuntimeError(f"Datoviz does not advertise {capability}")
    figure.display(session, block=False)
    print("Inspect the live Datoviz window; close it to continue.")
    session.run()
```

Expected:

- the tetrahedral mesh has at least two large, visibly distinct blue face tones;
- spheres, vectors, primitive geometry, pixels, and billboard text are also visible;
- the initial view clearly communicates 3D shape;
- no unlit fallback occurs;
- every exact capability is checked before native rendering;
- the process exits cleanly.

Review:

- [ ] Lighting and face normals are visibly effective.
- [ ] Geometry and initial camera are sensible.
- [ ] Capability checks fail closed.
- [ ] Process exits without crash or hang.
- [ ] Datoviz 3D finding: _________________________________________________

## 12. Consolidate the live-window comparison

Do not review checked-in images or generated PNGs. Use the paired live windows launched by
`manual_live_compare.py`, the API-focused windows in sections 3–6 and 10–11, and the interactive
window in section 14.

Compare the live realizations in this order:

| Journey | Matplotlib window | Datoviz window | Human check |
|---|---|---|---|
| Priority 2D | `manual_live_compare.py priority-2d` | same command | all families, placement, relative sizes |
| Scalar image/colorbar | section 4 | unavailable through current public VisPy2 DATA-image path | decide whether the documented coverage gap blocks the experiment |
| Perspective 3D | `manual_live_compare.py perspective-3d` | same command | mesh, spheres, vectors, text, depth, framing |
| Orthographic 3D | `manual_live_compare.py orthographic-3d` | same command | projection, primitive, pixels, framing, occlusion |
| Flat Lambert | `manual_live_compare.py flat-lambert` | same command | distinct face intensities and shape |
| Camera fit/orbit/pan/zoom/reset | the five matching `manual_live_compare.py camera-*` cases | same commands, plus section 14 for interactive Datoviz | coherent camera meaning and scale |

Known intentional differences:

- Matplotlib provides native semantic axes and titles; the qualified Datoviz title path is
  unsupported.
- Matplotlib 3D spheres are flat projected circles; Datoviz spheres are natively shaded analytic
  impostors with surface depth.
- Matplotlib 3D vectors, pixels, primitives, and billboards include documented projection/painter
  adaptations.
- fonts, glyph metrics, antialiasing, vector heads, and raster details are backend-specific.
- uniform primitive colors avoid claiming interpolation parity.
- titles and axes must not change the shared data viewport or make Datoviz geometry larger.

Live-window acceptance:

- [ ] Both canvases are 800×600.
- [ ] All data anchors and directions agree.
- [ ] Plot geometry is similarly scaled and centered.
- [ ] Camera states are distinct, coherent, and unclipped.
- [ ] Missing Datoviz title is diagnosed rather than silently claimed.
- [ ] Sphere and font differences match the documented adaptations.
- [ ] Every judgment above came from a live window, not a PNG.

## 13. Optional exact-wheel qualification

This is an automated integrity check, not a visual-review step. It generates PNGs internally
because the validator measures geometry and provenance, but you do not need to open or inspect
them. Skip this section during the human visual review if Mission Control already ran it at the
recorded commit.

From the shell in the same terminal:

```console
mkdir -p "$VISPY2_REVIEW_OUTPUT/wheels"
uv build --wheel --out-dir "$VISPY2_REVIEW_OUTPUT/wheels" ../gsp/packages/gsp-core
uv build --wheel --out-dir "$VISPY2_REVIEW_OUTPUT/wheels" ../gsp/packages/gsp-matplotlib
uv build --wheel --out-dir "$VISPY2_REVIEW_OUTPUT/wheels" ../gsp/packages/gsp-datoviz
uv build --wheel --out-dir "$VISPY2_REVIEW_OUTPUT/wheels" .

"$VISPY2_REVIEW_PYTHON" examples/validate_gallery.py \
  --python "$VISPY2_REVIEW_PYTHON" \
  --output-dir "$VISPY2_REVIEW_OUTPUT/exact-wheel-gallery" \
  --gsp-source ../gsp \
  --vispy2-source . \
  --gsp-core-wheel "$VISPY2_REVIEW_OUTPUT/wheels/gsp_core-0.2.0a1-py3-none-any.whl" \
  --gsp-matplotlib-wheel "$VISPY2_REVIEW_OUTPUT/wheels/gsp_matplotlib-0.2.0a1-py3-none-any.whl" \
  --gsp-datoviz-wheel "$VISPY2_REVIEW_OUTPUT/wheels/gsp_datoviz-0.2.0a1-py3-none-any.whl" \
  --vispy2-wheel "$VISPY2_REVIEW_OUTPUT/wheels/vispy2-0.2.0a1-py3-none-any.whl"
```

Expected:

- fourteen fresh PNGs and a schema-2 manifest;
- exact committed source revisions and wheel hashes;
- no project import outside the isolated wheel site;
- shared 800×600 layout and comparable camera geometry;
- capability and query checks pass;
- stale destination files cannot satisfy the run.

- [ ] Exact-wheel qualification completed.
- [ ] Manifest commits match section 1.
- [ ] The validator reported fourteen fresh captures; no manual PNG inspection was used.
- [ ] Any retry, timeout, or lifecycle diagnostic recorded: __________________

## 14. Review live Datoviz camera behavior

From the shell in the same terminal, run:

```console
GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=1 \
"$VISPY2_REVIEW_PYTHON" examples/gallery_05_datoviz_navigation.py
```

Controls:

- left-drag: orbit;
- right-drag: pan;
- wheel: zoom;
- double-click: reset construction camera;
- close window: normal session cleanup;
- terminal `Ctrl-C`: fallback cleanup.

Review in this order:

1. Confirm the initial tetrahedron has two visibly distinct lit faces.
2. Orbit slowly through a full range and watch face lighting and depth.
3. Pan in several directions.
4. Zoom in and out without losing the object unexpectedly.
5. Double-click reset and compare with the initial view.
6. Close the window and confirm the process exits.
7. Repeat once and use `Ctrl-C` instead of window close.

- [ ] Orbit is natural and stable.
- [ ] Pan direction is natural.
- [ ] Zoom direction and sensitivity are acceptable.
- [ ] Reset is predictable.
- [ ] Lighting remains attached to semantic scene state.
- [ ] Window close exits.
- [ ] Ctrl-C exits.
- [ ] No crash, hang, or leftover process.

Live finding: ________________________________________________________________

## 15. Read representative implementation slices

Do not read every line. Trace representative public calls vertically.

### Slice A: a 2D point

1. VisPy2 producer: [`Axes.scatter`](../src/vispy2/protocol.py)
2. GSP record: [`PointVisual`](../../gsp/packages/gsp-core/src/gsp/protocol/visuals.py)
3. Matplotlib lowering: [`protocol_renderer.py`](../../gsp/packages/gsp-matplotlib/src/gsp_matplotlib/protocol_renderer.py)
4. Datoviz lowering: [`protocol_renderer.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/protocol_renderer.py)

Check:

- [ ] public input is normalized once;
- [ ] IDs and DATA coordinates survive both adapters;
- [ ] adapter-specific raster details do not leak into the protocol;
- [ ] capability claims match the path used.

### Slice B: a lit 3D mesh and camera

1. VisPy2 `Axes3D.mesh`, camera methods, and `set_lighting`:
   [`protocol.py`](../src/vispy2/protocol.py)
2. GSP records and reducers:
   [`visuals.py`](../../gsp/packages/gsp-core/src/gsp/protocol/visuals.py),
   [`view3d.py`](../../gsp/packages/gsp-core/src/gsp/protocol/view3d.py), and
   [`navigation.py`](../../gsp/packages/gsp-core/src/gsp/protocol/navigation.py)
3. Matplotlib adaptation:
   [`protocol_renderer.py`](../../gsp/packages/gsp-matplotlib/src/gsp_matplotlib/protocol_renderer.py)
4. Datoviz retained lowering and capability gate:
   [`protocol_renderer.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/protocol_renderer.py) and
   [`capabilities.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/capabilities.py)

Check:

- [ ] normals and lighting follow the bounded flat-Lambert contract;
- [ ] camera reducers preserve non-camera state;
- [ ] unsupported binding surfaces fail before native calls;
- [ ] Matplotlib adaptations are documented;
- [ ] Datoviz strict claims are probe-dependent.

### Slice C: session, discovery, and query lifecycle

1. VisPy2 boundary: [`session.py`](../src/vispy2/session.py)
2. GSP provider SPI: [`backends.py`](../../gsp/packages/gsp-core/src/gsp/backends.py)
3. Matplotlib provider/session/query:
   [`plugin.py`](../../gsp/packages/gsp-matplotlib/src/gsp_matplotlib/plugin.py),
   [`session.py`](../../gsp/packages/gsp-matplotlib/src/gsp_matplotlib/session.py), and
   [`protocol_query.py`](../../gsp/packages/gsp-matplotlib/src/gsp_matplotlib/protocol_query.py)
4. Datoviz provider/session/query:
   [`plugin.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/plugin.py),
   [`session.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/session.py), and
   [`query.py`](../../gsp/packages/gsp-datoviz/src/gsp_datoviz/query.py)

Check:

- [ ] discovery is lazy;
- [ ] provider selection is explicit;
- [ ] sessions own native lifecycle;
- [ ] queries target rendered session-owned scenes;
- [ ] unsupported results and lifecycle errors remain distinct;
- [ ] no private/native object becomes public VisPy2 state.

Implementation finding:

| Slice | Fact observed | Interpretation | Severity/action |
|---|---|---|---|
| Point |  |  |  |
| Mesh/camera |  |  |  |
| Session/query |  |  |  |

## 16. Final human decision

Public API:

- [ ] Core 2D methods are coherent and sufficient.
- [ ] Core 3D methods are coherent and sufficient.
- [ ] Camera and lighting are discoverable and predictable.
- [ ] Sessions and capabilities are understandable.
- [ ] Query scope is small but honest.
- [ ] Errors and unsupported results are useful.

Matplotlib:

- [ ] The live Matplotlib reference is legible and behaves predictably.
- [ ] Guides, titles, scalar images, and colorbars are credible.
- [ ] 3D adaptations are acceptable and documented.
- [ ] No silent semantic loss was observed.

Datoviz:

- [ ] Priority 2D and 3D visuals render correctly when advertised.
- [ ] Capability probing is truthful and fail-closed.
- [ ] Live camera behavior is acceptable.
- [ ] Static and live processes clean up reliably.
- [ ] Backend-specific visual differences are documented.

Release-readiness classification:

| Category | Count | IDs |
|---|---:|---|
| BLOCKER | 0 |  |
| BUG | 0 |  |
| DOC | 0 |  |
| ADAPTATION accepted | 0 |  |
| DEFERRED accepted | 0 |  |
| PREFERENCE | 0 |  |

Decision:

- [ ] **Accept the reviewed API/backend scope for release preparation.**
- [ ] **Request bounded corrections before release preparation.**
- [ ] **Reopen feature scope because a first-release requirement is genuinely missing.**

Owner summary:

______________________________________________________________________________

______________________________________________________________________________

Date: ____________________  Reviewed commits verified: ____________________
