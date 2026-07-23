"""Minimal public GSP query through VisPy2.

This installed-wheel example uses Matplotlib only. It demonstrates one supported point ``HIT``
and one structured ``UNSUPPORTED`` result for a scene containing spheres and vectors. It is not a
claim of comprehensive picking support.
"""

from __future__ import annotations

import vispy2 as vp
from gsp.protocol import QueryPayload, QueryRequest, QueryResult, QueryStatus


def point_query() -> QueryResult:
    """Return a point HIT through one caller-owned Matplotlib session."""
    figure, axes = vp.subplots()
    axes.scatter([0.0], [0.0], size=16.0, color=[31, 119, 180, 255])
    request = QueryRequest(
        id="query:point",
        panel_id=axes.panel.id,
        coordinate=(0.0, 0.0),
        requested_payload=(QueryPayload.IDENTITY,),
    )
    with vp.open_session("matplotlib", require={"query.panel", "visual.points"}) as session:
        figure.display(session, block=False)
        return figure.query(session, request)


def unsupported_sphere_vector_query() -> QueryResult:
    """Return structured UNSUPPORTED for currently unqueryable visual families."""
    figure, axes = vp.subplots(projection="3d")
    axes.spheres([0.0], [0.0], [0.0], radius=0.4, color=[255, 127, 14, 255])
    axes.vectors(
        [0.0],
        [0.0],
        [0.0],
        [1.0],
        [0.0],
        [0.0],
        color=[44, 160, 44, 255],
    )
    request = QueryRequest(
        id="query:sphere-vector",
        panel_id=axes.panel.id,
        coordinate=(0.0, 0.0),
        requested_payload=(QueryPayload.IDENTITY,),
    )
    with vp.open_session(
        "matplotlib",
        require={"query.panel", "visual.sphere", "visual.vector"},
    ) as session:
        figure.display(session, block=False)
        return figure.query(session, request)


def run_example() -> tuple[QueryResult, QueryResult]:
    """Run the bounded HIT/UNSUPPORTED demonstration and verify its statuses."""
    hit = point_query()
    unsupported = unsupported_sphere_vector_query()
    if hit.status is not QueryStatus.HIT:
        raise RuntimeError(f"expected point HIT, received {hit.status.value}")
    if unsupported.status is not QueryStatus.UNSUPPORTED:
        raise RuntimeError(
            f"expected sphere/vector UNSUPPORTED, received {unsupported.status.value}"
        )
    return hit, unsupported


if __name__ == "__main__":
    for result in run_example():
        print(result)
