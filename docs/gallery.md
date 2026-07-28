# Installed-wheel gallery

The [accepted M292 human-review record](M284-human-review.md) links all fourteen qualified
captures and records the completed live-navigation review.

The seven M283 journeys are deliberately small and backend-neutral. Galleries 1--4 create seven
PNG states for each backend; gallery 5 is manual and interactive; galleries 6--7 validate
discovery and queries.

| Gallery | Journey | Run |
|---|---|---|
| 1 | Priority 2D families | `python gallery_01_priority_2d.py BACKEND --output-dir artifacts` |
| 2 | Perspective mesh, spheres, vectors, billboards | `python gallery_02_perspective_3d.py BACKEND --output-dir artifacts` |
| 3 | Orthographic primitive and pixels | `python gallery_03_orthographic_3d.py BACKEND --output-dir artifacts` |
| 4 | Fit, orbit, pan, zoom sequence | `python gallery_04_camera_sequence.py BACKEND --output-dir artifacts` |
| 5 | Experimental live Datoviz navigation with flat diffuse lighting | `python gallery_05_datoviz_navigation.py` |
| 6 | Discovery and ordered selection | `python gallery_06_capabilities.py` |
| 7 | Point hit and structured unsupported query | `python gallery_07_queries.py` |

Replace `BACKEND` with `matplotlib` or `datoviz`. Run from `examples/` for exploration. For
acceptance, first verify both candidate heads are clean, then build all four wheels from those
heads. From the VisPy2 repository:

## Live side-by-side comparison

From one terminal in the VisPy2 repository, launch matching Matplotlib and Datoviz windows
concurrently:

```console
python examples/manual_live_compare.py all
```

Use a case name instead of `all` to repeat only one pair, for example
`priority-2d`, `perspective-3d`, `orthographic-3d`, `flat-lambert`, `camera-fit`,
`camera-orbit`, `camera-pan`, `camera-zoom`, or `camera-reset`. Each backend runs in its own child
process, while the 3D pair consumes the same resolved plot viewport. Close both windows to advance
to the next case; terminal `Ctrl-C` terminates both children.

The [manual pre-release review workbook](manual-pre-release-review.md) is the linear human-review
path. Generated PNGs belong to automated qualification and are not required for human visual
review.

```console
test -z "$(git -C ../gsp status --porcelain)"
test -z "$(git status --porcelain)"
wheel_dir=../wheels
mkdir -p "$wheel_dir"
../gsp/.venv/bin/python -m build --no-isolation --wheel \
  --outdir "$wheel_dir" ../gsp/packages/gsp-core
../gsp/.venv/bin/python -m build --no-isolation --wheel \
  --outdir "$wheel_dir" ../gsp/packages/gsp-matplotlib
../gsp/.venv/bin/python -m build --no-isolation --wheel \
  --outdir "$wheel_dir" ../gsp/packages/gsp-datoviz
../gsp/.venv/bin/python -m build --no-isolation --wheel \
  --outdir "$wheel_dir" .
python examples/validate_gallery.py \
  --python ../gsp/.venv/bin/python \
  --output-dir examples/artifacts \
  --gsp-source ../gsp \
  --vispy2-source . \
  --gsp-core-wheel "$wheel_dir/gsp_core-0.2.0a1-py3-none-any.whl" \
  --gsp-matplotlib-wheel "$wheel_dir/gsp_matplotlib-0.2.0a1-py3-none-any.whl" \
  --gsp-datoviz-wheel "$wheel_dir/gsp_datoviz-0.2.0a1-py3-none-any.whl" \
  --vispy2-wheel "$wheel_dir/vispy2-0.2.0a1-py3-none-any.whl"
```

