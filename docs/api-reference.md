# Public API reference

This reference covers VisPy2's public producer surface. Methods append or replace semantic GSP
state; they do not create backend resources unless the method explicitly accepts or creates a
session.

## Conventions

- Array-like inputs accept Python sequences or NumPy-compatible arrays.
- Positions are DATA-space unless a method explicitly exposes `coordinate_space`.
- Colors are RGBA8, either one `(4,)` value or one `(N, 4)` value.
- Sizes, widths, stroke widths, and font sizes are logical canvas pixels.
- A scalar-or-array field accepts one value or a length-`N` value.
- Public visual methods return the typed GSP visual they append.
- `id=None` generates a process-local semantic ID; pass an ID when stable identity matters.

Invalid shapes, non-finite geometry, inconsistent lengths, unsupported enum values, and invalid
topology cardinalities raise `ValueError` or `TypeError` before backend execution.

## Construction and sessions

### `subplots`

`subplots(nrows=1, ncols=1, *, projection="2d", canvas_size=None, squeeze=True)`

Creates a row-major subplot grid. `projection` is one `"2d"` / `"3d"` string or a nested sequence
matching `(nrows, ncols)`. Both dimensions must be positive integers. `canvas_size` is a GSP
`CanvasSize`. The result is `(Figure, axes)`: a 1×1 grid returns an `Axes` / `Axes3D`; singleton
rows or columns are squeezed to a one-dimensional object array; larger grids return a
two-dimensional array. `squeeze=False` always returns a two-dimensional array.

Use `Figure.add_axes()` for incremental construction and custom allocations.

### `open_session`

`open_session(backend, *, require=(), adaptation=()) -> BackendSession`

Opens an explicit caller-owned GSP session. `require` is the set of capabilities that must be
available. `adaptation` is the set of adaptations the caller accepts. Use the returned object as a
context manager.

### Module-level visual helpers

`scatter`, `markers`, `pixels`, `segments`, `path`, `plot`, `vectors`, `quiver`, `primitives`,
`text`, `mesh`, and `imshow` create a temporary one-axes 2D figure and return its visual.
`color_scale` and `colorbar` similarly return detached semantic values from a temporary figure.
Use axes methods when visuals and guides must share a scene.

`affine2d(matrix)` validates a finite `(3, 3)` affine matrix and returns an inline semantic visual
transform binding.

## `Figure`

`Figure(*, axes=[], id="figure:main", canvas_size=None, ...)`

| Method | Result |
|---|---|
| `add_axes(projection="2d", allocation=None)` | appends and returns an `Axes` or `Axes3D` |
| `set_panel_allocation(axes, allocation)` | replaces one owned axes' normalized outer-panel rectangle |
| `panel_layout()` | validates and returns explicit panel allocations |
| `link_axes(*axes, x=True, y=True)` | merges selected producer/programmatic 2D limit groups |
| `set_limits(axes, xlim=None, ylim=None)` | atomically replaces ranges and propagates linked dimensions |
| `update_point(session, visual)` | updates retained point values, then producer state; returns scene revision |
| `to_scene()` | freezes the complete semantic figure state as a `gsp.Scene` |
| `visuals()` | visuals in creation order |
| `panels()`, `views()`, `attachments()` | corresponding scene records |
| `axis_guides()`, `panel_text_guides()` | guide intent |
| `color_scales()`, `texture_resources()`, `colorbar_guides()` | resources and guides |
| `savefig(path, **kwargs)` | renders through an ephemeral Matplotlib session |
| `show(session=None, block=True, **kwargs)` | blocking Matplotlib convenience or explicit-session display |
| `display(session, **kwargs)` | displays through a caller-owned session |
| `resolve_layout(session, **kwargs)` | renders and returns a backend-neutral layout snapshot |
| `query(session, request)` | queries this figure's stable scene ID |

`to_scene()` rejects an empty figure. With multiple axes, it emits one panel and view per axes and
an explicit layout; 2D and 3D axes may be mixed in any order. Ordinary `add_axes()` uses equal-width
horizontal strips; `subplots()` allocates a grid. Overrides use GSP `NormalizedRenderTargetRect`
with a top-left origin and coordinates inside `[0, 1]`. Positive, contained, non-overlapping
allocations are required; overlap is checked by `panel_layout()` / `to_scene()`.
`show(block=False)` requires an explicit session. `display`, `resolve_layout`, and `query` do not
close or retain the supplied session.

`link_axes` requires at least two distinct owned 2D axes and at least one linked dimension.
Selected limits initially come from the first axes. Groups merge transitively; each axes keeps
its own view ID. Links apply to setters and data fitting, and remain producer state. Native
backend navigation across linked axes is deferred.

`update_point` accepts an open `gsp.PointUpdateSession` advertising `scene.update.points.v1` after
this scene has been rendered there. The replacement must preserve ID, point count/dimension,
coordinate space, attachment, transform, and scalar-color binding. Values and sizes may change;
hidden attachments are unsupported. It validates before forwarding, and updates producer state
only after success. Earlier snapshots are unaffected. The session's `scene_revision(scene_id)`
starts at zero on first render and increments after successful rerenders or point updates.
Other scene changes require a full render.

