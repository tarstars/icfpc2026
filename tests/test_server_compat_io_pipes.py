"""The server counts a pipe running ALONGSIDE an I/O room as connected to it.

`reverse_03.man` passed the local judge 8/8 and preflight READY, then the
server returned `the input room has more than one outgoing pipe -- connect
exactly one at (0, 8)` and scored it 0/0. Our simulator attributes a pipe to
the rooms at its two ends, so an 18-cell return pipe that merely ran flush
along the input room's wall was invisible to us.

These tests pin the rule and, more importantly, guard against the check
being too aggressive: every artifact the server has actually accepted must
keep passing it.
"""

import glob
import json
import pathlib

import pytest

from littleman import server_compat

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _server_accepted(man: str) -> bool:
    record = pathlib.Path(man.replace(".man", "-submit.json"))
    if not record.exists():
        return False
    try:
        loaded = json.loads(record.read_text())
    except Exception:
        return False
    return loaded.get("loadError") is None and bool(loaded.get("width"))


ACCEPTED = [f for f in sorted(glob.glob(str(ROOT / "submissions" / "*" / "*.man")))
            if _server_accepted(f)]


@pytest.mark.parametrize("man", ACCEPTED, ids=lambda p: pathlib.Path(p).name)
def test_no_false_positive_on_anything_the_server_accepted(man: str) -> None:
    """A rejected-but-valid layout would cost us submissions, so this is the
    load-bearing half of the check."""
    server_compat.validate_io_pipe_counts(pathlib.Path(man).read_text())


def test_flags_the_layout_the_server_actually_rejected() -> None:
    bad = ROOT / "submissions" / "reverse-a-list" / "reverse_03.man"
    if not bad.exists():
        pytest.skip("the rejected artifact is no longer in the tree")
    with pytest.raises(server_compat.ServerCompatibilityError, match="against its wall"):
        server_compat.validate_io_pipe_counts(bad.read_text())


def test_the_check_runs_as_part_of_validate_layout() -> None:
    """preflight calls validate_layout, so the rule must be reached from there."""
    bad = ROOT / "submissions" / "reverse-a-list" / "reverse_03.man"
    if not bad.exists():
        pytest.skip("the rejected artifact is no longer in the tree")
    with pytest.raises(server_compat.ServerCompatibilityError):
        server_compat.validate_layout(bad.read_text())
