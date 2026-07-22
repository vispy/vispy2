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

This repository has a fresh history curated from the experimental `gsp_vispy2` producer in
`vispy/GSP_API`. It is not yet published and has no configured remote.