## `Axes`

### View and guides

| Method | Purpose |
|---|---|
| `set_xlim(left, right)`, `set_ylim(bottom, top)` | replace one DATA range |
| `get_xlim()`, `get_ylim()` | return the current DATA range |
| `set_view2d(xlim=None, ylim=None)` | replace ranges and propagate linked dimensions |
| `fit_data(margin=1.1)`, `autoscale(margin=1.1)` | explicitly fit current finite DATA geometry once |
| `sharex(other)`, `sharey(other)` | link the selected limit group, initially adopting the other's limits |
| `set_clip_scope(scope)` | set `plot`, `panel`, or `render_target` clipping on current and future attachments |
| `set_xlabel(text)`, `set_ylabel(text)`, `set_title(text)` | set or clear semantic labels |
| `get_xlabel()`, `get_ylabel()`, `get_title()` | return current labels |
| `set_xticks(ticks, labels=None)`, `set_yticks(...)` | set explicit ticks and optional labels |
| `get_xticks()`, `get_yticks()` | return explicit ticks or `()` |
| `grid(visible=True, axis="both")` | set grid intent for `"x"`, `"y"`, or `"both"` |

`fit_data` includes image extents, segment/vector endpoints, and inline affine transforms. It
preserves reversed axes and expands degenerate ranges. Screen-sized marks do not enlarge bounds.
The finite margin is a span multiplier of at least one. Non-empty finite 2D DATA geometry is
required; unresolved referenced transforms raise `ValueError`. Later visuals do not trigger
fitting automatically.

### Points and markers

`scatter(x, y=None, *, c=None, color=None, color_scale=None, cmap=None, clim=None, alpha=1.0,
s=36.0, size=None, transform=None, id=None)`

Accepts separate `x`, `y` values or one `(N, 2)` positions array. `c` takes precedence over
`color`; `size` takes precedence over `s`. Color may be RGBA or scalar values paired with
`color_scale`, or with `cmap` plus `clim`.

`markers` uses the same position and scalar-color conventions and adds `shape="disc"`,
`fill_color`, `angle=0.0`, `stroke_color`, and `stroke_width=0.0`. Shapes, angles, and sizes may
be scalar or per item.

`pixels(x, y=None, *, color=None, size=1.0, transform=None, id=None)` creates screen-aligned square
pixels anchored at `(N, 2)` DATA positions.

### Lines and vectors

`segments(start, end, *, color=None, width=1.0, cap="butt", transform=None, id=None)` requires
matching `(N, 2)` endpoint arrays.

`path(positions, path_lengths=None, *, color=None, width=1.0, cap="butt", join="miter",
miter_limit=4.0, transform=None, id=None)` creates one or more open paths. `path_lengths` partitions
the ordered positions; colors and widths are per path.

`plot(x, y=None, **kwargs)` is the one-path convenience over `path`.

`vectors(x, y, u, v, *, color=None, width=1.0, scale=1.0, anchor="tail", start_cap="butt",
end_cap="triangle_out", transform=None, id=None)` creates straight displacement vectors.
`anchor` is `"tail"`, `"center"`, or `"head"`. `quiver` is an exact thin alias.

### Scientific conveniences

`bar(x, height, *, width=0.8, bottom=0, color=None, id=None) -> PrimitiveVisual`

Finite one-dimensional x centers define bars. Height, positive width, and bottom are scalar or
matching arrays. Negative and zero heights are allowed. Color is uniform RGBA or per-bar RGBA.
Each rectangle lowers to six DATA-space triangle-list vertices.

`hist(x, *, bins=10, range=None, weights=None, density=False, cumulative=False, color=None,
id=None) -> (values, edges, PrimitiveVisual)`

Samples and matching optional weights must be finite, non-empty, one-dimensional arrays.
Bins are a positive integer or finite strictly increasing edges. An optional finite increasing
range bounds integer-bin generation. Returned values and edges are float64 arrays. Values are
bin counts/weight totals, density per unit x when `density=True`, cumulative totals when
`cumulative=True`, or normalized cumulative weight when both are true. Unequal bin widths are
accounted for in density. Density requires a positive finite total weight. Zero-count bins are
accepted. Empty or non-finite input is rejected.

`fill_between(x, y1, y2=0, *, color=None, id=None) -> PrimitiveVisual`

Requires at least two finite strictly monotonic x values. Both y inputs are finite scalar or
matching arrays. Curves may touch but must not cross. The band lowers to triangle lists with
zero-area triangles omitted; an entirely zero-area band is rejected before append. Masks, step
modes, general polygons, and crossing interpolation are outside this bounded method.

`axhline(y=0, *, color=None, width=1, id=None) -> SegmentVisual`

`axvline(x=0, *, color=None, width=1, id=None) -> SegmentVisual`

