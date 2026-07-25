"""Network interpreter: N block graphs joined by FIFO pipes.

A `.man` machine is decompiled (see `decompile`) into one block graph per
man; this module runs them together. Pipes become FIFOs whose capacity is
the pipe's cell count, `r`/`s` block, and the men are scheduled
round-robin, block-atomically, until the network is quiescent.

Tick counts are deliberately NOT reproduced -- block-atomic execution has
no notion of a tick. For a `patient` network (blocking `r`/`s` only) the
latency-insensitivity result in docs/synthesis-stack.md says the *output
sequence* is nevertheless the same, and that is what we compare.

Machines using `q` (pipe occupancy), `R`/`U` (arrival order) or a display
observe timing and are therefore not patient; `impatient_ops` reports
them so callers can skip with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import blockgraph, decompile
from .sim import Machine

BLOCKING = frozenset("rsSR")
IMPATIENT = frozenset("qRU")
_ONE_OP: dict = {}


def _single(op: str) -> dict:
    """A one-op program, so op semantics come from `blockgraph.run` itself."""
    if op not in _ONE_OP:
        _ONE_OP[op] = {"_": blockgraph.Block(name="_", ops=[op], kind="H")}
    return _ONE_OP[op]


def next_block(block: blockgraph.Block, st: blockgraph.State) -> str | None:
    """Apply a block's terminator. Mirrors `blockgraph.run`'s transitions."""
    if block.kind == "H":
        return None
    if block.kind == "goto":
        return block.targets[0]
    if block.kind == "if":
        return block.targets[0 if st.A < 0 else 1 if st.A == 0 else 2]
    if block.kind == "if-bp":
        return block.targets[0 if st.BP > 0 else 1]
    return block.targets[0 if st.BP & 1 else 1]


def impatient_ops(blocks: dict) -> set:
    """Ops in this graph that observe timing rather than data.

    Port forms count too: `(q p3_4)` is still an occupancy read. `if-recv`
    (`U`) is arrival-order control flow, so it counts as well.
    """
    heads = set()
    for block in blocks.values():
        for op in block.ops:
            heads.add(op[1:-1].split()[0] if op.startswith("(") else op)
        if block.kind == "if-recv":
            heads.add("U")
    return heads & IMPATIENT


@dataclass
class Fifo:
    """A pipe as a bounded queue; capacity is the pipe's cell count."""

    capacity: int
    values: list = field(default_factory=list)

    @property
    def full(self) -> bool:
        return len(self.values) >= self.capacity

    @property
    def empty(self) -> bool:
        return not self.values


@dataclass
class Proc:
    """One man: its graph, its program counter, its registers."""

    name: str
    blocks: dict
    binds: dict                      # (block name, op index) -> tuple of pipes
    room: object
    block: str
    index: int = 0
    state: blockgraph.State = field(default_factory=blockgraph.State)
    halted: bool = False
    reason: str = ""


