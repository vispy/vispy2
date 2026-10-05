"""Guided, source-linked review steps for a broad VisPy2 project walkthrough."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewStep:
    """One explainable unit in the interactive project review."""

    id: str
    title: str
    explanation: str
    checks: tuple[str, ...]
    sources: tuple[str, ...]
    command: tuple[str, ...] = ()
    backends: tuple[str, ...] = ("matplotlib", "datoviz")
    smoke: bool = False
    estimated_minutes: int = 3
    kind: str = "read"


STEPS: tuple[ReviewStep, ...] = (
    ReviewStep(
        "orientation",
        "Scope and project map",
        "Start with the producer boundary: VisPy2 authors semantic figures and GSP scenes; adapters render them. Trace the package layout before judging feature parity.",
        (
            "Can you identify producer, protocol, and adapter responsibilities?",
            "Which repository owns each behavior?",
        ),
        ("vispy2/README.md", "vispy2/docs/index.md", "vispy2/AGENTS.md", "gsp/AGENTS.md"),
        smoke=True,
        estimated_minutes=4,
    ),
    ReviewStep(
        "architecture",
        "Architecture and lazy providers",
        "Follow Figure publication into an explicit session and lazy backend discovery. Metadata inspection should not create graphics resources, and VisPy2 should not import a concrete adapter.",
        (
            "Where does backend selection happen?",
            "What happens when a backend is absent?",
            "Are unsupported capabilities visible as diagnostics?",
        ),
        (
            "vispy2/src/vispy2/_figure.py",
            "vispy2/src/vispy2/session.py",
            "vispy2/src/vispy2/protocol.py",
            "gsp/packages/gsp-core/src/gsp/backends.py",
        ),
        estimated_minutes=5,
    ),
    ReviewStep(
        "protocol",
        "GSP protocol and semantic state",
        "Inspect how figures become typed scene snapshots and protocol commands. Check validation, ownership, and explicit capability negotiation at the boundary.",
        (
            "Which state is semantic and backend independent?",
            "How are malformed or unsupported requests reported?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/visuals.py",
            "gsp/packages/gsp-core/src/gsp/protocol/commands.py",
            "gsp/packages/gsp-core/src/gsp/protocol/capabilities.py",
            "gsp/packages/gsp-core/src/gsp/scene.py",
        ),
        estimated_minutes=5,
    ),
    ReviewStep(
        "visual-families",
        "All eleven visual families",
        "Walk the eleven protocol visual families and their producer entry points: point, pixel, sphere, vector, primitive, marker, segment, path, image, text, and mesh. The priority 2D case exercises points, markers, segments, paths, vectors, primitives, text, and pixels together.",
        (
            "Can you find validation and lowering for each family?",
            "Which families have distinct backend adaptations?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/visuals.py",
            "vispy2/docs/api-reference.md",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/protocol_renderer.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
        ),
        command=("python", "examples/manual_live_compare.py", "priority-2d"),
        smoke=True,
        kind="live",
        estimated_minutes=8,
    ),
    ReviewStep(
        "guides-colors",
        "Shared guides and color mapping",
        "Review titles, axes, colorbars, legends, ticks, and color mapping as protocol features. Inspect their per-backend lowering and label adaptations rather than assuming identical native controls.",
        (
            "Which guides are represented in shared scene state?",
            "Legends are deferred; what differences or omissions are diagnosed?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/guides.py",
            "gsp/packages/gsp-core/src/gsp/protocol/color_mapping.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/guides.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/guides.py",
        ),
        command=("python", "examples/manual_live_compare.py", "scalar-image"),
        smoke=True,
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "images",
        "Images, scalar fields, and pixels",
        "Compare scalar-image color mapping with pixel visuals, including coordinate and alpha behavior. Ask where data is decoded and how resource limits are enforced.",
        (
            "How are scalar values mapped to colors?",
            "How do image and pixel coordinate conventions differ?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/color_mapping.py",
            "gsp/packages/gsp-core/src/gsp/protocol/resources.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/tiled_image.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
        ),
        command=("python", "examples/review_live.py", "primitives-pixels"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "geometry-2d",
        "2D geometry and transforms",
        "Follow points, lines, markers, vectors, and primitive topology through shared transforms. Check how data coordinates, aspect, and device pixels meet at each backend.",
        (
            "Which transforms are shared protocol state?",
            "Where are backend-specific coordinate conversions made?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/transforms.py",
            "gsp/packages/gsp-core/src/gsp/protocol/visuals.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/transforms.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/geometry.py",
        ),
        command=("python", "examples/review_live.py", "strokes"),
        kind="live",
        estimated_minutes=6,
    ),
    ReviewStep(
        "geometry-3d",
        "3D projection, cameras, and meshes",
        "Review view3d state, projection, camera operations, mesh data, and material capability checks. Matplotlib adapts 3D projection; Datoviz native live navigation remains experimental and opt-in. Keep declared support distinct from behavior actually qualified on a backend.",
        (
            "How are orthographic and perspective views specified?",
            "Which material and normal features are capability gated?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/view3d.py",
            "gsp/packages/gsp-core/src/gsp/protocol/navigation.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
            "vispy2/docs/capability-matrix.md",
        ),
        command=("python", "examples/manual_live_compare.py", "perspective-3d"),
        smoke=True,
        kind="live",
        estimated_minutes=7,
    ),
    ReviewStep(
        "orthographic",
        "Orthographic projection and 3D pixel geometry",
        "Compare the orthographic 3D path, including pixel-sized geometry and its deliberate projection adaptation. Separate axis and projection behavior from perspective camera fitting.",
        (
            "Which state selects orthographic projection?",
            "How are pixel geometry and depth handled?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/view3d.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
            "vispy2/docs/capability-matrix.md",
        ),
        command=("python", "examples/manual_live_compare.py", "orthographic-3d"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "mesh-pick",
        "Mesh picking and query limits",
        "Inspect the dedicated Datoviz mesh-pick path and its bounded query contract. Treat a successful focused example as evidence for that path only.",
        ("Which hit data is returned?", "Which geometry and backend conditions bound this query?"),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/mesh_pick_geometry.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/query_execution.py",
            "gsp/packages/gsp-datoviz/tests/test_session_mesh_pick.py",
            "vispy2/examples/check_mesh_pick.py",
        ),
        command=("python", "examples/review_live.py", "mesh-pick"),
        backends=("datoviz",),
        kind="live",
        estimated_minutes=4,
    ),
    ReviewStep(
        "lighting",
        "Mesh materials and lighting",
        "Compare the flat Lambert mesh case with the Matplotlib projected reference and Datoviz lighting path. Inspect the explicit capability requirements before interpreting visual differences.",
        (
            "Which normal and light capabilities are required?",
            "Are shading and depth differences described as backend behavior?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/view3d.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
            "vispy2/docs/capability-matrix.md",
        ),
        command=("python", "examples/manual_live_compare.py", "flat-lambert"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "textures",
        "Textures and image resources",
        "Trace image and mesh texture references from descriptors to backend resources. Inspect validation and disposal paths alongside the visual result.",
        (
            "Which resource forms are accepted?",
            "Who owns decoded and native resources, and when are they released?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/resources.py",
            "gsp/packages/gsp-core/src/gsp/protocol/data_sources.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/visual_lowering.py",
        ),
        command=("python", "examples/review_live.py", "textures"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "transforms",
        "Affine transforms and coordinate spaces",
        "Inspect affine mesh transforms in DATA and NDC coordinate spaces. Compare the authored matrices with the rendered placement and the shared transform protocol.",
        (
            "How are coordinate space and transform composed?",
            "Which conversions are backend-specific?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/transforms.py",
            "gsp/packages/gsp-core/src/gsp/protocol/visuals.py",
            "vispy2/docs/api-reference.md",
        ),
        command=("python", "examples/review_live.py", "transforms"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "navigation",
        "Navigation, queries, and linked state",
        "Separate caller-authored navigation protocol from backend gestures. Linked 2D limits are producer state; linked native mouse navigation is deferred. Review query semantics only where implemented and exercised.",
        (
            "Which navigation events are serialized?",
            "What query results are shared across backends?",
            "What remains backend-local or deferred?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/navigation.py",
            "gsp/packages/gsp-core/src/gsp/protocol/query.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/navigation.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/navigation.py",
        ),
        command=("python", "examples/manual_live_compare.py", "camera-orbit"),
        kind="live",
        estimated_minutes=6,
    ),
    ReviewStep(
        "updates",
        "Retained updates and ownership",
        "Inspect update commands and snapshot ownership. Verify which edits can retain backend objects, and what invalidates or replaces a resource.",
        (
            "Which visual data can be updated in place?",
            "How are stale snapshots and released resources handled?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/updates.py",
            "gsp/packages/gsp-core/src/gsp/protocol/ownership.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/session.py",
        ),
        command=("python", "examples/review_live.py", "retained-updates"),
        smoke=True,
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "failures",
        "Failures, diagnostics, and adaptations",
        "Use capability checks and diagnostics to distinguish an unsupported feature from an adaptation. Follow one failure from producer request through protocol validation to renderer feedback.",
        (
            "Does the diagnostic name the affected feature?",
            "Can a caller tell whether output was adapted or omitted?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/diagnostics.py",
            "gsp/packages/gsp-core/src/gsp/protocol/capabilities.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/capabilities.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/capabilities.py",
        ),
        estimated_minutes=4,
    ),
    ReviewStep(
        "layout",
        "Layout, grids, and mixed panels",
        "Inspect normalized layout inputs, panel assignment, and backend resolution. Compare authored intent with resolved geometry and note when layouts are backend-specific.",
        (
            "How are rows, columns, and panel spans validated?",
            "Which layout decisions happen in the protocol versus the adapter?",
        ),
        (
            "gsp/packages/gsp-core/src/gsp/protocol/layout.py",
            "gsp/packages/gsp-core/src/gsp/protocol/panels.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/layout.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/layout.py",
        ),
        command=("python", "examples/manual_live_compare.py", "mixed-panels"),
        kind="live",
        estimated_minutes=6,
    ),
    ReviewStep(
        "scientific",
        "Scientific features and end-to-end examples",
        "Use the scientific grid and examples to connect API semantics, generated scene state, and rendered output. Check numerical inputs and labels as well as appearance.",
        (
            "Are inputs represented explicitly in the resulting scene?",
            "Do labels and scaling survive each backend path?",
        ),
        (
            "vispy2/src/vispy2/_scientific.py",
            "vispy2/examples/check_scientific_grid.py",
            "vispy2/tests/test_scientific.py",
            "gsp/packages/gsp-core/src/gsp/protocol/ticks.py",
        ),
        command=("python", "examples/review_live.py", "scientific-grid"),
        smoke=True,
        kind="live",
        estimated_minutes=6,
    ),
    ReviewStep(
        "lifecycle",
        "Session and backend lifecycle",
        "Trace session start, publication, event handling, close, and teardown. Look for explicit caller ownership and safe native resource destruction on failure paths.",
        (
            "Who owns a non-blocking session?",
            "Does close release subscriptions before destroying backend state?",
        ),
        (
            "vispy2/src/vispy2/session.py",
            "gsp/packages/gsp-core/src/gsp/backends.py",
            "gsp/packages/gsp-datoviz/src/gsp_datoviz/session.py",
            "gsp/packages/gsp-matplotlib/src/gsp_matplotlib/session.py",
        ),
        command=("python", "examples/manual_live_compare.py", "priority-2d"),
        kind="live",
        estimated_minutes=5,
    ),
    ReviewStep(
        "packaging",
        "Packaging and qualification",
        "Review installation extras, producer-only dependencies, wheel qualification, and the documented backend support matrix. Treat a passing source checkout as weaker evidence than a tested wheel combination.",
        (
            "Can the producer install without a plotting adapter?",
            "Which exact versions and backend combinations were qualified?",
        ),
        (
            "vispy2/pyproject.toml",
            "vispy2/QUALIFICATION.md",
            "gsp/packages/gsp-core/pyproject.toml",
            "gsp/packages/gsp-datoviz/pyproject.toml",
            "gsp/packages/gsp-matplotlib/pyproject.toml",
        ),
        estimated_minutes=5,
    ),
    ReviewStep(
        "documentation",
        "Documentation and runnable examples",
        "Check that public API docs, capability descriptions, and examples tell the same story as the implementation. Examples should make backend choice and explicit session ownership easy to see.",
        (
            "Can a new user find installation, API, and backend guidance?",
            "Do documented examples match current commands and support claims?",
        ),
        (
            "vispy2/docs/user-guide.md",
            "vispy2/docs/api-reference.md",
            "vispy2/docs/producer-and-backends.md",
            "vispy2/examples/README.md",
        ),
        estimated_minutes=4,
    ),
    ReviewStep(
        "risks",
        "Known risks and remaining review questions",
        "End by recording concrete gaps: unqualified backend behavior, diagnosed adaptations, resource or lifecycle concerns, and missing examples. Keep observations separate from assumptions.",
        (
            "What evidence supports each concern?",
            "What is the smallest follow-up that would resolve it?",
        ),
        (
            "vispy2/docs/capability-matrix.md",
            "vispy2/QUALIFICATION.md",
            "vispy2/docs/manual-pre-release-review.md",
        ),
        smoke=True,
        estimated_minutes=4,
    ),
)


def select_steps(plan: str = "full") -> tuple[ReviewStep, ...]:
    """Return the ordered full walkthrough or its short smoke subset."""
    if plan == "full":
        return STEPS
    if plan == "smoke":
        return tuple(step for step in STEPS if step.smoke)
    raise ValueError(f"unknown review plan {plan!r}; expected 'full' or 'smoke'")
