# Installed-wheel gallery

For M285 owner acceptance, use the [human-review index](M284-human-review.md), which links all
fourteen exact-head captures and provides the live navigation checklist.

The seven M283 journeys are deliberately small and backend-neutral. Galleries 1--4 create seven
PNG states for each backend; gallery 5 is manual and interactive; galleries 6--7 validate
discovery and queries.

| Gallery | Journey | Run |
|---|---|---|
| 1 | Priority 2D families | `python gallery_01_priority_2d.py BACKEND --output-dir artifacts` |
| 2 | Perspective mesh, spheres, vectors, billboards | `python gallery_02_perspective_3d.py BACKEND --output-dir artifacts` |
| 3 | Orthographic primitive and pixels | `python gallery_03_orthographic_3d.py BACKEND --output-dir artifacts` |
| 4 | Fit, orbit, pan, zoom sequence | `python gallery_04_camera_sequence.py BACKEND --output-dir artifacts` |
| 5 | Experimental live Datoviz navigation | `python gallery_05_datoviz_navigation.py` |
| 6 | Discovery and ordered selection | `python gallery_06_capabilities.py` |
| 7 | Point hit and structured unsupported query | `python gallery_07_queries.py` |

Replace `BACKEND` with `matplotlib` or `datoviz`. Run from `examples/` for exploration. For
acceptance, use the installed-wheel harness:

```console
python examples/validate_gallery.py \
  --python /path/to/wheel-environment/bin/python \
  --output-dir /tmp/vispy2-gallery \
  --gsp-source /path/to/gsp \
  --vispy2-source /path/to/vispy2
```

This is a shell template; replace every `/path/to/...` placeholder. The harness copies scripts to
a temporary directory outside both repositories, rejects source-tree imports, applies a
20-second process-group timeout, retries each Datoviz capture once, requires fourteen pixel-exact
800×600 PNGs, and writes dimensions, byte counts, and SHA-256 hashes to `manifest.json`.

## Live navigation

Gallery 5 is manual. From the Mission Control `GSP_API` checkout, enable it only for isolated
review with this copyable repository-relative command:

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

All fourteen checked-in artifacts were regenerated during M285 with wheel-installed GSP and
VisPy2 imports while the scripts ran outside both source trees. They are exactly 800×600 and the
manifest records exact committed source revisions plus script, wheel, and artifact hashes. The
Codex worker's two bounded native attempts encountered the known macOS service denial; the final
unsandboxed run completed all fourteen captures without retry. See
`examples/artifacts/M285-DATOVIZ-SANDBOX-STOP.md` for the environment distinction.

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
