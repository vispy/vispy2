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

Use an explicit caller-owned session for Datoviz, non-blocking execution, or interactive lifecycle
control. See [Producer and backend boundary](docs/producer-and-backends.md).

The optional extras name the intended published package combinations. While these repositories are
still local and unpublished, install the corresponding built `gsp-core`, adapter, and `vispy2`
wheels together. Datoviz development additionally requires an explicit `GSP_DATOVIZ_SOURCE` until
an ordinary RC3-compatible dependency artifact exists.

This repository has a fresh history curated from the experimental `gsp_vispy2` producer in
`vispy/GSP_API`. Its source repository is [vispy/vispy2](https://github.com/vispy/vispy2); the
package is not yet published.
