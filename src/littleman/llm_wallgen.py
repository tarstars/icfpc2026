"""Generate packed DRAW deltas for one discovered LLM room border."""

from __future__ import annotations

from .lllm_fetch import build_relay
from .lllm_scan import _compile, _Fsm

DISPLAY = 16
COLOR_WALL = 4
WALL_END = -4000


def wallgen_reference(bounds: list[int]) -> list[int]:
    """Convert ``left,right,top-left,bottom-left`` to wall-color deltas."""
    left, right, top_left, bottom_left = bounds
    width = right - left + 1
    top_right = top_left + width - 1
    bottom_right = bottom_left + width - 1
    addrs = [
        *range(top_left, top_right + 1),
        *range(bottom_left, bottom_right + 1),
        *range(top_left + DISPLAY, bottom_left, DISPLAY),
        *range(top_right + DISPLAY, bottom_right, DISPLAY),
    ]
    return [*(addr * 16 + COLOR_WALL for addr in addrs), WALL_END]


def _read_slot_to_a(index: int) -> str:
    """Read one slot while restoring canonical ``L,R,T,B`` ring order."""
    code = ""
    for slot in range(4):
        code += "rMs" if slot == index else "rs"
    return code + "W"


def _width_to_bp() -> str:
    # L -> B, then (R-L+1) -> BP; relay T/B to restore the head.
    return "rMsrs-M1+brsrs"


def _height_to_bp() -> str:
    # Relay L/R, then leave A=B-T and B=B-T for a literal-safe divide.
    return "rsrsrMsrs-M"


def _right_start() -> str:
    """Read L/R/T and return A=top-right, with canonical ring order."""
    return "rMsrs-Mrs+MrsW"


def _height_count(fsm: _Fsm, name: str, target: str) -> None:
    fsm.go(name, "right", _height_to_bp(), f"{name}_div")
    fsm.go(f"{name}_div", "lit_r", " `0016`W/M1W-b", target)


def _pack_start(fsm: _Fsm, name: str, step: int, target: str) -> None:
    """A=address -> A=address*16+4, B=packed-delta step."""
    fsm.go(name, "right", "M", f"{name}_mul")
    fsm.go(f"{name}_mul", "lit_r", " `0016`W*M4+M", f"{name}_step")
    fsm.go(f"{name}_step", "lit_r", f" `{step:04d}`W", target)


def _add_sixteen(fsm: _Fsm, name: str, target: str) -> None:
    fsm.go(name, "right", "M", f"{name}_literal")
    fsm.go(f"{name}_literal", "lit_r", " `0016`+", target)


def _loop(
    fsm: _Fsm,
    name: str,
    *,
    done: str,
) -> None:
    """Emit A, advance by B, and repeat exactly BP times."""
    fsm.go(name, "left", "s+", f"{name}_count")
    fsm.bp(f"{name}_count", "mid", "m", zero=done, pos=name)


def _build_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@0", "seed_0")
    for index in range(4):
        target = f"seed_{index + 1}" if index < 3 else "load_0"
        fsm.go(f"seed_{index}", "right", "s", target)
    for index in range(4):
        target = f"load_{index + 1}" if index < 3 else "top_count"
        fsm.go(f"load_{index}", "right", "r", f"read_{index}")
        fsm.go(f"read_{index}", "left", "r", f"store_{index}")
        fsm.go(f"store_{index}", "right", "s", target)

    fsm.go("top_count", "right", _width_to_bp(), "top_addr")
    fsm.go("top_addr", "right", _read_slot_to_a(2), "top_pack")
    _pack_start(fsm, "top_pack", 16, "top_loop")
    _loop(fsm, "top_loop", done="bottom_count")

    fsm.go("bottom_count", "right", _width_to_bp(), "bottom_addr")
    fsm.go("bottom_addr", "right", _read_slot_to_a(3), "bottom_pack")
    _pack_start(fsm, "bottom_pack", 16, "bottom_loop")
    _loop(fsm, "bottom_loop", done="left_count")

    _height_count(fsm, "left_count", "left_addr")
    fsm.go("left_addr", "right", _read_slot_to_a(2), "left_step")
    _add_sixteen(fsm, "left_step", "left_pack")
    _pack_start(fsm, "left_pack", 256, "left_loop")
    _loop(fsm, "left_loop", done="right_count")

    _height_count(fsm, "right_count", "right_addr")
    fsm.go("right_addr", "right", _right_start(), "right_step")
    _add_sixteen(fsm, "right_step", "right_pack")
    _pack_start(fsm, "right_pack", 256, "right_loop")
    _loop(fsm, "right_loop", done="wall_end")

    fsm.go("wall_end", "lit_l", " `4000`Ns", "load_0")
    return fsm


def build_wallgen_room() -> list[str]:
    return _compile(_build_fsm())


CTRL_LEFT = 5
INPUT_ROW, OUTPUT_ROW = 2, 6
RING_OUT_ROW, RING_IN_ROW = 2, 9


def build_wallgen_rig() -> str:
    """One tuple at I -> packed wall deltas at O, with private state ring."""
    from .canvas import Canvas

    room = build_wallgen_room()
    right = CTRL_LEFT + len(room[0]) - 1
    relay_left = right + 5
    far = relay_left + 17
    cv = Canvas()
    cv.put(0, CTRL_LEFT, room)
    cv.put(INPUT_ROW - 1, 0, ["+-+", "|I|", "+-+"])
    cv.put(OUTPUT_ROW - 1, 0, ["+-+", "|O|", "+-+"])
    cv.put(20, relay_left, build_relay().render())
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
