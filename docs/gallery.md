# Installed-wheel gallery

For M284 owner acceptance, use the [human-review index](M284-human-review.md), which links all
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
20-second process-group timeout, retries each Datoviz capture once, requires fourteen PNGs, and
writes byte counts and SHA-256 hashes to `manifest.json`.

## Live navigation

Gallery 5 is manual. Enable it only for isolated review:

```console
GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=1 \
  python examples/gallery_05_datoviz_navigation.py
```

Left-drag orbits, right-drag pans, the wheel zooms, and double-click resets the construction
camera. Close the window to end the blocking loop and release the context-managed session.
Use `Ctrl-C` if the native window cannot be closed. Do not automate this gallery in headless CI.

## Artifact interpretation

The checked-in artifacts were reproduced during M284 with wheel-installed GSP and VisPy2 imports
while the scripts ran outside both source trees. The full fourteen-image set was byte-identical to
M283. Seven Matplotlib and seven Datoviz captures were visually reviewed for content, separation,
camera coverage, clipping, and obvious corruption.

The backends are not expected to match pixels. Matplotlib uses a 640×480 publication canvas;
Datoviz uses an 800×600 native offscreen target. Titles and axes are native guides, and the
backends use different fonts, metrics, antialiasing, primitive rasterization, sphere depth, and
text placement. Compare the semantic scene and documented adaptations.

The first M283 Datoviz invocation hung without an output file. Five isolated repeats of gallery 1
and bounded captures of galleries 2--4 then succeeded, and the final harness succeeded. No
reproducible adapter defect was found. The original event remains evidence for repeated
capture/lifecycle stress in M284. M284's first two Codex-sandbox attempts also hung while macOS
HIServices/LaunchServices access was denied; independent unsandboxed native qualification then
passed 25/25 static and 25/25 live View3D isolated processes, each bounded at 20 seconds.
