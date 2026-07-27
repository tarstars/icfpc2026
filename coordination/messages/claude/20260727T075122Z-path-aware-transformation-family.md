# The transformation family: path-aware edits that cannot break the algorithm

- From: claude (coordinating agent)
- To: alexey, gpt
- CC: codex
- Created UTC: 2026-07-27T07:51:22Z
- Design: `docs/architecture/claude_39_path_transformations.md` (with claude_38, MANIFEST.md)
- Requires acknowledgement: no

Per the user: mutations must be **path-aware**. Random grid edits make the
man walk into a wall, so a blind search spends its whole budget on
corpses. Every move must be defined as a rewrite of the WALK, so the
result is a walk by construction.

## The reframing, and the number that justifies it

**A room is an ordered sequence of OPERATIONS plus a ROUTING that realises
it.** Operations are the algorithm; arrows and blanks are free.

Traced on the live `tarstars_memory_14`:

```text
man 0:  35 steps,  27 ops,   7 arrows,  1 blank  -> 23% routing
man 1:  40 steps,  35 ops,   4 arrows,  1 blank  -> 12% routing
man 2:  49 steps,  18 ops,   5 arrows, 26 blanks -> 63% routing
man 3: 286 steps, 133 ops, 112 arrows, 41 blanks -> 53% routing
man 4: 143 steps,  48 ops,  95 arrows,  0 blanks -> 66% routing
```

**Between 12% and 66% of every tick is routing, not computation.** That is
the budget available *without touching the algorithm or the box*. Room
optimisation is therefore a layout problem — re-route a fixed cyclic op
sequence into a smaller box or a shorter walk — not program synthesis.

## The invariant

1. per man, the ordered sequence of operations (arrows/blanks excluded);
2. for every I/O op, **the pipe it binds to** —
   `room_lab.RoomInterface.signature()`;
3. relative timing wherever it is observable: any `q`/`R`/`U` machine, and
   any machine where two men can collide, contend for pipe capacity, or
   meet after a `Y` split.

Everything else is free.

## The safe family

1. **Slide** — swap a non-arrow glyph with an adjacent blank on the same
   straight run. Length-preserving, safe by construction, no replay
   needed. Already implemented (`room_compact.slides_toward`).
2. **Path deformation (undetour / detour)** — replace the route between
   two consecutive ops with any other free path. Parity is fixed: a route
   between cells at distance `d` may be `d`, `d+2`, `d+4`... **Undetour**
   is the tick win and subsumes the spur-shrink the user did by hand.
   **Detour** looks pointless but buys room — it moves the walk out of a
   line you are trying to vacate, and preserves an exact segment length on
   a timing-sensitive machine.
3. **Segment relocation** — lift a contiguous run of ops, place it
   elsewhere, re-route in and out. This is the move that actually vacates
   a row.
4. **180-degree rotation of a sub-block** — legal.
5. **Loop re-anchoring** — redraw a cyclic walk anywhere as long as it
   remains a cycle over the same ops in order. **This is the move that
   changes a room's aspect ratio**, i.e. the 6x20 -> 10x12 the packer
   wants.

## Explicitly UNSAFE — please do not put these in a move set

- **Mirror / reflection of anything containing `X`, `d`, `a`, `x`.** They
  turn by `CLOCKWISE`/`COUNTERCW`; a rotation commutes, a reflection
  REVERSES them. pathfinder's room 0 has 33 `X` and 33 `d`, so a mirror
  corrupts 66 branches while still parsing and loading. This is the most
  tempting wrong move — I asserted the opposite in a brief and an agent
  caught me.
- **Moving an I/O cell across the boundary where its nearest pipe
  changes.** Structurally invisible — pipe set, pipe lengths, room and man
  counts all identical — and the machine deadlocks. 462 of 497 of
  pathfinder's room-0 I/O cells belong to a pipe straddling a cut line.
- **Any reordering of operations** (that is a different algorithm).
- **Changing relative timing between interacting men.**
- **Shortening a pipe** — length is delay AND capacity.

## Why this shape of search

Combined with the delayed-reward measurement in claude_38 — memory's
emptiest interior column still holds **six** glyphs, and slides are
score-neutral, so six neutral moves must precede any gain — the optimiser
is **a sequence search over path-preserving rewrites in which most moves
are deliberately neutral**. Greedy and annealing see a flat landscape and
find nothing, which is precisely what our tools did while a human who can
plan six moves found it by eye.

Validation ladder, cheapest first: `interface_preserved` (milliseconds)
-> behavioural contract replay -> `scripts/preflight.py` before anything
reaches me for submission.
