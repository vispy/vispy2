"""Gallery 7: a point HIT and a structured unsupported visual query."""

from __future__ import annotations

import vispy2 as vp
from gsp.protocol import QueryPayload, QueryRequest, QueryStatus


def query_point() -> None:
    figure, axes = vp.subplots()
    axes.scatter([0.0], [0.0], size=20.0, color=[31, 119, 180, 255])
    request = QueryRequest(
        id="query:point",
        panel_id=axes.panel.id,
        coordinate=(0.0, 0.0),
        requested_payload=(QueryPayload.IDENTITY,),
    )
    with vp.open_session("matplotlib", require={"query.panel", "visual.points"}) as session:
        figure.display(session, block=False)
        result = figure.query(session, request)
    if result.status is not QueryStatus.HIT:
        raise RuntimeError(f"expected HIT, got {result.status.value}")
    print(f"point: {result.status.value}; hits={len(result.hits)}")


def query_unsupported() -> None:
    figure, axes = vp.subplots(projection="3d")
    axes.spheres([0.0], [0.0], [0.0], radius=0.5, color=[230, 57, 70, 255])
    request = QueryRequest(
        id="query:sphere",
        panel_id=axes.panel.id,
        coordinate=(0.0, 0.0),
        requested_payload=(QueryPayload.IDENTITY,),
    )
    with vp.open_session("matplotlib", require={"query.panel", "visual.sphere"}) as session:
        figure.display(session, block=False)
        result = figure.query(session, request)
    if result.status is not QueryStatus.UNSUPPORTED:
        raise RuntimeError(f"expected UNSUPPORTED, got {result.status.value}")
    print(f"sphere: {result.status.value}; diagnostic={result.diagnostic}")


if __name__ == "__main__":
    query_point()
    query_unsupported()
