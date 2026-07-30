# Installation

VisPy2 requires Python 3.13 and is currently an unpublished `0.2.0a1` candidate. Until ordinary
package publication, install freshly built local wheels for VisPy2, `gsp-core`, and any selected
adapter together. Do not mix source-tree imports with an environment intended to qualify wheels.

## Build the local wheels

The commands below assume sibling `vispy2` and `gsp` checkouts and start in the VisPy2 repository:

```console
python -m pip install "build>=1,<2"
mkdir -p ../wheels

python -m build --wheel --outdir ../wheels ../gsp/packages/gsp-core
python -m build --wheel --outdir ../wheels ../gsp/packages/gsp-matplotlib
python -m build --wheel --outdir ../wheels .
```

Use a clean output directory when exact artifact identity matters. The checked-in qualification
harness accepts explicit wheel paths and verifies hashes rather than selecting an arbitrary wheel
from a directory. Build `gsp-datoviz` separately only for the development workflow below; it is
not part of the intended first ordinary publication set.

## Producer-only installation

A producer-only environment proves that semantic scene construction does not require an adapter:

```console
python -m venv .venv-producer
.venv-producer/bin/python -m pip install \
  ../wheels/gsp_core-0.2.0a1-py3-none-any.whl \
  ../wheels/vispy2-0.2.0a1-py3-none-any.whl
.venv-producer/bin/python examples/semantic_scene.py
```

`gsp_matplotlib` and `gsp_datoviz` should not be importable in this environment.

## Matplotlib installation

Install all three wheels in one resolver transaction:

```console
python -m venv .venv-matplotlib
.venv-matplotlib/bin/python -m pip install \
  ../wheels/gsp_core-0.2.0a1-py3-none-any.whl \
  ../wheels/gsp_matplotlib-0.2.0a1-py3-none-any.whl \
  ../wheels/vispy2-0.2.0a1-py3-none-any.whl
.venv-matplotlib/bin/python examples/static_mesh3d.py matplotlib
```

This is the intended local equivalent of the future `vispy2[matplotlib]` extra. `Figure.savefig`
and implicit blocking `Figure.show` require this provider.

## Development-only Datoviz installation

The current Datoviz adapter additionally needs an RC3-compatible Datoviz v0.4 binding. During
local development, build its unpublished adapter wheel and identify its checkout explicitly:

```console
python -m build --wheel --outdir ../wheels ../gsp/packages/gsp-datoviz
python -m venv .venv-datoviz
.venv-datoviz/bin/python -m pip install \
  ../wheels/gsp_core-0.2.0a1-py3-none-any.whl \
  ../wheels/gsp_datoviz-0.2.0a1-py3-none-any.whl \
  ../wheels/vispy2-0.2.0a1-py3-none-any.whl

GSP_DATOVIZ_SOURCE=../datoviz \
PYTHONPATH=../datoviz \
.venv-datoviz/bin/python examples/gallery_02_perspective_3d.py datoviz
```

There is deliberately no `vispy2[datoviz]` publication extra while the compatible Datoviz runtime
cannot be resolved from an ordinary package artifact. This source selector is a development
bootstrap, not a published dependency claim. Do not enable experimental live View3D navigation
for ordinary rendering. The isolated manual-review command and opt-in variable are documented in
the [gallery guide](gallery.md).

## Verify provider discovery

Probe after installation so missing dependencies and unavailable binding surfaces produce
diagnostics:

```python
import gsp

for backend in gsp.discover_backends(probe=True):
    print(backend.name, backend.available, backend.diagnostics)
```

Metadata discovery is lazy. Probing performs provider dependency and API checks; opening a session
also enforces the requested capabilities.

## Exact-wheel qualification

The commands above are for development and exploration. Release evidence checks the three intended
publication wheels independently from the optional fourth development-only Datoviz adapter wheel.
The [gallery guide](gallery.md) records the broader exact-wheel native procedure.
