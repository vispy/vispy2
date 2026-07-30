# Qualification history

Qualification records are immutable snapshots. The newest source/documentation gate appears first;
the original producer-only bootstrap remains below with its exact artifact hashes.

## M303 pre-release mechanical correction gate

Date: 2026-07-30

Committed VisPy2 head: `c60d9941ee2c2b88203a86c653c5b83b3df8f9bc`.

Committed GSP head: `aee00ca22f52b8168ab6d5e6ceb877b218452729`.

| Gate | Result |
|---|---|
| VisPy2 source pytest with Matplotlib 3.11.1 | 124 passed |
| strict mypy | 3 source files clean |
| Ruff | source, tests, and examples clean |
| documentation validation | 30 Python blocks compiled; 64 local links resolved |
| strict MkDocs | passed with recorded informational checkout-link notices |
| intended publication set from isolated wheels | 628 passed, one Datoviz-only conformance module skipped |
| installed semantic example | passed from `site-packages` |
| Twine and wheel contents | passed without warnings |
| packaged license | SPDX `BSD-3-Clause` and LICENSE present |

The brittle 10,000-exact-pixel flat-Lambert assertion was replaced by a normalized semantic check:
the rendered face colors occupy a substantial total mesh footprint and each contributes a
material fraction of that footprint. This passes across the declared Matplotlib 3.10–3.x range
without weakening the requirement for two visible face tones.

The intended first ordinary publication set contains `gsp-core`, `gsp-matplotlib`, and `vispy2`.
The `datoviz` extra is intentionally absent until a compatible runtime is ordinarily resolvable;
local `gsp-datoviz` development and native qualification remain supported separately.

| Artifact | SHA-256 |
|---|---|
| `vispy2-0.2.0a1-py3-none-any.whl` | `460ca0bc69b2b935d0e45ac178a05bc1b2446d62ea1d99a6bfe19816edff0f71` |

This gate performs no version, tag, push, or publication operation. P038 still blocks the
independent Panel and producer-capability protocol refactor.

## Current committed-head source and documentation gate

Date: 2026-07-28

The committed VisPy2 head `0f6c78e3032ab6fbe47389a3faae308e5d8c0845` was exported to a
temporary directory rather than tested from the working tree. The sibling committed GSP head was
`fd20c94264bf8893eed6c27e35966ff0397f14cb`. CPython 3.13.4 imported VisPy2 from the exported
`src` directory, excluding concurrent uncommitted working-tree changes.

| Gate | Result |
|---|---|
| VisPy2 pytest | 116 passed |
| strict mypy | 3 source files, no issues |
| Ruff | source, tests, and examples passed |
| documentation validation | 32 Python blocks compiled; 59 local links resolved across both exported repositories |
| wheel build | `vispy2-0.2.0a1-py3-none-any.whl` built successfully with `uv build --wheel` |
| wheel SHA-256 | `c0c473b18c0fc34e6b9a83d7192d819b43e958761319e761f0ba641d7292fc8f` |

This is a committed-head source, documentation, and build gate. It does not supersede M292's
four-wheel import isolation, cross-backend artifacts, native lifecycle evidence, or owner review;
those exact historical claims remain in
[`examples/artifacts/M292-EXACT-WHEEL-QUALIFICATION.md`](examples/artifacts/M292-EXACT-WHEEL-QUALIFICATION.md).

The default shell `python` is an unrelated Python 3.12 environment and is not a valid VisPy2
qualification interpreter. The apparent ndarray typing failure observed there was not reproducible
under the required Python 3.13 environment.

## Original local bootstrap

Date: 2026-07-22

The unpublished `vispy2==0.2.0a1` wheel was installed with the built `gsp-core` wheel in an
isolated environment containing no adapter. All 10 producer tests and the backend-neutral semantic
example pass. Strict mypy passes for all three source files and Ruff passes.

Local wheel resolution for both `vispy2[matplotlib]` and `vispy2[datoviz]` succeeds when the built
GSP artifacts are supplied. One unchanged `Figure.to_scene()` snapshot rendered through both
provider interfaces: the Matplotlib PNG was 10,617 bytes and the Datoviz PNG was 24,280 bytes.
Datoviz used the explicit local development checkout at commit
`be7f2a80354c25e85bab88c85f5ea7340975b569`; this is not a published dependency claim.

| Artifact | SHA-256 |
|---|---|
| `vispy2-0.2.0a1-py3-none-any.whl` | `637b73fe6755b838744042024bf90e6255bc1491e342e325505fc2abd1ab9730` |
| `vispy2-0.2.0a1.tar.gz` | `04da53ac8e2676d53c43c8a9274729c6aa6518c816dc5eb0e9434724c539dd40` |
| qualified `gsp-core` wheel | `727ec6d12078b8abf2aa1f3eebc6373704eba6a2e17b5c98256c9e8f37e607cc` |
