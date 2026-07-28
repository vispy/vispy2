# VisPy2

VisPy2 is the high-level scientific plotting producer for Graphics Server Protocol scenes.
Figures and axes own semantic plotting state; GSP sessions own backend selection, capabilities,
native resources, windows, event loops, and displays.

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0, 1], [1, 0])
figure.show()
```

## Review the current implementation

Start with the [user guide](user-guide.md) and [public API reference](api-reference.md), then use
the [gallery](gallery.md) and [capability matrix](capability-matrix.md) to compare the Matplotlib
and Datoviz implementations.

For the complete human-in-the-loop review before an experimental release, follow the
[manual pre-release review workbook](manual-pre-release-review.md) from beginning to end.

## Documentation ownership

This site documents the VisPy2 plotting API. The GSP documentation separately owns protocol,
scene, capability, query, conformance, and backend-adapter contracts.
