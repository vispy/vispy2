# M292 qualified capability matrix

M292 requalifies comparable pixel-exact geometry after the Datoviz binding safety repairs and
corrects plot-local raster measurement for canvases whose outer background differs. All fourteen
artifacts were regenerated from exact committed wheels at GSP `fd20c94` and VisPy2 `7d2eb41`;
the schema-2 manifest records source, script, wheel, and artifact hashes.

Status vocabulary: **strict** preserves the named GSP semantic contract; **adapted** preserves
bounded semantics with documented raster/layout/depth differences; **experimental** is opt-in and
remains outside the default execution path; **unsupported** returns a capability error or
structured query result. “Probe” means gallery 6 checks installed provider metadata and
diagnostics. The recorded experimental live-navigation path has completed owner review, but that
acceptance does not make it a default or universal backend claim.

| Journey / visual | Protocol contract | VisPy2 API | Matplotlib | Datoviz v0.4 | Status | Test | Artifact | Diagnostic / boundary |
|---|---|---|---|---|---|---|---|---|
| G1 points | `visual.points` | `Axes.scatter` | yes | yes | strict semantic data; backend raster | installed-wheel G1 | both G1 PNGs | marker raster differs |
| G1 markers | `visual.markers` | `Axes.markers` | yes | yes | strict attributes; backend raster | installed-wheel G1 | both G1 PNGs | shape antialiasing differs |
| G1 pixels | `visual.pixels`, `pixelvisual.v1` | `Axes.pixels` | yes | yes when probed | strict logical size; backend raster | G1 + capability check | both G1 PNGs | physical raster differs |
| G1 vectors | `visual.vector`, `vectorvisual.straight.v1` | `Axes.vectors` | yes | yes when probed | MPL adapted; DVZ strict lowering | G1 + capability check | both G1 PNGs | cap raster differs |
| G1 primitive | `visual.primitive`, topology contract | `Axes.primitives` | yes | yes when probed | MPL adapted; DVZ strict lowering | G1 + capability check | both G1 PNGs | raster/depth differs |
| G1 text | `visual.text` | `Axes.text` | yes | yes when probed | adapted native font/layout | installed-wheel G1 | both G1 PNGs | font and metrics differ |
| G2 mesh | perspective View3D + DATA mesh | `Axes3D.mesh` | yes | yes when probed | MPL adapted projection; DVZ strict retained path | G2 checks | both G2 PNGs | depth/raster differs |
| G2 spheres | `spherevisual.v1` | `Axes3D.spheres` | yes | yes when probed | MPL flat projected circle; DVZ natively shaded analytic impostor | G2 checks | both G2 PNGs | intentional shading/depth adaptation; no material contract |
| G2 vectors | 3D DATA vector contract | `Axes3D.vectors` | yes | yes when probed | MPL adapted overlay; DVZ strict lowering | G2 checks | both G2 PNGs | depth/caps differ |
| G2 billboards | `textvisual.billboard3d.v1` | `Axes3D.text` | yes | yes when probed | adapted overlay on both | G2 checks | both G2 PNGs | no strict glyph parity/occlusion |
| G3 primitive | uniform-color indexed triangle strip + orthographic View3D | `Axes3D.primitives` | yes | yes when probed | MPL adapted; DVZ strict lowering | G3 construction + capture checks | both G3 PNGs | no cross-backend interpolation claim |
| G3 pixels | non-coincident 3D DATA logical-pixel squares | `Axes3D.pixels` | yes | yes when probed | MPL adapted overlay; DVZ strict lowering | G3 construction + capture checks | both G3 PNGs | no positional/depth ties; no raster parity |
| G4 fit | canonical perspective fit | `Axes3D.fit_camera` | yes | yes | strict camera state | installed-wheel G4 | both `04-00` PNGs | safe near/far set after fit |
| G4 orbit | canonical orbit reducer | `Axes3D.orbit` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-01` PNGs | not a live-input claim |
| G4 pan | canonical pan reducer | `Axes3D.pan` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-02` PNGs | not a live-input claim |
| G4 zoom | canonical zoom reducer | `Axes3D.zoom` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-03` PNGs | not a live-input claim |
| G5 live camera | `view3d.navigation.orbit_pan_zoom.v1` | caller-owned `display` | no | opt-in only | experimental | manual review | none | close window; `Ctrl-C` fallback |
| G6 discovery | provider metadata + snapshot | `discover_backends`, `open_session` | yes | yes | strict selection/probe | installed-wheel G6 | console only | Datoviz surface is binding-dependent |
| G7 point query | panel query, identity payload | `Figure.query` | yes | bounded point path | strict bounded path | G7 MPL; adapter/install DVZ | console `HIT` | rendered caller-owned session required |
| G7 sphere query | structured unsupported result | `Figure.query` | unsupported | unsupported | unsupported by design | G7 MPL; capability boundary DVZ | console `UNSUPPORTED` | no sphere/3D picking |

Guide/title and file-output support are cross-cutting. Matplotlib provides native semantic
axes/title layout and deterministic PNG/SVG/PDF; it hides the default native frame for guide-free
View3D. Datoviz provides native/adapted axes and PNG when its capture binding qualifies, but the
qualified binding exposes no public `PanelTextGuide` renderer. Its snapshot therefore reports
panel titles as unsupported with
`panel_text_title_unsupported_no_public_renderer_path`; it does not claim an invisible
adaptation. M284's 25/25 static and 25/25 live lifecycle evidence remains exact-runtime evidence,
not a universal lifecycle claim.
