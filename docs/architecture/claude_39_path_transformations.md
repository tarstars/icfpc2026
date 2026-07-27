# claude_39: the transformation family — path-aware edits that cannot break the algorithm

Status: design, 2026-07-27. Companion to `claude_38` (the Rust optimizer)
and `docs/MANIFEST.md`. This defines *what the optimizer is allowed to do*.

## The reframing that makes everything else easy

**A room is an ordered sequence of OPERATIONS plus a ROUTING that realises
it on the grid.** The operations are the algorithm. The routing — arrows,
blanks, the shape of the walk — is free.

Measured on the live `tarstars_memory_14`, tracing every man:

    man 0:  35 steps,  27 operations,   7 arrows,  1 blank  -> 23% routing
    man 1:  40 steps,  35 operations,   4 arrows,  1 blank  -> 12% routing
    man 2:  49 steps,  18 operations,   5 arrows, 26 blanks -> 63% routing
    man 3: 286 steps, 133 operations, 112 arrows, 41 blanks -> 53% routing
    man 4: 143 steps,  48 operations,  95 arrows,  0 blanks -> 66% routing

**Between 12% and 66% of every tick is spent routing rather than
computing.** That is the budget a re-routing optimiser is playing for, and
it is available without changing the algorithm or the box at all.

So room optimisation becomes a well-posed problem: **re-route a fixed
cyclic operation sequence into a smaller box and/or a shorter walk.** That
is a layout problem, not a program-synthesis problem, and it is exactly
the kind of thing MCTS or annealing eats.

## The invariant a transformation must preserve

1. **Per man, the ordered sequence of operations executed.** Arrows and
   blanks are not operations; they are routing.
2. **For every I/O operation, the pipe it binds to.** `r`/`R` read from the
   *nearest incoming* pipe and `s`/`S` write to the nearest outgoing one,
   by Manhattan distance from the man's own cell — so moving an I/O cell
   can silently rewire the machine. Check with
   `room_lab.RoomInterface.signature()`.
3. **Relative timing, where timing is observable.** Two cases: machines
   containing `q`/`R`/`U` read pipe state and are timing-sensitive
   everywhere; and *any* machine where two men can interact (collide,
   contend for a pipe's capacity, or meet after a `Y` split) can change
   behaviour if their relative arrival times move. When in doubt, preserve
   segment lengths exactly rather than merely the sequence.

Everything else — where cells sit, the shape of the walk, the box — is
free.

## The safe family

### 1. Slide (length-preserving)
Swap a non-arrow glyph with an adjacent blank **on the same straight run**
of the walk. The man traverses the same cells in the same order and
executes the same instructions; only the position within the run changes.
Ticks identical. Safe by construction — no replay needed.
*Implemented: `room_compact.slides_toward`.*

### 2. Path deformation — detour and undetour (THE core move)
Between two consecutive operations, replace the connecting route with any
other free path. Parity is fixed: a route between two cells at Manhattan
distance `d` can be `d`, `d+2`, `d+4`, ... so a deformation changes the
tick count by an even number.

- **Undetour** (shorten): the tick win. Subsumes the "shrink a spur"
  transformation the user performed by hand — 12 cells, 3 rows, 2.71%
  fewer ticks on memory.
- **Detour** (lengthen): looks pointless but is not. It buys *room* — it
  moves the walk out of a row or column you are trying to vacate, and it
  is how you preserve an exact segment length on a timing-sensitive
  machine after moving something else.

### 3. Segment relocation — "move parts of code"
Lift a contiguous run of operations, place it elsewhere, re-route in and
out. Order preserved, so the algorithm is preserved. This is the move that
actually vacates a row, and the one that needs the most collision care.

### 4. Rotation of a sub-block by 180 degrees
Legal. **A mirror is NOT.** `X`, `d`, `a`, `x` turn by
`CLOCKWISE`/`COUNTERCW`; a rotation commutes with both, a reflection
reverses them, silently turning every conditional branch the wrong way.
pathfinder's room 0 holds 33 `X` and 33 `d`, so a mirror there would
corrupt 66 branches while still parsing and loading. An agent caught this
in a brief of mine that had asserted the opposite.

### 5. Loop re-anchoring
A cyclic walk may be redrawn anywhere on the grid provided it remains a
cycle visiting the same operations in the same order. This is the move
that reshapes a room's aspect ratio — the 6x20 into 10x12 that the packer
wants.

## Explicitly UNSAFE — do not put these in the move set

- **Mirror / reflection of anything containing `X`, `d`, `a`, `x`.** See
  above. This is the single most tempting wrong move.
- **Any reordering of operations.** Not a routing change; a different
  algorithm.
- **Moving an I/O cell across the boundary where its nearest pipe
  changes.** Structurally invisible: pipe set, pipe lengths, room count
  and man count all stay identical and the machine deadlocks. This is
  exactly how the pathfinder fold died — 462 of 497 of that room's I/O
  cells belong to a pipe whose cells straddle a cut line.
- **Changing relative timing between interacting men**, or any timing at
  all on a `q`/`R`/`U` machine.
- **Shortening a pipe.** Length is delay *and* capacity; a shortened
  storage pipe deadlocks with no other symptom and still passes the public
  tests.

## How to represent it

Extract, per man, `[(operation, route_to_next)]` — the algorithm as a list,
the routing as spans. Then:

- a **transformation** is a rewrite of the routing spans;
- the **op list is the invariant**, compared directly;
- **fitness** is `max(w, h)` first, then total route length (ticks), then a
  reward for a `w x h` not yet in the library;
- **validation** is `room_lab.interface_preserved` (milliseconds) then the
  behavioural contract (a replay), then `scripts/preflight.py` before
  anything is submitted.

## Why this specific family and not "random edits"

A random grid edit almost always makes the man walk into a wall or onto a
bad op, so a blind search spends all its time on corpses. Every move above
is **path-aware**: it is defined as a rewrite of the walk, so the result is
a walk by construction. The search then only has to check the three
invariants above rather than rediscover basic viability, and the whole
budget goes into exploring shapes.

Combined with the delayed-reward finding in `claude_38` — memory's
emptiest column still holds six glyphs, so several score-neutral moves must
precede any gain — this gives the optimiser its shape: **a sequence search
over path-preserving rewrites, where most moves are deliberately neutral.**
