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

## Integration

The three agents do not commit; this worktree integrates them, runs the
full suite, and only then points the solver at llm. Note four failures in
`tests/test_history_81.py` are pre-existing and unrelated.

The general claim, for whoever comes next: **timing-sensitive machines
are currently 100% out of the solver's reach, and the exclusion is
near-total because the flag is layout-wide.** This is the cheapest large
capability increase available to the stack, and it composes with
`room_reflow.py` (see `claude_32` §7 for the M2 ablation this corrects).
