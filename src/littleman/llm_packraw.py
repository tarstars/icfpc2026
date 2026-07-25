"""Pack LLM raw cells four-per-word and report every man address."""

from __future__ import annotations

from .lllm_scan import _Fsm, _compile, build_relay

RAW_BITS = 10
RAW_BASE = 1 << RAW_BITS
CELLS = 256
WORDS = CELLS // 4
AT = ord("@")
SETUP_END = -1000


def pack_reference(tokens: list[int]) -> list[int]:
    """Interleave negative man events with 64 big-endian packed words."""
    cells, tail = tokens[:CELLS], tokens[CELLS + 1 :]
    out = []
    acc = 0
    for addr, cell in enumerate(cells):
        acc = acc * RAW_BASE + cell
        if cell == AT:
            out.append(-(addr + 1))
        if addr % 4 == 3:
            out.append(acc)
            acc = 0
    return out + [SETUP_END, *tail]


def unpack_words(stream: list[int]) -> tuple[list[int], list[int]]:
    """Decode the setup prefix for tests and the downstream GEOM model."""
    prefix = stream[: stream.index(SETUP_END)]
    words = [token for token in prefix if token >= 0]
    if len(words) != WORDS:
        raise ValueError(f"expected {WORDS} packed words, got {len(words)}")
    cells = []
    for word in words:
        group = [0] * 4
        for i in range(3, -1, -1):
            group[i] = word % RAW_BASE
            word //= RAW_BASE
        cells.extend(group)
    men = [-(token + 1) for token in prefix if -257 <= token <= -1]
    return cells, men


def _literal(value: int) -> str:
    if value < 0:
        return f" `{-value:04d}`N"
    return f" `{value:04d}`"


PACK_PRE = "+MrWsWM"
PACK_MUL = " `1024`*Mr+s"


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "right", "@0s", "read_0")
    for addr in range(CELLS):
        next_name = f"read_{addr + 1}" if addr + 1 < CELLS else "read_end"
        pack_target = f"flush_r_{addr}" if addr % 4 == 3 else next_name
        fsm.go(f"read_{addr}", "left", "r", f"cmp_{addr}")
        fsm.sign(
            f"cmp_{addr}",
            "lit_l",
            "M`0064`W-",
            neg=f"pack_{addr}",
            zero=f"event_{addr}",
            pos=f"pack_{addr}",
        )
        fsm.go(f"event_{addr}", "lit_l", _literal(-(addr + 1)) + "s0", f"pack_{addr}")
        fsm.go(f"pack_{addr}", "right", PACK_PRE, f"mul_{addr}")
        fsm.go(f"mul_{addr}", "lit_r", PACK_MUL, pack_target)
        if addr % 4 == 3:
            fsm.go(f"flush_r_{addr}", "right", "r", f"flush_s_{addr}")
            fsm.go(f"flush_s_{addr}", "left", "s", f"reset_{addr}")
            fsm.go(f"reset_{addr}", "right", "0s", next_name)
    fsm.go("read_end", "left", "r", "setup_end")
    fsm.go("setup_end", "lit_l", _literal(SETUP_END) + "s", "relay")
    fsm.go("relay", "left", "rs", "relay")
    return fsm


def build_pack_room() -> list[str]:
    return _compile(_build_fsm())


PACK_LEFT = 5
CMD_ROW, RESP_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_pack_rig() -> str:
    from .canvas import Canvas

    room = build_pack_room()
    right = PACK_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 8
    cv = Canvas()
    cv.put(0, PACK_LEFT, room)
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, PACK_LEFT - 1)])
    cv.pipe([(RESP_ROW, PACK_LEFT - 1), (RESP_ROW, 3)])
    cv.put(1, relay_left, build_relay())
    cv.pipe([(RING_OUT_ROW, right + 1), (RING_OUT_ROW, relay_left - 1)])
    cv.pipe([(3, relay_left + 6), (3, far), (RING_IN_ROW, far), (RING_IN_ROW, right + 1)])
    return cv.render()
