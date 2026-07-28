# Qualification history

Qualification records are immutable snapshots. The newest source/documentation gate appears first;
the original producer-only bootstrap remains below with its exact artifact hashes.

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
