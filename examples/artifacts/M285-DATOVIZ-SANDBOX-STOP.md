# M285 Datoviz sandbox stop

Date: 2026-07-25

Status: resolved for M285 by the previously proven unsandboxed execution route.

## Completed work

- VisPy2 propagates canonical `CanvasSize` through `Figure`, `subplots`, and `to_scene`.
- All static gallery scenes request `CanvasSize.pixel_exact(800, 600)`.
- The installed-wheel validator parses PNG headers and rejects any dimension other than 800×600.
- Matplotlib file output preserves the resolved figure DPI; all seven regenerated captures are
  exactly 800×600.
- Guide-free Matplotlib View3D scenes hide the unintended native 2D frame while preserving panel
  titles and View2D semantic guides.
- The Datoviz capability snapshot no longer advertises a nonexistent `PanelTextGuide` screen-text
  adaptation. It reports `panel_text_title_unsupported_no_public_renderer_path`.
- Gallery 3 uses one uniform primitive color and pixel anchors that do not coincide with primitive
  vertices or create equal-depth ties.
- The repository suites pass 768 tests after the focused live-loop regressions. Strict mypy, Ruff,
  documentation Python blocks, local links, wheel builds, import isolation, and diff checks pass.
- Gallery 5 returns to Python after every bounded native frame, honors one `Ctrl-C`, releases the
  context-managed session, and leaves no process behind.

## Native sandbox result

The installed-wheel harness copied its scripts outside both source trees and completed all seven
Matplotlib captures. The first Datoviz gallery process then emitted macOS HIServices and
LaunchServices connection-denial messages and exceeded the 20-second process-group boundary. Its
one configured retry failed in the same way. Both process groups were terminated by the harness;
no gallery process was left running.

This matches the sandbox-only M284 environment finding. Independent M284 execution outside the
Codex sandbox completed the same native lifecycle normally, so this result is not evidence of a
Datoviz adapter failure and does not justify weakening another capability.

## Evidence disposition

After committing and integrating the implementation as GSP `4ff1614` and VisPy2 `d4c8d65`, Mission
Control rebuilt all four wheels and ran the updated harness outside the Codex sandbox. All fourteen
captures completed without retry, imported GSP and VisPy2 from the isolated wheel site, and passed
the exact 800×600 requirement. Gallery 3's Datoviz artifact changed with the corrected uniform
primitive and separated pixels; unchanged Datoviz scenes reproduced byte-identically. The final
manifest records exact source revisions plus script, wheel, and artifact hashes. Rebuilding the
VisPy2 wheel after the Gallery 5-only correction reproduced its prior wheel hash byte-for-byte, and
the complete fourteen-capture harness reproduced every artifact byte-for-byte at the final source
revision. This resolves the artifact-regeneration stop without reclassifying the sandbox denial as
a product defect.
