"""Gallery 6: lazy backend discovery and explicit capability-based selection."""

from __future__ import annotations

import gsp


REQUIRED = {"output.file", "visual.mesh"}


def main() -> None:
    for metadata in gsp.discover_backends():
        print(f"installed: {metadata.name}")
    for probe in gsp.discover_backends(probe=True):
        missing = sorted(REQUIRED - probe.capabilities)
        state = "eligible" if probe.available and not missing else "ineligible"
        print(f"{probe.name}: {state}; missing={missing}; diagnostics={probe.diagnostics}")

    # Selection is ordered and explicit. It never silently chooses an arbitrary plugin.
    with gsp.open_session(prefer=("datoviz", "matplotlib"), require=REQUIRED) as session:
        print(f"selected: {session.backend_name}")
        print(f"snapshot: {session.capabilities.snapshot_id}")


if __name__ == "__main__":
    main()