`axhspan(ymin, ymax, *, color=None, id=None) -> PrimitiveVisual`

`axvspan(xmin, xmax, *, color=None, id=None) -> PrimitiveVisual`

Reference lines and spans capture the current other-axis limits as ordinary DATA geometry.
They do not track subsequent limit changes. There is no automatic legend or special query-guide
semantics attached to these helpers.

### Geometry

`primitives(positions, *, topology, color=None, indices=None, transform=None, id=None)` accepts
`(N, 2)` public positions. Topology is `"point_list"`, `"line_list"`, `"line_strip"`,
`"triangle_list"`, or `"triangle_strip"`. Optional indices select public positions and colors
before topology validation.

`mesh(positions, faces, *, color, color_mode=None, coordinate_space="data",
shading="unlit_rgba", normal_mode=None, normals=None, normal_generation="none", order=0.0,
transform=None, texture=None, uvs=None, texture_filter="nearest", id=None)` creates indexed
triangle geometry. `faces` has shape `(M, 3)`.

The texture path requires both an RGBA8 `texture` and `(N, 2)` UV coordinates. It resolves to
unlit texture shading and cannot be combined with explicit mesh lighting.

### Text, images, and color

`text(x, y, texts, *, color=None, font_size_px=13.0, font_role="default", anchor_x="left",
anchor_y="baseline", rotation_rad=0.0, z_order=0, transform=None, id=None)` requires one string or
one string per DATA anchor.

`imshow(image, *, extent=None, origin="upper", interpolation="nearest", colormap=None, cmap=None,
clim=None, color_scale=None, id=None)` creates a DATA-space image. Without an extent, pixel centers
use integer coordinates. Scalar images can reference a registered color scale or create one from
`cmap` and `clim`.

`color_scale(*, cmap="viridis", clim, id=None, description=None)` registers and returns a linear
semantic color scale.

`colorbar(color_scale, *, label="", orientation="vertical", placement=None, ticks=None,
tick_labels=None, linked_visual_ids=(), style=None, ..., id=None)` appends colorbar guide intent.
`color_scale` may be a registered ID or a `ColorScale`.

## `Axes3D`

### Camera, projection, and lighting

| Method | Purpose |
|---|---|
| `set_camera(eye=..., target=..., up=...)` | replace the three-vector camera |
| `get_camera()` | return the current `Camera3D` |
| `set_perspective(fov_y_degrees=45, near=0.1, far=1000, aspect_ratio=None)` | set perspective projection |
| `set_orthographic(xlim=(-1, 1), ylim=(-1, 1), near=0, far=1000)` | set orthographic projection |
| `get_projection()` | return the current projection |
| `fit_camera(margin=1.1)` | fit finite DATA-space 3D bounds |
| `orbit(yaw_radians=..., pitch_radians=...)` | apply the canonical orbit reducer |
| `pan(right=..., up=...)` | apply the canonical view-basis pan reducer |
| `zoom(scale, anchor_ndc=None)` | apply the canonical zoom reducer |
| `reset_camera()` | restore the construction camera and projection |
| `set_title(text)` / `get_title()` | set, clear, or read the panel title |

`set_lighting(*, ambient_light_intensity, direction_to_light,
directional_light_intensity=1.0)` sets one ambient term and an optional directional light.
Pass `direction_to_light=None` to clear the directional light.

Camera and lighting mutations increment the `View3D` revision. `fit_camera` requires at least one
finite DATA-space 3D visual and a finite margin of at least `1.0`.

### Three-dimensional visuals

`mesh` has the same contract as `Axes.mesh`, but positions must have shape `(N, 3)` and transforms
are rejected in the current static View3D slice.

`spheres(x, y, z, *, radius, color, id=None)` requires strictly positive DATA-space radii.

`vectors(x, y, z, u, v, w, *, color=None, width=1.0, scale=1.0, anchor="tail",
start_cap="butt", end_cap="triangle_out", id=None)` creates straight DATA-space vectors.
`quiver` is a thin alias.

`primitives(positions, *, topology, color=None, indices=None, id=None)` accepts `(N, 3)` DATA
positions and the same five bounded topologies as the 2D method.

`pixels(x, y=None, z=None, *, color=None, size=1.0, id=None)` accepts separate coordinates or one
`(N, 3)` array and creates screen-facing square pixels.

`text(x, y, z, texts, *, color=None, font_size_px=13.0, font_role="default", anchor_x="left",
anchor_y="baseline", rotation_rad=0.0, z_order=0, id=None)` creates screen-facing billboards at
3D DATA anchors. It does not claim glyph parity or strict depth occlusion.

## Backend and lifecycle errors

Provider discovery, capability errors, session-state errors, and query result statuses come from
GSP. VisPy2 does not reinterpret them. The only one-shot convenience wrapping is for a missing
Matplotlib extra, where `savefig` and implicit blocking `show` raise an actionable `RuntimeError`.

For backend-specific status, consult the [capability matrix](capability-matrix.md). For the
session boundary, see [producer and backend ownership](producer-and-backends.md).
