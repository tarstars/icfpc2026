"""Persistent round control around the exact physical LLM tick."""

from __future__ import annotations

from .canvas import Canvas
from .lllm_scan import _compile, _Fsm, _layout
from .llm_framebaseline import framebaseline_reference
from .llm_fulltick import build_fulltick_rig, fulltick_reference
from .llm_roomfind import SETUP_END
from .llm_roomstage import _strip_io
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
    fsm.go("boot", "left", "@", "source_r")
    fsm.go("source_r", "left", "r", "source_cmp")
    fsm.sign(
        "source_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="source_restore",
        zero="source_end",
        pos="source_restore",
    )
    fsm.go("source_restore", "right", "Ws", "source_r")
    fsm.go("source_end", "right", "Ws", "ticks_r")
    fsm.go("ticks_r", "right", "rb", "cycle_count")
    fsm.bp(
        "cycle_count",
        "mid",
        "m",
        zero="final_r",
        pos="recycle_r",
    )

    fsm.go("recycle_r", "right", "r", "recycle_cmp")
    fsm.sign(
        "recycle_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="recycle_restore",
        zero="recycle_end",
        pos="recycle_restore",
    )
    fsm.go("recycle_restore", "right", "Ws", "recycle_r")
    fsm.go("recycle_end", "right", "Ws", "cycle_count")

    fsm.go("final_r", "right", "r", "final_cmp")
    fsm.sign(
        "final_cmp",
        "lit_l",
        f"M`{abs(SETUP_END)}`+",
        neg="final_restore",
        zero="final_end",
        pos="final_restore",
    )
    fsm.go("final_restore", "right", "Ws", "final_r")
    fsm.go("final_end", "right", "Ws", "source_r")
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
        lambda name, zone, code: zone == "left" and name == "source_r" and "r" in code,
    )
    command_in = _rows_for(
        fsm,
        lambda name, zone, code: zone == "right" and name == "ticks_r" and "r" in code,
    )
    feedback_out = _rows_for(
        fsm,
        lambda name, zone, code: (
            zone == "right" and name.startswith("final_") and "s" in code
        ),
    )
    pipeline_out = (
        _rows_for(
            fsm,
            lambda name, zone, code: (
                zone == "right"
                and name
                in {"source_restore", "source_end", "recycle_restore", "recycle_end"}
                and "s" in code
            ),
        )
        + 3
    )
    pipeline_in = (
        _rows_for(
            fsm,
            lambda name, zone, code: (
                zone == "right" and name in {"recycle_r", "final_r"} and "r" in code
            ),
        )
        - 1
    )
    return state_in, command_in, feedback_out, pipeline_out, pipeline_in


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

    cv = Canvas()
    control_left = 500
    setup_top = 0
    copy_top = 60
    demux_top = 350
    frame_top = 430
    baseline_top = 850
    gate_top = 950
    tick_top = 1030
    tick_left = 250

    setup = build_setupdemux_room()
    setup_in, setup_state, setup_command = _setupdemux_rows()
    cv.put(setup_top, control_left, setup)
    initial_in, feedback_in, copy_out, _copy_bottom = add_statecopy_network(
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

    gate = build_roundgate_room()
    state_in, command_in, feedback_out, tick_out, tick_in = _roundgate_rows()
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
    gate_state = (gate_top + state_in, control_left - 1)
    gate_command = (
        gate_top + command_in,
        control_left + len(gate[0]),
    )
    gate_feedback = (
        gate_top + feedback_out,
        control_left + len(gate[0]),
    )
    gate_tick_out = (
        gate_top + tick_out,
        control_left + len(gate[0]),
    )
    gate_tick_in = (
        gate_top + tick_in,
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

    # The second state copy refreshes OLD := ADDR before entering ROUNDGATE.
    # The first copy has already rendered the just-finished round, so OLD is
    # precisely the cell that must be restored by the next delta frame.
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
    cv.pipe(
        [
            baseline_output,
            (baseline_output[0], state_left_track),
            (gate_state[0], state_left_track),
            gate_state,
        ]
    )

    # Commands stay on the right.  ROUNDGATE's command receive is separated
    # from its state receive so these two long-lived streams cannot rebind.
    command_track = control_left + 130
    cv.pipe(
        [
            setup_command_out,
            (setup_command_out[0], command_track),
            (gate_command[0], command_track),
            gate_command,
        ]
    )

    # Final state returns below ROUNDGATE, then climbs in column 1 to a second
    # STATECOPY input.  Uppercase R selects whichever of the initial/feedback
    # pipes is ready; they are never live together.
    feedback_right_track = control_left + 140
    feedback_row = gate_top + len(gate) + 10
    feedback_left_track = 1
    cv.pipe(
        [
            gate_feedback,
            (gate_feedback[0], feedback_right_track),
            (feedback_row, feedback_right_track),
            (feedback_row, feedback_left_track),
            (feedback_in[0], feedback_left_track),
            feedback_in,
        ]
    )

    # The exact tick pipeline is a second local cycle on the right.  Its
    # request and response tracks are ordered so neither crosses the feedback
    # return just above the pipeline.
    request_track = control_left + 160
    response_track = control_left + 150
    request_turn_row = tick_top - 10
    request_left_track = tick_left - 10
    cv.pipe(
        [
            gate_tick_out,
            (gate_tick_out[0], request_track),
            (request_turn_row, request_track),
            (request_turn_row, request_left_track),
            (tick_input[0], request_left_track),
            tick_input,
        ]
    )
    response_turn_row = tick_top - 15
    response_left_track = tick_left - 20
    cv.pipe(
        [
            tick_output,
            (tick_output[0], response_left_track),
            (response_turn_row, response_left_track),
            (response_turn_row, response_track),
            (gate_tick_in[0], response_track),
            gate_tick_in,
        ]
    )
    return cv.render()
