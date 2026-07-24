"""Generators for the Sort problem's streaming insertion pipeline."""

from __future__ import annotations

from itertools import pairwise

from .canvas import Canvas


def _put_text(
    cells: dict[tuple[int, int], str],
    row: int,
    col: int,
    text: str,
) -> None:
    for offset, value in enumerate(text):
        cells[(row, col + offset)] = value


def _room(height: int, width: int, cells: dict[tuple[int, int], str]) -> list[str]:
    """Build a rectangular room from interior cell placements."""

    rows = [
        list("+" + "-" * (width - 2) + "+"),
        *[list("|" + " " * (width - 2) + "|") for _ in range(height - 2)],
        list("+" + "-" * (width - 2) + "+"),
    ]
    for (row, col), value in cells.items():
        rows[row][col] = value
    return ["".join(row) for row in rows]


def _render_cropped(canvas: Canvas) -> str:
    """Render the occupied bounding box without source-padding whitespace."""

    min_row = min(row for row, _ in canvas.cells)
    max_row = max(row for row, _ in canvas.cells)
    min_col = min(col for _, col in canvas.cells)
    max_col = max(col for _, col in canvas.cells)
    lines = []
    for row in range(min_row, max_row + 1):
        line = "".join(
            canvas.cells.get((row, col), " ") for col in range(min_col, max_col + 1)
        )
        lines.append(line.rstrip())
    return "\n".join(lines) + "\n"


def build_sort_stage_room() -> list[str]:
    """Return one compare/store stage.

    B holds the stage register. For every nonnegative input A, the stage sends
    min(A, B) and retains max(A, B). A negative input resets B to zero and is
    forwarded unchanged.
    """

    return _room(
        14,
        20,
        {
            # Entry and sign dispatch.
            (4, 2): ">",
            (4, 3): "@",
            (4, 4): "r",
            (4, 5): "X",
            # Negative reset token: B=0, rebuild -1, forward.
            (1, 5): ">",
            (1, 6): "0",
            (1, 7): "M",
            (1, 8): "1",
            (1, 9): "N",
            (1, 10): "s",
            (1, 18): "v",
            # Positive and zero sign paths merge before comparison.
            (4, 9): "v",
            (8, 5): ">",
            (8, 9): ">",
            (8, 10): "-",
            (8, 11): "X",
            # Incoming < stored: reconstruct incoming, forward it.
            (5, 11): ">",
            (5, 12): "+",
            (5, 13): "s",
            (5, 18): "v",
            # Incoming == stored: same operation on the straight path.
            (8, 12): "+",
            (8, 13): "s",
            (8, 18): "v",
            # Incoming > stored: forward old stored value, retain incoming.
            (10, 11): ">",
            (10, 12): "W",
            (10, 13): "s",
            (10, 14): "+",
            (10, 15): "M",
            (10, 18): "v",
            # Shared return track.
            (12, 18): "<",
            (12, 2): "^",
        },
    )


def build_sort_dispatcher_room() -> list[str]:
    """Broadcast each round's n, then relay exactly n raw values to the loader."""

    return _room(
        9,
        18,
        {
            # Prologue: receive n, broadcast it to loader and gate, save count.
            (1, 2): ">",
            (1, 3): "@",
            (1, 4): "r",
            (1, 5): "S",
            (1, 6): "b",
            (1, 7): "v",
            # Relay n values through the loader-targeted outgoing pipe.
            (3, 7): ">",
            (3, 8): "r",
            (3, 9): "s",
            (3, 10): "m",
            (3, 11): "d",
            # BP>0 loop.
            (5, 11): "<",
            (5, 7): "^",
            # BP==0 return to the prologue.
            (3, 15): "v",
            (7, 15): "<",
            (7, 2): "^",
        },
    )


def build_sort_loader_room(stage_count: int = 16) -> list[str]:
    """Encode a round, append HIGH flush tokens, then append RESET."""

    cells: dict[tuple[int, int], str] = {
        # Prologue: receive n, save it, and put SHIFT in B.
        (1, 2): ">",
        (1, 3): "@",
        (1, 4): "r",
        (1, 5): "b",
        (1, 13): "M",
        (1, 14): "v",
        # Encode and forward exactly n real values.
        (3, 14): ">",
        (3, 15): "r",
        (3, 16): "+",
        (3, 17): "s",
        (3, 18): "m",
        (3, 19): "d",
        # BP>0 input loop.
        (5, 19): "<",
        (5, 14): "^",
        # HIGH flush loop entry and body.
        (3, 24): "b",
        (3, 32): "v",
        (7, 32): ">",
        (7, 33): "s",
        (7, 34): "m",
        (7, 35): "d",
        # BP>0 flush loop.
        (9, 35): "<",
        (9, 32): "^",
        # BP==0: send RESET and return to the prologue.
        (7, 36): "1",
        (7, 37): "N",
        (7, 38): "s",
        (7, 42): "v",
        (10, 42): "<",
        (10, 2): "^",
    }
    _put_text(cells, 1, 6, "`10001`")
    _put_text(cells, 3, 20, f"`{stage_count}`")
    flush_literal_col = 21 + len(str(stage_count)) + 2
    # Keep the following fixed placements honest if stage_count gains digits.
    assert flush_literal_col == 25
    _put_text(cells, 3, flush_literal_col, "`20002`")
    return _room(12, 45, cells)


