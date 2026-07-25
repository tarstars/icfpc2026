"""The block-graph notation must parse, check, and interpret exactly."""

from __future__ import annotations

import pytest

from littleman.blockgraph import BlockGraphError, State, parse, run

USER_EXAMPLE = """
(mark K) @ 1 (if A B C)
(mark A) W 2 - (goto K)
(mark B) W 3 / (goto K)
(mark C) W 4 * (goto K)
"""


def test_parses_the_user_example():
    g = parse(USER_EXAMPLE)
    assert set(g) == {"K", "A", "B", "C"}
    assert g["K"].kind == "if" and g["K"].targets == ("A", "B", "C")
    assert g["K"].ops == ["@", "1"]


@pytest.mark.parametrize(
    "src,fragment",
    [
        ("(mark X) 1", "terminator"),
        ("(mark X) (goto NOPE)", "unknown mark"),
        ("(mark X) (if A B) H", "3 targets"),
        ("1 (goto X)", "before any"),
        ("(mark X) H (mark X) H", "duplicate"),
        ("(mark X) q H", "quarantined"),
        ("(mark X) Z H", "unknown op"),
    ],
)
def test_structural_faults_are_caught(src, fragment):
    with pytest.raises(BlockGraphError, match=fragment):
        parse(src)


def test_sign_branch_takes_all_three_arms():
    src = """
    (mark s) (if neg zero pos)
    (mark neg) 1 N H
    (mark zero) 0 H
    (mark pos) 7 H
    """
    g = parse(src)
    for a, expect in ((-5, -1), (0, 0), (5, 7)):
        assert run(g, "s", state=State(A=a)).A == expect


def test_divide_writes_both_registers_and_arithmetic_wraps():
    assert (lambda s: (s.A, s.B))(run(parse("(mark m) `100` M 7 W / H"))) == (14, 2)
    over = run(parse("(mark m) M + H"), state=State(A=2**62, B=2**62))
    assert over.A == -(2**63)


def test_b_survives_arithmetic_but_not_M_W_divide():
    st = run(parse("(mark m) M 5 + - * H"), state=State(A=3, B=9))
    assert st.B == 3           # M set B=A(3); nothing after that rewrote it
    assert run(parse("(mark m) W H"), state=State(A=1, B=2)).B == 1


def test_counted_loop_and_parity_branches():
    g = parse("""
    (mark s) 3 b (goto l)
    (mark l) (if-bp body done)
    (mark body) m (goto l)
    (mark done) H
    """)
    st = run(g, "s")
    assert st.BP == 0 and st.trace.count("body") == 3
    par = parse("(mark s) (if-par odd even) (mark odd) 1 H (mark even) 0 H")
    assert run(par, "s", state=State(BP=3)).A == 1
    assert run(par, "s", state=State(BP=4)).A == 0


def test_pipes_via_callbacks():
    out: list[int] = []
    values = iter([3, 4])
    st = run(parse("(mark m) r M r + s H"), recv=lambda: next(values), send=out.append)
    assert out == [7] and st.A == 7


def test_runaway_loop_hits_the_step_cap():
    with pytest.raises(BlockGraphError, match="step cap"):
        run(parse("(mark l) 1 (goto l)"), max_steps=500)


def test_mark_notes_are_retained_for_join_invariants():
    g = parse("(mark K :A dead :B mask) 1 H")
    assert g["K"].notes == {"A": "dead", "B": "mask"}


# --- timing-sensitive ops: q, R, U -----------------------------------------
# q and R read the ENVIRONMENT (occupancy, arrival) without changing control
# flow; only U branches. All three make behaviour depend on timing rather than
# on token sequences, which is what breaks latency-insensitive composition.


def test_q_reads_occupancy_into_bp_without_branching():
    st = run(
        parse("(mark m) q H", allow_timing_ops=True), occupancy=lambda: 5
    )
    assert st.BP == 5 and st.A == 0


def test_recv_any_is_a_data_read_not_a_branch():
    st = run(
        parse("(mark m) R H", allow_timing_ops=True),
        recv_any=lambda: (1, 42),
    )
    assert st.A == 42


def test_if_recv_branches_on_which_pipe_delivered():
    src = """
    (mark m) (if-recv left right)
    (mark left) 1 H
    (mark right) 2 H
    """
    g = parse(src, allow_timing_ops=True)
    assert run(g, "m", recv_any=lambda: (0, 7)).A == 1
    assert run(g, "m", recv_any=lambda: (1, 7)).A == 2


def test_if_recv_requires_at_least_one_target():
    with pytest.raises(BlockGraphError, match="at least one target"):
        parse("(mark m) (if-recv)", allow_timing_ops=True)


def test_timing_ops_are_rejected_by_default():
    for src in ("(mark m) q H", "(mark m) R H"):
        with pytest.raises(BlockGraphError, match="quarantined"):
            parse(src)
