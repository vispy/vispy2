from collections.abc import Callable
from pathlib import Path
import runpy
from typing import cast

from gsp.protocol import QueryResult, QueryStatus


def test_installed_wheel_query_example_has_bounded_hit_and_unsupported_paths() -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "minimal_query.py"))
    run_example = cast(
        Callable[[], tuple[QueryResult, QueryResult]],
        example["run_example"],
    )

    hit, unsupported = run_example()

    assert hit.status is QueryStatus.HIT
    assert hit.hit
    assert hit.visual_id is not None
    assert unsupported.status is QueryStatus.UNSUPPORTED
    assert not unsupported.hit
    assert unsupported.diagnostic is not None