def build_sort_gate_room(stage_count: int = 16) -> list[str]:
    """Discard pipeline warm-up, decode n sorted values, and consume RESET."""

    cells: dict[tuple[int, int], str] = {
        # Receive n from the control pipe; preserve it in B and discard one
        # pipeline-width of warm-up output before the sorted values.
        (1, 2): ">",
        (1, 3): "@",
        (1, 4): "r",
        (1, 5): "M",
        (1, 10): "b",
        (1, 12): "d",
        # BP>0: discard stage_count zeroes from the data pipe.
        (4, 12): ">",
        (4, 28): "r",
        (4, 29): "m",
        (4, 30): "d",
        (6, 30): "<",
        (6, 27): "^",
        (4, 27): ">",
        # Both discard paths merge here. Restore n to BP and SHIFT to B.
        (1, 35): "v",
        (4, 35): "v",
        (8, 35): ">",
        (8, 36): "W",
        (8, 37): "b",
        (8, 45): "M",
        (8, 46): "v",
        # Decode and output n values.
        (10, 46): ">",
        (10, 47): "r",
        (10, 48): "-",
        (10, 49): "s",
        (10, 50): "m",
        (10, 51): "d",
        (12, 51): "<",
        (12, 46): "^",
        # Consume RESET from the data pipe, then return for the next n.
        (10, 53): "v",
        (13, 53): "<",
        (13, 38): "r",
        (13, 2): "^",
    }
    _put_text(cells, 1, 6, f"`{stage_count}`")
    _put_text(cells, 8, 38, "`10001`")
    return _room(15, 56, cells)


def build_sort() -> str:
    """Build the submitted baseline Sort program."""

    stage_count = 16
    stage_height = 14
    stage_width = 20
    row_pitch = stage_height + 2
    col_pitch = stage_width + 2
    pipeline_top = 20
    pipeline_left = 10

    canvas = Canvas()

    dispatcher_top = 2
    dispatcher_left = 10
    loader_top = 2
    loader_left = 35
    gate_top = 86
    gate_left = 25

    canvas.put(
        dispatcher_top,
        dispatcher_left,
        build_sort_dispatcher_room(),
    )
    canvas.put(loader_top, loader_left, build_sort_loader_room(stage_count))
    canvas.put(gate_top, gate_left, build_sort_gate_room(stage_count))

    # Input -> dispatcher.
    canvas.put(2, 5, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, 8), (3, 9)])

    # Dispatcher n control -> gate. Keep this on the outside of the pipeline.
    canvas.pipe(
        [
            (1, 15),
            (0, 15),
            (0, 0),
            (84, 0),
            (84, 29),
            (85, 29),
        ]
    )

    # Dispatcher n/data -> loader. This is the nearest outgoing pipe to the
    # dispatcher's lowercase s; uppercase S also sends n to the control pipe.
    canvas.pipe(
        [
            (11, 19),
            (16, 19),
            (16, 32),
            (3, 32),
            (3, 34),
        ]
    )

    positions: list[tuple[int, int]] = []
    for stage_index in range(stage_count):
        grid_row, offset = divmod(stage_index, 4)
        grid_col = offset if grid_row % 2 == 0 else 3 - offset
        top = pipeline_top + grid_row * row_pitch
        left = pipeline_left + grid_col * col_pitch
        positions.append((top, left))
        canvas.put(top, left, build_sort_stage_room())

    # Loader -> first stage.
    first_top, first_left = positions[0]
    canvas.pipe(
        [
            (14, 67),
            (17, 67),
            (17, first_left + 4),
            (first_top - 1, first_left + 4),
        ]
    )

    # Serpentine chain of identical stages.
    for index, ((top, left), (next_top, next_left)) in enumerate(pairwise(positions)):
        if top == next_top and next_left > left:
            canvas.pipe(
                [
                    (top + 4, left + stage_width),
                    (top + 4, next_left - 1),
                ]
            )
        elif top == next_top:
            canvas.pipe(
                [
                    (top + 4, left - 1),
                    (top + 4, next_left + stage_width),
                ]
            )
        else:
            assert index in {3, 7, 11}
            canvas.pipe(
                [
                    (top + stage_height, left + 10),
                    (next_top - 1, next_left + 10),
                ]
            )

    # Final stage data -> gate's top data input.
    final_top, final_left = positions[-1]
    canvas.pipe(
        [
            (final_top + stage_height, final_left + 10),
            (83, final_left + 10),
            (83, gate_left + 37),
            (gate_top - 1, gate_left + 37),
        ]
    )

    # Gate -> output.
    canvas.put(95, 83, ["+-+", "|O|", "+-+"])
    canvas.pipe([(96, 81), (96, 82)])

    return canvas.render()


