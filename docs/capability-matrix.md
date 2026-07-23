# M284 exact-head capability matrix

Evidence revision: GSP `d2d25a2cd328b5026878015cb3f23560309d26b7`, VisPy2
`66734a37487fa719ec0c3c1e10ba57eb74703548`. M284 refreshed the evidence at these exact heads
without changing any capability status.

Status vocabulary: **strict** preserves the named GSP semantic contract; **adapted** preserves
bounded semantics with documented raster/layout/depth differences; **experimental** is opt-in and
still requires human review; **unsupported** returns a capability error or structured query
result. “Probe” means gallery 6 checks installed provider metadata and diagnostics.

| Journey / visual | Protocol contract | VisPy2 API | Matplotlib | Datoviz v0.4 | Status | Test | Artifact | Diagnostic / boundary |
|---|---|---|---|---|---|---|---|---|
| G1 points | `visual.points` | `Axes.scatter` | yes | yes | strict semantic data; backend raster | installed-wheel G1 | both G1 PNGs | marker raster differs |
| G1 markers | `visual.markers` | `Axes.markers` | yes | yes | strict attributes; backend raster | installed-wheel G1 | both G1 PNGs | shape antialiasing differs |
| G1 pixels | `visual.pixels`, `pixelvisual.v1` | `Axes.pixels` | yes | yes when probed | strict logical size; backend raster | G1 + capability check | both G1 PNGs | physical raster differs |
| G1 vectors | `visual.vector`, `vectorvisual.straight.v1` | `Axes.vectors` | yes | yes when probed | MPL adapted; DVZ strict lowering | G1 + capability check | both G1 PNGs | cap raster differs |
| G1 primitive | `visual.primitive`, topology contract | `Axes.primitives` | yes | yes when probed | MPL adapted; DVZ strict lowering | G1 + capability check | both G1 PNGs | interpolation/depth differs |
| G1 text | `visual.text` | `Axes.text` | yes | yes when probed | adapted native font/layout | installed-wheel G1 | both G1 PNGs | font and metrics differ |
| G2 mesh | perspective View3D + DATA mesh | `Axes3D.mesh` | yes | yes when probed | MPL adapted projection; DVZ strict retained path | G2 checks | both G2 PNGs | depth/raster differs |
| G2 spheres | `spherevisual.v1` | `Axes3D.spheres` | yes | yes when probed | MPL adapted circle; DVZ analytic impostor | G2 checks | both G2 PNGs | MPL no analytic surface depth |
| G2 vectors | 3D DATA vector contract | `Axes3D.vectors` | yes | yes when probed | MPL adapted overlay; DVZ strict lowering | G2 checks | both G2 PNGs | depth/caps differ |
| G2 billboards | `textvisual.billboard3d.v1` | `Axes3D.text` | yes | yes when probed | adapted overlay on both | G2 checks | both G2 PNGs | no strict glyph parity/occlusion |
| G3 primitive | indexed triangle strip + orthographic View3D | `Axes3D.primitives` | yes | yes when probed | MPL adapted; DVZ strict lowering | G3 checks | both G3 PNGs | painter vs GPU depth |
| G3 pixels | 3D DATA logical-pixel squares | `Axes3D.pixels` | yes | yes when probed | MPL adapted overlay; DVZ strict lowering | G3 checks | both G3 PNGs | no raster parity |
| G4 fit | canonical perspective fit | `Axes3D.fit_camera` | yes | yes | strict camera state | installed-wheel G4 | both `04-00` PNGs | safe near/far set after fit |
| G4 orbit | canonical orbit reducer | `Axes3D.orbit` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-01` PNGs | not a live-input claim |
| G4 pan | canonical pan reducer | `Axes3D.pan` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-02` PNGs | not a live-input claim |
| G4 zoom | canonical zoom reducer | `Axes3D.zoom` | yes | yes | strict programmatic state | installed-wheel G4 | both `04-03` PNGs | not a live-input claim |
| G5 live camera | `view3d.navigation.orbit_pan_zoom.v1` | caller-owned `display` | no | opt-in only | experimental | manual review | none | close window; `Ctrl-C` fallback |
| G6 discovery | provider metadata + snapshot | `discover_backends`, `open_session` | yes | yes | strict selection/probe | installed-wheel G6 | console only | Datoviz surface is binding-dependent |
| G7 point query | panel query, identity payload | `Figure.query` | yes | bounded point path | strict bounded path | G7 MPL; adapter/install DVZ | console `HIT` | rendered caller-owned session required |
| G7 sphere query | structured unsupported result | `Figure.query` | unsupported | unsupported | unsupported by design | G7 MPL; capability boundary DVZ | console `UNSUPPORTED` | no sphere/3D picking |

Guide/title and file-output support are cross-cutting. Matplotlib provides native axes/title layout
and deterministic PNG/SVG/PDF. Datoviz provides native/adapted panel guides and PNG only when its
capture binding qualifies; its resolved layout snapshot remains partial. M283 proves PNG capture
for the exact probed runtime. M284 additionally proves 25/25 isolated static and 25/25 isolated
live View3D Datoviz processes under a 20-second boundary in the qualified unsandboxed native
environment; this remains exact-runtime evidence, not a universal lifecycle claim.
