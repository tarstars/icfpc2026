"""Fast, bit-exact drop-in executor for `sim.Machine`.

`sim.py` is the specification; this module never changes it.  It re-uses
`sim.Machine.parse` verbatim (so loading, rooms, pipes, literals and load
errors are literally the same code) and only replaces the hot `run()` loop
with a flattened representation:

* the grid is compiled to four integer opcode arrays (one per direction),
  which folds `_literal_load`, the digit/`hdigits` test and the long
  `if/elif` character chain into a single array lookup plus an int compare;
* pipes keep the `runs` bookkeeping but drop the dense `values` list: a
  pipe is a flat `[start, end, start, end, ...]` run list plus a `deque` of
  the values in index order.  `shift()` becomes O(#runs) integer adds with
  no list slicing at all;
* man state lives in parallel lists indexed by man index, cells are dense
  interior-cell ids with a precomputed `step[d][cell]` move table (-1 means
  `sim`'s "wall" error), and directions are ints 0..3 (UP, RIGHT, DOWN,
  LEFT) so that clockwise is `(d + 1) & 3`.

Everything else -- tick order, the `heapq` wake-in-the-same-tick rule for
men unblocked by a lower-indexed man, nearest-pipe resolution, `R`/`U`
ordering, collisions, wall errors, signed-64 wrapping -- is a line-by-line
transcription of `sim._tick` / `sim._execute`.

Public entry point: `fastsim.Machine`, a subclass of `sim.Machine` whose
`run()` uses the fast path and falls back to `sim.Machine.run` if anything
about the machine is not supported.
"""

from __future__ import annotations

import heapq
import os
import re
from collections import deque

from .sim import LoadError, Machine as _SimMachine, RunResult  # noqa: F401

MASK64 = (1 << 64) - 1
SIGN64 = 1 << 63

# direction indices: 0 UP, 1 RIGHT, 2 DOWN, 3 LEFT  (clockwise order)
_DIR_TUPLES = ((-1, 0), (0, 1), (1, 0), (0, -1))
_DIR_INDEX = {t: i for i, t in enumerate(_DIR_TUPLES)}

# ------------------------------------------------------------------ opcodes
OP_NOP = 0
OP_SETDIR = 1  # 1..4 -> direction (op - 1)
OP_LIT = 5  # load precomputed backtick literal
OP_CONST = 5  # load bare digit (same handler as OP_LIT)
OP_HALT = 7
OP_M = 8
OP_W = 9
OP_ADD = 10
OP_SUB = 11
OP_MUL = 12
OP_NEG = 13
OP_MOD = 14
OP_DIV = 15
OP_AND = 16
OP_OR = 17
OP_XOR = 18
OP_SHL = 19
OP_SHR = 20
OP_X = 21
OP_SEND1 = 22  # s
OP_SENDALL = 23  # S
OP_RECV1 = 24  # r
OP_RECVANY = 25  # R
OP_RECVTURN = 26  # U
OP_Q = 27
OP_SETBP = 28  # b
OP_DECBP = 29  # m
OP_BPCW = 30  # d
OP_BPCCW = 31  # a
OP_BPSHR = 32  # ]
OP_BPBIT = 33  # x
OP_BAD = 34

_CHAR_OPS = {
    " ": OP_NOP,
    ".": OP_NOP,
    "@": OP_NOP,
    ">": OP_SETDIR + 1,
    "<": OP_SETDIR + 3,
    "^": OP_SETDIR + 0,
    "v": OP_SETDIR + 2,
    "V": OP_SETDIR + 2,
    "H": OP_HALT,
    "M": OP_M,
    "W": OP_W,
    "+": OP_ADD,
    "-": OP_SUB,
    "*": OP_MUL,
    "N": OP_NEG,
    "%": OP_MOD,
    "/": OP_DIV,
    "&": OP_AND,
    "|": OP_OR,
    "~": OP_XOR,
    "{": OP_SHL,
    "}": OP_SHR,
    "X": OP_X,
    "s": OP_SEND1,
    "S": OP_SENDALL,
    "r": OP_RECV1,
    "R": OP_RECVANY,
    "U": OP_RECVTURN,
    "q": OP_Q,
    "b": OP_SETBP,
    "m": OP_DECBP,
    "d": OP_BPCW,
    "a": OP_BPCCW,
    "]": OP_BPSHR,
    "x": OP_BPBIT,
}


