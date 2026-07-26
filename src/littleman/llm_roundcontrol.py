"""Persistent round control around the exact physical LLM tick."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm_framebaseline import framebaseline_reference
from .llm_fulltick import build_fulltick_rig, fulltick_reference
from .llm_roomfind import SETUP_END
from .llm_roomstage import _strip_io
from .llm_roundstatus import roundstatus_reference
from .llm_statecopy import (
    COPY_END,
    COPY_SPLIT,
    build_statecopy_room,
)
from .llm_statecopy import _build_fsm as _build_statecopy_fsm


def setupdemux_reference(tokens: list[int]) -> tuple[list[int], list[int]]:
    end = tokens.index(SETUP_END) + 1
    return list(tokens[:end]), list(tokens[end:])


def copydemux_reference(tokens: list[int]) -> tuple[list[int], list[int]]:
    split = tokens.index(COPY_SPLIT)
    end = tokens.index(COPY_END, split + 1)
    if end + 1 != len(tokens):
        raise ValueError("unexpected copy-demux tail")
    first = list(tokens[:split])
    second = list(tokens[split + 1 : end])
    if first != second:
        raise ValueError("state copies disagree")
    return first, second


def round_states_reference(tokens: list[int]) -> list[list[int]]:
    state, commands = setupdemux_reference(tokens)
    world = state[:64]
    out = [list(state)]
    runtime = framebaseline_reference(state)[64:]
    for command in commands:
        for _ in range(command):
            if not roundstatus_reference(runtime):
                break
            runtime = fulltick_reference([*world, *runtime])
        out.append(list(runtime))
        runtime = framebaseline_reference([*world, *runtime])[64:]
    return out


def _build_setupdemux_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "state_r")
    fsm.go("state_r", "left", "r", "state_cmp")
    fsm.sign(
        "state_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="state_restore",
        zero="setup_restore",
        pos="state_restore",
    )
    fsm.go("state_restore", "left", "Ws", "state_r")
    fsm.go("setup_restore", "left", "Ws", "command_r")
    fsm.go("command_r", "left", "r", "command_out")
    fsm.go("command_out", "right", "s", "command_r")
    return fsm


def _build_copydemux_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "first_r")
    for prefix, zone, done in (
        ("first", "left", "split_r"),
        ("second", "right", "end_r"),
    ):
        fsm.go(f"{prefix}_r", "left", "r", f"{prefix}_cmp")
        fsm.sign(
            f"{prefix}_cmp",
            "lit_l",
            f"M`{abs(SETUP_END)}`+",
            neg=f"{prefix}_restore",
            zero=f"{prefix}_setup_restore",
            pos=f"{prefix}_restore",
        )
        fsm.go(f"{prefix}_restore", zone, "Ws", f"{prefix}_r")
        fsm.go(f"{prefix}_setup_restore", zone, "Ws", done)
    fsm.go("split_r", "left", "r", "split_cmp")
    fsm.sign(
        "split_cmp",
        "lit_l",
        f"M`{abs(COPY_SPLIT)}`+",
        neg="bad_stream",
        zero="second_r",
        pos="bad_stream",
    )
    fsm.go("end_r", "left", "r", "end_cmp")
    fsm.sign(
        "end_cmp",
        "lit_l",
        f"M`{abs(COPY_END)}`+",
        neg="bad_stream",
        zero="first_r",
        pos="bad_stream",
    )
    fsm.go("bad_stream", "left", "H", "bad_stream")
    return fsm


def _build_roundgate_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "command_r")
    fsm.go("final_r", "left", "r", "final_cmp")
    fsm.sign(
        "final_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="final_restore",
        zero="final_end",
        pos="final_restore",
    )
    fsm.go("final_restore", "right", "Ws", "final_r")
    fsm.go("final_end", "right", "Ws", "command_r")

    fsm.go("command_r", "right", "rb", "status_r")
    fsm.go("tick_dec", "mid", "m", "tick_r")
    fsm.go("tick_r", "left", "r", "tick_cmp")
    fsm.sign(
        "tick_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="tick_restore",
        zero="tick_end",
        pos="tick_restore",
    )
    fsm.go("tick_restore", "right", "Ws", "tick_r")
    fsm.go("tick_end", "right", "Ws", "status_r")

    # Keep status physically below the shared state input and on the left
    # wall.  This makes the state/status/tick endpoints planar even though
    # status executes before every tick.
    fsm.go("status_r", "left", "r", "status_branch")
    fsm.sign(
        "status_branch",
        "mid",
        "",
        neg="bad_status",
        zero="final_r",
        pos="cycle_count",
    )
    fsm.bp(
        "cycle_count",
        "mid",
        "",
        zero="final_r",
        pos="tick_dec",
    )
    fsm.go("bad_status", "left", "H", "bad_status")
    return fsm


def build_setupdemux_room() -> list[str]:
    return _compile(_build_setupdemux_fsm())


def build_copydemux_room() -> list[str]:
    return _compile(_build_copydemux_fsm())


def build_roundgate_room() -> list[str]:
    return _compile(_build_roundgate_fsm(), extra_gap=32)


def _build_inputmerge_fsm() -> _Fsm:
    fsm = _Fsm()
    fsm.go("boot", "left", "@", "item_r")
    fsm.go("item_r", "left", "R", "item_s")
    fsm.go("item_s", "right", "s", "item_r")
    return fsm


def build_inputmerge_room() -> list[str]:
    return _compile(_build_inputmerge_fsm())


def _rows_for(
    fsm: _Fsm,
    predicate,
) -> int:
    _routes, blocks, _height = _layout(fsm)
    rows = [
        blocks[name]
        for name, zone, code, _kind, _targets in fsm.blocks
        if predicate(name, zone, code)
    ]
    return (min(rows) + max(rows)) // 2


def _statecopy_rows() -> tuple[int, int, int, int]:
    fsm = _build_statecopy_fsm()
    main_in = _rows_for(
        fsm,
        lambda name, zone, code: zone == "left" and name == "item_r" and "r" in code,
    )
    main_out = _rows_for(
        fsm,
        lambda _name, zone, code: zone == "left" and "s" in code,
    )
    scratch_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right"
            and name in {"scratch_s", "setup_scratch", "scratch_end"}
            and "s" in code
        ),
    )
    scratch_in = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name.startswith("copy_") and "r" in code
        ),
    )
    return main_in, main_out, scratch_out, scratch_in


def add_statecopy_network(
    cv: Canvas,
    *,
    top: int,
    left: int,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], int]:
    from .lllm_fetch import build_relay

    room = build_statecopy_room()
    right = left + len(room[0]) - 1
    main_in, main_out, scratch_out, scratch_in = _statecopy_rows()
    merge = build_inputmerge_room()
    merge_left = left - len(merge[0]) - 14
    merge_right = merge_left + len(merge[0]) - 1
    merge_in = _rows_for(
        _build_inputmerge_fsm(),
        lambda _name, zone, code: zone == "left" and "R" in code,
    )
    merge_out = _rows_for(
        _build_inputmerge_fsm(),
        lambda _name, zone, code: zone == "right" and "s" in code,
    )
    relay_left = right + 5
    far = relay_left + 17
    buffer_bottom = top + max(len(room) + 20, 260)
    cv.put(top, merge_left, merge)
    cv.put(top, left, room)
    merge_track = left - 10
    cv.pipe(
        [
            (top + merge_out, merge_right + 1),
            (top + merge_out, merge_track),
            (top + main_in, merge_track),
            (top + main_in, left - 1),
        ]
    )
    cv.put(top + 20, relay_left, build_relay().render())
    cv.pipe(
        [
            (top + scratch_out, right + 1),
            (top + scratch_out, far),
            (top + 21, far),
            (top + 21, relay_left + 6),
        ]
    )
    cv.pipe(
        [
            (top + 21, relay_left - 1),
            (top + 21, right + 3),
            (buffer_bottom, right + 3),
            (buffer_bottom, right + 2),
            (top + scratch_in, right + 2),
            (top + scratch_in, right + 1),
        ]
    )
    return (
        (top + merge_in, merge_left - 1),
        (top + merge_in + 3, merge_left - 1),
        (top + main_out, left - 1),
        buffer_bottom + 1,
    )


def _setupdemux_rows() -> tuple[int, int, int]:
    fsm = _build_setupdemux_fsm()
    input_row = _rows_for(
        fsm,
        lambda _name, zone, code: zone == "left" and "r" in code,
    )
    state_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "left"
            and name in {"state_restore", "setup_restore"}
            and "s" in code
        ),
    )
    command_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name == "command_out" and "s" in code
        ),
    )
    return input_row, state_out, command_out


def _copydemux_rows() -> tuple[int, int, int]:
    fsm = _build_copydemux_fsm()
    input_row = _rows_for(
        fsm,
        lambda _name, zone, code: zone == "left" and "r" in code,
    )
    frame_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "left" and name.startswith("first_") and "s" in code
        ),
    )
    state_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name.startswith("second_") and "s" in code
        ),
    )
    return input_row, frame_out, state_out


def _roundgate_rows() -> tuple[int, int, int, int, int]:
    fsm = _build_roundgate_fsm()
    state_in = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "left" and name in {"tick_r", "final_r"} and "r" in code
        ),
    )
    command_in = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name == "command_r" and "r" in code
        ),
    )
    status_in = _rows_for(
        fsm,
        lambda name, zone, code: zone == "left" and name == "status_r" and "r" in code,
    )
    feedback_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name.startswith("final_") and "s" in code
        ),
    )
    tick_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name.startswith("tick_") and "s" in code
        ),
    )
    return state_in, command_in, status_in, feedback_out, tick_out


def _strip_input(text: str) -> tuple[list[str], tuple[int, int]]:
    rows = [list(row) for row in text.splitlines()]
    width = max(map(len, rows))
    for row in rows:
        row.extend([" "] * (width - len(row)))
    matches = [
        (r, c)
        for r, row in enumerate(rows)
        for c, char in enumerate(row)
        if char == "I" and c and c + 1 < width and row[c - 1 : c + 2] == ["|", "I", "|"]
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one I box, found {matches}")
    row, center = matches[0]
    left = center - 1
    for rr in range(row - 1, row + 2):
        for cc in range(left, left + 3):
            rows[rr][cc] = " "
    return ["".join(row) for row in rows], (row, left + 3)


def build_runtime_loop_rig() -> str:
    from .llm_framebaseline import build_framebaseline_rig
    from .llm_framerender import build_framerender_rig
    from .llm_roundstatus import strip_roundstatus_rig

    cv = Canvas()
    control_left = 500
    setup_top = 0
    copy_top = 60
    demux_top = 350
    frame_top = 430
    baseline_top = 850
    check_top = 950
    check_demux_top = 1230
    gate_top = 1350
    status_top = 1420
    tick_top = 1620
    tick_left = 250

    setup = build_setupdemux_room()
    setup_in, setup_state, setup_command = _setupdemux_rows()
    cv.put(setup_top, control_left, setup)
    initial_in, _feedback_in, copy_out, _copy_bottom = add_statecopy_network(
        cv,
        top=copy_top,
        left=control_left,
    )
    demux = build_copydemux_room()
    _demux_in, frame_out, state_out = _copydemux_rows()
    cv.put(demux_top, control_left, demux)
    frame_rows, frame_in = _strip_input(build_framerender_rig())
    cv.put(frame_top, 20, frame_rows)
    baseline_rows, baseline_in, baseline_out = _strip_io(build_framebaseline_rig())
    cv.put(baseline_top, control_left, baseline_rows)

    check_initial, check_feedback, check_copy_out, check_bottom = add_statecopy_network(
        cv,
        top=check_top,
        left=control_left,
    )
    assert check_bottom < check_demux_top
    check_demux = build_copydemux_room()
    _check_in, check_status_out, check_state_out = _copydemux_rows()
    cv.put(check_demux_top, control_left, check_demux)

    # The initial baseline still carries the 64 packed world words.  Later
    # full-tick responses contain runtime state only, so this stateful scanner
    # skips the prefix exactly once.
    status_rows, status_in, status_out = strip_roundstatus_rig(prefix_world=True)
    status_left = 270
    cv.put(status_top, status_left, status_rows)

    gate = build_roundgate_room()
    state_in, command_in, status_flag_in, feedback_out, tick_out = _roundgate_rows()
    cv.put(gate_top, control_left, gate)
    tick_rows, tick_ingress, tick_egress = _strip_io(build_fulltick_rig())
    cv.put(tick_top, tick_left, tick_rows)

    setup_input = (setup_top + setup_in, control_left - 1)
    setup_state_out = (setup_top + setup_state, control_left - 1)
    setup_command_out = (
        setup_top + setup_command,
        control_left + len(setup[0]),
    )
    frame_output = (demux_top + frame_out, control_left - 1)
    state_output = (
        demux_top + state_out,
        control_left + len(demux[0]),
    )
    frame_input = (frame_top + frame_in[0], 20 + frame_in[1])
    baseline_input = (
        baseline_top + baseline_in[0],
        control_left + baseline_in[1],
    )
    baseline_output = (
        baseline_top + baseline_out[0],
        control_left + baseline_out[1],
    )
    check_demux_input = (
        check_demux_top - 1,
        control_left + len(check_demux[0]) // 2,
    )
    check_status_output = (
        check_demux_top + check_status_out,
        control_left - 1,
    )
    check_state_output = (
        check_demux_top + check_state_out,
        control_left + len(check_demux[0]),
    )
    status_input = (
        status_top + status_in[0],
        status_left + status_in[1],
    )
    status_output = (
        status_top + status_out[0],
        status_left + status_out[1],
    )
    gate_state = (gate_top + state_in, control_left - 1)
    gate_command = (
        gate_top + command_in,
        control_left + len(gate[0]),
    )
    gate_status = (gate_top + status_flag_in, control_left - 1)
    gate_feedback = (
        gate_top + feedback_out,
        control_left + len(gate[0]),
    )
    gate_tick_out = (
        gate_top + tick_out,
        control_left + len(gate[0]),
    )
    tick_input = (tick_top + tick_ingress[0], tick_left + tick_ingress[1])
    tick_output = (tick_top + tick_egress[0], tick_left + tick_egress[1])

    cv.put(setup_input[0] - 1, 0, ["+-+", "|I|", "+-+"])
    cv.pipe([(setup_input[0], 3), setup_input])

    # SETUPDEMUX -> STATECOPY.  The shared track is reusable below because
    # the two vertical spans are separated by ten rows.
    control_track = control_left - 100
    cv.pipe(
        [
            setup_state_out,
            (setup_state_out[0], control_track),
            (initial_in[0], control_track),
            initial_in,
        ]
    )

    # STATECOPY -> COPYDEMUX.  Enter the demux through its top wall so its
    # first-copy output can leave the left wall without crossing this pipe.
    demux_top_input = (
        demux_top - 1,
        control_left + len(demux[0]) // 2,
    )
    cv.pipe(
        [
            copy_out,
            (copy_out[0], control_track),
            (demux_top - 10, control_track),
            (demux_top - 10, demux_top_input[1]),
            demux_top_input,
        ]
    )

    # First state copy is rendered.  The renderer remains left of the
    # controller, leaving a clear column between their bounding boxes.
    frame_track = 10
    cv.pipe(
        [
            frame_output,
            (frame_output[0], frame_track),
            (frame_input[0], frame_track),
            frame_input,
        ]
    )

    # The second display copy refreshes OLD := ADDR.  It then enters a second
    # STATECOPY: one copy is destructively checked for stop conditions and
    # the other remains intact for ROUNDGATE.
    state_right_track = control_left + 120
    state_left_track = control_left - 50
    baseline_turn_row = baseline_top - 20
    cv.pipe(
        [
            state_output,
            (state_output[0], state_right_track),
            (baseline_turn_row, state_right_track),
            (baseline_turn_row, state_left_track),
            (baseline_input[0], state_left_track),
            baseline_input,
        ]
    )

    initial_track = control_left - 50
    cv.pipe(
        [
            baseline_output,
            (baseline_output[0], initial_track),
            (check_top - 10, initial_track),
            (check_top - 10, check_initial[1] - 9),
            (check_initial[0], check_initial[1] - 9),
            check_initial,
        ]
    )

    # Tick results are the feedback input of the pre-tick state copier.
    tick_feedback_track = tick_left - 50
    cv.pipe(
        [
            tick_output,
            (tick_output[0], tick_feedback_track),
            (check_feedback[0], tick_feedback_track),
            check_feedback,
        ]
    )

    # The checker copy feeds its demultiplexer along the open corridor on
    # their left.
    check_copy_track = control_left - 100
    cv.pipe(
        [
            check_copy_out,
            (check_copy_out[0], check_copy_track),
            (check_demux_top - 10, check_copy_track),
            (check_demux_top - 10, check_demux_input[1]),
            check_demux_input,
        ]
    )

    # The first checker copy runs through ROUNDSTATUS; the second approaches
    # ROUNDGATE from the left without intersecting that service path.
    status_input_track = tick_left + 10
    cv.pipe(
        [
            check_status_output,
            (check_status_output[0], status_input_track),
            (status_input[0], status_input_track),
            status_input,
        ]
    )
    state_turn_row = gate_top - 10
    state_approach_track = control_left - 30
    check_state_track = control_left + 100
    cv.pipe(
        [
            check_state_output,
            (check_state_output[0], check_state_track),
            (state_turn_row, check_state_track),
            (state_turn_row, state_approach_track),
            (gate_state[0], state_approach_track),
            gate_state,
        ]
    )

    # ROUNDSTATUS exits beside the service, turns through the gap above it,
    # and reaches the gate's dedicated lower left-wall port.  This avoids
    # both the checker input on the service's left and the tick tracks on the
    # controller's right.
    status_right_track = status_left + len(status_rows[0]) + 3
    status_left_track = control_left - 10
    status_turn_row = status_top - 10
    cv.pipe(
        [
            status_output,
            (status_output[0], status_right_track),
            (status_turn_row, status_right_track),
            (status_turn_row, status_left_track),
            (gate_status[0], status_left_track),
            gate_status,
        ]
    )

    tick_track = control_left + 150
    tick_turn_row = tick_top - 10
    cv.pipe(
        [
            gate_tick_out,
            (gate_tick_out[0], tick_track),
            (tick_turn_row, tick_track),
            (tick_turn_row, tick_input[1] - 3),
            (tick_input[0], tick_input[1] - 3),
            tick_input,
        ]
    )

    command_track = control_left + 140
    cv.pipe(
        [
            setup_command_out,
            (setup_command_out[0], command_track),
            (gate_command[0], command_track),
            gate_command,
        ]
    )

    # The final state climbs between the status and command tracks and enters
    # INPUTMERGE through its top wall.  Its uppercase R accepts this feedback
    # pipe as well as the initial-state pipe on the left.
    feedback_track = control_left + 130
    feedback_top = (copy_top - 1, control_left - 20)
    cv.pipe(
        [
            gate_feedback,
            (gate_feedback[0], feedback_track),
            (copy_top - 10, feedback_track),
            (copy_top - 10, feedback_top[1]),
            feedback_top,
        ]
    )
    return cv.render()
