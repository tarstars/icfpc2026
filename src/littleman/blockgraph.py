"""Block-graph notation: write littleman algorithms without geometry.

A program is labelled straight-line blocks plus explicit transitions::

    (mark K) @ 1 (if A B C)
    (mark A) W 2 - (goto K)
    (mark B) W 3 / (goto K)
    (mark C) W 4 * (goto K)

Ops are single glyphs with exactly their `littleman.sim` semantics;
literals are written ```123```. Control forms:

===================  =====================================================
``(mark NAME)``      start a block (optionally ``:A dead :B mask`` notes)
``(goto NAME)``      unconditional transition
``(if N Z P)``       ``X`` -- targets for A<0, A==0, A>0
``(if-bp T S)``      ``d``/``a`` -- BP>0 taken, else straight
``(if-par O E)``     ``x`` -- BP low bit 1 / 0
``(if-recv A B..)``  ``U`` -- receive from any ready pipe, branch on which
``H``                halt
===================  =====================================================

This module parses, structurally checks, and INTERPRETS such graphs, so
an algorithm can be developed and tested with zero layout work. Geometry
is a separate, later problem (docs/architecture/claude_15_blockgraph.md
proves any well-formed graph is implementable, so the checks here are
purely local).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .sim import wrap64

# `if-recv` is `U`: receive from any ready pipe, then branch on WHICH pipe
# delivered. Its arity is the room's incoming-pipe count, so it is checked
# against the targets given rather than a fixed number.
CONTROL = {"goto": 1, "if": 3, "if-bp": 2, "if-par": 2, "if-recv": None,
           "wall": 0}
# Non-terminator forms that name a PORT. `s`/`r`/`q` bind to the NEAREST pipe
# by geometry, so a room with two outgoing pipes needs to say which one; bare
# `s`/`r`/`q` mean "the room's only pipe of that direction".
PORT_OPS = {"s", "r", "q", "S", "R"}


class BlockGraphError(ValueError):
    pass


@dataclass
class Block:
    name: str
    ops: list[str] = field(default_factory=list)
    kind: str = ""                       # goto | if | if-bp | if-par | H
    targets: tuple[str, ...] = ()
    notes: dict[str, str] = field(default_factory=dict)


def tokenize(text: str) -> list[str]:
    """Split source into s-expressions, literals and single-glyph ops."""
    text = re.sub(r";[^\n]*", " ", text)          # ; line comments
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == "(":
            j = text.index(")", i)
            out.append(text[i : j + 1])
            i = j + 1
        elif ch == "`":
            j = text.index("`", i + 1)
            out.append(text[i : j + 1])
            i = j + 1
        else:
            out.append(ch)
            i += 1
    return out


def parse(text: str, *, allow_timing_ops: bool = False) -> dict[str, Block]:
    """Source -> {name: Block}. Raises BlockGraphError on structure faults.

    `allow_timing_ops` permits q/R/U (occupancy- and arrival-sensitive), which
    are rejected by default because they break latency-insensitive
    composition. Decompiled graphs that use them are not `patient` and their
    behaviour is only reproducible tick-accurately.
    """
    blocks: dict[str, Block] = {}
    current: Block | None = None
    for tok in tokenize(text):
        if tok.startswith("("):
            head, *rest = tok[1:-1].split()
            if head == "mark":
                if current and not current.kind:
                    raise BlockGraphError(f"block {current.name!r} has no terminator")
                name = rest[0]
                if name in blocks:
                    raise BlockGraphError(f"duplicate mark {name!r}")
                notes = {}
                for key, value in zip(rest[1::2], rest[2::2]):
                    notes[key.lstrip(":")] = value
                current = Block(name=name, notes=notes)
                blocks[name] = current
                continue
            if head in PORT_OPS:
                if current is None:
                    raise BlockGraphError(f"{tok!r} before any (mark ...)")
                if current.kind:
                    raise BlockGraphError(f"op {tok!r} after terminator")
                if head in ("S", "R") and rest:
                    raise BlockGraphError(f"{head!r} takes no port")
                if head in ("s", "r", "q") and len(rest) > 1:
                    raise BlockGraphError(f"{head!r} takes at most one port")
                current.ops.append(tok)
                continue
            if head not in CONTROL:
                raise BlockGraphError(f"unknown form {tok!r}")
            if current is None:
                raise BlockGraphError(f"{tok!r} before any (mark ...)")
            if current.kind:
                raise BlockGraphError(f"block {current.name!r} terminated twice")
            arity = CONTROL[head]
            if arity is None:
                if not rest:
                    raise BlockGraphError("'if-recv' needs at least one target")
            elif len(rest) != arity:
                raise BlockGraphError(
                    f"{head!r} takes {arity} targets, got {len(rest)}"
                )
            current.kind, current.targets = head, tuple(rest)
            continue
        if current is None:
            raise BlockGraphError(f"op {tok!r} before any (mark ...)")
        if current.kind:
            raise BlockGraphError(f"op {tok!r} after terminator in {current.name!r}")
        if tok == "H":
            current.kind = "H"
            continue
        current.ops.append(tok)
    if current and not current.kind:
        raise BlockGraphError(f"block {current.name!r} has no terminator")
    check(blocks, allow_timing_ops=allow_timing_ops)
    return blocks


def check(blocks: dict[str, Block], *, allow_timing_ops: bool = False) -> None:
    """Local structural checks (claude_15 §checker)."""
    if not blocks:
        raise BlockGraphError("empty program")
    for block in blocks.values():
        for target in block.targets:
            if target not in blocks:
                raise BlockGraphError(f"{block.name!r} -> unknown mark {target!r}")
        for op in block.ops:
            if op.startswith("`"):
                digits = op[1:-1].replace(" ", "")
                if digits and not digits.isdigit():
                    raise BlockGraphError(f"bad literal {op!r} in {block.name!r}")
            elif op in "RUq" and not allow_timing_ops:
                raise BlockGraphError(
                    f"quarantined op {op!r} in {block.name!r} (timing-sensitive)"
                )
            elif op.startswith("("):
                pass          # port form, validated at parse
            elif op not in "0123456789@.MW+-*/%N&|~{}bm]qsrSR<>^vV":
                raise BlockGraphError(f"unknown op {op!r} in {block.name!r}")


@dataclass
class State:
    A: int = 0
    B: int = 0
    BP: int = 0
    ticks: int = 0
    trace: list[str] = field(default_factory=list)


def run(
    blocks: dict[str, Block],
    start: str | None = None,
    *,
    recv=None,
    send=None,
    occupancy=None,
    recv_any=None,
    send_all=None,
    max_steps: int = 1_000_000,
    state: State | None = None,
) -> State:
    """Interpret the graph. `recv()`/`send(v)` model the room's pipes.

    Semantics are exactly `littleman.sim`'s: B is written only by M, W and
    `/`; arithmetic wraps signed-64; `X` branches on sign(A); `d`/`a` on
    BP > 0; `x` on BP's low bit.
    """
    st = state or State()
    name = start or next(iter(blocks))
    while True:
        block = blocks[name]
        st.trace.append(name)
        for op in block.ops:
            st.ticks += 1
            port = None
            if op.startswith("("):
                head, *rest = op[1:-1].split()
                port, op = (rest[0] if rest else None), head
            if op.startswith("`"):
                st.A = int(op[1:-1].replace(" ", "") or 0)
            elif op.isdigit():
                st.A = int(op)
            elif op == "M":
                st.B = st.A
            elif op == "W":
                st.A, st.B = st.B, st.A
            elif op == "+":
                st.A = wrap64(st.A + st.B)
            elif op == "-":
                st.A = wrap64(st.A - st.B)
            elif op == "*":
                st.A = wrap64(st.A * st.B)
            elif op == "N":
                st.A = wrap64(-st.A)
            elif op == "%":
                st.A = 0 if st.B == 0 else wrap64(st.A % st.B)
            elif op == "/":
                if st.B == 0:
                    st.A, st.B = 0, st.A
                else:
                    st.A, st.B = st.A // st.B, st.A - (st.A // st.B) * st.B
            elif op == "&":
                st.A = wrap64(st.A & st.B)
            elif op == "|":
                st.A = wrap64(st.A | st.B)
            elif op == "~":
                st.A = wrap64(st.A ^ st.B)
            elif op == "{":
                st.A = wrap64(st.A << st.B) if 0 <= st.B <= 63 else 0
            elif op == "}":
                st.A = 0 if st.B < 0 else wrap64(st.A >> min(st.B, 63))
            elif op == "b":
                st.BP = st.A
            elif op == "m":
                st.BP -= 1
            elif op == "]":
                st.BP >>= 1
            elif op == "r":
                if recv is None:
                    raise BlockGraphError("'r' with no recv callback")
                st.A = recv(port) if port else recv()
            elif op == "q":
                if occupancy is None:
                    raise BlockGraphError("'q' with no occupancy callback")
                st.BP = occupancy(port) if port else occupancy()
            elif op == "R":
                if recv_any is None:
                    raise BlockGraphError("'R' with no recv_any callback")
                st.A = recv_any()[1]
            elif op == "s":
                if send is None:
                    raise BlockGraphError("'s' with no send callback")
                send(st.A, port) if port else send(st.A)
            elif op == "S":
                if send_all is None:
                    raise BlockGraphError("'S' (broadcast) with no send_all callback")
                send_all(st.A)
            elif op in "@.<>^vV":
                pass                      # spawn marker, nop, headings
            if st.ticks > max_steps:
                raise BlockGraphError(f"step cap in block {block.name!r}")
        if block.kind == "H":
            return st
        if block.kind == "wall":
            st.trace.append("__wall")
            raise BlockGraphError("stepped into a wall (error terminator)")
        if block.kind == "goto":
            name = block.targets[0]
        elif block.kind == "if":
            name = block.targets[0 if st.A < 0 else 1 if st.A == 0 else 2]
        elif block.kind == "if-bp":
            name = block.targets[0 if st.BP > 0 else 1]
        elif block.kind == "if-recv":      # U: branch on WHICH pipe delivered
            if recv_any is None:
                raise BlockGraphError("'if-recv' with no recv_any callback")
            index, st.A = recv_any()
            name = block.targets[index]
        else:                              # if-par
            name = block.targets[0 if st.BP & 1 else 1]
