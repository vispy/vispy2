from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest

from tools.review_catalog import STEPS, ReviewStep, select_steps


VIZ_ROOT = Path(__file__).resolve().parents[2]
VISPY2_ROOT = VIZ_ROOT / "vispy2"


def test_steps_are_unique_ordered_and_well_formed() -> None:
    ids = [step.id for step in STEPS]
    assert len(ids) == len(set(ids))
    assert len(STEPS) >= 16
    assert all(isinstance(step, ReviewStep) for step in STEPS)
    assert all(step.kind in {"read", "live", "check"} for step in STEPS)
    assert all(step.estimated_minutes > 0 for step in STEPS)
    assert all(step.title and step.explanation and step.checks for step in STEPS)


def test_sources_are_repository_qualified_and_exist() -> None:
    for step in STEPS:
        assert step.sources
        for source in step.sources:
            assert source.startswith(("vispy2/", "gsp/"))
            assert (VIZ_ROOT / source).is_file(), source


def test_live_commands_exist_and_cover_supported_backends() -> None:
    case_sets = {
        "examples/manual_live_compare.py": _literal_cases(
            VISPY2_ROOT / "examples/manual_live_compare.py", "CASES"
        ),
        "examples/review_live.py": _literal_cases(VISPY2_ROOT / "examples/review_live.py", "CASES"),
    }
    for step in STEPS:
        if step.kind not in {"live", "check"}:
            continue
        assert step.command
        assert step.command[0] in {"python", "python3"}
        assert step.command[1].startswith("examples/")
        assert (VISPY2_ROOT / step.command[1]).is_file(), step.command
        if step.command[1] in case_sets:
            assert step.command[2] in case_sets[step.command[1]], step.command
        assert step.backends
        assert set(step.backends) <= {"matplotlib", "datoviz"}


def test_all_visual_families_are_explicitly_named() -> None:
    visual_step = next(step for step in STEPS if step.id == "visual-families")
    text = f"{visual_step.explanation} {' '.join(visual_step.checks)}".lower()
    for family in (
        "point",
        "pixel",
        "sphere",
        "vector",
        "primitive",
        "marker",
        "segment",
        "path",
        "image",
        "text",
        "mesh",
    ):
        assert family in text


def test_smoke_is_an_ordered_subset_and_invalid_plan_is_rejected() -> None:
    smoke = select_steps("smoke")
    assert [step.id for step in smoke] == [
        "orientation",
        "visual-families",
        "guides-colors",
        "geometry-3d",
        "updates",
        "scientific",
        "risks",
    ]
    assert all(step.smoke for step in smoke)
    assert [step.id for step in smoke] == [step.id for step in STEPS if step.smoke]
    assert select_steps() is STEPS
    with pytest.raises(ValueError, match="unknown review plan"):
        select_steps("recent")


def test_console_list_uses_the_seven_step_smoke_plan() -> None:
    result = subprocess.run(
        [sys.executable, "tools/review.py", "--list", "--plan", "smoke"],
        cwd=VISPY2_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    listed_ids = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if fields and fields[0].endswith(".") and fields[0][:-1].isdigit():
            listed_ids.append(fields[1])
    assert listed_ids == [step.id for step in select_steps("smoke")]


def _literal_cases(path: Path, name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    def values(node: ast.expr) -> tuple[str, ...]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return (node.value,)
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(item for child in node.elts for item in values(child))
        if isinstance(node, ast.Starred):
            return values(node.value)
        if isinstance(node, ast.Name):
            return values(assignments[node.id])
        raise AssertionError(f"cannot resolve case expression {ast.dump(node)} in {path}")

    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return values(node.value)
    raise AssertionError(f"{name} not found in {path}")


def test_read_steps_can_be_command_free() -> None:
    assert any(step.kind == "read" and not step.command for step in STEPS)
