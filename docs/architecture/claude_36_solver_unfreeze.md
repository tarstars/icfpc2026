# claude_36: unfreezing the layout solver on timing-sensitive machines

Status: decomposed and in build, 2026-07-27 ~04:45Z.

## The diagnosis, measured

M2 concluded that L0 placement was exhausted. That conclusion came from
tcp, plotter and matmul — machines that are *already tight*, where port
freedom gives identical diameters. It was the wrong sample. The machines
where placement has enormous slack are the giant sparse ones, and on
those the solver is not exhausted: **it is frozen, by two
over-approximations that compound.**

### 1. `Conn.exact` is layout-wide, not per-pipe

`layout_ir.py` (~line 149) sets `exact=timing`, where `timing` is true if
**any** room anywhere contains a timing op (`q`, `R`, `U` —
`TIMING_OPS`, line 35). One `q` in one room marks every pipe in the
machine length-exact.

### 2. An exact LENGTH is modelled as an exact DISTANCE

`layout_solve.py` (~line 332) then emits, per exact pipe:

    model.Add(dist == conn.length - 1)      # dist = |dr| + |dc|

That is a category error. A grid path between two cells at Manhattan
distance `d` can have length `d`, `d+2`, `d+4`, … — every detour adds two
cells. Requiring the *distance* to equal `L-1` pins the geometric
relation between the two rooms, rather than merely requiring that a path
of `L` cells exists.

### What that costs, on the live little-little-man machine

    llm_codex_01:  145 rooms, 231 pipes, timing_sensitive = True
      rooms actually containing q/R/U .....   2 of 145
      pipes touching one of those rooms ...   6 of 231
      pipes marked exact .................. 231 of 231

231 simultaneous exact-distance equalities. The placement cannot move at
all. Six pipes needed the constraint.

### Why this machine is the prize

    749 wide x 25,797 tall     box 25,797     1.17% occupancy
    total room area 2,858,685 + 65,166 pipe cells = 2,923,851
    perfect-square side 1,710
    BUT the tallest single room is 82 x 10,024

It is a *column* of 145 rigid rooms with 25,000 columns of free width.
Pure re-placement — no reflow, no new geometry — is bounded below by that
10,024-tall room, giving box ~10,024 and taking the score
`8.78e15 -> 1.33e15`, which clears a rank on its own. Combined with
`room_reflow.py` folding that one room, the floor drops to about box
2,000, worth roughly +0.2.

## The decomposition

Three packages, each owning **one source file** so they can run in
parallel without collision, and each with an acceptance test that does
**not** depend on the other two being built. (An earlier decomposition of
mine failed exactly there: a package whose "done" depended on an unbuilt
neighbour is not a package.)

### A — per-pipe timing classification  (`layout_ir.py`)

A pipe is length-exact only if its source or destination room actually
contains a timing op. `Layout.timing_sensitive` stays as-is; other code
reads it.

*Accepts when*: byte-exact round trip still holds; llm goes 231 -> 6; a
machine with no timing ops has zero exact pipes; one where every room has
them has all pipes exact.

### B — parity relaxation  (`layout_solve.py`)

Replace the equality with `dist <= conn.length - 1` **and**
`conn.length - 1 - dist == 2*k`, `k >= 0` integer.

*Accepts when*: for `L-1 = 4`, distances 4/2/0 are feasible and 3/1 are
not (proving the constraint was relaxed, not deleted); a placement the
old equality rejected is now accepted with the same endpoints.

Independent of A: `conn.exact` is a plain bool however it is set.

### C — coil to an exact length  (`layout_route.py`)

Today the router *detects* a length mismatch and gives up
(`if conn.exact and len(path) != conn.length: fail`, ~lines 132 and 402).
It should repair: insert two-cell detours beside the path until the
length matches.

    coil_to_length(path, target, blocked) -> path | None

*Accepts when*: distance-4 path coils to exactly 7 and 9 with endpoints
fixed and no repeats; an odd shortfall returns None; a hemmed-in path
returns None rather than colliding. **Never shorten a path** — length is
delay *and* capacity, and a short pipe deadlocks silently.

Independent of A and B: it is a pure function on a grid.

## PREREQUISITE FOUND DURING INTEGRATION: the IR is not faithful

While verifying package A I checked `render(parse(t)) == t` across every
artifact under 400 KB. **76 of 88 round-trip byte-exact; 12 do not.**

    history_04 / _05 / _06     differ by 4,507 / 4,313 / 4,221 cells
    matmul_00 / _01 / _02      PARSE FAIL (IndexError, ragged lines)
    history_00                 PARSE FAIL (LoadError)
    reverse_03 / _04 / _05     differ by 1 cell each
    tarstars_sort_09           differs by 1 cell
    alexey-triangle_8x8_960    differs by 14 cells

