"""Read-only random access to PACK's 64-word raw LLM canvas."""

from __future__ import annotations

from .lllm_fetch import Room, build_relay

RECORD_BITS = 10
RECORD_BASE = 1 << RECORD_BITS
RECORDS_PER_TOKEN = 4
WORLD_TOKENS = 64
CELLS = WORLD_TOKENS * RECORDS_PER_TOKEN


def unpack_raw_world(world: list[int]) -> list[int]:
    """Decode PACK's little-endian base-1024 words into 256 raw cells."""
    if len(world) != WORLD_TOKENS:
        raise ValueError(f"world must have {WORLD_TOKENS} words")
    cells = []
    for word in world:
        group = []
        for _ in range(RECORDS_PER_TOKEN):
            group.append(word % RECORD_BASE)
            word //= RECORD_BASE
        cells.extend(group)
    return cells


def raw_fetch_reference(world: list[int], requests: list[int]) -> list[int]:
    cells = unpack_raw_world(world)
    if any(not 0 <= addr < CELLS for addr in requests):
        raise ValueError("raw fetch address outside 0..255")
    return [cells[addr] for addr in requests]


FETCH_ROWS, FETCH_COLS = 17, 45
CMD_ROW, RESP_ROW = 2, 13
RING_OUT_ROW, RING_IN_ROW = 2, 5
CHAIN = "WM8W+M4W/bWM`10`*M1{"


def _setup(room: Room) -> None:
    room.put(1, 1, "@ `63`b")
    room.put(1, 20, "v")
    room.put(2, 20, ">rsv")
    room.put(3, 20, "^ md")
    room.put(4, 23, ">")
    room.put(4, 30, "1Nsv")
    room.put(5, 33, "<")
    room.put(5, 1, "v")
    room.put(6, 1, ">rM1W+X")
    room.put(6, 45, "v")


def _decode(room: Room) -> None:
    # The first divide proves every request is the sole (kind=0) arm and
    # leaves its address in B.  CHAIN derives word+2 in BP and
    # 2**(10*field) in B for PACK's little-endian field order.
    room.put(7, 7, ">-M`256`W/X")
    room.put(7, 18, CHAIN)
    room.put(7, 44, "v")
    room.put(9, 44, "M")


def _relay_and_peel(room: Room) -> None:
    room.put(10, 44, "<")
    room.put(10, 37, "v")
    room.put(11, 37, ">m d")
    room.put(11, 41, "WX")
    room.put(12, 37, "^sr<")
    room.put(12, 42, "v")
    # Walked west: W / M `1023` & s.
    room.put(13, 25, "&`3201`M/W")
    room.put(13, 42, "<")
    room.put(13, 2, "vs")
    for row in range(10, 14):
        room.put(row, 2, "v")


def _restore_rotation(room: Room) -> None:
    room.put(14, 2, ">")
    room.put(14, 39, ">")
    room.put(14, 44, "v")
    room.put(15, 39, "^s<<")
    room.put(15, 44, "v")
    room.put(16, 41, "^Xr<")
    room.put(17, 41, "s<")
    for row in range(7, 18):
        room.put(row, 1, "^")


def build_raw_fetch() -> Room:
    room = Room(FETCH_ROWS, FETCH_COLS)
    _setup(room)
    _decode(room)
    _relay_and_peel(room)
    _restore_rotation(room)
    return room


def build_raw_fetch_rig() -> str:
    from .canvas import Canvas

    cv = Canvas()
    cv.put(0, 5, build_raw_fetch().render())
    cv.put(20, 55, build_relay().render())
    cv.put(CMD_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(RESP_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.pipe([(CMD_ROW, 3), (CMD_ROW, 4)])
    cv.pipe([(RESP_ROW, 4), (RESP_ROW, 3)])
    cv.pipe([(RING_OUT_ROW, 52), (RING_OUT_ROW, 72), (21, 72), (21, 61)])
    cv.pipe([(21, 54), (21, 53), (RING_IN_ROW, 53), (RING_IN_ROW, 52)])
    return cv.render()


def rig_stream(world: list[int], requests: list[int]) -> list[int]:
    return [*world, *requests]
