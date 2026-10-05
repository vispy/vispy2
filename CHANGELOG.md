# Changelog

This file records user-visible VisPy2 changes. The project is not yet published; the version below
describes the current experimental candidate rather than a package-index release.

## Unreleased

### Producer conveniences

- Added subplot grids with squeezing, mixed projections, and custom normalized panel allocations;
  single-axes construction and ordinary `add_axes()` horizontal strips remain compatible.
- Added explicit 2D `fit_data()` / `autoscale()` with finite geometry bounds and inline transforms.
- Added transitive programmatic linked x/y limits through `link_axes`, `sharex`, and `sharey`;
  native linked navigation remains deferred.
- Added triangle-based bars, weighted/density/cumulative histograms, non-crossing filled bands,
  and reference lines/spans capturing the current ranges.
- Added optional retained point updates through caller-owned `PointUpdateSession`, preserving
  visual topology and updating producer state only after session success.
- Split the producer implementation into focused internal modules while keeping public imports.
- Semantic records own immutable array payloads, so caller mutations cannot alter a snapshot.

### Protocol architecture

- Emit identity-only GSP panels plus explicit full-target panel layout intent.
- Move clipping policy to visual attachments through `Axes.set_clip_scope`.
- Expose typed local `EmissionFeature` values for textured-unlit mesh and linear-filter emission;
  these values are non-wire producer information and never session capabilities.

### Documentation

- Publish checked-in gallery PNGs in the documentation site and resolve repository source links
  to GitHub while retaining local review links.

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

- Scene execution accepts one or more 2D or 3D axes, including mixed figures, and emits an
  explicit deterministic left-to-right panel layout.
- VisPy2 imports `gsp-core` but no concrete adapter.
- Non-blocking and interactive execution requires an explicit caller-owned session.
- Datoviz DATA-space scalar images and linked colorbars are supported on the qualified retained
  View2D path; image-texel readback and comprehensive 3D/item/glyph queries remain unsupported.
- Live Datoviz View3D navigation remains experimental and opt-in.