class Unsupported(Exception):
    """Raised by the compiler when the fast path cannot represent a machine."""


class Program:
    """Flattened, run-ready form of a parsed `sim.Machine`.

    Cells are indexed by a dense *interior cell id* (room-major, row-major
    inside each room), not by grid position: a big layout is mostly walls
    and pipes, and indexing the whole `W * H` rectangle costs an order of
    magnitude more memory than the part a man can ever stand on.
    `step[d][cell]` is the cell a man reaches by moving one step in
    direction `d`, or -1 when that is `sim`'s "wall" error.
    """

    __slots__ = (
        "machine", "W", "H", "n_cells", "code", "lit", "step", "cellpos",
        "cellroom",
        "n_men", "mcell", "mdir", "mA", "mB", "mBP", "mhalt", "mroom",
        "n_pipes", "p_len", "p_runs", "p_q", "p_turn",
        "out_by_room", "in_by_room", "in_sorted", "near_out", "near_in",
        "out_cand", "in_cand",
        "input_pipe", "output_pipe", "display_pipes", "displays",
    )


_NONBLANK = re.compile(r"[^ .@]")


def _compile_grid(machine, bases, n_cells):
    """Four opcode arrays + four literal arrays, indexed by interior cell."""
    grid = machine.grid
    hpairs, vpairs = machine.hpairs, machine.vpairs
    hdigits, vdigits = machine.hdigits, machine.vdigits
    code = [[OP_NOP] * n_cells for _ in range(4)]
    lit = [[0] * n_cells for _ in range(4)]
    for room, base in zip(machine.rooms, bases):
        top, left, right = room.top, room.left, room.right
        width = right - left - 1
        for rr in range(room.bottom - top - 1):
            r = top + 1 + rr
            row = grid[r]
            row_base = base + rr * width
            for match in _NONBLANK.finditer("".join(row[left + 1:right])):
                ci = match.start()
                ch = match.group()
                c = left + 1 + ci
                cell = row_base + ci
                if ch == "`":
                    for d in range(4):
                        cells = None
                        if d == 1 or d == 3:
                            span = hpairs.get((r, c))
                            if span is not None:
                                a, b = span
                                if d == 1 and c == b:
                                    cells = [row[x] for x in range(a + 1, b)]
                                elif d == 3 and c == a:
                                    cells = [row[x] for x in range(b - 1, a, -1)]
                        else:
                            span = vpairs.get((r, c))
                            if span is not None:
                                a, b = span
                                if d == 2 and r == b:
                                    cells = [grid[x][c] for x in range(a + 1, b)]
                                elif d == 0 and r == a:
                                    cells = [grid[x][c] for x in range(b - 1, a, -1)]
                        if cells is None:
                            continue
                        digits = "".join(x for x in cells if x.isdigit())
                        if digits:
                            code[d][cell] = OP_LIT
                            lit[d][cell] = int(digits)
                elif ch.isdigit():
                    value = int(ch)
                    if (r, c) not in hdigits:
                        code[1][cell] = code[3][cell] = OP_CONST
                        lit[1][cell] = lit[3][cell] = value
                    if (r, c) not in vdigits:
                        code[0][cell] = code[2][cell] = OP_CONST
                        lit[0][cell] = lit[2][cell] = value
                else:
                    op = _CHAR_OPS.get(ch, OP_BAD)
                    if op != OP_NOP:
                        for d in range(4):
                            code[d][cell] = op
    return code, lit


def _layout_cells(machine, W):
    """Dense interior-cell ids: bases, cellpos, cellroom and step tables."""
    bases = []
    total = 0
    for room in machine.rooms:
        bases.append(total)
        total += (room.bottom - room.top - 1) * (room.right - room.left - 1)
    cellpos = [0] * total
    cellroom = [0] * total
    step = [[-1] * total for _ in range(4)]
    up, right_s, down, left_s = step
    for index, room in enumerate(machine.rooms, start=1):
        base = bases[index - 1]
        w = room.right - room.left - 1
        h = room.bottom - room.top - 1
        for rr in range(h):
            rb = base + rr * w
            pos0 = (room.top + 1 + rr) * W + room.left + 1
            cellpos[rb:rb + w] = range(pos0, pos0 + w)
            cellroom[rb:rb + w] = [index] * w
            right_s[rb:rb + w - 1] = range(rb + 1, rb + w)
            left_s[rb + 1:rb + w] = range(rb, rb + w - 1)
            if rr:
                up[rb:rb + w] = range(rb - w, rb)
            if rr + 1 < h:
                down[rb:rb + w] = range(rb + w, rb + 2 * w)
    return bases, total, cellpos, cellroom, step


