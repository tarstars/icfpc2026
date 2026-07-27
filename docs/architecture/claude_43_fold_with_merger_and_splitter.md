# claude_43: folding a tall room — the complete construction, with both primitives tested

Solves the problem that killed two fold attempts. The design is complete
and both primitives it rests on are **verified empirically**, not assumed.
The remaining work is assembly, which is mechanical.

## The prize

`pathfinder_03` is 267x1130, box 1130, and its room 0 is **183x938** —
the entire height. Folding that interior with a single cut gives:

    interior 181 x 936   ->   352 x 480       (pathfinder_fold.fold_interior,
                                               one unrouted crossing at row 468)

Room 0 becomes ~354x482, so the machine box falls from ~960 to about 500:
`(500/960)^2 = 0.27`, a further **~3.7x**. Pathfinder would go from
16.07e12 this morning to roughly **1.2e12**.

## Why the fold failed twice

Folding moves the lower half of the room **+181 columns**. `r`/`s` bind to
the *nearest* pipe, and in room 0 **all eight pipe endpoints sit on row
942** (its bottom wall) at columns 92, 97, 112, 117, 152, 157, 192, 197.
Because they share a row, the Manhattan tie cancels the row term and
**binding is decided purely by column**.

The room is therefore organised in vertical lanes: cells using pipe 0 sit
near column 92, pipe 1 near 112, and so on. After a fold, a band-B cell
that was at column 92 is at 273 — past every endpoint — so it binds to
whichever endpoint is rightmost. **All band-B I/O rebinds at once.** That
is the deadlock, with the pipe multiset byte-identical throughout.

One endpoint cannot be nearest to two disjoint column clusters while seven
rivals compete. So each split pipe needs **one endpoint per band**, and
the two halves must then be reunited without breaking FIFO order.

## Measurement: only 5 of 8 pipes actually need splitting

Counting I/O cells per pipe on each side of the cut (interior row 473):

    pipe  dir   half A   half B   needs
      0   out       10       69   SPLIT
      1   out       71       42   SPLIT
      2   out       45       24   SPLIT
      3   out       27        0   half A only -- leave alone
      4   in        55       64   SPLIT
      5   in         3        0   half A only -- leave alone
      6   in        60       22   SPLIT
      7   in         5        0   half A only -- leave alone

**Three outgoing and two incoming.** And pipes **2<->4** and **1<->6** are
request/response pairs: room 0 asks rooms 1 and 3, they answer. That
matters, because a responder *can* know which band asked.

## OUTGOING: the merger room  (the user's idea)

Split pipe P into `Pa` (endpoint in band A, original column) and `Pb`
(endpoint in band B, column +181). A small merger room reads both and
emits into the real destination pipe:

    merger interior:   @ R s   in a loop

### Why order is preserved — the part that needed checking

The naive argument is "the man is in one band at a time, so only one
source is ever ready". **That is not sufficient**: band A's pipe can still
hold in-flight values while the man has moved into band B, so both inputs
can be ready simultaneously and `R`'s choice then decides ordering.

`sim.py` line 942 settles it:

    pipe = min(ready, key=lambda p: p.cells[-1])

**`R` takes the ready pipe whose entry cell is smallest in (row, col)
order** — deterministic and purely geometric. So place `Pa`'s entry cell
above (or left of) `Pb`'s, and whenever both are ready the merger drains
**A first**. Since band A is the earlier half of the program, A's values
always precede B's within a pass, and **FIFO order is preserved**.

**Verified empirically.** Two incoming pipes entering a room at (4,7) and
(5,6), both loaded, one `R` executed: it took the value from **(4,7)**,
the smaller entry cell. Ordering is controllable by geometry alone.

## INCOMING: the `U` splitter

The source cannot know which band the man is in — but for a
request/response pair it does not have to. Room 0's band A sends its
request on `2a`, band B on `2b`. The responder distinguishes them with
`U`, then replies on the matching return pipe.

**`U` turns the man away from the side of the room the pipe attaches to**
(not from the individual pipe — our old spec copy said "pipe", the live
site says "the side of the room"). So **the two request pipes must arrive
on DIFFERENT WALLS** of the responder; then the turn itself is the branch.

**Verified empirically**, both directions:

    pipe on the NORTH wall  ->  U leaves the man heading SOUTH
    pipe on the WEST  wall  ->  U leaves the man heading EAST

with the value correctly delivered (A=7) in both cases.

So the responder becomes: `U` reads the request and lands on one of two
code paths; each path computes the same answer and `s`-sends it into that
band's return pipe. The response direction needs no merger at all,
because it is already per-band.

## The full construction

1. Fold room 0's interior at the midpoint; rotate the lower band **180
   degrees** (a rotation preserves handedness — a MIRROR does not, and
   would silently reverse all 33 `X` and 33 `d` in that room).
2. Route the one remaining crossing at interior row 468.
3. Split pipes 0, 1, 2 into `Xa`/`Xb`, endpoints at column `c` and
   `c + 181` on the folded room's bottom wall.
4. Add three merger rooms (`@ R s`), each with `Xa` entering at a smaller
   (row, col) than `Xb`.
5. Split pipes 4 and 6 the same way; rework rooms 1 and 3 to read requests
   with `U` **on two different walls** and reply per band.
6. Leave pipes 3, 5, 7 untouched — they are single-band.
7. Shift rooms 1-6 up by the height saved (~458 rows) and re-route.

## Verified on the ORGANIZERS' OWN ENGINE, not just ours

This distinction matters: our simulator was proven wrong twice on
2026-07-27 -- it never implemented `Y`, and its wall rule changed
pass/fail. A design resting on `sim.py` alone is not verified.

    U, pipe on NORTH wall   WASM: dir [0,1] = SOUTH, a=7      matches sim.py
    U, pipe on WEST  wall   WASM: dir [1,0] = EAST,  a=7      matches sim.py
    R tie-break             WASM: output [7,9], status done   matches sim.py

The `R` probe is a real machine (`tests/data_fold_r_tiebreak.man`): two
values are sent into two pipes whose entry cells are (11,4) and (11,11),
the first value going to the smaller. `R` twice, then out. **Both engines
emit [7, 9]** -- the smaller-(row,col) entry drains first -- so a merger's
ordering is controllable by geometry alone.

`tests/test_fold_primitives.py` -- 7 tests, 4 against `sim.py` and 3
against the WASM, all passing.

## What is verified, and what is not

**Verified:** the fold geometry routes (one crossing short); the exact set
of pipes needing a split; `R`'s ordering tie-break, in source and by
experiment; `U`'s wall-side discrimination, in both directions by
experiment.

**Not yet verified:** that rooms 1 and 3 have two free walls each; that the
one remaining crossing routes; the assembled machine's tick cost — each
merger adds ~2-3 ticks per value, and pathfinder's score is
`footprint x ticks`, so the ~3.7x box win must not be eaten by merger
latency on a hot pipe. **Pipe 0 carries 79 sends per pass and pipes 1/2
carry 113/69** — those are the ones to watch.

## Why this generalises

This is the answer to "one endpoint cannot serve two clusters", which is
the wall every multi-band fold hits. `R` merges by geometry, `U` splits by
wall side. Together they make **room splitting** (BACKLOG B3) implementable
too, which is strictly more general than the snake line-merge because it
does not require a snake — and llm's 82x10,024 room is worth `0.0625x`
under it.
