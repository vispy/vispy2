# M281 text billboard review

The deterministic Matplotlib artifact is `matplotlib-text-billboards3d.png`. It uses three separated 3D stations: a sphere with a sans ASCII label, a triangle with a serif `Δ café` label, and a vector with a monospace label rotated 20° in the display plane. Each label is a separate `TextVisual` with a distinct horizontal anchor, vertical anchor, color, font role, and `z_order`.

Matplotlib maps generic roles through its configured font-family aliases and converts logical pixels to points at the active canvas DPI. Datoviz uses the public retained text object, UTF-8 string, style, and placement API. Its current public `DvzTextStyle` exposes an optional concrete `DvzFont*`, not a generic role selector; the GSP adapter therefore leaves the pointer unset and uses the backend default font. `FontLayoutCapability.font_family_request` and `rasterization_parity` remain false, so this adaptation does not claim exact role selection, glyph coverage, metrics, shaping, or raster parity.

Matplotlib renders the labels as ordered screen-facing overlays by projecting DATA anchors into axes-fraction coordinates. Datoviz adapter coverage is limited to public lowering and a no-capture smoke path: it projects DATA anchors into retained panel-relative placement and recomputes placement after retained camera/projection updates. M281 produced no native Datoviz PNG and does not qualify native rendering or capture; M284 owns that work. Neither backend advertises `textvisual.billboard3d.depth_occlusion.v1`.

Later evidence: M283 gallery 2 produced an installed-wheel Datoviz billboard PNG. This note remains
the historical M281 review and does not claim font, shaping, or depth-occlusion parity.

No public font files, glyph IDs, atlases, rich-text model, shaping guarantees, hidden backend text handles, or per-glyph query behavior were introduced.
