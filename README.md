# VisPy2

VisPy2 is a high-level scientific plotting producer for GSP scenes.

Figures and axes own semantic plotting state only. Backend selection, capabilities, native
resources, windows, event loops, and displays belong to GSP sessions. VisPy2 depends on `gsp-core`
and never imports a concrete backend adapter.

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0, 1], [1, 0])
scene = figure.to_scene()

# Requires the optional Matplotlib provider.
figure.savefig("figure.png")
```

For a static 3D scene, request an `Axes3D`, add a DATA-space mesh, and fit the semantic camera:

```python
figure, axes = vp.subplots(projection="3d")
axes.mesh(
    [[-1, -1, 0], [1, -1, 0], [0, 1, 0]],
    [[0, 1, 2]],
    color=[70, 130, 220, 255],
)
axes.fit_camera()
```

For bounded DATA-space spheres, use `Axes3D.spheres()`. Camera fitting includes radii:

```python
figure, axes = vp.subplots(projection="3d")
axes.spheres(
    [0.0, 1.0],
    [0.0, 0.0],
    [0.0, -0.5],
    radius=[0.5, 0.25],
    color=[[230, 57, 70, 255], [69, 123, 157, 255]],
)
axes.fit_camera()
```

Use an explicit caller-owned session for Datoviz, non-blocking execution, or interactive lifecycle
control. See [Producer and backend boundary](docs/producer-and-backends.md).

For an end-to-end introduction, see the [user guide](docs/user-guide.md), the
[installed-wheel gallery](docs/gallery.md), and the exact
[capability matrix](docs/capability-matrix.md).

The optional extras name the intended published package combinations. While these repositories are
still local and unpublished, install the corresponding built `gsp-core`, adapter, and `vispy2`
wheels together. Datoviz development additionally requires an explicit `GSP_DATOVIZ_SOURCE` until
an ordinary RC3-compatible dependency artifact exists.

This repository has a fresh history curated from the experimental `gsp_vispy2` producer in
`vispy/GSP_API`. Its source repository is [vispy/vispy2](https://github.com/vispy/vispy2); the
package is not yet published.
