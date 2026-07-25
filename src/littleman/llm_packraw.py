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
    """Emit 64 big-endian words, negative man events, then the relay."""
    cells, tail = tokens[:CELLS], tokens[CELLS + 1 :]
    words = []
    men = []
    acc = 0
    for addr, cell in enumerate(cells):
        acc = acc * RAW_BASE + cell
        if cell == AT:
            men.append(-(addr + 1))
        if addr % 4 == 3:
            words.append(acc)
            acc = 0
    return words + men + [SETUP_END, *tail]


def unpack_words(stream: list[int]) -> tuple[list[int], list[int]]:
    """Decode the setup prefix for tests and the downstream GEOM model."""
    prefix = stream[: stream.index(SETUP_END)]
    words = prefix[:WORDS]
    if len(words) != WORDS:
        raise ValueError(f"expected {WORDS} packed words, got {len(words)}")
    cells = []
    for word in words:
        group = [0] * 4
        for i in range(3, -1, -1):
            group[i] = word % RAW_BASE
            word //= RAW_BASE
        cells.extend(group)
    men = [-(token + 1) for token in prefix[WORDS:]]
    return cells, men


def _literal(value: int) -> str:
    if value < 0:
        return f" `{-value:04d}`N"
    return f" `{value:04d}`"


RING_SLOTS = 5


def _add_event_store(fsm: _Fsm, addr: int, target: str) -> None:
    """Insert ``addr`` into the first -1 man slot and restore ring order."""
    pre = f"event_pre_{addr}"
    scan = f"event_scan_{addr}"
    compare = f"event_compare_{addr}"
    after = f"event_after_{addr}"
    restore = f"event_restore_{addr}"
    fsm.go(f"event_{addr}", "right", "rs", pre)
    fsm.sign(
        pre,
        "right",
        "rM1+",
        neg=f"event_full_{addr}",
        zero=f"event_put_{addr}",
        pos=f"event_keep_{addr}",
    )
    fsm.go(f"event_keep_{addr}", "right", "Ws", pre)
    fsm.go(f"event_put_{addr}", "lit_r", _literal(addr) + "s", scan)
    fsm.go(f"event_full_{addr}", "right", "Ws", restore)
    fsm.go(scan, "right", "r", compare)
    fsm.sign(
        compare,
        "lit_r",
        "M`1001`W+",
        neg=f"event_more_{addr}",
        zero=after,
        pos=f"event_more_{addr}",
    )
    fsm.go(f"event_more_{addr}", "right", "-s", scan)
    fsm.go(after, "lit_r", _literal(-1001) + "s", restore)
    fsm.go(restore, "lit_r", _literal(64) + "M0", target)


def _add_pack(fsm: _Fsm, addr: int, target: str) -> None:
    """Accumulate one raw cell while preserving the four metadata slots."""
    state = f"pack_{addr}"
    fsm.go(state, "right", "+", f"pack_mul_{addr}_0")
    multiplications = 3 - addr % 4
    for index in range(multiplications):
        next_state = (
            f"pack_mul_{addr}_{index + 1}"
            if index + 1 < multiplications
            else f"pack_acc_{addr}"
        )
        fsm.go(
            f"pack_mul_{addr}_{index}",
            "lit_r",
            "M`1024`*",
            next_state,
        )
    if not multiplications:
        fsm.go(f"pack_mul_{addr}_0", "right", "", f"pack_acc_{addr}")
    fsm.go(f"pack_acc_{addr}", "right", "Mr+s" + "rs" * 4, target)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "right", "@0s", "seed_m0")
    fsm.go("seed_m0", "lit_r", _literal(-1) + "s", "seed_m1")
    fsm.go("seed_m1", "lit_r", _literal(-1) + "s", "seed_m2")
    fsm.go("seed_m2", "lit_r", _literal(-1) + "s", "seed_mark")
    fsm.go("seed_mark", "lit_r", _literal(-1001) + "s", "read_0")
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
        _add_event_store(fsm, addr, f"pack_{addr}")
        _add_pack(fsm, addr, pack_target)
        if addr % 4 == 3:
            fsm.go(f"flush_r_{addr}", "right", "r", f"flush_s_{addr}")
            fsm.go(f"flush_s_{addr}", "left", "s", f"reset_{addr}")
            fsm.go(f"reset_{addr}", "right", "0s" + "rs" * 4, next_name)
    fsm.go("read_end", "left", "r", "drop_acc")
    fsm.go("drop_acc", "right", "r", "man_0")
    for index in range(3):
        next_name = f"man_{index + 1}" if index < 2 else "setup_end"
        fsm.sign(
            f"man_{index}",
            "right",
            "rM1+",
            neg=next_name,
            zero=next_name,
            pos=f"man_send_{index}",
        )
        fsm.go(f"man_send_{index}", "left", "Ns", next_name)
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
