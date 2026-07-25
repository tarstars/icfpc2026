# Folding rooms: a recipe for shrinking littleman geometry

Score is `max(w, h)² × avgTicks`. Everything here attacks the first factor
without touching the algorithm: same instructions, same order, same tick
count — just laid out in fewer cells. All of it was worked out on `memory`
in July 2026 and is reproducible from `submissions/memory/room-packing/`.

The central observation: **our rooms are mostly air.** A sweep of the best
live program for every problem gives instruction density (instruction cells
÷ interior cells):

| problem | best file | w×h | densest room | sparsest big room |
|---|---|---|---|---|
| memory | memory_06 | 34×32 | 0.59 | 0.16 |
| brackets | brackets_02 | 37×41 | 0.28 | 0.24 |
| sort | sort_06 | 19×18 | 0.24 | — |
| tcp | tcp_06 | 37×37 | 0.27 | 0.13 |
| plotter | plotter_04 | 113×326 | 0.33 | **0.01** |
| sudoku | sudoku_02 | 184×248 | 0.03 | **0.01** |
| gradebook | gradebook_02 | 386×423 | 0.02 | **0.00** |
| matmul | matmul_02 | 183×185 | 0.10 | **0.01** |
| history | history_01 | 89×89 | **0.94** | 0.11 |

`history` is a data table and is genuinely full. Everything else is 60-99%
empty. That is the whole opportunity.

---

## 0. Before anything: know which dimension you are paid for

`max(w, h)²`. Shrinking the *short* side buys nothing. Check first:

- `memory` 34×32 — **width** binds; two columns off the right edge → 1024.
- `brackets` 37×41 — **height** binds; four rows off → 1369.
- `plotter` 113×326, `sudoku` 184×248, `gradebook` 386×423 — height, by a
  mile, and the height is three or four enormous sparse rooms stacked.
- `tcp` 37×37 — square; both must come down together or nothing happens.

A fold that shrinks the non-binding side is still worth doing and worth
committing — it is **banked, not cashed**. It becomes a win the moment a
neighbouring block moves into the space you freed. Do not skip a cheap fold
because it does not move the number today.

---

## 1. Read the room before you touch it

```python
from littleman.sim import Machine
m = Machine.parse(open(path).read())
```

For each room collect four numbers. They decide which recipe applies.

**Instruction cells** — interior cells that are not `' '`, `'@'`, or a turn
glyph `<>^v`. This is the payload you must fit.

**Branch count** — cells in `dXax`. Zero means the room is straight-line
code and folds trivially (§3). One means §4. More than one needs thought.

**In/out pipe counts.** A room with exactly one incoming and one outgoing
pipe has **port freedom**: nearest-pipe resolution has nothing to choose
between, so every `r` hits the one inbound pipe and every `s` the one
outbound pipe no matter where you put them. You may move the ports to any
wall and re-lay the interior with zero resolution risk. This is the single
most useful precondition — check it first.

With two or more pipes on a side, re-audit every read and write after the
fold:

```python
man = type('M', (), {'r': row, 'c': col, 'room': room})()
m._nearest_incoming(man)   # or _nearest_outgoing for an s cell
```

**Turn count.** A room with far more turns than instructions (plotter's
87×36 room has 174 turns and 48 instructions) is a long thin corridor
walked back and forth. Those fold the hardest but pay the most.

---

## 2. Extract the instruction sequence by walking the room

Never read the room row by row — read it the way the man does.

```python
DIR = {'>': (0,1), '<': (0,-1), 'v': (1,0), '^': (-1,0)}
r, c = position_of('@'); d = (0, 1)          # the man always starts facing EAST
seq = []
while inside_interior(r, c):
    r, c = r + d[0], c + d[1]
    ch = grid[r][c]
    if ch in DIR: d = DIR[ch]
    elif ch not in ' @': seq.append(ch)
```

Stop when you revisit a cell — that is the loop closing. Keep backtick
literals whole as single tokens: `` `21` `` is four cells that must never
be split across a row boundary or written backwards.

