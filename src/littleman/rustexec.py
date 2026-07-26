"""Rust-backed exact executor for parsed littleman machines.

The Python parser and :mod:`littleman.fastsim` compiler remain authoritative.
This module owns backend selection, build diagnostics, and the versioned
Python-to-Rust boundary. It never parses ``.man`` source in Rust.
"""

from __future__ import annotations

from collections import deque

from . import fastsim
from .sim import Machine as ReferenceMachine
from .sim import RunResult

try:
    from . import _fastsim_rust as _rust
except ImportError:  # pragma: no cover - depends on local build state
    _rust = None

HAVE_RUST = _rust is not None
IR_VERSION = 1
OFFICIAL_SEMANTICS_VERSION = 2
OP_SPLIT = 35


def backend() -> str:
    """Return the active native backend name, or ``"unavailable"``."""
    return _rust.backend() if _rust is not None else "unavailable"


def run_program(program, result, input_queue, controller, max_ticks):
    """Execute one compiled :class:`fastsim.Program` through Rust."""
    if _rust is None:
        raise RuntimeError(
            "Rust executor is not built; run "
            "`uv run maturin develop --release --manifest-path rust/Cargo.toml`"
        )
    spec = fastsim.build_spec(program)
    spec["ir_version"] = IR_VERSION
    queue = getattr(controller, "queue", None)
    if type(controller).__name__ != "RoundController" or not isinstance(queue, list):
        queue = None
    raw = _rust.run(spec, controller, queue, input_queue, max_ticks)
    (
        status,
        error,
        verdict,
        ticks,
        output,
        output_ticks,
        frames,
        frame_ticks,
        program.mcell,
        program.mdir,
        program.mA,
        program.mB,
        program.mBP,
        halted,
        waits,
        program.p_runs,
        pipe_values,
        display_current,
        display_next,
        display_cursors,
    ) = raw
    program.mhalt = [bool(value) for value in halted]
    program.p_q = [deque(values) for values in pipe_values]
    for (room, _addr, _data, _swap, width, height), current, nxt, cursor in zip(
        program.displays,
        display_current,
        display_next,
        display_cursors,
    ):
        room.current = [
            current[row * width : (row + 1) * width] for row in range(height)
        ]
        room.next = [nxt[row * width : (row + 1) * width] for row in range(height)]
        room.cursor = cursor
    result.ticks = ticks
    result.output[:] = output
    result.output_ticks[:] = output_ticks
    result.frames[:] = frames
    result.frame_ticks[:] = frame_ticks
    if error:
        result.status = "error"
        result.error = error
    elif verdict:
        result.status = verdict
    else:
        result.status = status
    fastsim._writeback(program, [fastsim._WAIT_NAMES[kind] for kind in waits])
    return result


def run_machine(machine, inputs=None, max_ticks=5_000_000, controller=None):
    """Compile a parsed machine once and execute it through Rust."""
    try:
        program = fastsim.compile_machine(machine)
    except fastsim.Unsupported:
        return ReferenceMachine.run(machine, inputs, max_ticks, controller)
    machine._input_queue = list(inputs or [])
    machine._controller = controller
    machine._verdict = None
    result = RunResult(status="tick-cap")
    return run_program(
        program,
        result,
        machine._input_queue,
        controller,
        max_ticks,
    )


class Machine(ReferenceMachine):
    """Authoritative Python parser with the Rust execution loop."""

    def run(self, inputs=None, max_ticks: int = 5_000_000, controller=None):
        return run_machine(self, inputs, max_ticks, controller)


def build_official_spec(machine):
    """Compile current contest semantics, including ``Y`` and annihilation."""
    program = fastsim.compile_machine(machine)
    spec = fastsim.build_spec(program)
    spec["ir_version"] = IR_VERSION
    spec["semantics_version"] = OFFICIAL_SEMANTICS_VERSION
    width = program.W
    for cell, position in enumerate(program.cellpos):
        row, column = divmod(position, width)
        if machine.grid[row][column] == "Y":
            for direction in range(4):
                spec["code"][direction][cell] = OP_SPLIT
    return program, spec


def run_official(
    machine,
    inputs=None,
    max_ticks=5_000_000,
    controller=None,
    *,
    men_cap=65_536,
):
    """Run a parsed machine under the post-``/split`` contest semantics.

    The returned dictionary includes an ``malive`` vector because split and
    collision can change the live-man set; the legacy fastsim writeback shape
    cannot represent that dynamic state.
    """
    if _rust is None:
        raise RuntimeError("Rust executor is not built")
    program, spec = build_official_spec(machine)
    spec["men_cap"] = men_cap
    input_queue = list(inputs or [])
    queue = getattr(controller, "queue", None)
    if type(controller).__name__ != "RoundController" or not isinstance(queue, list):
        queue = None
    result = _rust.run_official(
        spec,
        controller,
        queue,
        input_queue,
        max_ticks,
    )
    result["cellpos"] = program.cellpos
    return result
