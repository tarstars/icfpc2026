# Decompiling the `.man` corpus into block-graph notation

Work order: `docs/architecture/claude_16_decompile_workorder.md`.
Code: `src/littleman/decompile.py`, `src/littleman/blocknet.py`,
tests: `tests/test_decompile.py` (71 tests, all green).

## Headline

| | count |
|---|---|
| `.man` artifacts under `submissions/` that `Machine.parse` accepts | 59 |
| decompiled **and** round-tripped through `blockgraph.parse` | **59 / 59** |
| block graphs produced (one per man) | 2551 |
| blocks / edges / op tokens | 29272 / 38892 / 101096 |
| phase B (single man, exact vs `littleman.sim`) | **5 / 5** |
| phase C (multi-man, output sequences vs `sim`) | **46 pass, 1 diverge, 7 skip** |

`submissions/history/history_00.man` is the one allowed exception: it does
not parse locally, so it never reaches the decompiler.

## What was built

**Phase A — `decompile.py`.** The CFG node is `(row, col, heading)`, not
the cell: one cell crossed in two headings is two nodes, which is exactly
how a corridor crossing works and why the walk terminates. A state's
successor is "execute the glyph (it may set the heading), then step",
mirroring `sim`'s tick order. `X`/`d`/`a`/`x` yield all their arms —
this is reachability, not simulation, so a data-dependent branch costs
nothing. Straight chains collapse into blocks; a new `(mark ...)` starts
at the man's `@`, at every fork target and at every merge point. Loops
close as `goto`s; nothing is unrolled. Every graph is re-parsed and
compared structurally to the graph that produced it — the round-trip is
a hard gate inside `decompile_man`, not a test-only check.

**Phase C — `blocknet.py`.** N graphs, one FIFO per pipe with capacity =
the pipe's cell count, blocking `r`/`s`, round-robin block-atomic
scheduling until quiescent. Op semantics are not reimplemented: each op
is executed by handing `blockgraph.run` a one-op program and the man's
own `State`, so the two interpreters cannot drift apart. Tick counts are
never compared.

## The constructs the notation could not express

This is the most valuable output of the exercise, so it is stated in
full, including the part that was fixed mid-session.

**1. Which pipe an `r`/`s`/`q` touches — fixed upstream during this
work.** `sim` resolves those glyphs to the pipe *nearest the man's cell*.
Two pipes on one room are therefore two different channels reached by the
same glyph, and a block graph has no cells. The corpus leans on this
hard: 150 rooms have more than one incoming pipe, 161 more than one
outgoing, and 169 of the 2551 graphs (52 of 59 files) need it. The first
implementation had to carry an out-of-band `(block, op index) -> pipe`
map, i.e. the text alone was *not* a program. Commits `cb6ef6c` and
`0261e00` added the port forms `(s NAME)` / `(r NAME)` / `(q NAME)`,
plus `(wall)` and `(if-recv ...)`; the decompiler now emits ports named
by the cell where the pipe meets the room, and `blocknet` binds them from
the parsed text alone. Gap closed.

**2. A glyph the engine rejects at runtime — still open.** Two
deliberate probe artifacts (`memory/memory_05_probe_y_nav.man`,
`memory/memory_06_probe_y_collision.man`) contain `Y`, the newly
discovered Split instruction, which our `sim._execute` answers with
`bad-op`. The notation has `(wall)` for the fatal wall step but no
sibling for a fatal glyph, so the decompiler invents `(goto __badop)`
plus a `(mark __badop) H` block — a convention *outside* the notation.
Either a `(bad-op)` terminator or real `Y`/Split support is needed.

**3. Man-to-man collision — structurally inexpressible.** Two men
stepping onto the same cell halt *both* (`sim.py`, movement phase). That
is a position-level, room-global event between two programs. A block
graph has no positions and the network model has no shared room, so no
graph and no interpreter built on this notation can express it. It is not
an oversight in the decompiler: it is outside the model. Note that our
own `memory_06_probe_y_collision.man` exists to probe exactly this
behaviour, so it is live in our design space, not a curiosity.

