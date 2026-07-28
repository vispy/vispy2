from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    path = Path(__file__).parents[1] / "examples" / "validate_docs.py"
    spec = importlib.util.spec_from_file_location("validate_docs_example", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validation_covers_root_docs_and_skips_environment_readmes(tmp_path: Path) -> None:
    module = _load_validator()
    (tmp_path / "CHANGELOG.md").write_text("```python\nvalue = 1\n```\n", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("[changes](../CHANGELOG.md)\n", encoding="utf-8")
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "README.md").write_text("```python\nvalue = 2\n```\n", encoding="utf-8")
    environment = tmp_path / ".venv"
    environment.mkdir()
    (environment / "README.md").write_text(
        "```python\nfrom invalid import ...\n```\n",
        encoding="utf-8",
    )

    assert module.validate(tmp_path) == (2, 1)
