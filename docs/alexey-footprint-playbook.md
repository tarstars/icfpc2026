# Footprint playbook — the moves that are always right

Written 2026-07-26 by the alexey line, as the durable base for this work.
Self-sufficient on purpose: a fresh session (or a different model) should be
able to open this file and continue without re-reading anything else.

Score is `max(width, height)^2 x avgTicks`. **Only the larger dimension is
paid for.** A move that shortens the shorter side buys nothing today — but it
is still correct, because it becomes a win the moment a neighbour moves into
the space. That is the whole spirit of this file: *these moves are right even
when the score does not move yet.*

## The method (do not skip this)

**Move one thing, judge, record, then move the next thing relative to that.**
Never design the final layout and never argue that the target is impossible
before trying — I wrote a structural proof that reverse could not reach 13x13
and it was wrong; six small moves got there, and the move that mattered
(step 2) made the score *worse* at the time it was made.

Working shape: one experiment folder per program, one `.man` per step, a
`STEPS.md` note per step, and a `check()` helper that runs every gate and
prints one line. See `experiments/alexey-reverse06/` and
`experiments/alexey-brackets04/`.

## The always-correct moves, in order

### 1. Delete empty rows and columns

`alexey_squeeze(text, rows=True, cols=True)`. **It shortens every pipe it
crosses, and that is a behaviour change when the pipe stores.** claude's
measured counterexample (2026-07-26): squeezed snake passes 5/5 public and
looks 1.16x better, but its ring lost capacity and the adversarial
maximal-growth game fails at snake length 68 where the live artifact passes.
My subset-sum data point is the same class: the full squeeze shortened 118
pipes (39,755 -> 20,305 cells) while looking structurally identical.

So the acceptance rule is: **diff the pipe-length multiset before accepting
a squeeze** (`alexey_resolveaudit.structure` prints it). If no pipe shrank,
the squeeze is free. If any pipe shrank, run the occupancy probe: peak well
under the new length -> the pipe is transport and the squeeze also buys
ticks; peak near the new length -> re-prove capacity adversarially, and
never on the public suite alone.

**Re-run it after EVERY move.** It is exhausted for a *layout*, never for a
*program*: it found nothing on brackets_04, and 3 rows + 2 columns on the same
program once three rooms and four pipes had shifted. My own notes used to say
"brackets is tight, do not look again" — that was true of the layout only.

Column deletion changes Manhattan distances and therefore nearest-pipe
resolution; if the full pass fails, fall back to rows-only or cols-only.

### 2. Delete the whitespace at a room's edge

Interior blank rows/columns are pure cost. Safe to delete when every pipe on
that room meets the same pair of walls (all top/bottom ⇒ rows are free; all
left/right ⇒ columns are free). Otherwise re-audit every `r`/`s` in the room,
because nearest-pipe resolution reads those distances.

### 3. Press rooms together

- **Flush an I/O room against the machine** by bending its pipe into a SIDE
  wall instead of dropping it into the roof. A roof drop needs two cells below
  the machine; a side entry needs one cell plus a bend, so the room climbs two
  rows.
- **Two rooms may touch** (adjacent walls are distinct cells; only *shared*
  cells are illegal). A gap column between two rooms is only needed if a pipe
  must pass between them — so first check whether that pipe can leave through
  the roof or the floor instead. Giving a room **two free rows above it** lets
  its pipe leave through the ROOF, and that is what makes the gap column
  disappear. This is the single highest-value move in the file.
- **The shift ladder** for a width-bound program: move the widest room one
  column toward the wall, fold the pipe that was climbing past it into the
  freed column, measure, repeat. Measure every rung — brackets paid at shifts
  1, 2, 3 and *regressed* at 4, because the next pipe terminal would have
  needed column 0 and the box grew west instead.
  Keep every pipe's attachment cell at the same offset *inside* the moved
  room — nearest-pipe resolution reads those cells. A room with a single
  outgoing (or incoming) pipe is the free variable that makes the jog
  possible, because its resolution cannot be ambiguous.

### 4. Pipe length: the rule cuts both ways

A pipe is simultaneously **a delay line** and **a buffer** — one value per
cell, one cell per tick.

- **Where the pipe is a data path, shorter is faster.** Every cell is a tick
  of latency on every value that crosses it.
- **Where the pipe is storage, length is capacity, and shortening it
  deadlocks the machine with no other symptom** — it simply stops. Ring
  machines (reverse, sort, tcp) park a whole frame in the ring.
- So when re-laying, **preserve the total length**: `alexey_piperoute`'s
  `route_via(..., target=N)` inflates a shortest path back to exactly N cells
  with two-cell bumps. Same length ⇒ identical tick counts, which also makes
  the step trivially reviewable.
- Length can be moved *between* pipes of one ring: reverse_07 shortened the
  return leg and lengthened the inbound leg to compensate.
- **A longer pipe can be faster.** reverse_07's ring-out went 11 -> 13 cells
  and got 0.6% quicker, because the extra parking removed blocking upstream.
