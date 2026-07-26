"""Protocol prototypes for a compact Plotter racetrack.

The live Plotter uses two large finite-state rooms for error testing and
error update.  They pipeline well, but together they walk three copies of
the same ``(dy, E, dx)`` state:

* ETEST rotates the ring once to decide the Bresenham step code;
* EUPD rotates it once to apply the chosen update;
* a long return pipe carries the updated state back to ETEST.

This prototype combines those rooms into one worker.  The worker rotates a
local three-value ring twice per iteration: a read-only test pass followed by
the selected update pass.  It emits exactly the stream expected by the live
ADDRESS room::

    [sx, 32*sy, address, step_code..., -1]

The first executable milestone is deliberately a component harness with
ordinary integer output.  It makes the protocol independently judgeable
before any full-machine packing or display timing is attempted.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .canvas import Canvas
from .gradebook import Fsm, compile_fsm
from .matmul import RELAY
from .sim import Machine

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "submissions" / "plotter" / "plotter_07.man"
SOURCE_SHA256 = "8e85252c84b2f89771642b823ecf38d9b49eb8a1eb6c2a09a4c687daedbb07e8"

# Ports are kept close enough for a compact component, but separated so every
# nearest-pipe choice has a positive geometric margin.
ERROR_ZONES = {
    "logic": 0,
    "setup": 8,
    "ring_in": 16,
    "control": 24,
    "ring_out": 32,
}

FUSED_ZONES = {
    "logic": 0,
    "setup": 4,
    "ring_in": 8,
    "output": 8,
    "ring_out": 12,
}

COMPACT_PORTS = {
    "setup": 5,
    "ring_in": 9,
    "control": 14,
    "ring_out": 17,
}

FUSED_COMPACT_PORTS = {
    "setup": 5,
    "ring_in": 9,
    "output": 9,
    "ring_out": 13,
}

# Vertical mirror of the standard relay.  Its input `r` is one row above its
# output `s`, which lets the full-machine return route leave below the inbound
# route without a planar pipe crossing.
RACETRACK_RELAY = [
    "+---+",
    "|vr<|",
    "|>s^|",
    "| @^|",
    "+---+",
]

PLOT_DRIVER = [
    "+----------+",
    "|>@r     sv|",
    "|^   s`51`<|",
    "+----------+",
]


def build_combined_error_fsm() -> Fsm:
    """Return the two-pass ``(dy, E, dx)`` Bresenham error worker."""

    fsm = Fsm()

    # Existing S5 compatibility:
    # [N, N, dy, E, dx, sx, 32*sy, address].
    fsm.go("start", "setup", "@rb", "init_n_drop")
    fsm.go("init_n_drop", "setup", "r", "init_dy_read")
    fsm.go("init_dy_read", "setup", "r", "init_dy_send")
    fsm.go("init_dy_send", "ring_out", "s", "init_error_read")
    fsm.go("init_error_read", "setup", "r", "init_error_send")
    fsm.go("init_error_send", "ring_out", "s", "init_dx_read")
    fsm.go("init_dx_read", "setup", "r", "init_dx_send")
    fsm.go("init_dx_send", "ring_out", "s", "init_sx_read")
    fsm.go("init_sx_read", "setup", "r", "init_sx_send")
    fsm.go("init_sx_send", "control", "s", "init_sy_read")
    fsm.go("init_sy_read", "setup", "r", "init_sy_send")
    fsm.go("init_sy_send", "control", "s", "init_address_read")
    fsm.go("init_address_read", "setup", "r", "init_address_send")
    fsm.go("init_address_send", "control", "s", "loop_check")

    fsm.bp(
        "loop_check",
        "logic",
        "",
        zero="flush_dy",
        positive="test_dy_read",
    )

    # Test pass.  It restores the original ring unchanged while its branch
    # geometry remembers c1 and c2.
    fsm.go("test_dy_read", "ring_in", "rM", "test_dy_send")
    fsm.go("test_dy_send", "ring_out", "s", "test_error_read")
    fsm.go("test_error_read", "ring_in", "r", "test_error_send")
    fsm.go("test_error_send", "ring_out", "s", "test_c1")
    fsm.sign(
        "test_c1",
        "logic",
        "-",
        negative="c1_no_recover",
        zero="c1_yes_recover",
        positive="c1_yes_recover",
    )

    for prefix in ("c1_no", "c1_yes"):
        fsm.go(f"{prefix}_recover", "logic", "+M", f"{prefix}_dx_read")
        fsm.go(f"{prefix}_dx_read", "ring_in", "r", f"{prefix}_dx_send")
        fsm.go(f"{prefix}_dx_send", "ring_out", "s", f"{prefix}_test_c2")

    fsm.sign(
        "c1_no_test_c2",
        "logic",
        "-",
        negative="impossible",
        zero="two_dy_read",
        positive="two_dy_read",
    )
    fsm.sign(
        "c1_yes_test_c2",
        "logic",
        "-",
        negative="one_dy_read",
        zero="three_dy_read",
        positive="three_dy_read",
    )
    # Symmetric Bresenham always takes at least one branch.  Keep the
    # impossible path explicit so an invariant violation becomes a wall.
    fsm.go("impossible", "logic", "H", "impossible")

    # Update pass, code 1: E += 2*dy.
    fsm.go("one_dy_read", "ring_in", "rM", "one_dy_send")
    fsm.go("one_dy_send", "ring_out", "s", "one_error_read")
    fsm.go("one_error_read", "ring_in", "r++", "one_error_send")
    fsm.go("one_error_send", "ring_out", "s", "one_dx_read")
    fsm.go("one_dx_read", "ring_in", "r", "one_dx_send")
    fsm.go("one_dx_send", "ring_out", "s", "one_code")
    fsm.go("one_code", "logic", "1", "one_code_send")
    fsm.go("one_code_send", "control", "s", "loop_decrement")

    # Update pass, code 2: E += 2*dx.
    fsm.go("two_dy_read", "ring_in", "r", "two_dy_send")
    fsm.go("two_dy_send", "ring_out", "s", "two_error_read")
    fsm.go("two_error_read", "ring_in", "rM", "two_dx_read")
    fsm.go("two_dx_read", "ring_in", "rW++", "two_error_send")
    fsm.go("two_error_send", "ring_out", "sW", "two_dx_send")
    fsm.go("two_dx_send", "ring_out", "s", "two_code")
    fsm.go("two_code", "logic", "2", "two_code_send")
    fsm.go("two_code_send", "control", "s", "loop_decrement")

    # Update pass, code 3: E += 2*dy + 2*dx.
    fsm.go("three_dy_read", "ring_in", "rM", "three_dy_send")
    fsm.go("three_dy_send", "ring_out", "s", "three_error_read")
    fsm.go("three_error_read", "ring_in", "r++M", "three_dx_read")
    fsm.go("three_dx_read", "ring_in", "rW++", "three_error_send")
    fsm.go("three_error_send", "ring_out", "sW", "three_dx_send")
    fsm.go("three_dx_send", "ring_out", "s", "three_code")
    fsm.go("three_code", "logic", "3", "three_code_send")
    fsm.go("three_code_send", "control", "s", "loop_decrement")

    fsm.go("loop_decrement", "logic", "m", "loop_check")

    # Drop the parked state after the Nth update and terminate the ADDRESS
    # control stream.  The next lap blocks at the next round's setup input.
    fsm.go("flush_dy", "ring_in", "r", "flush_error")
    fsm.go("flush_error", "ring_in", "r", "flush_dx")
    fsm.go("flush_dx", "ring_in", "r", "end_value")
    fsm.go("end_value", "logic", "1N", "end_send")
    fsm.go("end_send", "control", "s", "start")
    return fsm


def build_fused_plotter_fsm() -> Fsm:
    """Fuse error testing, error update and address update in one ring.

    Canonical state is ``(dy, E, dx, sx, 32*sy, address)``.  A test rotation
    restores it unchanged; the selected update rotation changes ``E`` and
    ``address`` and emits the new address.  This removes the live ADDRESS
    room and its separate three-token relay.
    """

    fsm = Fsm()
    fsm.go("start", "setup", "@rb", "init_n_drop")
    fsm.go("init_n_drop", "setup", "r", "init_dy_read")
    for field in ("dy", "error", "dx", "sx", "sy"):
        next_field = {
            "dy": "error",
            "error": "dx",
            "dx": "sx",
            "sx": "sy",
            "sy": "address",
        }[field]
        fsm.go(f"init_{field}_read", "setup", "r", f"init_{field}_send")
        fsm.go(
            f"init_{field}_send",
            "ring_out",
            "s",
            f"init_{next_field}_read",
        )
    fsm.go("init_address_read", "setup", "r", "init_address_output")
    fsm.go("init_address_output", "output", "s", "init_address_send")
    fsm.go("init_address_send", "ring_out", "s", "loop_check")

    fsm.bp(
        "loop_check",
        "logic",
        "",
        zero="flush_dy",
        positive="test_dy_read",
    )
    fsm.go("test_dy_read", "ring_in", "rM", "test_dy_send")
    fsm.go("test_dy_send", "ring_out", "s", "test_error_read")
    fsm.go("test_error_read", "ring_in", "r", "test_error_send")
    fsm.go("test_error_send", "ring_out", "s", "test_c1")
    fsm.sign(
        "test_c1",
        "logic",
        "-",
        negative="c1_no_recover",
        zero="c1_yes_recover",
        positive="c1_yes_recover",
    )
    for prefix in ("c1_no", "c1_yes"):
        fsm.go(f"{prefix}_recover", "logic", "+M", f"{prefix}_dx_read")
        fsm.go(f"{prefix}_dx_read", "ring_in", "r", f"{prefix}_dx_send")
        fsm.go(f"{prefix}_dx_send", "ring_out", "s", f"{prefix}_test_c2")
    fsm.sign(
        "c1_no_test_c2",
        "logic",
        "-",
        negative="impossible",
        zero="two_test_sx_read",
        positive="two_test_sx_read",
    )
    fsm.sign(
        "c1_yes_test_c2",
        "logic",
        "-",
        negative="one_test_sx_read",
        zero="three_test_sx_read",
        positive="three_test_sx_read",
    )
    fsm.go("impossible", "logic", "H", "impossible")

    # Finish the read-only test rotation without losing the spatially encoded
    # step code.
    for code in ("one", "two", "three"):
        for field, next_field in (
            ("sx", "sy"),
            ("sy", "address"),
            ("address", "update_dy"),
        ):
            target = (
                f"{code}_update_dy_read"
                if next_field == "update_dy"
                else f"{code}_test_{next_field}_read"
            )
            fsm.go(
                f"{code}_test_{field}_read",
                "ring_in",
                "r",
                f"{code}_test_{field}_send",
            )
            fsm.go(
                f"{code}_test_{field}_send",
                "ring_out",
                "s",
                target,
            )

    # Error update half of the second rotation.
    fsm.go("one_update_dy_read", "ring_in", "rM", "one_update_dy_send")
    fsm.go("one_update_dy_send", "ring_out", "s", "one_update_error_read")
    fsm.go("one_update_error_read", "ring_in", "r++", "one_update_error_send")
    fsm.go("one_update_error_send", "ring_out", "s", "one_update_dx_read")
    fsm.go("one_update_dx_read", "ring_in", "r", "one_update_dx_send")
    fsm.go("one_update_dx_send", "ring_out", "s", "one_update_sx_read")

    fsm.go("two_update_dy_read", "ring_in", "r", "two_update_dy_send")
    fsm.go("two_update_dy_send", "ring_out", "s", "two_update_error_read")
    fsm.go("two_update_error_read", "ring_in", "rM", "two_update_dx_read")
    fsm.go("two_update_dx_read", "ring_in", "rW++", "two_update_error_send")
    fsm.go("two_update_error_send", "ring_out", "sW", "two_update_dx_send")
    fsm.go("two_update_dx_send", "ring_out", "s", "two_update_sx_read")

    fsm.go("three_update_dy_read", "ring_in", "rM", "three_update_dy_send")
    fsm.go("three_update_dy_send", "ring_out", "s", "three_update_error_read")
    fsm.go(
        "three_update_error_read",
        "ring_in",
        "r++M",
        "three_update_dx_read",
    )
    fsm.go("three_update_dx_read", "ring_in", "rW++", "three_update_error_send")
    fsm.go("three_update_error_send", "ring_out", "sW", "three_update_dx_send")
    fsm.go("three_update_dx_send", "ring_out", "s", "three_update_sx_read")

    # Address update half.  The updated address is both emitted and restored
    # as the final ring token.
    fsm.go("one_update_sx_read", "ring_in", "rM", "one_update_sx_send")
    fsm.go("one_update_sx_send", "ring_out", "s", "one_update_sy_read")
    fsm.go("one_update_sy_read", "ring_in", "r", "one_update_sy_send")
    fsm.go("one_update_sy_send", "ring_out", "s", "one_update_address_read")
    fsm.go(
        "one_update_address_read",
        "ring_in",
        "r+",
        "one_update_address_output",
    )

    fsm.go("two_update_sx_read", "ring_in", "r", "two_update_sx_send")
    fsm.go("two_update_sx_send", "ring_out", "s", "two_update_sy_read")
    fsm.go("two_update_sy_read", "ring_in", "rM", "two_update_sy_send")
    fsm.go("two_update_sy_send", "ring_out", "s", "two_update_address_read")
    fsm.go(
        "two_update_address_read",
        "ring_in",
        "r+",
        "two_update_address_output",
    )

    fsm.go("three_update_sx_read", "ring_in", "rM", "three_update_sx_send")
    fsm.go("three_update_sx_send", "ring_out", "s", "three_update_sy_read")
    fsm.go(
        "three_update_sy_read",
        "ring_in",
        "r",
        "three_update_sy_send",
    )
    fsm.go(
        "three_update_sy_send",
        "ring_out",
        "s+M",
        "three_update_address_read",
    )
    fsm.go(
        "three_update_address_read",
        "ring_in",
        "r+",
        "three_update_address_output",
    )

    for code in ("one", "two", "three"):
        fsm.go(
            f"{code}_update_address_output",
            "output",
            "s",
            f"{code}_update_address_send",
        )
        fsm.go(
            f"{code}_update_address_send",
            "ring_out",
            "s",
            "loop_decrement",
        )
    fsm.go("loop_decrement", "logic", "m", "loop_check")

    for field, next_field in (
        ("dy", "error"),
        ("error", "dx"),
        ("dx", "sx"),
        ("sx", "sy"),
        ("sy", "address"),
    ):
        fsm.go(f"flush_{field}", "ring_in", "r", f"flush_{next_field}")
    fsm.go("flush_address", "ring_in", "r", "end_value")
    fsm.go("end_value", "logic", "1N", "end_send")
    fsm.go("end_send", "output", "s", "start")
    return fsm


def build_fused_plotter_harness() -> str:
    """I/O harness for the fully fused address-emitting worker."""

    worker = compile_fsm(build_fused_plotter_fsm(), FUSED_ZONES, right_padding=0)
    canvas = Canvas()
    top, left = 5, 10
    canvas.put(top, left, worker.rows)
    setup_x = left + worker.zones["setup"]
    ring_in_x = left + worker.zones["ring_in"]
    output_x = left + worker.zones["output"]
    ring_out_x = left + worker.zones["ring_out"]
    bottom = top + len(worker.rows) - 1

    canvas.put(0, setup_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, setup_x), (top - 1, setup_x)])
    output_top = bottom + 3
    canvas.put(output_top, output_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, output_x), (output_top - 1, output_x)])

    relay_top = bottom + 9
    relay_left = left + worker.width + 8
    canvas.put(relay_top, relay_left, RELAY)
    canvas.pipe(
        [
            (bottom + 1, ring_out_x),
            (relay_top + 3, ring_out_x),
            (relay_top + 3, relay_left - 1),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 2, relay_left - 1),
            (relay_top + 2, left + worker.width + 3),
            (top - 3, left + worker.width + 3),
            (top - 3, ring_in_x),
            (top - 1, ring_in_x),
        ]
    )
    return canvas.render()


def build_combined_error_harness() -> str:
    """Build an I/O harness for the combined error-worker protocol."""

    worker = compile_fsm(
        build_combined_error_fsm(),
        ERROR_ZONES,
        right_padding=0,
    )
    canvas = Canvas()
    top, left = 5, 10
    canvas.put(top, left, worker.rows)

    setup_x = left + worker.zones["setup"]
    ring_in_x = left + worker.zones["ring_in"]
    ring_out_x = left + worker.zones["ring_out"]
    control_x = left + worker.zones["control"]
    bottom = top + len(worker.rows) - 1

    canvas.put(0, setup_x - 1, ["+-+", "|I|", "+-+"])
    canvas.pipe([(3, setup_x), (top - 1, setup_x)])

    output_top = bottom + 3
    canvas.put(output_top, control_x - 1, ["+-+", "|O|", "+-+"])
    canvas.pipe([(bottom + 1, control_x), (output_top - 1, control_x)])

    relay_top = bottom + 9
    relay_left = left + worker.width + 8
    canvas.put(relay_top, relay_left, RELAY)
    # Worker ring-out -> relay input on the relay's left wall.
    canvas.pipe(
        [
            (bottom + 1, ring_out_x),
            (relay_top + 3, ring_out_x),
            (relay_top + 3, relay_left - 1),
        ]
    )
    # Relay output -> worker ring-in.  It climbs just outside the worker's
    # right wall, so the top-wall setup and ring ports keep source order.
    canvas.pipe(
        [
            (relay_top + 2, relay_left - 1),
            (relay_top + 2, left + worker.width + 3),
            (top - 3, left + worker.width + 3),
            (top - 3, ring_in_x),
            (top - 1, ring_in_x),
        ]
    )
    return canvas.render()


def build_compact_error_room() -> list[str]:
    """Return the folded, squeezed 29x83 combined-worker rectangle."""

    # Import locally: these are geometry transformations, not dependencies of
    # the protocol definition above.
    from .alexey_squeeze import squeeze
    from .alexey_stairfold import fold_room

    folded, freed = fold_room(build_combined_error_harness(), 1)
    if freed != 44:
        raise ValueError(f"expected 44 folded worker rows, got {freed}")
    compact, rows_dropped, columns_dropped = squeeze(
        folded,
        rows=True,
        cols=True,
    )
    if rows_dropped != 51:
        raise ValueError(
            "unexpected combined-worker squeeze "
            f"{(rows_dropped, columns_dropped)}"
        )
    machine = Machine.parse(compact)
    room = machine.rooms[1]
    rows = [
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    ]
    if (len(rows), len(rows[0])) != (83, 29):
        raise ValueError(f"unexpected compact worker size {(len(rows), len(rows[0]))}")

    indices = {id(candidate): index for index, candidate in enumerate(machine.rooms)}
    observed = {}
    for pipe in machine.pipes:
        role = (indices[id(pipe.source)], indices[id(pipe.dest)])
        if role == (0, 1):
            observed["setup"] = pipe.cells[-1][1] - room.left
        elif role == (1, 2):
            observed["control"] = pipe.cells[0][1] - room.left
        elif role == (1, 3):
            observed["ring_out"] = pipe.cells[0][1] - room.left
        elif role == (3, 1):
            observed["ring_in"] = pipe.cells[-1][1] - room.left
    if observed != COMPACT_PORTS:
        raise ValueError(f"unexpected compact worker ports {observed}")
    return rows


def build_compact_fused_room() -> list[str]:
    """Return the folded, squeezed 26x125 fused-worker rectangle."""

    from .alexey_squeeze import squeeze
    from .alexey_stairfold import fold_room

    folded, freed = fold_room(build_fused_plotter_harness(), 1)
    if freed != 76:
        raise ValueError(f"expected 76 folded worker rows, got {freed}")
    compact, rows_dropped, columns_dropped = squeeze(
        folded,
        rows=True,
        cols=True,
    )
    if (rows_dropped, columns_dropped) != (83, 33):
        raise ValueError(
            "unexpected fused-worker squeeze "
            f"{(rows_dropped, columns_dropped)}"
        )

    machine = Machine.parse(compact)
    room = machine.rooms[1]
    rows = [
        "".join(machine.grid[row][room.left : room.right + 1])
        for row in range(room.top, room.bottom + 1)
    ]
    if (len(rows), len(rows[0])) != (125, 26):
        raise ValueError(f"unexpected fused worker size {(len(rows), len(rows[0]))}")

    indices = {id(candidate): index for index, candidate in enumerate(machine.rooms)}
    observed = {}
    for pipe in machine.pipes:
        role = (indices[id(pipe.source)], indices[id(pipe.dest)])
        if role == (0, 1):
            observed["setup"] = pipe.cells[-1][1] - room.left
        elif role == (1, 2):
            observed["output"] = pipe.cells[0][1] - room.left
        elif role == (1, 3):
            observed["ring_out"] = pipe.cells[0][1] - room.left
        elif role == (3, 1):
            observed["ring_in"] = pipe.cells[-1][1] - room.left
    if observed != FUSED_COMPACT_PORTS:
        raise ValueError(f"unexpected compact fused worker ports {observed}")
    return rows


def build_plotter_fused_candidate() -> str:
    """Replace ETEST, EUPD, ADDRESS and PLOT with two racetracks.

    The tall west-side worker owns the six-token Bresenham/address state and
    emits raw addresses directly to the retained router.  A four-row manual
    PLOT driver replaces the compiled maze.  The retained setup, router,
    swapper and display stay byte-for-byte unchanged.
    """

    source = SOURCE.read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected plotter_07 source hash {digest}")
    machine = Machine.parse(source)
    indices = {id(room): index for index, room in enumerate(machine.rooms)}

    # ETEST, ADDRESS, ADDRESS relay, EUPD and compiled PLOT.
    removed_rooms = {0, 2, 8, 10, 11}
    removed: set[tuple[int, int]] = set()
    for index in removed_rooms:
        room = machine.rooms[index]
        removed.update(
            (row, col)
            for row in range(room.top, room.bottom + 1)
            for col in range(room.left, room.right + 1)
        )
    for pipe in machine.pipes:
        if (
            indices[id(pipe.source)] in removed_rooms
            or indices[id(pipe.dest)] in removed_rooms
        ):
            removed.update(pipe.cells)

    canvas = Canvas()
    for row, line in enumerate(source.rstrip("\n").split("\n")):
        for col, glyph in enumerate(line):
            if glyph != " " and (row, col) not in removed:
                canvas.cells[(row, col)] = glyph

    # Seven empty columns on the west side let both non-ring ports escape on
    # the same side of the worker.  The state ring stays entirely east of the
    # worker, which makes the four connections planar.
    worker_top, worker_left = 2, 7
    worker_rows = build_compact_fused_room()
    worker_bottom = worker_top + len(worker_rows) - 1
    canvas.put(worker_top, worker_left, worker_rows)

    # Existing S5 bottom port -> worker setup port.  It runs through the
    # vacated ADDRESS band and stays separate from the two west-side lanes.
    setup_x = worker_left + FUSED_COMPACT_PORTS["setup"]
    canvas.pipe(
        [
            (62, 102),
            (63, 102),
            (63, 134),
            (0, 134),
            (0, setup_x),
            (1, setup_x),
        ]
    )

    # Worker address stream escapes around the west and below the worker,
    # then climbs directly into the retained ROUTER input.
    output_x = worker_left + FUSED_COMPACT_PORTS["output"]
    canvas.pipe(
        [
            (worker_bottom + 1, output_x),
            (128, output_x),
            (128, 5),
            (129, 5),
            (129, 64),
            (71, 64),
            (71, 67),
        ]
    )
    canvas.cells[(71, 67)] = "v"

    # The six-token state ring is wholly east of the worker.  Its relay sits
    # in the vacated ADDRESS/PLOT band, keeping the bottom escape lane clear.
    relay_top, relay_left = 85, 36
    canvas.put(relay_top, relay_left, RELAY)
    ring_out_x = worker_left + FUSED_COMPACT_PORTS["ring_out"]
    canvas.pipe(
        [
            (worker_bottom + 1, ring_out_x),
            (128, ring_out_x),
            (128, 34),
            (relay_top + 3, 34),
            (relay_top + 3, relay_left - 1),
        ]
    )
    ring_in_x = worker_left + FUSED_COMPACT_PORTS["ring_in"]
    canvas.pipe(
        [
            (relay_top + 2, relay_left - 1),
            (relay_top + 2, 33),
            (1, 33),
            (1, ring_in_x),
        ]
    )
    # Canvas points the terminal cell along the final horizontal segment.
    # Patch it downward through the worker's top-wall receive port.
    canvas.cells[(1, ring_in_x)] = "v"

    # Retained ROUTER -> compact PLOT driver.
    plot_top, plot_left = 86, 75
    canvas.put(plot_top, plot_left, PLOT_DRIVER)
    canvas.pipe([(82, 78), (85, 78)])
    canvas.pipe([(90, 84), (94, 84), (94, 100), (98, 100)])
    canvas.pipe([(90, 80), (97, 80), (97, 87), (109, 87), (109, 89)])
    return canvas.render()


def build_plotter_racetrack_candidate() -> str:
    """Replace live ETEST+EUPD with the combined two-pass ring worker.

    The unchanged setup, ADDRESS, display and driver blocks are lifted from
    the frozen live artifact.  The new worker sits in the former error-room
    band.  Its private relay is below the old machine; this first full
    prototype prioritizes a measurable end-to-end proof over final packing.
    """

    source = SOURCE.read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected plotter_07 source hash {digest}")
    machine = Machine.parse(source)
    indices = {id(room): index for index, room in enumerate(machine.rooms)}

    removed_rooms = {0, 10}  # ETEST and EUPD in the frozen source.
    removed: set[tuple[int, int]] = set()
    for index in removed_rooms:
        room = machine.rooms[index]
        removed.update(
            (row, col)
            for row in range(room.top, room.bottom + 1)
            for col in range(room.left, room.right + 1)
        )
    for pipe in machine.pipes:
        if (
            indices[id(pipe.source)] in removed_rooms
            or indices[id(pipe.dest)] in removed_rooms
        ):
            removed.update(pipe.cells)

    canvas = Canvas()
    for row, line in enumerate(source.rstrip("\n").split("\n")):
        for col, glyph in enumerate(line):
            if glyph != " " and (row, col) not in removed:
                canvas.cells[(row, col)] = glyph

    worker_top, worker_left = 2, 136
    worker_rows = build_compact_error_room()
    worker_bottom = worker_top + len(worker_rows) - 1
    for row, line in enumerate(worker_rows):
        for col, glyph in enumerate(line):
            if glyph == " ":
                continue
            target = (worker_top + row, worker_left + col)
            if target in canvas.cells:
                raise ValueError(f"combined worker collision at {target}")
    canvas.put(worker_top, worker_left, worker_rows)

    relay_top, relay_left = 130, 135
    for row, line in enumerate(RACETRACK_RELAY):
        for col, glyph in enumerate(line):
            if glyph == " ":
                continue
            target = (relay_top + row, relay_left + col)
            if target in canvas.cells:
                raise ValueError(f"combined worker relay collision at {target}")
    canvas.put(relay_top, relay_left, RACETRACK_RELAY)

    setup_x = worker_left + COMPACT_PORTS["setup"]
    ring_in_x = worker_left + COMPACT_PORTS["ring_in"]
    ring_out_x = worker_left + COMPACT_PORTS["ring_out"]
    control_x = worker_left + COMPACT_PORTS["control"]

    # Existing S5 bottom port -> compact worker top.
    canvas.pipe(
        [(62, 102), (63, 102), (63, 134), (0, 134), (0, setup_x), (1, setup_x)]
    )

    # Local state ring.  The outbound leg drops below the old machine before
    # crossing the control path; the return climbs just outside the worker.
    canvas.pipe(
        [
            (worker_bottom + 1, ring_out_x),
            (127, ring_out_x),
            (127, 166),
            (relay_top + 1, 166),
            (relay_top + 1, relay_left + 5),
        ]
    )
    canvas.pipe(
        [
            (relay_top + 2, relay_left + 5),
            (relay_top + 2, 165),
            (136, 165),
            (136, 167),
            (0, 167),
            (0, ring_in_x),
            (worker_top - 1, ring_in_x),
        ]
    )

    # Existing ADDRESS control port.  This reuses the known-safe western half
    # of plotter_07's former EUPD->ADDRESS route.
    canvas.pipe(
        [
            (worker_bottom + 1, control_x),
            (126, control_x),
            (126, 134),
            (74, 134),
            (74, 88),
            (3, 88),
            (3, 38),
            (4, 38),
        ]
    )
    return canvas.render()


def build_plotter_racetrack_repacked() -> str:
    """Put the combined worker west of the retained live Plotter.

    The retained machine shifts two columns east, leaving a one-cell vertical
    lane between the 29-column worker and ADDRESS.  The old ADDRESS relay is
    moved below the worker and uses the mirrored relay orientation.  This
    turns the first end-to-end proof into a near-square candidate without
    changing any retained room program.
    """

    source = SOURCE.read_text()
    digest = hashlib.sha256(source.encode()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"unexpected plotter_07 source hash {digest}")
    machine = Machine.parse(source)
    indices = {id(room): index for index, room in enumerate(machine.rooms)}

    # Remove ETEST, EUPD and the old ADDRESS relay.  ADDRESS->ROUTER is also
    # redrawn so the relay can move through its former corridor.
    removed_rooms = {0, 8, 10}
    removed: set[tuple[int, int]] = set()
    for index in removed_rooms:
        room = machine.rooms[index]
        removed.update(
            (row, col)
            for row in range(room.top, room.bottom + 1)
            for col in range(room.left, room.right + 1)
        )
    for pipe in machine.pipes:
        role = (indices[id(pipe.source)], indices[id(pipe.dest)])
        if (
            role == (2, 9)
            or role[0] in removed_rooms
            or role[1] in removed_rooms
        ):
            removed.update(pipe.cells)

    canvas = Canvas()
    for row, line in enumerate(source.rstrip("\n").split("\n")):
        for col, glyph in enumerate(line):
            if glyph != " " and (row, col) not in removed:
                canvas.cells[(row, col + 2)] = glyph

    worker_top, worker_left = 2, 0
    worker_rows = build_compact_error_room()
    worker_bottom = worker_top + len(worker_rows) - 1
    canvas.put(worker_top, worker_left, worker_rows)

    private_relay_top, private_relay_left = 86, 0
    address_relay_top, address_relay_left = 86, 21
    canvas.put(private_relay_top, private_relay_left, RACETRACK_RELAY)
    canvas.put(address_relay_top, address_relay_left, RACETRACK_RELAY)

    setup_x = worker_left + COMPACT_PORTS["setup"]
    ring_in_x = worker_left + COMPACT_PORTS["ring_in"]
    ring_out_x = worker_left + COMPACT_PORTS["ring_out"]
    control_x = worker_left + COMPACT_PORTS["control"]

    # S5 -> worker.  Column 137 is one lane outside the translated source.
    canvas.pipe(
        [(62, 104), (63, 104), (63, 137), (0, 137), (0, setup_x), (1, setup_x)]
    )

    # Worker -> ADDRESS, reusing the translated safe corridor.
    canvas.pipe(
        [
            (worker_bottom + 1, control_x),
            (126, control_x),
            (126, 136),
            (74, 136),
            (74, 90),
            (3, 90),
            (3, 40),
            (4, 40),
        ]
    )

    # Private error-state ring.  Its long cold-side return goes below all
    # retained rooms; the terminal bend is patched because Canvas cannot
    # express a bend on the final pipe cell.
    canvas.pipe(
        [
            (worker_bottom + 1, ring_out_x),
            (private_relay_top + 1, ring_out_x),
            (private_relay_top + 1, private_relay_left + 5),
        ]
    )
    canvas.pipe(
        [
            (private_relay_top + 2, private_relay_left + 5),
            (127, private_relay_left + 5),
            (127, 138),
            (1, 138),
            (1, ring_in_x),
        ]
    )
    canvas.cells[(1, ring_in_x)] = "v"

    # Relocated ADDRESS three-token ring.
    canvas.pipe(
        [
            (65, 48),
            (83, 48),
            (83, 29),
            (address_relay_top + 1, 29),
            (address_relay_top + 1, address_relay_left + 5),
        ]
    )
    canvas.pipe(
        [
            (address_relay_top + 2, address_relay_left + 5),
            (address_relay_top + 2, 29),
            (3, 29),
            (3, 37),
            (4, 37),
        ]
    )

    # ADDRESS -> ROUTER, translated with the retained rooms.
    canvas.pipe([(65, 69), (71, 69)])
    return canvas.render()


def build_plotter_racetrack_driven() -> str:
    """Replace the compiled PLOT maze with a four-row racetrack.

    The first output send is on the right side of the room and drives ADDR.
    The return row walks the reversed ``15`` literal and sends DATA from a
    left-side port.  That port order matches the display endpoints, avoiding
    the forced crossing in the compiled room.
    """

    source = build_plotter_racetrack_candidate()
    machine = Machine.parse(source)
    indices = {id(room): index for index, room in enumerate(machine.rooms)}
    plot_index = next(
        index
        for index, room in enumerate(machine.rooms)
        if (room.bottom - room.top + 1, room.right - room.left + 1) == (10, 85)
    )
    plot_room = machine.rooms[plot_index]

    removed = {
        (row, col)
        for row in range(plot_room.top, plot_room.bottom + 1)
        for col in range(plot_room.left, plot_room.right + 1)
    }
    for pipe in machine.pipes:
        if (
            indices[id(pipe.source)] == plot_index
            or indices[id(pipe.dest)] == plot_index
        ):
            removed.update(pipe.cells)

    canvas = Canvas()
    for row, line in enumerate(source.rstrip("\n").split("\n")):
        for col, glyph in enumerate(line):
            if glyph != " " and (row, col) not in removed:
                canvas.cells[(row, col)] = glyph

    plot_top, plot_left = 86, 75
    canvas.put(plot_top, plot_left, PLOT_DRIVER)
    canvas.pipe([(82, 78), (85, 78)])

    # ADDR: compact driver bottom col 9 -> display top col 10.
    canvas.pipe([(90, 84), (94, 84), (94, 100), (98, 100)])
    # DATA: compact driver bottom col 5 -> around the display's left edge.
    canvas.pipe([(90, 80), (97, 80), (97, 87), (109, 87), (109, 89)])
    return canvas.render()
