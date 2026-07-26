"""Rust-backed exact executor for parsed littleman machines.

The Python parser and :mod:`littleman.fastsim` compiler remain authoritative.
This module owns backend selection, build diagnostics, and the versioned
Python-to-Rust boundary. It never parses ``.man`` source in Rust.
"""

from __future__ import annotations

import hashlib
import multiprocessing
import sys
from collections import deque
from dataclasses import dataclass

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


@dataclass(frozen=True)
class BatchResult:
    index: int
    status: str
    error: str | None
    ticks: int
    judged_ticks: int
    output: tuple[int, ...]
    output_ticks: tuple[int, ...]
    frame_ticks: tuple[int, ...]


class CompiledMachine:
    """One parse/IR build reused across independent fresh executions."""

    def __init__(self, text: str):
        if _rust is None:
            raise RuntimeError("Rust executor is not built")
        self.sha256 = hashlib.sha256(text.encode()).hexdigest()
        machine = ReferenceMachine.parse(text)
        self.program = fastsim.compile_machine(machine)
        self.spec = fastsim.build_spec(self.program)
        self.spec["ir_version"] = IR_VERSION

    def run_rounds(self, index, rounds, max_ticks=5_000_000):
        from .judge import RoundController

        controller = RoundController(rounds)
        if controller.done:
            return BatchResult(index, "passed", None, 0, 0, (), (), ())
        raw = _rust.run(
            self.spec,
            controller,
            controller.queue,
            [],
            max_ticks,
        )
        status, error, verdict, ticks = raw[:4]
        final_status = "error" if error else (verdict or status)
        return BatchResult(
            index=index,
            status=final_status,
            error=error,
            ticks=ticks,
            judged_ticks=controller.last_output_tick
            if final_status == "passed"
            else ticks,
            output=tuple(raw[4]),
            output_ticks=tuple(raw[5]),
            frame_ticks=tuple(raw[7]),
        )

    def cli_request(
        self,
        cases,
        *,
        max_ticks=5_000_000,
        workers=1,
        include_state=False,
        include_spec=True,
    ):
        """Build the JSON-serializable request consumed by ``littleman-rust``."""

        def frame(value):
            if value and isinstance(value[0], str):
                return [[int(character, 16) for character in row] for row in value]
            return [[int(character) for character in row] for row in value]

        jobs = []
        for index, rounds in enumerate(cases):
            jobs.append(
                {
                    "id": str(index),
                    "rounds": [
                        {
                            "in": [int(value) for value in round_["in"]],
                            "out": [int(value) for value in round_.get("out", [])],
                            "frames": [
                                frame(expected) for expected in round_.get("frames", [])
                            ],
                        }
                        for round_ in rounds
                    ],
                }
            )
        request = {
            "jobs": jobs,
            "max_ticks": max_ticks or 5_000_000,
            "workers": workers,
            "include_state": include_state,
        }
        if include_spec:
            request["spec"] = self.spec
        return request

    def encoded_ir(self) -> bytes:
        """Return the versioned zstd-compressed native IR cache."""
        return bytes(_rust.encode_ir(self.spec))


_FORK_COMPILED = None
_FORK_MAX_TICKS = 0


def _fork_run_case(item):
    index, rounds = item
    return _FORK_COMPILED.run_rounds(index, rounds, _FORK_MAX_TICKS)


def run_rounds_parallel(compiled, cases, *, max_ticks=5_000_000, workers=1):
    """Run independent round cases deterministically, reusing one cached IR."""
    max_ticks = max_ticks or 5_000_000
    indexed = list(enumerate(cases))
    if workers <= 1 or len(indexed) <= 1:
        return [compiled.run_rounds(i, rounds, max_ticks) for i, rounds in indexed]
    if "fork" not in multiprocessing.get_all_start_methods():
        raise RuntimeError(
            "multicore Rust batch execution requires multiprocessing fork"
        )
    global _FORK_COMPILED, _FORK_MAX_TICKS
    _FORK_COMPILED = compiled
    _FORK_MAX_TICKS = max_ticks
    try:
        with multiprocessing.get_context("fork").Pool(
            processes=min(workers, len(indexed))
        ) as pool:
            return pool.map(_fork_run_case, indexed)
    finally:
        _FORK_COMPILED = None
        _FORK_MAX_TICKS = 0


def pytest_configure(config):
    """Pytest plugin hook: redirect later ``sim.Machine`` imports to Rust."""
    # The wall-tolerant server oracle monkey-patches ``Machine._tick``. Its
    # behavior cannot be represented by replacing that class with this
    # executor because the native loop never calls the Python method. Import
    # both modules before redirecting ``sim.Machine`` and preserve their
    # reference-class bindings.
    from . import alexey_walljudge, judge, server_compat, sim

    protected = {alexey_walljudge.__name__, server_compat.__name__}

    if _rust is None:
        raise RuntimeError("littleman Rust pytest plugin requires the native extension")
    sim.Machine = Machine
    judge.Machine = Machine
    for name, module in list(sys.modules.items()):
        if (
            name not in protected
            and name.startswith("littleman.")
            and getattr(module, "Machine", None) is ReferenceMachine
        ):
            module.Machine = Machine


def pytest_collection_modifyitems(session, config, items):
    """Fail if a collected test module captured the Python executor."""
    stale = sorted(
        {
            item.module.__name__
            for item in items
            if getattr(item.module, "Machine", None) is ReferenceMachine
        }
    )
    if stale:
        raise RuntimeError(
            "Rust executor plugin found stale Python Machine bindings: "
            + ", ".join(stale)
        )


def pytest_report_header(config):
    return f"littleman executor: {backend()} (IR v{IR_VERSION})"


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