- **Measure capacity, do not guess it.** Patch the simulator to sample the
  occupancy of the ring pipes every tick and take the peak on the worst case
  (reverse_07: peak 16 against capacity 19, on three consecutive n=16 rounds).
  The old ">= 15 cells" rule of thumb was wrong in both directions.
- **Measure occupancy BEFORE preserving length.** The same probe on brackets
  showed peak 10 against 78 cells: that pipe was transport, not storage, and
  16 cells of "carefully preserved capacity" were pure latency. Shortening
  65 -> 49 was the first tick win of the day (-3%). `target=` is for pipes
  that store; carriers should be as short as the pinned geometry allows.

## Gates every candidate must pass before it is submitted

Run all of these on every step, not just the last one:

1. `Machine.parse` succeeds and the **pipe count is exactly what you drew**.
   One extra pipe means a bend went flush against a wall (see traps).
2. Every pipe is **>= 2 cells** — the server rejects one-cell pipes.
3. **No shared walls** (`server_compat.find_shared_walls`). Two rooms may
   touch, but they may not share a wall cell: the server sees only one room
   and the pipe aimed at the other fails to load.
4. **Exactly one pipe against the input room.** Adjacency, not endpoints —
   a pipe merely *passing* an input room's wall counts as a second connection
   and the server rejects the program 0/0. Output rooms are exempt (tcp_06 is
   live with two pipes against its output wall).
5. Every `s`/`r`/`q` resolves to the intended pipe — assert it empirically
   with `_nearest_outgoing`/`_nearest_incoming`, never by hand arithmetic.
6. All public cases pass, plus a fuzz at the constraint boundary (every
   length, extremes, every legal round count) — geometry changes shift walk
   timing, and a machine can pass 9/9 and still deadlock at max size.

## Traps already paid for (do not rediscover)

- **A bend flush against a wall becomes a phantom pipe.** A pipe starts at any
  arrowhead adjacent to a room border pointing *away* from it. Keep bends one
  cell clear of every foreign wall; only the two endpoints may touch.
  Corollary: `route_safe` refuses *every* arrowhead beside a room, which is
  stricter than the rule — an arrow pointing *along* or *into* the wall is
  fine, so short jogs can be hand-placed and audited.
- **Erase a pipe BEFORE moving a room onto its cells**, or the room's wall
  glyph is deleted by the erase and the program stops parsing.
- **Two pipes jogging the same way between the same two walls collide.** Send
  one along row N and the other along row N-1.
- **A pipe leaving a room's roof needs two free rows**: the first cell must
  point away from the room, and a bend needs its own cell.
- A dead arrow glyph left over from an old route is harmless but confusing —
  reverse_06 carried one for a day.

## Where this has been used

| program | before | after | factor |
|---|---|---|---|
| reverse-a-list | 117,214 (15x15) | **84,922** (13x13) | 1.38x |
| brackets | 836,345 (35x30) | **615,565** (30x27) | 1.36x |

Both are pure footprint — the tick averages never moved.

## Next target (handed over by the claude line, 2026-07-26)

**subset-sum**, `submissions/subset-sum/subset_sum_00.man`: 4046 x 3029,
fp 16,370,116, 2121 rooms, 2164 pipes, **1.5% non-blank**. Room boxes are
14.9% of the bounding box; a perfect pack of the room area is ~1354x1354, so
the mechanical ceiling is ~9x on footprint alone. Live 91,769,596,778,390,
rank 44/65. Caveat: one local judge run is 15m25s (48.9M ticks) — use the C
fastsim (44s) or the Rust executor for iteration, and only confirm with the
real judge.

## The cheap oracle: audit resolution statically instead of judging

`src/littleman/alexey_resolveaudit.py` (added 2026-07-26). On a big program a
judge run is minutes to a quarter of an hour, which kills the step ladder. But
if the room and pipe counts are unchanged, the only thing a row/column
deletion or a re-route can break is **which pipe an instruction resolves to**.

Rooms and pipes leave the parser in reading order, which a deletion preserves,
so room *i* before is room *i* after. `compare(before, after)` walks every
`s`/`S`/`r`/`R`/`U`/`q` cell in each room's own reading order and reports any
that changed pipe. Identical maps ⇒ identical behaviour.

    ok, diffs = compare(before_text, after_text)      # 68 s on subset-sum
    structure(text)                                   # rooms/pipes/men/lengths

Use it as the gate between steps, and spend the real judge only on the
candidate you intend to submit.

**It immediately paid for itself on subset-sum**: the full squeeze looked like
a free 2.36x (fp 13,293,316 -> 5,635,876, structure identical: 2121 rooms,
2164 pipes, 2119 men) and the audit showed it was not free at all —

* one room's `r` cells changed which pipe they read, and
* **118 pipes changed length**, total pipe cells 39,755 -> 20,305.

The second one is the pipe-length rule biting: on a program with 2048 systolic
cells you cannot assume a shorter pipe is harmless. Always print the
before/after pipe-length vector, not just the box.
