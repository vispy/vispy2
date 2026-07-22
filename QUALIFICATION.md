# Local bootstrap qualification

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
