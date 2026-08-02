"""Regression tests for the organizer's minimum pipe length."""

from pathlib import Path

import pytest

from littleman.server_compat import (
    MIN_PIPE_CELLS,
    ServerCompatibilityError,
    validate_pipe_lengths,
)

ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"


@pytest.mark.parametrize(
    ("relative_path", "bad_count"),
    [
        ("reverse-a-list/reverse_02.man", 3),
        ("sort/sort_05.man", 1),
    ],
    ids=lambda value: Path(value).name if isinstance(value, str) else str(value),
)
def test_rejects_one_cell_pipes(relative_path: str, bad_count: int) -> None:
    source = (SUBMISSIONS / relative_path).read_text()

    with pytest.raises(
        ServerCompatibilityError,
        match=rf"{bad_count} pipe\(s\) shorter than {MIN_PIPE_CELLS} cells",
    ):
        validate_pipe_lengths(source)


@pytest.mark.parametrize(
    "relative_path",
    [
        "reverse-a-list/reverse_01.man",
        "sort/sort_06.man",
        "triangle/triangle_04.man",
    ],
    ids=lambda path: Path(path).name,
)
def test_accepts_two_cell_or_longer_pipes(relative_path: str) -> None:
    source = (SUBMISSIONS / relative_path).read_text()

    validate_pipe_lengths(source)