**4. Displays — inexpressible.** A display room is fed by three
side-typed pipes (addr / data / swap), consumes one value per side per
tick, and commits a frame on the swap pipe. Nothing in the notation names
a display port or a frame, and the frame protocol is tick-level. 6
artifacts (5 `plotter`, 1 `snake`) are skipped for this reason.

**5. Expressible is not the same as patient.** After fix 1, `q`, `R` and
`U` all have notation. They still observe *timing* — occupancy, arrival
order — so their networks are not latency-insensitive and equality of
output sequences is not guaranteed by the theory. Empirically 11 of the
12 such machines agreed with `sim` anyway; `tcp/tcp_00.man` did not: on
public case 1 `sim` emits 17 values while the block network deadlocks
with 0. That single divergence is the concrete evidence that the patience
side-condition is a real constraint and not bookkeeping.

## Two honest caveats about the comparison

- `sim` aborts the whole machine on a wall error and *drops* values still
  travelling to the output room. The block model has no pipe latency, so
  the comparison adds those in-flight values back (`inflight()` in the
  test). Several triangle machines end by deliberately walking into a
  wall, so this matters.
- `subset-sum/subset_sum_00.man` (2119 men) decompiles and round-trips in
  ~45 s but is not run through phase C: `sim` advances all 2119 men per
  tick while the block network advances one man per quantum, so matching
  its tick budget costs ~10^9 Python quanta. This is an interpreter
  performance limit, not a semantic one.

## Verdict

The notation is expressive enough for our real machines. Every artifact
the engine accepts became a block graph that re-parses to itself, every
single-man machine is exactly equivalent, and 46 of 47 attempted
multi-man networks reproduce `sim`'s output sequence. What it cannot
express is the geometry-level behaviour that is not about one man's
control flow at all: collisions between men, a rejected glyph, and the
display protocol.

## Per-artifact table

Columns: rooms, men, decompiled, blocks, edges, ops, phase, verdict.
`[not patient: …]` marks a machine whose agreement is empirical rather
than guaranteed.

