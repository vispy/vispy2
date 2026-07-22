"""GSP session conveniences that preserve the producer/backend boundary."""

from __future__ import annotations

from collections.abc import Collection

from gsp import BackendError
from gsp.backends import BackendSession, open_session as _open_session


def open_session(
    backend: str,
    *,
    require: Collection[str] = (),
    adaptation: Collection[str] = (),
) -> BackendSession:
    """Open an explicit caller-owned GSP backend session."""
    return _open_session(backend, require=require, adaptation=adaptation)


def require_session(
    backend: str,
    *,
    extra: str,
    require: Collection[str] = (),
) -> BackendSession:
    """Open a convenience session with an actionable optional-extra error."""
    try:
        return open_session(backend, require=require)
    except BackendError as exc:
        raise RuntimeError(
            f"the {backend!r} backend is unavailable; install vispy2[{extra}] "
            f"and inspect gsp.discover_backends(probe=True): {exc}"
        ) from exc
