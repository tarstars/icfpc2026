"""Decompile `.man` machines into block-graph notation.

The control-flow graph of a little man is a graph over **(row, col,
heading)** states -- the triple, not the cell, because one cell crossed
in two headings executes the same glyph but continues to two different
places (that is how corridor crossings work).

A state's successor is found by executing the glyph (which may set the
heading) and then stepping one cell along the resulting heading, exactly
as `littleman.sim` does: execute, then move. Branch glyphs (`X`, `d`,
`a`, `x`) have several successors and we take *all* of them -- this is
reachability, not simulation.

Stepping onto a room wall is a fatal `wall` error in `sim`; here it
terminates the path in the distinguished block `__wall`, since in our
machines an unrouted arm is a deliberate assertion.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import blockgraph
from .sim import CLOCKWISE, COUNTERCW, DOWN, LEFT, Machine, Man, RIGHT, UP

HEADING_NAME = {UP: "N", DOWN: "S", LEFT: "W", RIGHT: "E"}
WALL = "__wall"
BADOP = "__badop"          # glyph `sim._execute` rejects -> machine error
SENTINELS = (WALL, BADOP)
# every glyph `sim._execute` accepts; anything else is a runtime "bad-op"
VALID_GLYPHS = frozenset(" .@`H0123456789><^vVMW+-*/%N&|~{}XsSrRUqbmda]x")

# glyph -> (blockgraph terminator, successor headings as a function of the
# incoming heading).  Order matches the target order of the control form.
FORKS = {
    "X": ("if", lambda d: (COUNTERCW[d], d, CLOCKWISE[d])),
    "d": ("if-bp", lambda d: (CLOCKWISE[d], d)),
    "a": ("if-bp", lambda d: (COUNTERCW[d], d)),
    "x": ("if-par", lambda d: (CLOCKWISE[d], COUNTERCW[d])),
}
SET_HEADING = {">": RIGHT, "<": LEFT, "^": UP, "v": DOWN, "V": DOWN}


@dataclass(frozen=True)
class Node:
    """One (row, col, heading) state: its op token and its successors."""

    op: str | None            # blockgraph op glyph/literal, None if it is a fork
    kind: str                 # goto | if | if-bp | if-par | H
    succs: tuple              # successor states, or WALL


def outgoing(machine: Machine, state) -> tuple[str, tuple]:
    """Return (terminator kind, successor states) for one state."""
    row, col, heading = state
    glyph = machine.grid[row][col]
    if glyph == "H":
        return "H", ()
    if glyph not in VALID_GLYPHS:
        return "goto", (BADOP,)
    if glyph == "U":
        # `U` receives from any ready pipe AND turns away from it: one
        # successor per incoming pipe, in `Machine._incoming` order.
        room = _room_of(machine, row, col)
        succs = []
        for pipe in machine.in_pipes.get(id(room), []):
            man = Man(row, col, room)
            machine._turn_away(man, pipe)
            new = man.direction
            nxt = (row + new[0], col + new[1], new)
            succs.append(nxt if room.contains_interior(nxt[0], nxt[1]) else WALL)
        return "if-recv", tuple(succs)
    if glyph in FORKS:
        kind, turns = FORKS[glyph]
        headings = turns(heading)
    else:
        kind = "goto"
        headings = (SET_HEADING.get(glyph, heading),)
    room = _room_of(machine, row, col)
    succs = []
    for new in headings:
        nxt = (row + new[0], col + new[1], new)
        succs.append(nxt if room.contains_interior(nxt[0], nxt[1]) else WALL)
    return kind, tuple(succs)


def _room_of(machine: Machine, row: int, col: int):
    for room in machine.rooms:
        if room.contains_interior(row, col):
            return room
    raise ValueError(f"cell {(row, col)} is in no room interior")


def walk_states(machine: Machine, start) -> set:
    """Reachable states from `start` = (row, col, heading)."""
    seen = {start}
    stack = [start]
    while stack:
        state = stack.pop()
        for succ in outgoing(machine, state)[1]:
            if succ not in SENTINELS and succ not in seen:
                seen.add(succ)
                stack.append(succ)
    return seen


def man_starts(machine: Machine) -> list:
    """Start state of every man in the machine, heading EAST."""
    return [(man.r, man.c, RIGHT) for man in machine.men]


def port_label(cell) -> str:
    """Name a pipe by the cell where it meets the room."""
    return f"p{cell[0]}_{cell[1]}"


def _fake_man(machine: Machine, row: int, col: int) -> Man:
    return Man(row, col, _room_of(machine, row, col))


def incoming_of(machine: Machine, row: int, col: int) -> list:
    return machine.in_pipes.get(id(_room_of(machine, row, col)), [])


def port_of(machine: Machine, state, glyph: str) -> str | None:
    """The port `sim` would pick, or None when the room leaves no choice.

    `s`/`r`/`q` resolve to the pipe NEAREST the man's cell, so two pipes on
    one wall are two different channels reached by the same glyph. Bare
    `s`/`r`/`q` in the notation mean "the room's only pipe that way".
    """
    man = _fake_man(machine, state[0], state[1])
    if glyph == "s":
        pipes, chosen = machine._outgoing(man), machine._nearest_outgoing(man)
        cell = chosen.cells[0] if chosen else None
    else:                                  # r / q -- incoming
        pipes, chosen = machine._incoming(man), machine._nearest_incoming(man)
        cell = chosen.cells[-1] if chosen else None
    if cell is None or len(pipes) < 2:
        return None
    return port_label(cell)


def _literal_digits(machine: Machine, state) -> str:
    """Digits a backtick span yields when *closed* in this walk direction.

    Mirrors `Machine._literal_load`: a span is one op token, and the walk
    direction decides both whether it fires at all (only the far end of the
    span loads) and the digit order -- ``001`` walked leftward is 100.
    """
    row, col, heading = state
    if heading in (LEFT, RIGHT) and (row, col) in machine.hpairs:
        low, high = machine.hpairs[(row, col)]
        if heading == RIGHT and col == high:
            cells = [machine.grid[row][x] for x in range(low + 1, high)]
        elif heading == LEFT and col == low:
            cells = [machine.grid[row][x] for x in range(high - 1, low, -1)]
        else:
            return ""
    elif heading in (UP, DOWN) and (row, col) in machine.vpairs:
        low, high = machine.vpairs[(row, col)]
        if heading == DOWN and row == high:
            cells = [machine.grid[x][col] for x in range(low + 1, high)]
        elif heading == UP and row == low:
            cells = [machine.grid[x][col] for x in range(high - 1, low, -1)]
        else:
            return ""
    else:
        return ""
    return "".join(ch for ch in cells if ch.isdigit())


def op_token(machine: Machine, state) -> str | None:
    """The blockgraph op this state executes, or None for a terminator."""
    row, col, heading = state
    glyph = machine.grid[row][col]
    if glyph in "HU" or glyph in FORKS or glyph not in VALID_GLYPHS:
        return None
    if glyph == "`":
        digits = _literal_digits(machine, state)
        return f"`{digits}`" if digits else "."
    if glyph.isdigit():
        table = machine.hdigits if heading in (LEFT, RIGHT) else machine.vdigits
        return "." if (row, col) in table else glyph
    if glyph in " .@":
        return "." if glyph == " " else glyph
    if glyph in "srq":
        port = port_of(machine, state, glyph)
        return f"({glyph} {port})" if port else glyph
    return glyph


def block_name(state) -> str:
    row, col, heading = state
    return f"L{row}_{col}_{HEADING_NAME[heading]}"


def leaders(graph: dict, start) -> set:
    """States that must begin a block: start, fork targets, merge points."""
    preds: dict = {}
    heads = {start}
    for state, node in graph.items():
        for succ in node.succs:
            if succ in SENTINELS:
                continue
            preds.setdefault(succ, set()).add(state)
            if len(node.succs) > 1:
                heads.add(succ)
    heads.update(s for s, p in preds.items() if len(p) > 1)
    return heads


def to_blocks(
    graph: dict, start, *, keep_nops: bool = False, sites: dict | None = None
) -> dict:
    """Collapse the state graph into maximal straight-line blocks.

    `sites`, if given, is filled with block name -> the state each emitted op
    came from. `r`/`s` pick their pipe by the man's *cell*, which the notation
    cannot express, so a network interpreter needs this out-of-band map.
    """
    heads = leaders(graph, start)
    order = [start] + sorted(h for h in heads if h != start)
    blocks: dict = {}
    sentinels_used: set = set()

    def name_of(state):
        if state in SENTINELS:
            sentinels_used.add(state)
            return state
        return block_name(state)

    for head in order:
        block = blockgraph.Block(name=block_name(head))
        where: list = []
        state = head
        while True:
            node = graph[state]
            if node.op is not None and (keep_nops or node.op != "."):
                block.ops.append(node.op)
                where.append(state)
            if node.kind != "goto":
                block.kind = node.kind
                block.targets = tuple(name_of(s) for s in node.succs)
                break
            succ = node.succs[0]
            if succ in SENTINELS or succ in heads:
                block.kind = "goto"
                block.targets = (name_of(succ),)
                break
            state = succ
        blocks[block.name] = block
        if sites is not None:
            sites[block.name] = where
    for sentinel in SENTINELS:
        if sentinel in sentinels_used:
            kind = "wall" if sentinel == WALL else "H"
            blocks[sentinel] = blockgraph.Block(name=sentinel, kind=kind)
    return blocks


TERMINATOR = {
    "H": lambda t: "H",
    "wall": lambda t: "(wall)",
    "if-recv": lambda t: "(if-recv " + " ".join(t) + ")",
    "goto": lambda t: f"(goto {t[0]})",
    "if": lambda t: f"(if {t[0]} {t[1]} {t[2]})",
    "if-bp": lambda t: f"(if-bp {t[0]} {t[1]})",
    "if-par": lambda t: f"(if-par {t[0]} {t[1]})",
}


def serialize(blocks: dict) -> str:
    """Blocks -> block-graph source text (one block per line)."""
    lines = []
    for block in blocks.values():
        notes = "".join(f" :{k} {v}" for k, v in block.notes.items())
        parts = [f"(mark {block.name}{notes})"]
        parts.extend(block.ops)
        parts.append(TERMINATOR[block.kind](block.targets))
        lines.append(" ".join(parts))
    return "\n".join(lines) + "\n"


def decompile_man(
    machine: Machine, start, *, keep_nops: bool = False, sites: dict | None = None
) -> dict:
    """One man's `.man` geometry -> block graph, round-trip verified."""
    graph = walk_graph(machine, start)
    blocks = to_blocks(graph, start, keep_nops=keep_nops, sites=sites)
    text = serialize(blocks)
    if blockgraph.parse(text, allow_timing_ops=True) != blocks:
        raise ValueError(f"round-trip mismatch for man at {start[:2]}")
    return blocks


def decompile_machine(machine: Machine, **kwargs) -> list:
    """Every man in the machine, in `machine.men` order."""
    return [decompile_man(machine, s, **kwargs) for s in man_starts(machine)]


def walk_graph(machine: Machine, start) -> dict:
    """Reachable states -> Node. Loops close naturally; nothing is unrolled."""
    graph: dict = {}
    stack = [start]
    while stack:
        state = stack.pop()
        if state in graph:
            continue
        kind, succs = outgoing(machine, state)
        graph[state] = Node(op_token(machine, state), kind, succs)
        for succ in succs:
            if succ not in SENTINELS and succ not in graph:
                stack.append(succ)
    return graph