If the walk returns fewer cells than the room visibly contains, **the room
branches** and your walk only followed one arm. Find the `d`/`X` and trace
the other side by hand. That is exactly how block 1 of `memory` was caught.

---

## 3. Straight-line rooms: fold the width, keep the height

The `memory` block 2 case. No branches, one pipe each way.

Keep the **same number of interior rows** and the **same port rows**, and
re-deal the instruction cells evenly across those rows in boustrophedon
order. Because the height and the port rows do not move, neither pipe needs
re-routing — you only extend the pipe that used to meet the old right wall.

```
before   4×29                          after   4×21
+---------------------------+          +-------------------+
|>@Mrsr-M`34`W%srM1  ...    |          |>@Mrsr-M`34`W%srM1v|
|^ ...                      |          |^ WsrsrsrM%W`43`M+<|
+---------------------------+          +-------------------+
```

Two rules when dealing cells into rows:

- A row walked **westbound** holds its instructions in reverse, and any
  multi-digit literal inside it is written reversed too (`` `43` `` is 34).
  Single digits and ops are direction-neutral.
- Never split a backtick literal across a row.

**Why width-only.** Folding into fewer, longer rows is tempting but it
moves the ports off their rows and forces you to re-route every attached
pipe — which is where the deadlocks live. Trading height for width also
usually makes the *binding* dimension worse. Fold one dimension at a time.

## 4. Rooms with one branch: use the perimeter as the corridor

The `memory` block 1 case: body is `PREFIX(19) d ARM(4)`, two arms of four
cells each.

`d` **turns clockwise only**. On an eastbound row that means south. So the
`d` must sit on an eastbound row whose row below is *not* part of the main
corridor — otherwise the main pass walks straight through the arm's cells
and executes them.

Make the corridor the **perimeter**: row 1 eastbound, right column down,
bottom row westbound, left column up. Everything inside the loop is then
off-corridor and free for the arm:

```
+---------------+
|> `21`*sMd0sWsv|   <- eastbound: prefix tail, d, then the BP==0 arm
|^        >rsWsv|   <- inside the loop: the BP>0 arm, reached by d going south
|^MWss/W3Mrbsr@<|   <- westbound: prefix head. @ marks the loop-body start
+---------------+
```

Three things make it work:

**Converge on the corner.** Both arms end at the top-right corner cell,
which is `v`. The straight path arrives heading south and is passed
through; the arm arrives heading east and is turned south. After that cell
the two paths are literally the same cells.

**The loop body may be rotated, and `@` marks the rotation point.** The
corridor executes `X · d · ARM · Z`; the truth is `PREFIX · d · ARM`. If
`@` sits at the start of the westbound row, everything west of it runs
first and row 1 runs the rest, so `PREFIX = Z · X` — a legal rotation.
Cells **east of `@`** on the westbound row must stay empty; anything there
would run *after* the arm instead of before it.

**Balance the halves.** Row 1 needs `|X| + (branch arm) + 3` columns, the
westbound row needs `|Z| + 3`, with `|X| + |Z| = |PREFIX|`. Equalise them.
For block 1: `|X| = 7`, `|Z| = 12` → interior 15, room 17, down from 29.
The 12/7 split landed exactly between two tokens, so no literal broke.

**Starting direction.** The man always starts facing east. Put `@` at the
east end of the westbound row and let him bounce off the corner `<`: one
wasted tick, zero wasted cells.

## 5. Pressing rooms together (herringbone)

Two rooms may not **share** a wall, but their walls may sit on **adjacent
rows** as long as they share no cell. Offset the lower room sideways so it
overhangs; the pipe then leaves through the overhang into a side wall and
you get a zero-gap join with a 2-cell pipe.

Every pipe must be **at least two cells** — the server rejects one-cell
pipes at load time even though our simulator accepts them. Run
`littleman.alexey_pipecheck.check` before every submission.

## 5a. Ask first whether the *pipes* are the problem

Before folding anything, compare the bounding box of the **rooms alone**
against the program's box. Measured 2026-07-25:

