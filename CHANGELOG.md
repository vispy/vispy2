# Changelog

This file records user-visible VisPy2 changes. The project is not yet published; the version below
describes the current experimental candidate rather than a package-index release.

## Unreleased

### Documentation

- Reconciled historical qualification reports with subsequent owner acceptance.
- Expanded the user guide to cover the complete public 2D surface, scalar images, color scales,
  colorbars, guides, lighting, output, sessions, and limitations.
- Added a compact public API reference plus installation and development guidance.

## 0.2.0a1 — unpublished candidate

### Added

- Backend-neutral `Figure`, `Axes`, and `Axes3D` producers for typed GSP scene snapshots.
- Points, markers, pixels, segments, paths, vectors, bounded primitives, text, meshes, and images.
- Scalar color scales, scalar point/marker encoding, image mapping, and colorbar guide intent.
- Semantic axes labels, titles, explicit ticks, grids, ranges, and canvas size.
- Perspective and orthographic View3D cameras with fit, orbit, pan, zoom, and reset reducers.
- DATA-space spheres, vectors, primitives, pixels, and screen-facing text billboards in View3D.
- Bounded mesh textures and flat-Lambert lighting with ambient and directional light state.
- Explicit caller-owned GSP sessions, resolved-layout forwarding, and bounded query forwarding.
- Matplotlib one-shot `savefig` and blocking `show` conveniences.
- Cross-backend galleries, live paired review, exact-wheel validation, and portable evidence.

### Boundaries

- Scene execution currently accepts exactly one 2D or 3D axes.
- VisPy2 imports `gsp-core` but no concrete adapter.
- Non-blocking and interactive execution requires an explicit caller-owned session.
- Datoviz DATA-space scalar images and linked colorbars are supported on the qualified retained
  View2D path; image-texel readback and comprehensive 3D/item/glyph queries remain unsupported.
- Live Datoviz View3D navigation remains experimental and opt-in.
