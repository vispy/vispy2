# M283 Datoviz capture finding

Date: 2026-07-23

Status: intermittent evidence retained for M284 lifecycle stress; no longer blocking M283

## Observed behavior

The exact baseline sources at GSP `d1136e0f73740fd0c11880d38c1caa4b4650757d` and VisPy2
`1befe28d5135ce8f5d7f69a6ab6b2efe67e8a1f7` were assembled into wheels, installed into an
isolated directory, and executed from a second directory outside both source trees.

`gsp.discover_backends(probe=True)` reported Datoviz available with `output.file` and the
`visual.points`, `visual.markers`, `visual.pixels`, `visual.vector`, `visual.primitive`, and
`visual.text` capabilities required by gallery 1. The isolated command was:

```console
python gallery_01_priority_2d.py datoviz --output-dir datoviz-artifacts
```

The process entered native Datoviz execution but did not return or produce a PNG after more than
60 seconds. macOS logged invalid connection messages for system application services. A prior
baseline review note also records that `capture_png_bytes()` could abort after rendering in the
available runtime; this run did not reach a Python exception or successful capture.

## Control evidence

The same isolated wheel installation successfully:

- imported `gsp` and `vispy2` from the isolated install directory;
- probed both backends;
- produced seven deterministic Matplotlib PNGs for galleries 1 through 4;
- returned a Matplotlib point-query `HIT`;
- returned a structured sphere-query `UNSUPPORTED` result and diagnostic.

## Final disposition

Independent bounded diagnosis produced gallery 1 successfully in five of five isolated runs with
byte-identical output. Galleries 2--4 then produced all six remaining Datoviz captures. Raw
Datoviz, minimal GSP, render, capture, and cleanup lifecycles also completed, so no reproducible
example, adapter, session, or capability defect was found.

The final M283 installed-wheel harness uses a 20-second process-group timeout and one retry for
each Datoviz capture. It produced all seven Datoviz artifacts. The original hang is preserved
here as intermittent orchestration/lifecycle evidence and should be included in repeated M284
stress testing; it is not evidence for removing the qualified `output.file` capability.