| problem | program | rooms only | pipes cost |
|---|---|---|---|
| matmul | 183×185 | 109×144 | **1.55×** |
| brackets | 37×41 | 35×38 | 1.16× |
| sudoku | 184×248 | 184×248 | 1.00× |
| plotter | 113×326 | 113×324 | 1.01× |
| gradebook | 386×423 | 385×423 | 1.00× |

matmul was paying 55% of its footprint for three delay pipes (268, 334, 106
cells) that wandered out to col 182 and row 184, plus an `O` room parked in
the far corner with nothing near it. Re-routing them inside the rooms' own
box, at their exact original lengths, took the score from 33.29B to 21.48B
without touching a single instruction.

For the other four the rooms *are* the box, so only folding pays. Run this
check first — it costs thirty seconds and it decides the whole approach.

### Lane assignment is the hard part of a multi-pipe re-route

Pipes cannot cross. When several leave the same wall and some have to end up
on the far side of the others, the ordering is forced: **the pipe exiting
furthest in the direction of travel must take the shallowest lane, and each
one further along must go deeper.** In matmul three pipes leave adjacent
bottom walls at cols 77, 85, 91 and two of them finish west of col 77; the
only arrangement that works gives p16 (col 77) rows 145-150, p17 (col 85)
the far corridor plus row 151, and p18 (col 91) everything east.

Print a free-cell map of the target region before routing. matmul's
`(134,74)` turned out to be reachable only through a two-column gap between
two rooms — three-cell pipes at cols 76, 84 and 90 sealed rows 134-136
completely, and no amount of re-routing was going to get through them.

### When a layout is simply blocked

`brackets` shows the other outcome. Its two wrap-around pipes (88 and 59
cells) hold col 36 and row 40, and the 1.16× is real — but the left column
strip is reachable only through rows 19-20, and pipe1 must occupy a cell in
cols 3-7 there to connect its two fixed ports. Rows 30-31 are sealed the
same way by pipes 3 and 4. So collecting that 1.16× means re-routing **all
six** pipes at once, not two. Recorded here so nobody re-derives it.

## 5b. All pipes on one wall is a licence to delete

The layout rule of §5a's sibling (put every incoming pipe on the same wall,
so the row term cancels and the zone is decided by column alone) is normally
used when *designing* a room. It is just as useful as a **safety proof**:

> If every pipe attached to a room meets its top or bottom wall, then
> deleting an empty interior **row** cannot change any `r`/`s` resolution.
> If they all meet the left or right wall, the same holds for **columns**.

matmul's room0 has eighteen pipes and every one is on the bottom wall, so
the ten empty rows inside it could be deleted outright — worth 21609 →
20164 with no audit needed. Check this before trimming any room; without it
a trim is a gamble.

Two further rules learned the same day:

* **Never terminate a pipe in a one-cell gap between two rooms.** Both rooms
  claim the cell and the parser emits a spurious one-cell pipe from the
  wrong room. Enter through a different wall.
* `alexey_squeeze` is now **exhausted on every live program** — the sweep on
  2026-07-25 found deletable lines only in matmul (15 columns, which do not
  pay because height binds). Do not spend time re-running it hopefully;
  re-run it only after you have moved something.

## 6. Magnetising

Trim a room down to its content, then slide its attached pipes into the
columns you freed. The pipes come out *shorter* than they started and the
bounding box follows them in. `littleman.alexey_trimrooms` does the trim;
the pipe slide is by hand.

---

## Re-routing a pipe after a fold

When the fold deletes the wall a pipe was attached to, the pipe must move.
Two hard constraints:

**Pipe length is buffer capacity.** Shortening a pipe below what the
protocol needs deadlocks the machine with no other symptom. When you
re-route, *keep the old cell count* unless you have a reason not to. Block
1's outgoing pipe went from a straight 10-cell drop to a 10-cell dog-leg
around block 2 — deliberately the same length.