These are **pre-existing** — confirmed by running the same check against
`HEAD`'s `layout_ir.py` — and package A did not cause any of them.

The single-cell cases are instructive. In `tarstars_sort_09`, line 16 is

    original  |+-+ >-----^v|^r <|
    rendered  |+-+ >-----^ |^r <|

`parse` drops the `v` at column 11: it attributes that cell to neither a
room nor a pipe, and `render` writes pipes from their stored cells, so
the glyph vanishes. Two adjacent counter-running pipe cells (`^` beside
`v`) are enough to lose one.

**Why this gates everything above.** The solver's entire contract is
"parse to rigid rooms + connections, re-place, re-emit". If `parse` loses
a cell, the re-emitted machine is missing an instruction — and it will
still parse, still load, and fail only in the judge, or worse, pass the
public cases and fail a hidden one. **A round-trip check must run before
any solver output is trusted**, and `layout_gate.py` should refuse a
machine whose IR does not reproduce its input. Until then the solver is
only safe on the 76.

Notably `history_06` is our LIVE 81-square, and it loses 4,221 cells.

## THE MISSING HAND-OFF: a fold must export its pipe bindings

The pathfinder fold was built and it **hangs** — 0/7, every case
tick-cap. This is not a bug in the implementation; it is a property of
the language, and it kills the naive approach outright.

The candidate was structurally perfect: 545x809 (box 813, down from
1873), parses as 7 rooms / 11 pipes / 5 men exactly like the original,
and its pipe-length multiset is **identical** —
`[2,3,3,3,3,10,10,23,35,142,146]`, nothing shortened.

Traced against the original, the program man executes an **identical
glyph sequence for 145 steps** and then:

    step 145   orig (14,97) 'r' A=16   |  fold (22,459) 'r' A=16
    step 146   orig (14,98) ' ' A=1    |  fold (22,459) 'r' A=16  BLOCKED
    ...        (continues)             |  (blocked forever)

Both machines reach the same `r`. The original's read succeeds; the
folded one blocks for ever, and eventually **all five men are blocked on
`r`** — total deadlock.

### Why

`r` receives from the **nearest incoming pipe**, and `s` sends to the
nearest outgoing one. `sim.Machine._nearest` picks by Manhattan distance
from *the man's own cell* to the pipe endpoint, tie-broken by absolute
coordinates. So **an `r`/`s` cell's binding is a function of where that
cell sits.**

Folding relocates interior cells — in this case by up to 362 columns —
and therefore **silently rebinds every `r` and `s` to a different pipe**.
Room #0 contains roughly 209 `r` and 288 `s`. The pipes are untouched;
the *bindings* are destroyed.

### This is a missing hand-off, not a dead end

The fold operated at the wrong level of abstraction: it moved cells while
treating the pipes as fixed furniture. But **which pipe an I/O cell binds
to is derivable before the move, and the placer already owns port
positions** — M2 made ports solver variables (`claude_32` §7). So the
fix is to carry the binding upward as a constraint rather than hope it
survives:

1. **`room_reflow` exports a binding map.** For each `r`/`R`/`s`/`S`/`U`
   cell in the ORIGINAL room, record which pipe `_nearest` resolves it
   to. That map is the room's I/O contract and it is invariant under the
   fold — it says what the folded room still needs to be true.
2. **`layout_solve` consumes it as constraints.** For every I/O cell at
   its new position, require that the intended pipe's port is strictly
   closer (Manhattan, with the same absolute-coordinate tie-break) than
   every other port on that room. These are ordinary linear constraints
   over port variables the model already has.
3. **Where one room's bands cannot share a port, split the pipe.** A
   per-band stub gives each band a local endpoint. That changes the pipe
   count and lengths, so it needs its own capacity argument — never
   shorter than the original.

Step 1 is small and mechanical; step 2 is the real work and reuses the
port machinery. Doing them in that order also makes the failure loud
instead of silent: with the binding map in hand, a fold can *check*
whether it preserved bindings before anyone spends a judge run.

Recording this so the next attempt starts from the constraint rather
than rediscovering it after building a 434 KB artifact.

## Integration

The three agents do not commit; this worktree integrates them, runs the
full suite, and only then points the solver at llm. Note four failures in
`tests/test_history_81.py` are pre-existing and unrelated.

The general claim, for whoever comes next: **timing-sensitive machines
are currently 100% out of the solver's reach, and the exclusion is
near-total because the flag is layout-wide.** This is the cheapest large
capability increase available to the stack, and it composes with
`room_reflow.py` (see `claude_32` §7 for the M2 ablation this corrects).
