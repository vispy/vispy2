# M292 exact-wheel qualification

M292 rebuilt exactly four wheels from clean committed heads, ran the gallery scripts outside both
source trees with project imports isolated to those wheels, and published a portable schema-2
manifest. The candidate revisions are GSP `fd20c94` and VisPy2 `7d2eb41`.

| Wheel | SHA-256 |
|---|---|
| `gsp-core` | `95b34b86cdbabda4bcd2cf5d6fb0f0910f731707e29201b1f1c56cba96aa74f0` |
| `gsp-matplotlib` | `989ea49d929f93662cfa53bdb107c83fcc384d3cc48bbd1a0665b2d5e7b0e63a` |
| `gsp-datoviz` | `db21fb96c9e66f7730ca4a0b9b0c9f17fd193e15b152f52f9c62d1d78e0b45e8` |
| `vispy2` | `214eb532c4ea6119cbfa7d1db59b295d949c46aba4572a504c50413e7a930e3b` |

## Automated result

- All fourteen canonical PNGs are fresh and exactly 800×600.
- Shared logical layout and projection evidence passes.
- Fit, orbit, pan, and zoom width/height ratios range from 0.988 to 0.995, within the 2% tolerance.
- Backend discovery, capability checks, point `HIT`, and structured unsupported query checks pass.
- A producer-only environment imports the exact `gsp-core` and `vispy2` wheels while neither
  adapter distribution is importable.
- Final committed-head gates pass with 801 GSP tests and 84 VisPy2 tests, strict mypy, Ruff, and
  documentation/link validation.
- Every artifact hash and all four wheel hashes are recorded in
  [manifest.json](manifest.json), with no host-absolute path.
- Gallery 5 started from the isolated four-wheel site, accepted one bounded interrupt, exited zero,
  and left no process running.

The initial camera-size diagnostic was a validator false positive, not a rendering regression. It
sampled the outer canvas corner as the plot background and included one row and column outside the
half-open plot rectangle. Datoviz uses a dark outer canvas around a white plot, while Matplotlib's
outer canvas is white. The corrected validator measures against the dominant inset plot-perimeter
background and has synthetic coverage that both accepts this backend background difference and
rejects a genuine scale mismatch above 2%.

## Review result

Visual review confirms matched 800×600 canvases, comparable camera scale, uniform orthographic
primitive color, consistent red-square/triangle depth ordering, and the documented axes/title
policy. Datoviz's natively shaded raycast spheres versus Matplotlib's flat projected circles remain
an intentional adapted rendering difference, not a material-parity claim.

An independent evidence review returned unconditional **ACCEPT**. At the time of this exact-wheel
run, M284 and S065 remained open only for the owner's visual and interactive acceptance. The owner
subsequently accepted S065 on 2026-07-28; that later decision is recorded in
[`../../docs/M284-human-review.md`](../../docs/M284-human-review.md).
