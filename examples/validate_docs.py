"""Compile Python documentation blocks and validate local Markdown links."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


FENCE = re.compile(r"```(?P<language>[^\n]*)\n(?P<body>.*?)```", re.DOTALL)
LINK = re.compile(r"(?<!!)\[[^]]+\]\((?P<target>[^)]+)\)")


def _documents(root: Path) -> tuple[Path, ...]:
    documents = {*root.rglob("README.md"), *(root / "docs").rglob("*.md")}
    return tuple(sorted(documents))


def validate(root: Path) -> tuple[int, int]:
    python_blocks = 0
    local_links = 0
    for document in _documents(root):
        text = document.read_text(encoding="utf-8")
        for match in FENCE.finditer(text):
            language = match.group("language").strip()
            if language == "python":
                compile(match.group("body"), f"{document}:python-block", "exec")
                python_blocks += 1
            elif language not in {"", "console", "text"}:
                raise RuntimeError(f"{document}: unclassified code fence {language!r}")
        for match in LINK.finditer(text):
            target = match.group("target").split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                raise RuntimeError(f"{document}: broken local link {target!r}")
            local_links += 1
    return python_blocks, local_links


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", type=Path, nargs="+")
    args = parser.parse_args()
    blocks = 0
    links = 0
    for root in args.roots:
        root_blocks, root_links = validate(root.resolve())
        blocks += root_blocks
        links += root_links
    print(f"validated {blocks} Python blocks and {links} local Markdown links")


if __name__ == "__main__":
    main()