def _pipe_state(values):
    """(flat run list, deque of values in index order) for a `Pipe.values`."""
    runs = []
    q = deque()
    for index, value in enumerate(values):
        if value is None:
            continue
        q.append(value)
        if runs and runs[-1] + 1 == index:
            runs[-1] = index
        else:
            runs.append(index)
            runs.append(index)
    return runs, q


def compile_machine(machine) -> Program:
    grid = machine.grid
    H = len(grid)
    W = len(grid[0]) if H else 0
    if W == 0 or H == 0:
        raise Unsupported("empty grid")
    P = Program()
    P.machine = machine
    P.W, P.H = W, H
    bases, n_cells, cellpos, cellroom, step = _layout_cells(machine, W)
    P.n_cells = n_cells
    P.cellpos, P.cellroom, P.step = cellpos, cellroom, step
    P.code, P.lit = _compile_grid(machine, bases, n_cells)
    room_index = {id(room): i + 1 for i, room in enumerate(machine.rooms)}
    cell_of = {}
    for index, room in enumerate(machine.rooms):
        base = bases[index]
        w = room.right - room.left - 1
        for rr in range(room.bottom - room.top - 1):
            cell_of[(room.top + 1 + rr, room.left + 1, index + 1)] = base + rr * w

    men = machine.men
    P.n_men = len(men)
    P.mcell = []
    for m in men:
        ri = room_index[id(m.room)]
        start = cell_of.get((m.r, m.room.left + 1, ri))
        if start is None:
            raise Unsupported("man outside its room interior")
        P.mcell.append(start + m.c - m.room.left - 1)
    P.mdir = [_DIR_INDEX[m.direction] for m in men]
    P.mA = [m.A for m in men]
    P.mB = [m.B for m in men]
    P.mBP = [m.BP for m in men]
    P.mhalt = [bool(m.halted) for m in men]
    P.mroom = [room_index[id(m.room)] for m in men]
    if any(m.blocked or m.wait_kind is not None for m in men):
        raise Unsupported("machine already mid-run")

    pipes = machine.pipes
    P.n_pipes = len(pipes)
    pipe_index = {id(p): i for i, p in enumerate(pipes)}
    P.p_len = [len(p.values) for p in pipes]
    P.p_runs = []
    P.p_q = []
    for p in pipes:
        runs, q = _pipe_state(p.values)
        P.p_runs.append(runs)
        P.p_q.append(q)
    P.p_turn = []
    for p in pipes:
        dr, dc = p.cells[-1]
        room = p.dest
        if dr < room.top:
            P.p_turn.append(2)
        elif dr > room.bottom:
            P.p_turn.append(0)
        elif dc < room.left:
            P.p_turn.append(1)
        else:
            P.p_turn.append(3)

    nrooms = len(machine.rooms)
    P.out_by_room = [[] for _ in range(nrooms + 1)]
    P.in_by_room = [[] for _ in range(nrooms + 1)]
    for room in machine.rooms:
        ri = room_index[id(room)]
        P.out_by_room[ri] = [pipe_index[id(p)] for p in machine.out_pipes.get(id(room), [])]
        P.in_by_room[ri] = [pipe_index[id(p)] for p in machine.in_pipes.get(id(room), [])]
    P.in_sorted = [
        sorted(idxs, key=lambda i: pipes[i].cells[-1]) for idxs in P.in_by_room
    ]
    P.out_cand = [
        [(i, pipes[i].cells[0][0], pipes[i].cells[0][1]) for i in idxs]
        for idxs in P.out_by_room
    ]
    P.in_cand = [
        [(i, pipes[i].cells[-1][0], pipes[i].cells[-1][1]) for i in idxs]
        for idxs in P.in_by_room
    ]
    P.near_out = {}
    P.near_in = {}
    P.input_pipe = pipe_index[id(machine.input_pipe)] if machine.input_pipe else -1
    P.output_pipe = pipe_index[id(machine.output_pipe)] if machine.output_pipe else -1
    P.display_pipes = [i for i, p in enumerate(pipes) if p.dest.kind == "display"]
    P.displays = []
    for disp in machine.displays:
        by_side = {}
        for p in machine.in_pipes.get(id(disp), []):
            by_side[p.side] = pipe_index[id(p)]
        P.displays.append(
            (
                disp,
                by_side.get("addr", -1),
                by_side.get("data", -1),
                by_side.get("swap", -1),
                disp.disp_w,
                disp.disp_h,
            )
        )
    return P