| artifact | rooms | men | dec | blocks | edges | ops | phase | verdict |
|---|---|---|---|---|---|---|---|---|
| `brackets/brackets_00.man` | 5 | 3 | yes | 54 | 70 | 183 | C | pass |
| `brackets/brackets_01.man` | 5 | 3 | yes | 54 | 70 | 183 | C | pass |
| `brackets/brackets_02.man` | 5 | 3 | yes | 54 | 70 | 183 | C | pass |
| `gradebook/gradebook_00.man` | 16 | 14 | yes | 286 | 386 | 2727 | C | pass [not patient: R] |
| `gradebook/gradebook_01.man` | 16 | 14 | yes | 286 | 386 | 2727 | C | pass [not patient: R] |
| `gradebook/gradebook_02.man` | 16 | 14 | yes | 286 | 386 | 2727 | C | pass [not patient: R] |
| `history/history_01.man` | 5 | 4 | yes | 12 | 12 | 813 | C | pass [not patient: R] |
| `matmul/matmul_00.man` | 58 | 56 | yes | 464 | 598 | 3415 | C | pass [not patient: R q] |
| `matmul/matmul_01.man` | 11 | 9 | yes | 34 | 42 | 409 | C | pass |
| `matmul/matmul_02.man` | 12 | 10 | yes | 35 | 43 | 419 | C | pass |
| `max-element/max_00.man` | 3 | 1 | yes | 9 | 11 | 29 | B | pass |
| `memory/memory.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/memory_01.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/memory_02.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/memory_03.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/memory_04.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/memory_05.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/memory_05_probe_y_nav.man` | 8 | 6 | yes | 33 | 40 | 196 | C | pass |
| `memory/memory_06.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/memory_06_probe_y_collision.man` | 8 | 6 | yes | 33 | 40 | 196 | C | pass |
| `memory/room-packing/alexey-memory-h33.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/room-packing/alexey-memory-narrow40.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/room-packing/alexey-memory-trimmed-top.man` | 7 | 5 | yes | 36 | 46 | 159 | C | pass |
| `memory/room-packing/alexey-memory-zig.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/room-packing/alexey-memory-zig4.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/room-packing/alexey-memory-zig5.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `memory/room-packing/alexey-memory-zig6.man` | 7 | 5 | yes | 31 | 39 | 195 | C | pass |
| `plotter/plotter_00.man` | 14 | 12 | yes | 69 | 91 | 931 | C | skip: display (frame timing) |
| `plotter/plotter_01.man` | 14 | 12 | yes | 69 | 91 | 931 | C | skip: display (frame timing) |
| `plotter/plotter_02.man` | 14 | 12 | yes | 69 | 91 | 931 | C | skip: display (frame timing) |
| `plotter/plotter_03.man` | 14 | 12 | yes | 69 | 91 | 931 | C | skip: display (frame timing) |
| `plotter/plotter_04.man` | 14 | 12 | yes | 69 | 91 | 931 | C | skip: display (frame timing) |
| `reverse-a-list/reverse_00.man` | 4 | 2 | yes | 15 | 19 | 50 | C | pass [not patient: q] |
| `reverse-a-list/reverse_01.man` | 4 | 2 | yes | 11 | 14 | 45 | C | pass |
| `reverse-a-list/reverse_02.man` | 4 | 2 | yes | 11 | 14 | 45 | C | pass |
| `snake/snake_00.man` | 11 | 9 | yes | 314 | 439 | 1117 | C | skip: display (frame timing) |
| `sort/sort.man` | 21 | 19 | yes | 197 | 267 | 609 | C | pass |
| `sort/sort_01.man` | 21 | 19 | yes | 197 | 267 | 609 | C | pass |
| `sort/sort_02.man` | 4 | 2 | yes | 20 | 26 | 65 | C | pass [not patient: q] |
| `sort/sort_03.man` | 4 | 2 | yes | 19 | 25 | 61 | C | pass [not patient: q] |
| `sort/sort_04.man` | 20 | 18 | yes | 208 | 277 | 563 | C | pass |
| `sort/sort_05.man` | 4 | 2 | yes | 19 | 25 | 70 | C | pass |
| `sort/sort_06.man` | 4 | 2 | yes | 19 | 25 | 70 | C | pass |
| `subset-sum/subset_sum_00.man` | 2121 | 2119 | yes | 25270 | 33662 | 72697 | C | skip: 2119 men exceed the interpreter budget |
| `sudoku-validity/sudoku_00.man` | 20 | 18 | yes | 98 | 121 | 913 | C | pass [not patient: R] |
| `sudoku-validity/sudoku_01.man` | 20 | 18 | yes | 98 | 121 | 913 | C | pass [not patient: R] |
| `sudoku-validity/sudoku_02.man` | 20 | 18 | yes | 98 | 121 | 913 | C | pass [not patient: R] |
| `tcp/tcp_00.man` | 4 | 2 | yes | 17 | 20 | 90 | C | FAIL sim=passed/17 net=deadlock/0 [not patient: q] |
| `tcp/tcp_01.man` | 5 | 3 | yes | 36 | 45 | 151 | C | pass |
| `tcp/tcp_02.man` | 5 | 3 | yes | 33 | 40 | 131 | C | pass |
| `tcp/tcp_03.man` | 5 | 3 | yes | 33 | 40 | 131 | C | pass |
| `tcp/tcp_04.man` | 5 | 3 | yes | 33 | 40 | 133 | C | pass |
| `tcp/tcp_05.man` | 5 | 3 | yes | 36 | 45 | 151 | C | pass |
| `tcp/tcp_06.man` | 5 | 3 | yes | 33 | 40 | 131 | C | pass |
| `triangle/alexey-triangle_8x8_960.man` | 3 | 1 | yes | 1 | 0 | 14 | B | pass |
| `triangle/triangle.man` | 3 | 1 | yes | 1 | 0 | 12 | B | pass |
| `triangle/triangle_02.man` | 4 | 2 | yes | 2 | 0 | 12 | C | pass |
| `triangle/triangle_03.man` | 3 | 1 | yes | 2 | 1 | 12 | B | pass |
| `triangle/triangle_04.man` | 3 | 1 | yes | 2 | 1 | 12 | B | pass |