**Redraw every pipe of a moved room in one pass**, with a per-cell
collision assert. Redrawing only some of them silently drops the pipe count
(7 → 6) and the machine fails instantly rather than deadlocking. This
mistake was made three times before the pattern was recognised.

Draw straight runs with segment glyphs `-` and `|`, arrowheads only at
corners and at the terminal cell. Repeated arrowheads along a straight run
blind `alexey_squeeze`, which is looking for rows of only `' '`/`'|'` and
columns of only `' '`/`'-'`.

---

## The verification loop — run all four, every time

```python
from littleman.alexey_pipecheck import check          # 1. server pipe rule
from littleman.alexey_walljudge import judge_problem  # 2. all cases pass
from littleman.alexey_squeeze  import squeeze         # 3. free rows/cols
```

1. `check(text)` — no pipe under two cells.
2. `judge_problem(text, problem)` — full pass, and **compare the per-case
   tick lists to the source**. A correct fold is behaviour-neutral: block 1
   and block 2 both reproduced 263/613/1591/1141/1567/911/22919 exactly.
   A tick change means the walk changed, which means you got something
   wrong even if the cases still pass.
3. `squeeze` afterwards — a fold often frees whole rows or columns.
4. `alexey_squeeze` is **not** unconditionally safe; if the column pass
   breaks cases, fall back to rows-only.

## The next target, already surveyed: plotter's staircase rooms

`plotter` is 113×326 and the height is three rooms — 87, 91 and 76 rows —
with instruction densities of 0.01–0.02. Their shape is a boustrophedon that
spends **two rows per instruction**:

```
row A:   .....v(16) ................. <(36)     <- westbound, no instructions
row B:   .....>(16) r(17) ........... v(36)     <- eastbound, ONE instruction
row C:   ...............v(29) ....... <(36)
row D:   ...............>(29) s(30) .. v(36)
```

Two facts make this foldable, and both are already verified:

1. **Rows are free, columns are not.** Each of these rooms has two incoming
   and two outgoing pipes, and every `r` splits between the two inbound and
   every `s` between the two outbound — so the columns carry meaning. But
   room(3,7)'s inbound pipes both land on **row 2** (cols 17 and 21) and its
   outbound pipes both leave on **row 90** (cols 25 and 30). Same wall each
   way ⇒ the row term cancels ⇒ **zone is decided by column alone.** An
   instruction may be moved to any row as long as it keeps its column.
2. Consecutive instructions whose columns increase can share one eastbound
   row: rows B and D above collapse to `>(16) r(17) ... s(30) ... v(36)`.
   The `>` at col 29 was only a turn glyph and is not needed.

The prologue of room(3,7) walks
`r@17 b r@17 s@30 r@17 s@25 r@17 s@25 r@17 s@25 r@17 s@30 r@17 s@30 r@17
s@30 d ...` — alternating left-zone reads and right-zone writes, which is
exactly the increasing-column pattern that collapses. Expect roughly a 2×
fold on the linear stretches.

**Why it was not done on 2026-07-25.** Deleting the freed rows *globally*
is not available: rows 8-61 also carry five small rooms at cols 59-92, which
a whole-program row delete would destroy. So the fold has to be room-local —
shrink the room, then move everything below it up and re-route the pipes
that cross. That is the matmul job again, at three times the size. The
router is in place for it; budget a session, not an hour.

`sudoku` (25.5B, rooms 82×87, 82×90 and 96×104 at density 0.01) and
`gradebook` (81.9B, four rooms of 199×94 at density 0.02) are the same shape
of problem and the same order of payoff.

## What does not work — do not re-derive

- Folding a branching room into a plain serpentine. Every cell of a
  serpentine corridor is on the main pass, so a branch target always
  collides with it. You need off-corridor space: §4.
- Putting the branch arm on a row the return path crosses. The return pass
  executes it.
- Mirroring a room vertically without swapping `v`↔`^`, and mirroring at
  all when the room contains a handed op (`X`, `d`, `a`, `x`) — a mirror
  turns clockwise into counter-clockwise.
- Trading height for width (or back) when the traded-into dimension is the
  binding one.
