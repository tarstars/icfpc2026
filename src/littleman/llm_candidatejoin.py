"""Join two packed-candidate replies into a SELECTELIGIBLE request."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm
from .llm_packedcandidate import unpack_room_context

REPLY_WORDS = 3
REQUEST_WORDS = 2 * REPLY_WORDS


def candidatejoin_reference(tokens: list[int]) -> list[int]:
    """Convert ``(context, target, eligible) * 2`` into selector records."""
    if len(tokens) % REQUEST_WORDS:
        raise ValueError("truncated candidate-join request")
    out = []
    for index in range(0, len(tokens), REQUEST_WORDS):
        context0, target0, eligible0, _context1, target1, eligible1 = tokens[
            index : index + REQUEST_WORDS
        ]
        addr = unpack_room_context(context0)[-1]
        out.extend((addr, eligible0, eligible1, target0, target1))
    return out


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "context0_r")
    for name, target in (
        ("context0", "target0_r"),
        ("target0", "eligible0_r"),
        ("eligible0", "context1_r"),
        ("context1", "target1_r"),
        ("target1", "eligible1_r"),
        ("eligible1", "addr_context_r"),
    ):
        fsm.go(f"{name}_r", "left", "r", f"{name}_s")
        fsm.go(f"{name}_s", "right", "s", target)

    fsm.go("addr_context_r", "right", "rM", "addr_div")
    fsm.go("addr_div", "lit_r", f" `{1 << 41}`W/", "addr_mask")
    fsm.go("addr_mask", "lit_r", "M`0255`W&", "addr_out")
    fsm.go("addr_out", "left", "s", "target0_rotate")

    # Ring: target0, eligible0, context1, target1, eligible1.
    fsm.go("target0_rotate", "right", "rs", "eligible0_out_r")
    fsm.go("eligible0_out_r", "right", "r", "eligible0_out")
    fsm.go("eligible0_out", "left", "s", "context1_drop")
    fsm.go("context1_drop", "right", "r", "target1_rotate")
    fsm.go("target1_rotate", "right", "rs", "eligible1_out_r")
    fsm.go("eligible1_out_r", "right", "r", "eligible1_out")
    fsm.go("eligible1_out", "left", "s", "target0_out_r")
    fsm.go("target0_out_r", "right", "r", "target0_out")
    fsm.go("target0_out", "left", "s", "target1_out_r")
    fsm.go("target1_out_r", "right", "r", "target1_out")
    fsm.go("target1_out", "left", "s", "context0_r")
    return fsm


def build_candidatejoin_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_candidatejoin_rig() -> str:
    room = build_candidatejoin_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(20, relay_left, build_relay().render())
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(INPUT_ROW, 3), (INPUT_ROW, CTRL_LEFT - 1)])
    cv.pipe([(OUTPUT_ROW, CTRL_LEFT - 1), (OUTPUT_ROW, 3)])
    cv.pipe(
        [
            (RING_OUT_ROW, right + 1),
            (RING_OUT_ROW, far),
            (21, far),
            (21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (21, relay_left - 1),
            (21, right + 2),
            (RING_IN_ROW, right + 2),
            (RING_IN_ROW, right + 1),
        ]
    )
    return cv.render()