def _nearest_pick(cand, pos, W):
    """`sim.Machine._nearest`: min by (manhattan, seg row, seg col)."""
    if not cand:
        return -1
    r, c = divmod(pos, W)
    best = -1
    best_key = None
    for pi, sr, sc in cand:
        key = (abs(sr - r) + abs(sc - c), sr, sc)
        if best_key is None or key < best_key:
            best_key = key
            best = pi
    return best


def run_program(P, res, input_queue, controller, max_ticks):  # noqa: C901
    W = P.W
    code = P.code
    lit = P.lit
    step = P.step
    cellpos = P.cellpos
    mcell, mdir, mA, mB, mBP = P.mcell, P.mdir, P.mA, P.mB, P.mBP
    mhalt, mroom = P.mhalt, P.mroom
    p_len, p_runs, p_q = P.p_len, P.p_runs, P.p_q
    p_turn = P.p_turn
    out_by_room, in_by_room = P.out_by_room, P.in_by_room
    in_ordered = P.in_sorted
    out_cand, in_cand = P.out_cand, P.in_cand
    near_out, near_in = P.near_out, P.near_in
    input_pipe, output_pipe = P.input_pipe, P.output_pipe
    display_pipes, displays = P.display_pipes, P.displays
    heappush, heappop = heapq.heappush, heapq.heappop

    n_men = P.n_men
    wait_kind = [None] * n_men
    wait_pipes = [()] * n_men
    recv_waiters = {}
    send_waiters = {}
    runnable = set(i for i in range(n_men) if not mhalt[i])
    occupied = {}
    for i in range(n_men):
        occupied[cellpos[mcell[i]]] = i
    active = {}
    for pi in range(P.n_pipes):
        runs = p_runs[pi]
        if runs and (len(runs) > 2 or runs[-1] != p_len[pi] - 1):
            active[pi] = 1
    tick_heap = None
    processed = ()
    cur_index = -1

    out_values = res.output
    out_ticks = res.output_ticks
    frames = res.frames
    frame_ticks = res.frame_ticks
    on_frame = getattr(controller, "on_frame", None)

    def clear_wait(index):
        kind = wait_kind[index]
        if kind is None:
            wait_pipes[index] = ()
            return
        wmap = recv_waiters if (kind == "r" or kind == "RU") else send_waiters
        for pi in wait_pipes[index]:
            waiters = wmap.get(pi)
            if waiters is None:
                continue
            waiters.discard(index)
            if not waiters:
                wmap.pop(pi, None)
        wait_kind[index] = None
        wait_pipes[index] = ()

    def cond_ready(index):
        kind = wait_kind[index]
        wps = wait_pipes[index]
        if kind == "r":
            pi = wps[0]
            runs = p_runs[pi]
            return bool(runs) and runs[-1] == p_len[pi] - 1
        if kind == "RU":
            for pi in wps:
                runs = p_runs[pi]
                if runs and runs[-1] == p_len[pi] - 1:
                    return True
            return False
        if kind == "s":
            runs = p_runs[wps[0]]
            return (not runs) or runs[0] != 0
        if kind == "S":
            for pi in wps:
                runs = p_runs[pi]
                if runs and runs[0] == 0:
                    return False
            return True
        return False

    def maybe_wake(index):
        if wait_kind[index] is None or not cond_ready(index):
            return
        if mhalt[index]:
            return
        clear_wait(index)
        if tick_heap is not None and index > cur_index and index not in processed:
            heappush(tick_heap, index)
        else:
            runnable.add(index)

    def wake_recv(pi):
        waiters = recv_waiters.get(pi)
        if waiters:
            for index in tuple(waiters):
                maybe_wake(index)

    def wake_send(pi):
        waiters = send_waiters.get(pi)
        if waiters:
            for index in tuple(waiters):
                maybe_wake(index)

    def put0(pi, value):
        """`_pipe_put(pipe, 0, value)`; caller guarantees slot 0 is empty."""
        runs = p_runs[pi]
        p_q[pi].appendleft(value)
        if runs and runs[0] == 1:
            runs[0] = 0
        else:
            runs.insert(0, 0)
            runs.insert(1, 0)
        last = p_len[pi] - 1
        if len(runs) > 2 or runs[-1] != last:
            active[pi] = 1
        else:
            active.pop(pi, None)
        if runs[-1] == last:
            wake_recv(pi)

    def take_last(pi):
        """`_pipe_take(pipe, -1)`; caller guarantees the last slot is full."""
        runs = p_runs[pi]
        value = p_q[pi].pop()
        last = p_len[pi] - 1
        if runs[-2] == last:
            del runs[-2:]
        else:
            runs[-1] = last - 1
        if runs and (len(runs) > 2 or runs[-1] != last):
            active[pi] = 1
        else:
            active.pop(pi, None)
        if not runs or runs[0] != 0:
            wake_send(pi)
        return value

    verdict = None
    error = None
    ticks = 0
    for _ in range(max_ticks):
        ticks += 1
        # ---------------------------------------------------- 1. pipes shift
        for pi in tuple(active):
            runs = p_runs[pi]
            last = p_len[pi] - 1
            src_was_full = runs[0] == 0
            dst_was_empty = runs[-1] != last
            n = len(runs)
            if runs[n - 1] == last:
                moving = n - 2
                blocked_suffix = True
            else:
                moving = n
                blocked_suffix = False
            i = 0
            while i < moving:
                runs[i] += 1
                runs[i + 1] += 1
                i += 2
            if blocked_suffix and moving:
                if runs[moving - 1] + 1 == runs[moving]:
                    runs[moving - 1] = runs[moving + 1]
                    del runs[moving : moving + 2]
            if len(runs) > 2 or runs[-1] != last:
                pass
            else:
                del active[pi]
            if src_was_full and runs[0] != 0:
                wake_send(pi)
            if dst_was_empty and runs[-1] == last:
                wake_recv(pi)
        # ------------------------------------------------------------ 2. I/O
        verdict = None
        if output_pipe >= 0:
            runs = p_runs[output_pipe]
            if runs and runs[-1] == p_len[output_pipe] - 1:
                value = take_last(output_pipe)
                out_values.append(value)
                out_ticks.append(ticks)
                if controller is not None:
                    verdict = controller.on_output(value, ticks)
                    if verdict:
                        break
                    verdict = None
        if input_pipe >= 0:
            runs = p_runs[input_pipe]
            if not runs or runs[0] != 0:
                if controller is not None:
                    value = controller.pop_input()
                    if value is not None:
                        put0(input_pipe, value)
                elif input_queue:
                    put0(input_pipe, input_queue.pop(0))
        # -------------------------------------------------------- 3. execute
        tick_heap = list(runnable)
        heapq.heapify(tick_heap)
        runnable = set()
        processed = set()
        movers = []
        while tick_heap:
            index = heappop(tick_heap)
            if index in processed:
                continue
            processed.add(index)
            cur_index = index
            if mhalt[index]:
                continue
            cell = mcell[index]
            d = mdir[index]
            op = code[d][cell]
            if op:
                if op < 5:
                    d = op - 1
                    mdir[index] = d
                elif op == 5:
                    mA[index] = lit[d][cell]
                elif op == 21:  # X
                    a = mA[index]
                    if a > 0:
                        mdir[index] = (d + 1) & 3
                    elif a < 0:
                        mdir[index] = (d - 1) & 3
                elif op == 8:  # M
                    mB[index] = mA[index]
                elif op == 10:  # +
                    v = mA[index] + mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 11:  # -
                    v = mA[index] - mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 22:  # s
                    pi = near_out.get(cell, -2)
                    if pi == -2:
                        pi = _nearest_pick(out_cand[mroom[index]], cellpos[cell], W)
                        near_out[cell] = pi
                    if pi < 0:
                        error = "no-pipe"
                        break
                    runs = p_runs[pi]
                    if runs and runs[0] == 0:
                        wait_kind[index] = "s"
                        wait_pipes[index] = (pi,)
                        w = send_waiters.get(pi)
                        if w is None:
                            send_waiters[pi] = {index}
                        else:
                            w.add(index)
                        continue
                    put0(pi, mA[index])
                elif op == 24:  # r
                    pi = near_in.get(cell, -2)
                    if pi == -2:
                        pi = _nearest_pick(in_cand[mroom[index]], cellpos[cell], W)
                        near_in[cell] = pi
                    if pi < 0:
                        error = "no-pipe"
                        break
                    runs = p_runs[pi]
                    if runs and runs[-1] == p_len[pi] - 1:
                        mA[index] = take_last(pi)
                    else:
                        wait_kind[index] = "r"
                        wait_pipes[index] = (pi,)
                        w = recv_waiters.get(pi)
                        if w is None:
                            recv_waiters[pi] = {index}
                        else:
                            w.add(index)
                        continue
                elif op == 9:  # W
                    mA[index], mB[index] = mB[index], mA[index]
                elif op == 12:  # *
                    v = mA[index] * mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 7:  # H
                    mhalt[index] = True
                    continue
                elif op == 30:  # d
                    if mBP[index] > 0:
                        mdir[index] = (d + 1) & 3
                elif op == 31:  # a
                    if mBP[index] > 0:
                        mdir[index] = (d - 1) & 3
                elif op == 33:  # x
                    mdir[index] = (d + 1) & 3 if mBP[index] & 1 else (d - 1) & 3
                elif op == 29:  # m
                    v = mBP[index] - 1
                    mBP[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 28:  # b
                    mBP[index] = mA[index]
                elif op == 32:  # ]
                    mBP[index] = mBP[index] >> 1
                elif op == 13:  # N
                    v = -mA[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 14:  # %
                    b = mB[index]
                    if b == 0:
                        mA[index] = 0
                    else:
                        v = mA[index] % b
                        mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 15:  # /
                    b = mB[index]
                    if b == 0:
                        mA[index], mB[index] = 0, mA[index]
                    else:
                        qv, rem = divmod(mA[index], b)
                        mA[index] = ((qv + SIGN64) & MASK64) - SIGN64
                        mB[index] = ((rem + SIGN64) & MASK64) - SIGN64
                elif op == 16:  # &
                    v = mA[index] & mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 17:  # |
                    v = mA[index] | mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 18:  # ~
                    v = mA[index] ^ mB[index]
                    mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 19:  # {
                    b = mB[index]
                    if 0 <= b <= 63:
                        v = mA[index] << b
                        mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                    else:
                        mA[index] = 0
                elif op == 20:  # }
                    b = mB[index]
                    if b < 0:
                        mA[index] = 0
                    else:
                        v = mA[index] >> (b if b < 63 else 63)
                        mA[index] = ((v + SIGN64) & MASK64) - SIGN64
                elif op == 23:  # S
                    outs = out_by_room[mroom[index]]
                    if not outs:
                        error = "no-pipe"
                        break
                    busy = False
                    for pi in outs:
                        runs = p_runs[pi]
                        if runs and runs[0] == 0:
                            busy = True
                            break
                    if busy:
                        wait_kind[index] = "S"
                        wait_pipes[index] = tuple(outs)
                        for pi in outs:
                            w = send_waiters.get(pi)
                            if w is None:
                                send_waiters[pi] = {index}
                            else:
                                w.add(index)
                        continue
                    a = mA[index]
                    for pi in outs:
                        put0(pi, a)
                elif op == 25 or op == 26:  # R / U
                    ins = in_by_room[mroom[index]]
                    if not ins:
                        error = "no-pipe"
                        break
                    chosen = -1
                    for pi in in_ordered[mroom[index]]:
                        runs = p_runs[pi]
                        if runs and runs[-1] == p_len[pi] - 1:
                            chosen = pi
                            break
                    if chosen < 0:
                        wait_kind[index] = "RU"
                        wait_pipes[index] = tuple(ins)
                        for pi in ins:
                            w = recv_waiters.get(pi)
                            if w is None:
                                recv_waiters[pi] = {index}
                            else:
                                w.add(index)
                        continue
                    mA[index] = take_last(chosen)
                    if op == 26:
                        mdir[index] = p_turn[chosen]
                elif op == 27:  # q
                    pi = near_in.get(cell, -2)
                    if pi == -2:
                        pi = _nearest_pick(in_cand[mroom[index]], cellpos[cell], W)
                        near_in[cell] = pi
                    if pi < 0:
                        error = "no-pipe"
                        break
                    mBP[index] = len(p_q[pi])
                else:  # OP_BAD
                    error = "bad-op"
                    break
            movers.append(index)
            runnable.add(index)
        if error:
            tick_heap = None
            break
        # -------------------------------------------------------- 3b. display
        for disp, addr_pi, data_pi, swap_pi, dw, dh in displays:
            size = dw * dh
            for side, pi in ((0, addr_pi), (1, data_pi), (2, swap_pi)):
                if pi < 0:
                    continue
                runs = p_runs[pi]
                if not runs or runs[-1] != p_len[pi] - 1:
                    continue
                v = take_last(pi)
                if side == 0:
                    if not 0 <= v < size:
                        error = "display"
                        break
                    disp.cursor = v
                elif side == 1:
                    if not 0 <= v <= 15:
                        error = "display"
                        break
                    cur = disp.cursor
                    disp.next[cur // dw][cur % dw] = v
                    disp.cursor = (cur + 1) % size
                else:
                    if v != 0 and v != 1:
                        error = "display"
                        break
                    disp.current = [row[:] for row in disp.next]
                    frames.append([row[:] for row in disp.current])
                    frame_ticks.append(ticks)
                    if on_frame is not None:
                        result = on_frame(disp.current, ticks)
                        if result:
                            verdict = result
                    if v == 0:
                        disp.next = [[0] * dw for _ in range(dh)]
                        disp.cursor = 0
            if error:
                break
        if error:
            tick_heap = None
            break
        # -------------------------------------------------------- 4. movement
        for index in movers:
            if mhalt[index]:
                continue
            cell = mcell[index]
            ncell = step[mdir[index]][cell]
            if ncell < 0:
                error = "wall"
                break
            npos = cellpos[ncell]
            occupant = occupied.get(npos, -1)
            if occupant >= 0:
                mhalt[index] = True
                mhalt[occupant] = True
                runnable.discard(index)
                runnable.discard(occupant)
                clear_wait(occupant)
                continue
            del occupied[cellpos[cell]]
            mcell[index] = ncell
            occupied[npos] = index
        tick_heap = None
        cur_index = -1
        if error:
            break
        if verdict:
            break
        if not runnable and not recv_waiters and not send_waiters:
            if output_pipe >= 0 and p_q[output_pipe]:
                continue
            drained = False
            for pi in display_pipes:
                if p_q[pi]:
                    drained = True
                    break
            if drained:
                continue
            res.ticks = ticks
            res.status = "halted"
            _writeback(P, wait_kind)
            return res
    res.ticks = ticks
    if error:
        res.status = "error"
        res.error = error
    elif verdict:
        res.status = verdict
    else:
        res.status = "tick-cap"
    _writeback(P, wait_kind)
    return res


_WAIT_NAMES = (None, "r", "RU", "s", "S")


def _writeback(P, wait_kind):
    """Copy the flattened state back onto the `sim` objects."""
    machine = P.machine
    W = P.W
    for i, man in enumerate(machine.men):
        pos = P.cellpos[P.mcell[i]]
        man.r, man.c = divmod(pos, W)
        man.direction = _DIR_TUPLES[P.mdir[i]]
        man.A, man.B, man.BP = P.mA[i], P.mB[i], P.mBP[i]
        man.halted = P.mhalt[i]
        man.wait_kind = wait_kind[i]
        man.blocked = wait_kind[i] is not None
    for i, pipe in enumerate(machine.pipes):
        length = P.p_len[i]
        values = [None] * length
        runs = P.p_runs[i]
        q = list(P.p_q[i])
        k = 0
        for j in range(0, len(runs), 2):
            for index in range(runs[j], runs[j + 1] + 1):
                values[index] = q[k]
                k += 1
        pipe.values = values
        pipe.runs = [[runs[j], runs[j + 1]] for j in range(0, len(runs), 2)]
        pipe.value_count = len(q)


_ENV = os.environ.get("LITTLEMAN_FASTSIM", "1")
FASTSIM_ENABLED = _ENV not in ("0", "off", "no", "false")
USE_EXTENSION = os.environ.get("LITTLEMAN_FASTSIM_EXT", "1") not in ("0", "off", "no", "false")


def run_machine(machine, inputs=None, max_ticks=5_000_000, controller=None):
    """Run `machine` on the fast path, or on `sim` if it is not supported."""
    if not FASTSIM_ENABLED:
        return _SimMachine.run(machine, inputs, max_ticks, controller)
    try:
        program = compile_machine(machine)
    except Unsupported:
        return _SimMachine.run(machine, inputs, max_ticks, controller)
    machine._input_queue = list(inputs or [])
    machine._controller = controller
    machine._verdict = None
    res = RunResult(status="tick-cap")
    if _ext is not None and USE_EXTENSION:
        return run_program_c(program, res, machine._input_queue, controller,
                             max_ticks)
    return run_program(program, res, machine._input_queue, controller, max_ticks)


class Machine(_SimMachine):
    """`sim.Machine` with the fast `run()`.  Parsing is inherited unchanged."""

    def run(self, inputs=None, max_ticks: int = 5_000_000, controller=None):
        return run_machine(self, inputs, max_ticks, controller)


# --------------------------------------------------------------- C extension
try:  # optional; everything below falls back to the pure-Python loop
    from . import _fastsim_ext as _ext
except Exception:  # pragma: no cover - depends on whether the ext was built
    _ext = None

HAVE_EXTENSION = _ext is not None


def build_spec(P):
    """Flat, C-friendly view of a `Program` (all plain lists of ints)."""
    machine = P.machine
    nrooms = len(machine.rooms)

    def flatten(per_room):
        off = [0] * (nrooms + 2)
        idx = []
        for ri in range(nrooms + 1):
            off[ri] = len(idx)
            idx.extend(per_room[ri])
        off[nrooms + 1] = len(idx)
        return off, idx

    out_off, out_idx = flatten(P.out_by_room)
    in_off, in_idx = flatten(P.in_by_room)
    ins_off, ins_idx = flatten(P.in_sorted)
    W = P.W
    disp = []
    disp_cur = []
    disp_next = []
    for room, addr, data, swap, dw, dh in P.displays:
        disp.append([addr, data, swap, dw, dh, room.cursor])
        disp_cur.append([v for row in room.current for v in row])
        disp_next.append([v for row in room.next for v in row])
    return {
        "W": P.W, "H": P.H, "n_cells": P.n_cells,
        "code": P.code, "lit": P.lit,
        "step": P.step, "cellpos": P.cellpos,
        "mcell": P.mcell, "mdir": P.mdir, "mroom": P.mroom,
        "mhalt": [1 if h else 0 for h in P.mhalt],
        "mA": P.mA, "mB": P.mB, "mBP": P.mBP,
        "p_len": P.p_len,
        "p_runs": P.p_runs,
        "p_vals": [list(q) for q in P.p_q],
        "p_turn": P.p_turn,
        "p_src_pos": [p.cells[0][0] * W + p.cells[0][1] for p in machine.pipes],
        "p_dst_pos": [p.cells[-1][0] * W + p.cells[-1][1] for p in machine.pipes],
        "room_out_off": out_off, "room_out_idx": out_idx,
        "room_in_off": in_off, "room_in_idx": in_idx,
        "room_ins_off": ins_off, "room_ins_idx": ins_idx,
        "input_pipe": P.input_pipe, "output_pipe": P.output_pipe,
        "disp_pipes": P.display_pipes,
        "disp": disp, "disp_cur": disp_cur, "disp_next": disp_next,
    }


def run_program_c(P, res, input_queue, controller, max_ticks):
    spec = build_spec(P)
    queue = getattr(controller, "queue", None)
    if type(controller).__name__ != "RoundController" or not isinstance(queue, list):
        queue = None
    (status, error, verdict, ticks, out_values, out_ticks, frames, frame_ticks,
     mcell, mdir, mA, mB, mBP, mhalt, mwait, p_runs, p_vals,
     dcur, dnext, dcursor) = _ext.run(spec, controller, queue, input_queue,
                                      max_ticks)
    P.mcell, P.mdir, P.mA, P.mB, P.mBP = mcell, mdir, mA, mB, mBP
    P.mhalt = [bool(h) for h in mhalt]
    P.p_runs = p_runs
    P.p_q = [deque(v) for v in p_vals]
    for (room, _a, _d, _s, dw, dh), cur, nxt, cursor in zip(
        P.displays, dcur, dnext, dcursor
    ):
        room.current = [cur[r * dw:(r + 1) * dw] for r in range(dh)]
        room.next = [nxt[r * dw:(r + 1) * dw] for r in range(dh)]
        room.cursor = cursor
    res.ticks = ticks
    res.output[:] = out_values
    res.output_ticks[:] = out_ticks
    res.frames[:] = frames
    res.frame_ticks[:] = frame_ticks
    if error:
        res.status = "error"
        res.error = error
    elif verdict:
        res.status = verdict
    else:
        res.status = status
    _writeback(P, [_WAIT_NAMES[k] for k in mwait])
    return res
