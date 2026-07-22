# Provenance

This repository has a fresh Git history curated from `vispy/GSP_API`.

| Item | Value |
|---|---|
| Source repository | `vispy/GSP_API` |
| Source baseline | `463d34d1d6560f045e5c40af594372d0fea93ab5` |
| Source bundle | `GSP_API-source-463d34d1-2026-07-22.bundle` |
| Bundle SHA-256 | `4b6b8bdd0e403ea9f0ed7d169a7694ac0985e7a8906890d2f74cf1dc5c611f8b` |
| Architecture decision | source ADR-0035 |

The complete research history remains recoverable from the source repository and bundle. Migration
commits record source paths/blob IDs and exact-versus-derived status.

## Producer migration

`src/vispy2/protocol.py` is derived from source blob
`2bc6e2f02cd75d676616c9c4d32270d9e286b9e9` at `src/gsp_vispy2/protocol.py`. Direct Matplotlib
imports and backend-specific rendering methods were removed; `Figure.to_scene()` and GSP session
delegation replace them. `src/vispy2/session.py` is a replacement for source blob
`531f4787829b98669cf036c6c540b859f160e0cd`: it delegates to the provider SPI and imports no
adapter. The package initializer is rewritten from source blob
`9c9fb3d470fc0bfb088eda1186d7387bc8b93012` without legacy helper packages or prototype aliases.