def build_sort_compact_geometry() -> str:
    """Build the same pipeline with a smaller, geometry-only layout.

    The rooms and token protocol are identical to :func:`build_sort`. This
    variant moves the gate immediately below the 4x4 stage array and routes
    the dispatcher pipes through otherwise unused gaps.
    """

    stage_count = 16
    stage_height = 14
    stage_width = 20
    row_pitch = stage_height + 2
    col_pitch = stage_width + 2
    pipeline_top = 20
    pipeline_left = 10

    canvas = Canvas()

    dispatcher_top = 6
    dispatcher_left = 60
    loader_top = 6
    loader_left = 5
    gate_top = 83
    gate_left = 26

    canvas.put(
        dispatcher_top,
        dispatcher_left,
        build_sort_dispatcher_room(),
    )
    canvas.put(loader_top, loader_left, build_sort_loader_room(stage_count))
    canvas.put(gate_top, gate_left, build_sort_gate_room(stage_count))

    # Input -> dispatcher.
    canvas.put(6, 84, ["+-+", "|I|", "+-+"])
    canvas.pipe([(7, 83), (7, 78)])

    # Dispatcher n control -> gate. The pipe runs around the stage array and
    # turns left in the single free row between the stages and the gate.
    canvas.pipe(
        [
            (11, 78),
            (11, 96),
            (gate_top - 1, 96),
            (gate_top - 1, gate_left - 2),
            (gate_top + 1, gate_left - 2),
            (gate_top + 1, gate_left - 1),
        ]
    )

    # Dispatcher n/data -> loader. The rooms face each other, making this
    # direct pipe much shorter than the baseline detour.
    canvas.pipe([(9, 59), (9, 50)])

    positions: list[tuple[int, int]] = []
    for stage_index in range(stage_count):
        grid_row, offset = divmod(stage_index, 4)
        grid_col = offset if grid_row % 2 == 0 else 3 - offset
        top = pipeline_top + grid_row * row_pitch
        left = pipeline_left + grid_col * col_pitch
        positions.append((top, left))
        canvas.put(top, left, build_sort_stage_room())

    # Loader -> first stage.
    first_top, first_left = positions[0]
    canvas.pipe(
        [
            (18, first_left + 4),
            (first_top - 1, first_left + 4),
        ]
    )

    # Serpentine chain of identical stages.
    for index, ((top, left), (next_top, next_left)) in enumerate(pairwise(positions)):
        if top == next_top and next_left > left:
            canvas.pipe(
                [
                    (top + 4, left + stage_width),
                    (top + 4, next_left - 1),
                ]
            )
        elif top == next_top:
            canvas.pipe(
                [
                    (top + 4, left - 1),
                    (top + 4, next_left + stage_width),
                ]
            )
        else:
            assert index in {3, 7, 11}
            canvas.pipe(
                [
                    (top + stage_height, left + 10),
                    (next_top - 1, next_left + 10),
                ]
            )

    # Final stage data -> gate. The gate begins on the row directly below the
    # pipeline, so the short pipe enters its left wall.
    final_top, final_left = positions[-1]
    canvas.pipe(
        [
            (final_top + stage_height, final_left + 10),
            (gate_top + 4, final_left + 10),
            (gate_top + 4, gate_left - 1),
        ]
    )

    # Gate -> output.
    output_row = gate_top + 9
    output_left = gate_left + 61
    canvas.put(output_row, output_left, ["+-+", "|O|", "+-+"])
    canvas.pipe(
        [
            (gate_top + 10, gate_left + 56),
            (gate_top + 10, output_left - 1),
        ]
    )

    return _render_cropped(canvas)
