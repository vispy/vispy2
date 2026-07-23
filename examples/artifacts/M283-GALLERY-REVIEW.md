# M283 gallery review

Date: 2026-07-23

The final installed-wheel harness produced fourteen PNGs: seven 640×480 Matplotlib captures and
seven 800×600 Datoviz captures. `manifest.json` records source revisions, wheel import paths,
script hashes, artifact byte counts, and artifact SHA-256 hashes.

Visual inspection confirmed:

- gallery 1 contains separated points, markers, pixels, vectors, primitive, and text;
- gallery 2 contains a mesh, two distinct spheres, three vectors, and three non-overlapping labels;
- gallery 3 contains the indexed primitive strip and four differently sized pixel squares;
- all four gallery 4 states contain complete geometry without the former clipping;
- orbit, pan, and zoom states change consistently on both backends;
- no capture is empty, corrupted, or unexpectedly cropped.

The review compares semantic content, not pixel parity. Matplotlib supplies native publication
titles and guide layout; Datoviz uses its native/adapted guide path and a larger offscreen raster.
Font metrics, title placement, antialiasing, sphere shading, primitive interpolation, and vector
heads are intentionally backend-specific.

The initial Datoviz hang remains recorded in `M283-DATOVIZ-CAPTURE-FINDING.md`. The bounded final
run required no retry and found no reproducible backend defect.
