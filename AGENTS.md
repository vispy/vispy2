# AGENTS.md

## Product boundary

- VisPy2 produces typed GSP scenes and does not define protocol semantics.
- Figures, axes, visuals, and scene snapshots contain semantic state only.
- Never import `gsp_matplotlib`, `gsp_datoviz`, or another concrete adapter.
- One-shot publication conveniences delegate to GSP sessions.
- Interactive and non-blocking execution requires an explicit caller-owned GSP session.
- Do not add remotes, push, tag, publish, or import legacy Git history without owner approval.

## Migration

Record exact source provenance. Preserve semantic behavior, not unpublished legacy import paths.
Validate producer-only installation with `gsp-core` and adapter combinations from built wheels.

