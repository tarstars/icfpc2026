"""Generated Bresenham Plotter machine.

The machine follows a stream-oriented design:

* five setup rooms turn ``x0, y0, x1, y1`` into loop constants;
* a test room and update room circulate ``(dy, 2*err, dx)`` and emit one
  address delta per Bresenham iteration;
* an address room circulates ``(sx, 32*sy, address)``;
* tiny router, plot, and swap rooms drive a 32x24 LM-75 display.

The implementation lives separately from the earlier protected Plotter
driver sketch.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from .canvas import Canvas
from .gradebook import CompiledRoom, Fsm, compile_fsm
from .matmul import RELAY

STREAM_ZONES = {"io": 20}

ETEST_ZONES = {
    "logic": 0,
    "setup": 20,
    "ring_in": 50,
    "ring_out": 80,
    "code_out": 110,
}

EUPD_ZONES = {
    "logic": 0,
    "to_address": 20,
    "ring_out": 50,
    "ring_in": 80,
    "code_in": 110,
}

ADDRESS_ZONES = {
    "logic": 0,
    "ring_in": 10,
    "control": 20,
    "ring_out": 80,
    "display": 170,
}

ROUTER_ZONES = {
    "logic": 0,
    "input": 170,
    "plot": 190,
    "swap": 220,
}

PLOT_ZONES = {
    "logic": 0,
    "input": 190,
    "data": 230,
    "address": 270,
}

SWAP_ZONES = {
    "logic": 0,
    "input": 0,
    "swap": 30,
}


@dataclass(frozen=True)
class PlotterLayout:
    """Vertical clearances and compiler padding for the Plotter pipeline."""

    stream_step: int = 12
    error_room_step: int = 18
    error_return_depth: int = 5
    address_step: int = 18
    address_relay_step: int = 8
    relay_router_step: int = 12
    router_drivers_step: int = 16
    router_swap_depth: int = 6
    display_step: int = 20
    fsm_right_padding: int = 3

    def validate(self) -> None:
        if self.stream_step < 6:
            raise ValueError("stream rooms need five rows for their connecting pipe")
        if self.error_room_step < 6:
            raise ValueError("error rooms need five rows for their connecting pipes")
        if self.error_return_depth < 2:
            raise ValueError("error return route must clear the update room")
        if self.address_step < max(6, self.error_return_depth + 2):
            raise ValueError("address room must clear the error return route")
        if self.address_relay_step < 2:
            raise ValueError("relay must not touch the address room")
        if self.relay_router_step < 2:
            raise ValueError("router must not touch the relay")
        if self.router_swap_depth < 2:
            raise ValueError("swap route must clear the router")
        if self.router_drivers_step < max(5, self.router_swap_depth + 2):
            raise ValueError("driver rooms must clear their incoming routes")
        if self.display_step < 7:
            raise ValueError("display must clear the plot data route")
        if self.fsm_right_padding < 0:
            raise ValueError("FSM right padding cannot be negative")


BASELINE_LAYOUT = PlotterLayout()
COMPACT_LAYOUT = PlotterLayout(
    stream_step=6,
    error_room_step=6,
    error_return_depth=2,
    address_step=6,
    address_relay_step=2,
    relay_router_step=2,
    router_drivers_step=5,
    router_swap_depth=2,
    display_step=7,
    fsm_right_padding=0,
)


def bresenham_addresses(x0: int, y0: int, x1: int, y1: int) -> list[int]:
    """Return the exact address sequence required by the contest statement."""
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    addresses = []
    while True:
        addresses.append(32 * y0 + x0)
        if x0 == x1 and y0 == y1:
            return addresses
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x0 += sx
        if doubled <= dx:
            error += dx
            y0 += sy


def setup_constants(x0: int, y0: int, x1: int, y1: int) -> list[int]:
    """Return the setup stream consumed by the error-test room."""
    dx = abs(x1 - x0)
    sx = 1 if x1 >= x0 else -1
    dy = -abs(y1 - y0)
    sy_width = 32 if y1 >= y0 else -32
    error2 = 2 * (dx + dy)
    steps = max(dx, -dy)
    address = 32 * y0 + x0
    return [steps, steps, dy, error2, dx, sx, sy_width, address]


def build_setup_one_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "io", "@rMrsWssWsrMrsWs", "start")
    return fsm


def build_setup_two_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "io", "@rM`32`*Mr+MrsrsrsrsWs", "start")
    return fsm


def build_setup_three_fsm() -> Fsm:
    fsm = Fsm()
    fsm.sign(
        "start",
        "io",
        "@rMrsrsr-",
        negative="negative",
        zero="nonnegative",
        positive="nonnegative",
    )
    fsm.go("negative", "io", "Ns1Ns", "tail")
    fsm.go("nonnegative", "io", "s1s", "tail")
    fsm.go("tail", "io", "rs", "start")
    return fsm


def build_setup_four_fsm() -> Fsm:
    fsm = Fsm()
    fsm.sign(
        "start",
        "io",
        "@rMr-",
        negative="negative",
        zero="nonnegative",
        positive="nonnegative",
    )
    fsm.go("negative", "io", "MsrsWsWsrs`32`Nsrs", "start")
    fsm.go("nonnegative", "io", "NMsrsWsWsrs`32`srs", "start")
    return fsm


def build_setup_five_fsm() -> Fsm:
    fsm = Fsm()
    fsm.sign(
        "start",
        "io",
        "@rMr+",
        negative="dy_dominant",
        zero="dx_dominant",
        positive="dx_dominant",
    )
    fsm.go("dy_dominant", "io", "WNss", "tail")
    fsm.go("dx_dominant", "io", "W-Nss", "tail")
    fsm.go("tail", "io", "rsWM+srsrsrsrs", "start")
    return fsm


def build_error_test_fsm() -> Fsm:
    fsm = Fsm()

    fsm.go("start", "setup", "@rb", "init_n_read")
    fsm.go("init_n_read", "setup", "r", "init_n_send")
    fsm.go("init_n_send", "code_out", "s", "init_dy_read")
    fsm.go("init_dy_read", "setup", "r", "init_dy_send")
    fsm.go("init_dy_send", "ring_out", "s", "init_error_read")
    fsm.go("init_error_read", "setup", "r", "init_error_send")
    fsm.go("init_error_send", "ring_out", "s", "init_dx_read")
    fsm.go("init_dx_read", "setup", "r", "init_dx_send")
    fsm.go("init_dx_send", "ring_out", "s", "init_sx_read")
    fsm.go("init_sx_read", "setup", "r", "init_sx_send")
    fsm.go("init_sx_send", "code_out", "s", "init_sy_read")
    fsm.go("init_sy_read", "setup", "r", "init_sy_send")
    fsm.go("init_sy_send", "code_out", "s", "init_address_read")
    fsm.go("init_address_read", "setup", "r", "init_address_send")
    fsm.go("init_address_send", "code_out", "s", "loop_check")

    fsm.bp(
        "loop_check",
        "logic",
        "",
        zero="flush_state",
        positive="dy_read",
    )
    fsm.go("dy_read", "ring_in", "rM", "dy_send")
    fsm.go("dy_send", "ring_out", "s", "error_read")
    fsm.go("error_read", "ring_in", "r", "error_send")
    fsm.go("error_send", "ring_out", "s", "test_c1")
    fsm.sign(
        "test_c1",
        "logic",
        "-",
        negative="c1_no_recover",
        zero="c1_yes_recover",
        positive="c1_yes_recover",
    )

    fsm.go("c1_no_recover", "logic", "+M", "c1_no_dx_read")
    fsm.go("c1_no_dx_read", "ring_in", "r", "c1_no_dx_send")
    fsm.go("c1_no_dx_send", "ring_out", "s", "c1_no_test_c2")
    fsm.sign(
        "c1_no_test_c2",
        "logic",
        "-",
        negative="code_impossible",
        zero="code_two",
        positive="code_two",
    )

    fsm.go("c1_yes_recover", "logic", "+M", "c1_yes_dx_read")
    fsm.go("c1_yes_dx_read", "ring_in", "r", "c1_yes_dx_send")
    fsm.go("c1_yes_dx_send", "ring_out", "s", "c1_yes_test_c2")
    fsm.sign(
        "c1_yes_test_c2",
        "logic",
        "-",
        negative="code_one",
        zero="code_three",
        positive="code_three",
    )

    for name, value in (
        ("code_impossible", "0"),
        ("code_one", "1"),
        ("code_two", "2"),
        ("code_three", "3"),
    ):
        fsm.go(name, "logic", value, f"{name}_send")
        fsm.go(f"{name}_send", "code_out", "s", "loop_decrement")

    fsm.go("loop_decrement", "logic", "m", "loop_check")
    fsm.go("flush_state", "ring_in", "rrr", "start")
    return fsm


def build_error_update_fsm() -> Fsm:
    fsm = Fsm()

    fsm.go("start", "code_in", "@rb", "init_sx_read")
    fsm.go("init_sx_read", "code_in", "r", "init_sx_send")
    fsm.go("init_sx_send", "to_address", "s", "init_sy_read")
    fsm.go("init_sy_read", "code_in", "r", "init_sy_send")
    fsm.go("init_sy_send", "to_address", "s", "init_address_read")
    fsm.go("init_address_read", "code_in", "r", "init_address_send")
    fsm.go("init_address_send", "to_address", "s", "seed_dy_read")

    # Return the freshly initialized state once so ETEST can begin its first
    # iteration. Subsequent states are returned by the update lanes.
    fsm.go("seed_dy_read", "ring_in", "r", "seed_dy_send")
    fsm.go("seed_dy_send", "ring_out", "s", "seed_error_read")
    fsm.go("seed_error_read", "ring_in", "r", "seed_error_send")
    fsm.go("seed_error_send", "ring_out", "s", "seed_dx_read")
    fsm.go("seed_dx_read", "ring_in", "r", "seed_dx_send")
    fsm.go("seed_dx_send", "ring_out", "s", "loop_check")

    fsm.bp(
        "loop_check",
        "logic",
        "",
        zero="end_value",
        positive="code_read",
    )
    fsm.go("code_read", "code_in", "rM", "code_compare")
    fsm.sign(
        "code_compare",
        "logic",
        "2W-",
        negative="one_dy_read",
        zero="two_dy_read",
        positive="three_dy_read",
    )

    fsm.go("one_dy_read", "ring_in", "rM", "one_dy_send")
    fsm.go("one_dy_send", "ring_out", "s", "one_error_read")
    fsm.go("one_error_read", "ring_in", "r++", "one_error_send")
    fsm.go("one_error_send", "ring_out", "s", "one_dx_read")
    fsm.go("one_dx_read", "ring_in", "r", "one_dx_send")
    fsm.go("one_dx_send", "ring_out", "s", "one_delta")
    fsm.go("one_delta", "logic", "1", "one_delta_send")
    fsm.go("one_delta_send", "to_address", "s", "loop_decrement")

    fsm.go("two_dy_read", "ring_in", "r", "two_dy_send")
    fsm.go("two_dy_send", "ring_out", "s", "two_error_read")
    fsm.go("two_error_read", "ring_in", "rM", "two_dx_read")
    fsm.go("two_dx_read", "ring_in", "rW++", "two_error_send")
    fsm.go("two_error_send", "ring_out", "sW", "two_dx_send")
    fsm.go("two_dx_send", "ring_out", "s", "two_delta")
    fsm.go("two_delta", "logic", "2", "two_delta_send")
    fsm.go("two_delta_send", "to_address", "s", "loop_decrement")

    fsm.go("three_dy_read", "ring_in", "rM", "three_dy_send")
    fsm.go("three_dy_send", "ring_out", "s", "three_error_read")
    fsm.go("three_error_read", "ring_in", "r++M", "three_dx_read")
    fsm.go("three_dx_read", "ring_in", "rW++", "three_error_send")
    fsm.go("three_error_send", "ring_out", "sW", "three_dx_send")
    fsm.go("three_dx_send", "ring_out", "s", "three_delta")
    fsm.go("three_delta", "logic", "3", "three_delta_send")
    fsm.go("three_delta_send", "to_address", "s", "loop_decrement")

    fsm.go("loop_decrement", "logic", "m", "loop_check")
    fsm.go("end_value", "logic", "1N", "end_send")
    fsm.go("end_send", "to_address", "s", "start")
    return fsm


def build_address_fsm() -> Fsm:
    fsm = Fsm()

    fsm.go("start", "control", "@r", "init_sx_send")
    fsm.go("init_sx_send", "ring_out", "s", "init_sy_read")
    fsm.go("init_sy_read", "control", "r", "init_sy_send")
    fsm.go("init_sy_send", "ring_out", "s", "init_address_read")
    fsm.go("init_address_read", "control", "r", "init_plot")
    fsm.go("init_plot", "display", "s", "init_address_send")
    fsm.go("init_address_send", "ring_out", "s", "delta_read")

    fsm.sign(
        "delta_read",
        "control",
        "r",
        negative="end_sx_drop",
        zero="end_sx_drop",
        positive="delta_compare",
    )
    fsm.sign(
        "delta_compare",
        "logic",
        "M2W-",
        negative="delta_one_sx_read",
        zero="delta_two_sx_read",
        positive="delta_three_sx_read",
    )

    fsm.go("delta_one_sx_read", "ring_in", "rM", "delta_one_sx_send")
    fsm.go("delta_one_sx_send", "ring_out", "s", "delta_one_sy_read")
    fsm.go("delta_one_sy_read", "ring_in", "r", "delta_one_sy_send")
    fsm.go("delta_one_sy_send", "ring_out", "s", "delta_one_address_read")
    fsm.go("delta_one_address_read", "ring_in", "r+", "delta_one_plot")
    fsm.go("delta_one_plot", "display", "s", "delta_one_address_send")
    fsm.go("delta_one_address_send", "ring_out", "s", "delta_read")

    fsm.go("delta_two_sx_read", "ring_in", "r", "delta_two_sx_send")
    fsm.go("delta_two_sx_send", "ring_out", "s", "delta_two_sy_read")
    fsm.go("delta_two_sy_read", "ring_in", "rM", "delta_two_sy_send")
    fsm.go("delta_two_sy_send", "ring_out", "s", "delta_two_address_read")
    fsm.go("delta_two_address_read", "ring_in", "r+", "delta_two_plot")
    fsm.go("delta_two_plot", "display", "s", "delta_two_address_send")
    fsm.go("delta_two_address_send", "ring_out", "s", "delta_read")

    fsm.go("delta_three_sx_read", "ring_in", "rM", "delta_three_sx_send")
    fsm.go("delta_three_sx_send", "ring_out", "s", "delta_three_sy_read")
    fsm.go("delta_three_sy_read", "ring_in", "r", "delta_three_sy_send")
    fsm.go("delta_three_sy_send", "ring_out", "s+M", "delta_three_address_read")
    fsm.go("delta_three_address_read", "ring_in", "r+", "delta_three_plot")
    fsm.go("delta_three_plot", "display", "s", "delta_three_address_send")
    fsm.go("delta_three_address_send", "ring_out", "s", "delta_read")

    fsm.go("end_sx_drop", "ring_in", "r", "end_sy_drop")
    fsm.go("end_sy_drop", "ring_in", "r", "end_address_drop")
    fsm.go("end_address_drop", "ring_in", "r", "end_value")
    fsm.go("end_value", "logic", "1N", "end_send")
    fsm.go("end_send", "display", "s", "start")

    return fsm


def build_router_fsm() -> Fsm:
    fsm = Fsm()
    fsm.sign(
        "start",
        "input",
        "@r",
        negative="swap_send",
        zero="plot_send",
        positive="plot_send",
    )
    fsm.go("plot_send", "plot", "s", "start")
    fsm.go("swap_send", "swap", "s", "start")
    return fsm


def build_plot_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@r", "address_send")
    fsm.go("address_send", "address", "s", "color")
    fsm.go("color", "logic", "`15`", "data_send")
    fsm.go("data_send", "data", "s", "start")
    return fsm


def build_swap_fsm() -> Fsm:
    fsm = Fsm()
    fsm.go("start", "input", "@r0", "swap_send")
    fsm.go("swap_send", "swap", "s", "start")
    return fsm


def _compile_streams(right_padding: int = 3) -> list[CompiledRoom]:
    return [
        compile_fsm(builder(), STREAM_ZONES, right_padding=right_padding)
        for builder in (
            build_setup_one_fsm,
            build_setup_two_fsm,
            build_setup_three_fsm,
            build_setup_four_fsm,
            build_setup_five_fsm,
        )
    ]


def _vertical_pipe(
    canvas: Canvas,
    source_bottom: int,
    source_x: int,
    destination_top: int,
    destination_x: int,
) -> None:
    middle = source_bottom + 3
    canvas.pipe(
        [
            (source_bottom + 1, source_x),
            (middle, source_x),
            (middle, destination_x),
            (destination_top - 1, destination_x),
        ]
    )


def _display_rows() -> list[str]:
    return [
        "+" + "=" * 32 + "+",
        *[":" + " " * 32 + ":" for _ in range(24)],
        "+" + "=" * 32 + "+",
    ]


def build_plotter(layout: PlotterLayout = BASELINE_LAYOUT) -> str:
    layout.validate()
    padding = layout.fsm_right_padding
    streams = _compile_streams(padding)
    error_test = compile_fsm(build_error_test_fsm(), ETEST_ZONES, right_padding=padding)
    error_update = compile_fsm(
        build_error_update_fsm(), EUPD_ZONES, right_padding=padding
    )
    address = compile_fsm(build_address_fsm(), ADDRESS_ZONES, right_padding=padding)
    router = compile_fsm(build_router_fsm(), ROUTER_ZONES, right_padding=padding)
    plot = compile_fsm(build_plot_fsm(), PLOT_ZONES, right_padding=padding)
    swap = compile_fsm(build_swap_fsm(), SWAP_ZONES, right_padding=padding)

    canvas = Canvas()
    left = 20
    top = 7

    input_x = left + streams[0].zones["io"]
    canvas.put(0, input_x - 1, ["+-+", "|I|", "+-+"])

    placed_streams: list[tuple[int, CompiledRoom]] = []
    for room in streams:
        canvas.put(top, left, room.rows)
        placed_streams.append((top, room))
        top += room.height + layout.stream_step

    first_top, _first = placed_streams[0]
    canvas.pipe([(3, input_x), (first_top - 1, input_x)])
    for (source_top, source), (destination_top, destination) in pairwise(
        placed_streams
    ):
        _vertical_pipe(
            canvas,
            source_top + source.height + 1,
            left + source.zones["io"],
            destination_top,
            left + destination.zones["io"],
        )

    etest_top = top
    canvas.put(etest_top, left, error_test.rows)
    last_top, last = placed_streams[-1]
    _vertical_pipe(
        canvas,
        last_top + last.height + 1,
        left + last.zones["io"],
        etest_top,
        left + error_test.zones["setup"],
    )

    eupd_top = etest_top + error_test.height + layout.error_room_step
    canvas.put(eupd_top, left, error_update.rows)
    etest_bottom = etest_top + error_test.height + 1
    eupd_bottom = eupd_top + error_update.height + 1

    for source_zone, destination_zone in (
        ("ring_out", "ring_in"),
        ("code_out", "code_in"),
    ):
        _vertical_pipe(
            canvas,
            etest_bottom,
            left + error_test.zones[source_zone],
            eupd_top,
            left + error_update.zones[destination_zone],
        )

    # State return: below EUPD, outside both rooms, then into ETEST's top.
    return_x = left + max(error_test.width, error_update.width) + 8
    return_source_x = left + error_update.zones["ring_out"]
    return_destination_x = left + error_test.zones["ring_in"]
    canvas.pipe(
        [
            (eupd_bottom + 1, return_source_x),
            (eupd_bottom + layout.error_return_depth, return_source_x),
            (eupd_bottom + layout.error_return_depth, return_x),
            (etest_top - 4, return_x),
            (etest_top - 4, return_destination_x),
            (etest_top - 1, return_destination_x),
        ]
    )

    address_top = eupd_bottom + layout.address_step
    canvas.put(address_top, left, address.rows)
    _vertical_pipe(
        canvas,
        eupd_bottom,
        left + error_update.zones["to_address"],
        address_top,
        left + address.zones["control"],
    )
    address_bottom = address_top + address.height + 1

    # Three-value address state ring through a small relay to the left.
    relay_top = address_bottom + layout.address_relay_step
    relay_left = 0
    canvas.put(relay_top, relay_left, RELAY)
    ring_source_x = left + address.zones["ring_out"]
    canvas.pipe(
        [
            (address_bottom + 1, ring_source_x),
            (relay_top + 3, ring_source_x),
            (relay_top + 3, relay_left + 5),
        ]
    )
    ring_destination_x = left + address.zones["ring_in"]
    canvas.pipe(
        [
            (relay_top + 2, relay_left + 5),
            (relay_top + 2, left - 3),
            (address_top - 4, left - 3),
            (address_top - 4, ring_destination_x),
            (address_top - 1, ring_destination_x),
        ]
    )

    router_top = relay_top + len(RELAY) + layout.relay_router_step
    canvas.put(router_top, left, router.rows)
    _vertical_pipe(
        canvas,
        address_bottom,
        left + address.zones["display"],
        router_top,
        left + router.zones["input"],
    )
    router_bottom = router_top + router.height + 1

    drivers_top = router_bottom + layout.router_drivers_step
    plot_left = left
    swap_left = plot_left + plot.width + 20
    canvas.put(drivers_top, plot_left, plot.rows)
    canvas.put(drivers_top, swap_left, swap.rows)

    _vertical_pipe(
        canvas,
        router_bottom,
        left + router.zones["plot"],
        drivers_top,
        plot_left + plot.zones["input"],
    )
    swap_source_x = left + router.zones["swap"]
    swap_destination_x = swap_left + swap.zones["input"]
    canvas.pipe(
        [
            (router_bottom + 1, swap_source_x),
            (router_bottom + layout.router_swap_depth, swap_source_x),
            (router_bottom + layout.router_swap_depth, swap_destination_x),
            (drivers_top - 1, swap_destination_x),
        ]
    )

    plot_bottom = drivers_top + plot.height + 1
    swap_bottom = drivers_top + swap.height + 1
    display_top = max(plot_bottom, swap_bottom) + layout.display_step
    address_x = plot_left + plot.zones["address"]
    display_left = address_x - 10
    display_bottom = display_top + 25
    canvas.put(display_top, display_left, _display_rows())

    # ADDR approaches the top directly.
    canvas.pipe(
        [
            (plot_bottom + 1, address_x),
            (display_top - 1, address_x),
        ]
    )

    # DATA moves left of the display before descending to its left edge.
    data_source_x = plot_left + plot.zones["data"]
    data_row = display_top + 10
    canvas.pipe(
        [
            (plot_bottom + 1, data_source_x),
            (display_top - 5, data_source_x),
            (display_top - 5, display_left - 3),
            (data_row, display_left - 3),
            (data_row, display_left - 1),
        ]
    )

    # SWAP goes below the display and approaches its bottom edge upward.
    swap_source_x = swap_left + swap.zones["swap"]
    swap_x = display_left + 20
    canvas.pipe(
        [
            (swap_bottom + 1, swap_source_x),
            (display_bottom + 5, swap_source_x),
            (display_bottom + 5, swap_x),
            (display_bottom + 1, swap_x),
        ]
    )
    return canvas.render()


def build_plotter_compact() -> str:
    """Build the geometry-only compact successor to ``plotter_00``."""

    return build_plotter(COMPACT_LAYOUT)
