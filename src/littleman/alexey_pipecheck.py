"""Pre-submission check for a server rule our simulator does not enforce.

THE RULE: every pipe must be at least TWO cells long. The contest server
rejects a one-cell pipe at load time with

    pipe runs into a room wall -- end it with an arrowhead pointing into
    the room at (col, row)

while `littleman.sim.Machine.parse` accepts it and the local judge then
reports a clean pass. Two smaller variants were built, validated locally
and abandoned before anyone connected the load error to pipe length:

* `sort_05.man`   18x18, fp 324 (vs the live 361) -- one 1-cell pipe
* `reverse_02.man` 15x15, fp 225 (vs the live 256) -- three 1-cell pipes

Practical consequence for layout: **two rooms must be at least two cells
apart**, not one. A room beside a room needs a 2-column gap; above or
below, a 2-row gap. When a straight run cannot fit, bend the pipe out of a
different wall -- but re-audit nearest-pipe resolution afterwards, because
moving where a pipe enters a room changes which `r` cell claims it. That
is what happened when `sort_05`'s input was rerouted three rows down: the
ring read at rel(5,11) had exactly one step of margin and flipped to the
input pipe, and the machine deadlocked while still parsing fine.

`sort_06.man` is `sort_05` with one column of gap restored: same fp as the
live sort_03 (361) but 6.6% fewer ticks, which is why it is worth having.

Divergences run BOTH ways: `history_00.man` is live at 7,921 yet the local
parser rejects it with `invalid vertical literal at (20, 2)`. Never treat a
local parse failure as proof the server will refuse a program.

`littleman.server_compat.validate_layout` covers the other two known
divergences (rooms sharing a wall; a man stepping into a wall after its
final send). It does not cover this one, so run `check` as well.
"""

from .sim import LoadError, Machine

MIN_PIPE_CELLS = 2


class PipeLengthError(Exception):
    """Raised for a pipe the server will reject at load time."""


def check(program: str) -> None:
    """Raise PipeLengthError if any pipe is shorter than the server allows.

    A program the local parser cannot read at all is passed through: the
    divergence runs both ways. `history_00.man` scores 7,921 live but
    raises `invalid vertical literal` here, so a local parse failure is not
    evidence that the server will refuse it.
    """
    try:
        machine = Machine.parse(program)
    except LoadError:
        return
    bad = [p for p in machine.pipes if len(p.cells) < MIN_PIPE_CELLS]
    if bad:
        where = ", ".join(str(p.cells[0]) for p in bad)
        raise PipeLengthError(
            f"{len(bad)} pipe(s) shorter than {MIN_PIPE_CELLS} cells at {where}; "
            "the server rejects these at load time -- widen the gap between the "
            "rooms to two cells or bend the pipe out of another wall"
        )


def report(program: str) -> list[int] | None:
    """Every pipe's cell count, shortest first; None if it will not parse."""
    try:
        return sorted(len(p.cells) for p in Machine.parse(program).pipes)
    except LoadError:
        return None
