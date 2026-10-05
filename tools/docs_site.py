"""Publish repository-owned artifacts while keeping source Markdown locally useful."""

from __future__ import annotations

from pathlib import Path
import re

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files
from mkdocs.structure.pages import Page

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_MARKDOWN_TARGET = re.compile(r"(?P<prefix>\]\()(?P<target>[^)]+)(?P<suffix>\))")


def on_files(files: Files, config: MkDocsConfig) -> Files:
    """Expose the original PNG bytes as site assets, without a tracked second copy."""
    for artifact in sorted((_REPOSITORY_ROOT / "examples" / "artifacts").glob("*.png")):
        uri = artifact.relative_to(_REPOSITORY_ROOT).as_posix()
        files.append(File.generated(config, uri, abs_src_path=str(artifact)))
    return files


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
    """Resolve outside-docs links for publication; source Markdown keeps local links."""

    def rewrite(match: re.Match[str]) -> str:
        target = match.group("target")
        if target.startswith("../examples/artifacts/") and target.split("#", 1)[0].endswith(".png"):
            target = target.removeprefix("../")
        elif target.startswith("../../gsp/"):
            target = "https://github.com/vispy/gsp/blob/main/" + target.removeprefix("../../gsp/")
        elif target.startswith("../"):
            target = "https://github.com/vispy/vispy2/blob/main/" + target.removeprefix("../")
        return match.group("prefix") + target + match.group("suffix")

    return _MARKDOWN_TARGET.sub(rewrite, markdown)
