# Producer and backend boundary

VisPy2 builds typed, backend-neutral `gsp.Scene` snapshots. A `Figure` and its `Axes` never retain a
Matplotlib figure, a Datoviz handle, an open session, or backend capability state.

```python
import vispy2 as vp

figure, axes = vp.subplots()
axes.scatter([0, 1], [1, 0])
scene = figure.to_scene()
```

Backend packages register providers in the `gsp.backends` entry-point group. Discovering metadata
is lazy; probing or opening a session performs dependency and API checks. Selection is explicit:

```python
import gsp

print(gsp.discover_backends())
print(gsp.discover_backends(probe=True))

with gsp.open_session("datoviz", require={"visual.points"}) as session:
    figure.display(session, block=True, frame_count=2)
```

`Figure.savefig()` and blocking `Figure.show()` are deliberate one-shot conveniences that open and
close a Matplotlib session. Install `vispy2[matplotlib]` for those methods. Non-blocking or
interactive execution requires a caller-owned session so its lifecycle remains explicit.

The current `Scene` execution boundary supports at most one `Axes`; `Figure.to_scene()` rejects
multi-axes figures instead of silently discarding panels.