This is a shell template; adjust the relative interpreter and wheel locations if needed. The harness copies scripts to
a temporary directory outside both repositories and unpacks exactly the four named newly built
project wheels into an isolated project site. The requested prequalified Python environment supplies
only third-party dependencies; the probe rejects any of the four project imports outside that site
and also proves Pillow is importable. The qualified M292 run applied a 30-second timeout; the
harness retries each Datoviz capture once and renders into a fresh temporary capture directory.
Subprocesses normally run in
isolated process groups so timeout cleanup can terminate the entire group. On macOS only, native
Datoviz captures run as direct children because creating a new session can corrupt otherwise
successful native teardown; their bounded timeout cleanup terminates and, if necessary, kills only
the direct child. This exception changes only harness process lifecycle and does not claim any
third-party dependency or Datoviz rebuild. Only after all
fourteen new pixel-exact 800×600 PNGs, layout evidence, queries, and the schema-2 manifest validate
does it copy the result to `--output-dir`, so stale destination artifacts cannot satisfy a run.
The manifest records the probed interpreter runtime, portable logical paths for all four project
imports, clean candidate source revisions, and stable project-name-to-SHA-256 wheel evidence without
wheel paths; it rejects host-absolute paths before publication. The build-and-run procedure, rather
than wheel introspection, establishes that those exact wheel hashes came from the recorded clean
candidate heads. For galleries 2–4, exact shared `plot_rect` equality proves that Datoviz's
explicitly unsupported title neither resizes nor shifts the data viewport.

## Live flat-Lambert navigation

Gallery 5 is manual. Its tetrahedron uses strict flat diffuse Lambert shading with generated face
normals so its faces remain visibly distinct while the camera moves. The intentionally narrow
backend-neutral lighting model is one scalar ambient term plus one white directional light.
From the Mission Control `GSP_API` checkout, enable it only for isolated review with this copyable
repository-relative command:

```console
cd ../vispy2 &&
GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=1 \
PYTHONPATH=src:../datoviz \
GSP_DATOVIZ_SOURCE=../datoviz \
../gsp/.venv/bin/python examples/gallery_05_datoviz_navigation.py
```

Left-drag orbits, right-drag pans, the wheel zooms, and double-click resets the construction
camera. Close the window to end the blocking loop and release the context-managed session.
Use `Ctrl-C` if the native window cannot be closed. Do not automate this gallery in headless CI.

## Artifact interpretation

All fourteen checked-in artifacts were requalified during M292 with wheel-installed GSP and
VisPy2 imports while the scripts ran outside both source trees. They are exactly 800×600 and the
schema-2 manifest records exact committed source revisions plus script, wheel, and artifact hashes.
The native run completed all fourteen captures without a crash or retry. The four camera-state
Datoviz-to-Matplotlib width and height ratios are 0.988–0.995, within the 2% contract. Gallery 5
also started successfully from the isolated four-wheel site, handled one bounded `Ctrl-C`, exited
zero, and left no process. See
`examples/artifacts/M292-EXACT-WHEEL-QUALIFICATION.md` for the final evidence.

The backends are not expected to match pixels, but both now receive the same canonical
pixel-exact 800×600 canvas. Matplotlib View3D captures suppress the unintended native 2D frame.
Matplotlib preserves semantic panel titles; the qualified Datoviz binding has no public
`PanelTextGuide` rendering path and reports that title as explicitly unsupported. Gallery 3 uses
one uniform primitive color and pixel anchors distinct from all primitive vertices. Fonts,
metrics, antialiasing, rasterization, vector heads, and billboard placement remain
backend-specific. Datoviz raycast spheres use native shading and analytic surface depth;
Matplotlib uses flat projected circles ordered by adapted center depth. This difference does not
define a sphere material contract.

The first M283 Datoviz invocation hung without an output file. Five isolated repeats of gallery 1
and bounded captures of galleries 2--4 then succeeded, and the final harness succeeded. No
reproducible adapter defect was found. The original event remains evidence for repeated
capture/lifecycle stress in M284. M284's first two Codex-sandbox attempts also hung while macOS
HIServices/LaunchServices access was denied; independent unsandboxed native qualification then
passed 25/25 static and 25/25 live View3D isolated processes, each bounded at 20 seconds.
