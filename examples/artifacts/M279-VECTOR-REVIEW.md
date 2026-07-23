# M279 vector review

The `vectors_2d_3d.py` example builds a 2D rotational field and a perspective View3D field from nonzero DATA-space displacement vectors. The 2D grid explicitly removes the origin vector; the 3D field has a nonzero vertical component for every item.

The Datoviz adapter lowers the semantic visual through public `dvz_vector` attributes and `DvzVectorStyle` values while preserving one native item per source vector. M279 did not produce or qualify a native Datoviz capture, and no Datoviz PNG is included as evidence. The file-output example is explicitly Matplotlib-only and rejects a Datoviz backend before opening a session. Native GUI and capture qualification remain assigned to M284.

Matplotlib preserves resolved endpoints, colors, logical-pixel widths, and deterministic ordering. Vector heads are an explicit marker-based adaptation. The View3D path projects canonical 3D endpoints into a 2D overlay; it is not evidence of native Matplotlib 3D axes or native 3D vector-head rasterization.
