# M284 Datoviz lifecycle environment finding

Date: 2026-07-23

Status: two Codex-sandbox hangs distinguished from successful unsandboxed native qualification

## Provenance

| Component | Revision or artifact |
|---|---|
| GSP source | `d2d25a2cd328b5026878015cb3f23560309d26b7` |
| VisPy2 source | `66734a37487fa719ec0c3c1e10ba57eb74703548` |
| Datoviz read-only source | `be7f2a80354c25e85bab88c85f5ea7340975b569` |
| Python | CPython 3.13.4 |
| `gsp-core` wheel SHA-256 | `010329652f440dd7aeaedf2009a34c7d25fde396a156fd9b34424c67b1fa1d65` |
| `gsp-matplotlib` wheel SHA-256 | `838116ccc8635cd714b655fbcc55c35c18d54bddc8f9ed7dea47ba52b572aae9` |
| `gsp-datoviz` wheel SHA-256 | `0b5df379caec97c2eb6d3cc0ad041a477f05edbd04bc4842092ad46934802ef9` |
| `vispy2` wheel SHA-256 | `c70c1be9298972440ecd4e26a028234e18682bcf824349929d2decb3c169daa9` |

The four wheels were installed into `/private/tmp/m284-qualification.79VRUA/wheel-env`. A probe
from `/private/tmp` confirmed that `gsp`, `gsp_matplotlib`, `gsp_datoviz`, and `vispy2` resolved
from that environment's `site-packages`; NumPy, Matplotlib, pytest, and the pinned Datoviz source
binding were supplied from the existing qualified Python 3.13 dependency environment because
network access was unavailable.

## Codex-sandbox result

The installed-wheel gallery harness copied the gallery scripts to its own temporary directory and
invoked:

```console
python gallery_01_priority_2d.py datoviz --output-dir /Users/cyrille/GIT/Viz/GSP_API-agent-workspaces/R20260723-182045-M284/vispy2/examples/artifacts
```

The first process produced no new Datoviz artifact and did not exit within 20 seconds. The harness
terminated its process group and performed its one configured retry. The retry also produced no
new Datoviz artifact and did not exit within 20 seconds. The harness then failed with:

```text
RuntimeError: timed out after 20s: ... gallery_01_priority_2d.py datoviz --output-dir .../vispy2/examples/artifacts
```

Both sandboxed attempts emitted macOS HIServices/LaunchServices connection denials, including
`com.apple.hiservices-xpcservice` connection-invalid and `_LSModifyNotification` failures, before
hanging. The checked-in `datoviz-gallery-01-priority-2d.png` retained its pre-mission timestamp and
is not evidence from either failed run. These are **2/2 Codex-sandbox failures**, not evidence of
an adapter or native-runtime failure.

## Independent unsandboxed native result

An independent exact-wheel rerun outside the Codex sandbox succeeded under the same 20-second
per-process boundary:

| Native gate | Result |
|---|---|
| Datoviz gallery 1 | passed in 1.72 s; 31,547-byte PNG |
| Static process lifecycle | 25/25 passed; each isolated; 0.609--0.779 s |
| Static artifact | 32,071 bytes each; SHA-256 prefix `eb799781` |
| Live View3D process lifecycle | 25/25 passed; each isolated; 0.496--0.564 s |
| Full gallery | 14/14 passed; byte-identical to M283 |
| Import isolation | GSP and VisPy2 imports resolved from wheel-environment `site-packages` |

The full gallery used GSP `d2d25a2cd328b5026878015cb3f23560309d26b7` and VisPy2
`66734a37487fa719ec0c3c1e10ba57eb74703548`. Its fourteen hashes and byte counts are recorded in
`manifest.json`.

## Other completed gates

| Gate | Result |
|---|---|
| GSP source pytest | 696 passed |
| VisPy2 source pytest | 63 passed |
| GSP strict mypy | 51 source files, no issues |
| VisPy2 strict mypy | 3 source files, no issues |
| GSP and VisPy2 Ruff | passed |
| Documentation Python blocks and local links | 15 blocks and 25 links validated after review-pack correction |
| Wheel builds | all four succeeded |
| Installed-wheel GSP pytest | 696 passed |
| Installed-wheel VisPy2 pytest | 63 passed |
| Wheel import isolation probe | all four project imports resolved from the clean wheel environment |
| Matplotlib gallery 1-4 regeneration | seven captures completed |

## Disposition

The original stop was correct for the evidence available to that worker, but the independent
unsandboxed evidence classifies the hang as a sandbox/macOS service-access limitation. No GSP,
VisPy2, Datoviz, or capability-status change is justified. Automated M284 qualification is
complete; S065 remains open for project-owner visual and interactive acceptance.
