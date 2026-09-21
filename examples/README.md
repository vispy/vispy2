# VisPy2 examples

The M283 installed-wheel gallery is the current cross-backend feature tour:

1. `gallery_01_priority_2d.py` — priority 2D visual families.
2. `gallery_02_perspective_3d.py` — mesh, spheres, vectors, and billboard text.
3. `gallery_03_orthographic_3d.py` — indexed primitive geometry and pixels.
4. `gallery_04_camera_sequence.py` — fit, orbit, pan, and zoom captures.
5. `gallery_05_datoviz_navigation.py` — manual experimental Datoviz input with flat diffuse
   shading, generated face normals, and one ambient-plus-directional light.
6. `gallery_06_capabilities.py` — discovery and explicit selection.
7. `gallery_07_queries.py` — point hit and structured unsupported query.
8. `gallery_mixed_panels.py` — permanent mixed View2D/View3D capture, resize, query-routing, and
   lifecycle qualification.
9. `manual_live_compare.py` — launch matching Matplotlib and Datoviz windows together from one
   terminal while retaining one isolated child process per backend; its `mixed-panels` case is a
   post-RC3 manual harness for panel-local 2D/3D navigation, resize, clipping, and clean teardown,
   not a completed interaction qualification.

See [`../docs/gallery.md`](../docs/gallery.md) for commands, live controls, cleanup, artifact
interpretation, and the installed-wheel validation harness. `validate_docs.py` compiles every
Python block in both repositories' README/docs trees and checks local Markdown links.
