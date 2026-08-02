"""Regression tests for organizer input-room pipe counting.

``reverse_03.man`` passed the local judge 8/8 and preflight READY, then the
server returned ``the input room has more than one outgoing pipe -- connect
exactly one at (0, 8)`` and scored it 0/0. Its input room has two outward ``^``
arrowheads immediately above the top border. One of them is already consumed by
a pipe discovered from an earlier room, so the local parser's attributed pipe
list hides the second start.

The first compatibility check counted every parsed pipe body cell adjacent to
the input-room wall. That was too broad: organizer-accepted ``matmul_05`` and
``matmul_06`` contain unrelated pipe bodies running alongside the room and were
rejected locally. The organizer rule is about outward pipe starts, not arbitrary
adjacent body cells.

These tests pin both sides and retain a corpus guard over every artifact with a
preserved successful submission response.
"""

import glob
import json
import pathlib

import pytest

from littleman import server_compat

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUBMISSIONS = ROOT / "submissions"


def _records_for(man: str):
    """Every submission record for this artifact, whoever submitted it.

    Records are named both ``tcp_06-submit.json`` and
    ``alexey-tcp_06-submit.json``. Matching only the first form is how the old
    output-room false positive got through: ``tcp_06.man`` is a live machine,
    but its record carries the ``alexey-`` prefix.
    """

    path = pathlib.Path(man)
    stem = path.stem
    return list(path.parent.glob(f"*{stem}-submit.json"))


def _server_accepted(man: str) -> bool:
    for record in _records_for(man):
        try:
            loaded = json.loads(record.read_text())
        except Exception:
            continue
        if loaded.get("loadError") is None and loaded.get("width"):
            return True
    return False


ACCEPTED = [
    path
    for path in sorted(glob.glob(str(SUBMISSIONS / "*" / "*.man")))
    if _server_accepted(path)
]


@pytest.mark.parametrize("man", ACCEPTED, ids=lambda p: pathlib.Path(p).name)
def test_no_false_positive_on_anything_the_server_accepted(man: str) -> None:
    """A rejected-but-valid layout would cost a submission."""

    server_compat.validate_io_pipe_counts(pathlib.Path(man).read_text())


@pytest.mark.parametrize("name", ["matmul_05.man", "matmul_06.man"])
def test_accepts_organizer_accepted_matmul_layouts(name: str) -> None:
    """These accepted artifacts lack per-file response records in the tree, so
    keep them as explicit regressions in addition to the corpus scan."""

    source = (SUBMISSIONS / "matmul" / name).read_text()

    server_compat.validate_io_pipe_counts(source)
    machine = server_compat.parse_server_compatible(source)

    assert machine.input_pipe is not None


def test_flags_the_layout_the_server_actually_rejected() -> None:
    bad = SUBMISSIONS / "reverse-a-list" / "reverse_03.man"
    if not bad.exists():
        pytest.skip("the rejected artifact is no longer in the tree")

    with pytest.raises(
        server_compat.ServerCompatibilityError,
        match=r"2 outward pipe starts.*\(7, 1\).*\(7, 2\)",
    ):
        server_compat.validate_io_pipe_counts(bad.read_text())


def test_the_check_runs_as_part_of_validate_layout() -> None:
    """Preflight calls ``validate_layout``, so the rule must be reached there."""

    bad = SUBMISSIONS / "reverse-a-list" / "reverse_03.man"
    if not bad.exists():
        pytest.skip("the rejected artifact is no longer in the tree")
    with pytest.raises(server_compat.ServerCompatibilityError):
        server_compat.validate_layout(bad.read_text())