class Net:
    """Every man of a `.man` machine, decompiled and run as a network."""

    def __init__(self, machine: Machine, **kwargs):
        self.machine = machine
        self.fifos = {id(p): Fifo(len(p.cells)) for p in machine.pipes}
        self.ports: dict = {}
        for pipe in machine.pipes:
            self.ports[(id(pipe.source), decompile.port_label(pipe.cells[0]))] = pipe
            self.ports[(id(pipe.dest), decompile.port_label(pipe.cells[-1]))] = pipe
        self.procs: list[Proc] = []
        for start in decompile.man_starts(machine):
            blocks = decompile.decompile_man(machine, start, **kwargs)
            room = decompile._room_of(machine, start[0], start[1])
            self.procs.append(
                Proc(
                    name=decompile.block_name(start),
                    blocks=blocks,
                    binds=self._bind(machine, blocks, room),
                    room=room,
                    block=next(iter(blocks)),
                )
            )
        self.input = machine.input_pipe
        self.output = machine.output_pipe

    def _bind(self, machine: Machine, blocks: dict, room) -> dict:
        """Resolve every port op to its pipe(s), from the notation alone.

        `(s p4_12)` names the pipe by the cell where it meets the room; a bare
        `s`/`r`/`q` means the room's only pipe that way. Nothing here consults
        the geometry the graph came from, so a hand-written graph binds too.
        """
        out_pipes = machine.out_pipes.get(id(room), [])
        in_pipes = machine.in_pipes.get(id(room), [])
        binds: dict = {}
        for name, block in blocks.items():
            slots = list(enumerate(block.ops))
            if block.kind == "if-recv":
                slots.append(("term", "R"))
            for index, token in slots:
                head, port = token, None
                if token.startswith("("):
                    head, *rest = token[1:-1].split()
                    port = rest[0] if rest else None
                if head not in "rsSRq":
                    continue
                if port is not None:
                    chosen = (self.ports[(id(room), port)],)
                elif head == "S":
                    chosen = tuple(out_pipes)
                elif head == "R":
                    chosen = tuple(in_pipes)
                else:
                    chosen = tuple(out_pipes if head == "s" else in_pipes)
                if not chosen:
                    raise ValueError(f"{token!r} in {name!r} has no pipe")
                if port is None and head in "srq" and len(chosen) > 1:
                    raise ValueError(f"bare {head!r} in {name!r} is ambiguous")
                binds[(name, index)] = chosen
        return binds

    # ------------------------------------------------------------ execution
    @staticmethod
    def _head(token: str) -> str:
        return token[1:-1].split()[0] if token.startswith("(") else token

    def _pipes(self, proc: Proc, index) -> list:
        return list(proc.binds.get((proc.block, index), ()))

    def _ready(self, proc: Proc, token: str) -> bool:
        """Would this op block? (`sim`: `s` needs a free head cell, `r` a
        value at the tail; `S`/`R` quantify over all the room's pipes.)"""
        head = self._head(token)
        if head not in BLOCKING:
            return True
        fifos = [self.fifos[id(p)] for p in self._pipes(proc, proc.index)]
        if head == "r":
            return not fifos[0].empty
        if head == "R":
            return any(not f.empty for f in fifos)
        if head == "s":
            return not fifos[0].full
        return all(not f.full for f in fifos)

    def _take(self, pipes: list) -> tuple:
        """`sim`'s R/U rule: among ready pipes, lowest destination cell wins."""
        order = sorted(range(len(pipes)), key=lambda i: pipes[i].cells[-1])
        for i in order:
            fifo = self.fifos[id(pipes[i])]
            if not fifo.empty:
                return i, fifo.values.pop(0)
        raise RuntimeError("no ready pipe")

    def _exec(self, proc: Proc, token: str) -> None:
        """Run one op with `blockgraph`'s own semantics, so they cannot drift."""
        pipes = self._pipes(proc, proc.index)
        fifos = [self.fifos[id(p)] for p in pipes]
        proc.state.trace.clear()
        blockgraph.run(
            _single(token),
            recv=lambda port=None: fifos[0].values.pop(0),
            send=lambda value, port=None: fifos[0].values.append(value),
            send_all=lambda value: [f.values.append(value) for f in fifos],
            occupancy=lambda port=None: len(fifos[0].values),
            recv_any=lambda: self._take(pipes),
            state=proc.state,
            max_steps=1 << 62,
        )

    def quantum(self, proc: Proc) -> int:
        """Advance one man by at most one block. Returns ops executed + 1."""
        if proc.halted:
            return 0
        block = proc.blocks[proc.block]
        used = 0
        while proc.index < len(block.ops):
            op = block.ops[proc.index]
            if not self._ready(proc, op):
                return used
            self._exec(proc, op)
            proc.index += 1
            used += 1
        if block.kind == "wall":
            proc.halted, proc.reason = True, decompile.WALL
            return used + 1
        if block.kind == "if-recv":        # U: branch on WHICH pipe delivered
            pipes = self._pipes(proc, "term")
            if all(self.fifos[id(p)].empty for p in pipes):
                return used
            index, proc.state.A = self._take(pipes)
            proc.block, proc.index = block.targets[index], 0
            return used + 1
        target = next_block(block, proc.state)
        if target is None:
            proc.halted = True
            proc.reason = (
                block.name if block.name in decompile.SENTINELS else "halted"
            )
        else:
            proc.block, proc.index = target, 0
        return used + 1

    def _io(self, gate) -> int:
        """Drain the output room, then feed the input room -- `sim`'s order."""
        moved = 0
        if self.output is not None:
            fifo = self.fifos[id(self.output)]
            while fifo.values:
                gate.on_output(fifo.values.pop(0))
                moved += 1
        if self.input is not None:
            fifo = self.fifos[id(self.input)]
            while not fifo.full:
                value = gate.pop_input()
                if value is None:
                    break
                fifo.values.append(value)
                moved += 1
        return moved

    def run(self, gate, max_steps: int = 20_000_000) -> str:
        """Round-robin until quiescent. `gate` supplies pop_input/on_output."""
        steps = 0
        while steps < max_steps:
            progress = self._io(gate)
            if getattr(gate, "stop", False) and getattr(gate, "done", False):
                return "passed"            # the protocol is satisfied
            for proc in self.procs:
                progress += self.quantum(proc)
            steps += progress
            if not progress:
                break
        else:
            return "step-cap"
        self._io(gate)
        if all(proc.halted for proc in self.procs):
            reasons = {proc.reason for proc in self.procs}
            for sentinel in decompile.SENTINELS:
                if sentinel in reasons:
                    return sentinel
            return "halted"
        return "deadlock"

    def impatient(self) -> set:
        ops = set()
        for proc in self.procs:
            ops |= impatient_ops(proc.blocks)
        if any(room.kind == "display" for room in self.machine.rooms):
            ops.add("display")
        return ops
