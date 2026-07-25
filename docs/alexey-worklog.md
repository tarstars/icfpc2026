# Alexey research line — worklog

Append-only. Companion files: `docs/alexey-protected-files.md` (files this
line never edits), `docs/alexey-simple-model-tricks.md` (digest for
cheaper models). Focus: **space (footprint) optimization** of solved
programs.

## 2026-07-24 — sort_03: footprint 729 → 361, server score 3.46M → 1.46M

- Analyzed `sort_02` (27×24): width was driven by the ring-return pipe
  looping out to col 26 purely to reach 16 cells of capacity (n ≤ 16,
  one value per pipe cell), and by the input room sitting above a
  full-width delay corridor.
- Rebuilt the same machine compactly in
  `src/littleman/alexey_sort_ring2.py` (new file; `sort_ring.py`
  untouched):
  - input room feeds the pump's **left wall** at the entry row
    (−3 rows);
  - scan block shifted 5 columns left; climb col 10, descent col 11;
  - delay corridor reduced to 3 rows, load path joins row 3 eastbound,
    emit-climb rejoins via a straight-through `>` at (3,10);
  - relay reduced to 4×6 (2×4 interior loop; `@` placed so the man hits
    `r` before the first `s` — otherwise it injects a spurious 0);
  - ring-return folded into a 21-cell serpentine under the pump.
- Timing invariant kept (the fragile part): every circulating value must
  be inside the ring-return pipe before `q` executes. Estimated walks
  (~27 ticks post-load, ~55 ticks post-scan) vs worst transit (~19/~35),
  then verified empirically.
- Validation: 7/7 public via judge; 8 worst-shape + 300 randomized
  cases in `tests/test_alexey_sort_ring2.py`; full suite 69 passed
  (`tests/test_api_client.py` needs httpx, now installed).
- Submitted `submissions/sort/sort_03.man` (sha256 `3a56a95d…`):
  **25/25, width 18 × height 19, area² 361, avgTicks 4032.52, score
  1,455,739.72** (submission `cea48dba-bac0-4f99-bb19-7580c712535b`,
  full response in `submissions/sort/alexey-sort_03-submit.json`).
  Previous best `sort_02`: 3,460,708.8 → **2.38× better**.
- Catalogue: `submissions/sort/alexey-variants.json`.

### Environment notes (this machine)

- `uv` is not installed here; use the pyenv env `claude`
  (`pyenv local claude` is set; `.python-version` is kept out of git via
  `.git/info/exclude`, not `.gitignore`).
- Run everything as `PYTHONPATH=src python3 …` (pytest, judge CLI,
  generators). API CLI:
  `PYTHONPATH=src python3 -c "from icfpc_api.cli import main; import sys; sys.argv=['icfpc-api', …]; main()"`.
- Installed into the `claude` env: `httpx`, `typing_extensions`,
  `python-dotenv`.

### Possible next steps

- Same treatment for reverse-a-list (`reverse_00`, 28×24 → likely ≈18×19
  with the identical skeleton; server 1.95M).
- memory (67×38, score 43.8M): footprint 4489 dominates; canvas
  compaction is the big lever.
- tcp (38×41, 20.0M): ring is paired-value; same folding ideas apply.

## 2026-07-24 — merged teammates' work, pushed

- `origin/main` was 4 commits ahead (plotter v2, toolchain plan,
  littleman cookbook, synthesis stack). Zero file overlap with this
  line, so `git merge --no-ff origin/main` was clean.
- Full suite after merge: 75 passed. Pushed as `6572bea`.
- Protected-files list extended with the teammates' new files
  (`docs/littleman-cookbook.md`, `docs/toolchain-plan.md`,
  `docs/synthesis-stack.md`, `claude/plotter-plan.md`,
  `src/littleman/plotter.py`).
- The cookbook is now the authoritative semantics reference; the
  trick sheet points at it instead of duplicating register rules.

## 2026-07-24 — reverse_01: footprint 784 → 256, server score 1.95M → 472k

Generator `src/littleman/alexey_reverse2.py` (new file; `reverse.py`
untouched). Not a repack of reverse_00 — two machine changes removed the
rows, and both are reusable on any ring machine:

1. **Ring size in B, no `q`.** `q` misses values still in flight, which
   is the only reason reverse_00 carried a 4-row delay corridor. The
   pump now holds j in the off hand: `W b M` at the branch, `1 W - M`
   after the emit. Tracked counters cannot race — an early `r` just
   blocks. The decrement re-establishes B with an explicit `M`, so it
   does not depend on whether `-` preserves B (the cookbook and the
   simulator disagree there; this machine is correct either way).
2. **Test-before-relay skip loop.** `>rsv / ^ md` relays BP+1, so the
   old machine primed BP = j-2 and needed a separate j == 1 bypass lane
   plus a merge cell. Reaching the `d` first relays exactly BP times, so
   BP = j-1 covers every j including 1. Bypass lane, merge, and one `m`
   all gone.

Also: `@` moved onto an empty cell of the emit row, so the startup walk
(A=B=BP=0, heading east) falls through no-op cells into the load
prologue and no cell is spent on it; input and output both attach to the
pump's left wall; 17-cell serpentine ring-return under the pump.

- Validation: 8/8 public (avg 1162 ticks, local score 297,536), pipe
  resolution audited for all 7 send/receive cells, ring capacity
  asserted, 10 worst-shape + 250 randomized cases in
  `tests/test_alexey_reverse2.py`.
- Submitted `submissions/reverse-a-list/reverse_01.man` (sha256
  `e7666c52…`): **20/20, 16×16, area² 256, avgTicks 1845.1, score
  472,345.6** (submission `2168dd65-77a6-4168-83bc-6b2bb7d3d600`).
  reverse_00 was 1,950,905.6 → **4.13× better**.
- Catalogue: `submissions/reverse-a-list/alexey-variants.json`.

Gotcha worth repeating: the first render parsed as 5 pipes, not 4. The
ring-return's northward bend sat directly above the relay's top-left
corner, and corner attachment is legal, so the tail parsed as its own
pipe. Ending the leg one column earlier fixed it. Always assert the
pipe count.

### Next candidates

- memory (67×38, footprint 4489, 43.8M) — biggest remaining prize.
- tcp (38×41, 20.0M) — paired-value ring; both upgrades above apply,
  and its `q`-counted design has a corridor to delete.
- sort_03 could drop its corridor the same way (its ring size is also
  derivable), but the counter would have to survive the min-scan.

## 2026-07-24 — analysis: is a compacted 16-stage pipeline worth building?

Question raised: sort_00/01's systolic pipeline has 16 nearly-empty
rooms; compacted, shouldn't it beat the ring on ticks? Measured both on
identical single rounds (ticks to last output):

| n  | pipeline sort_01 | ring sort_02 | ring sort_03 |
|----|------------------|--------------|--------------|
| 1  | 1071             | 100          | 57           |
| 2  | 1119             | 202          | 135          |
| 4  | 1221             | 462          | 347          |
| 8  | 1444             | 1226         | 1015         |
| 12 | 1656             | 2274         | 1967         |
| 16 | 1877             | 3638         | 3235         |

The tick intuition is right only for n >= 12. The pipeline is linear
(53.7 ticks per token — that is one stage's cycle time, since stages run
in parallel and throughput is what matters) on top of a **1017-tick
fixed overhead** (~19 token-slots: 16 flush tokens plus the depth of the
16-stage chain). The ring is quadratic but starts near zero, so it wins
below n = 12 and loses 1.7x at n = 16. Public rounds are mixed-size, so
the average is not dominated by n = 16.

Where the 53.7 ticks go: the stage room is 14x20 with a 24-cell shared
return track (row 12 west, then col 2 north). A compact stage needs ~17
instruction cells (r, X, the reset chain `0 M 1 N s`, `-`, X, and the
three compare arms `+ s` / `+ s` / `W s + M`) plus routing, so ~30 cells
-> a 6x6 interior at best, and its return walk still costs ~10-14 ticks.
Realistic cycle: 15-20 ticks, i.e. a 3x speedup, not more.

Break-even against sort_03 (361 x 4032.52 = 1.456M):

| stage speedup | server ticks | break-even footprint | max dimension |
|---------------|--------------|----------------------|---------------|
| x2            | 2294         | 635                  | 25            |
| x3            | 1529         | 952                  | 31            |
| x4.5          | 1019         | 1428                 | 38            |
| x6            | 764          | 1904                 | 44            |

Sixteen rooms of 8x8 in a 4x4 grid with one-cell pipe gaps is already
35x35 = 1225, before the loader, gate and dispatcher (currently 12x45
and 15x56, both literal-heavy). So the achievable pair is roughly
footprint 1225-2000 at a 3x speedup = **1.9M-3.1M, worse than the
1.46M sort_03 already scores**. Winning would need footprint ~900 AND a
5x+ speedup simultaneously.

**Verdict: do not build it.** Footprint is squared and ticks are linear;
16 rooms cannot pay for themselves here. Recorded so nobody re-derives
it.

### The better lever for sort

Apply the reverse_01 treatment to the ring: no `q`, no delay corridor.
The obstacle is that sort's min-scan already uses B for the candidate
minimum, so the ring size cannot ride in B as it does in reverse_01.
Fix: circulate the count as an extra value in the ring itself — read it
first each cycle, re-send it last. That removes 3 corridor rows
(361 -> ~256-289) and the per-cycle corridor walk. Estimated score
~800-900k, i.e. 1.6-1.8x better, at a fraction of the pipeline's risk.

## 2026-07-24 — sort_04: the compacted pipeline, built and measured

Built despite the earlier analysis predicting it would lose, because the
open question was whether unseen private tests favour it. They do favour
it on ticks — and it still loses. Server results for the three lines:

| variant | footprint | server avgTicks | server score |
|---------|-----------|-----------------|--------------|
| sort_01 pipeline (baseline) | 8464 | 4587.72 | 38,830,462 |
| sort_04 pipeline (compacted) | 2500 | 2224.96 | 5,562,400 |
| sort_03 ring | 361 | 4032.52 | 1,455,740 |

So the compaction is a real **7.0x** improvement on the pipeline line,
and the speed hypothesis is confirmed more strongly on the private tests
than on the public ones: the pipeline is **1.81x faster per tick** than
the ring on the server (only 1.43x locally), which says the private
cases carry longer lists. But footprint is squared: 2500 vs 361 is a
6.9x penalty, so the pipeline lands 3.8x behind.

Break-even would need footprint <= 654, i.e. a bounding box of 25x25.
Sixteen stage rooms at 8x9 are already 1152 cells and a 25x25 box holds
625 — before the loader, the gate and 19 pipes. The gap is structural,
not a matter of more golfing.

### What made the compaction work

- **Stage 14x20 -> 8x9.** The old room lost 24 cells to a shared return
  track. Instructions were moved ONTO the vertical branch runs (the
  reset `s` and the `+ s` of the d<0 arm execute while the man walks
  north), and one `s` cell is shared by the reset path walking east and
  the d<0 arm walking north. Cycle time 53.7 -> 20 ticks per token.
- **The dispatcher room disappeared.** It only existed to broadcast n to
  the gate. Having the gate end its round by testing the sign of the
  RESET token removes the need for n, which removes the control pipe,
  which leaves every room with exactly one incoming and one outgoing
  pipe — no nearest-pipe audits anywhere in the program.
- **Vertical serpentine.** Running the chain down col 0, up col 1, and
  so on puts stage 0 and stage 15 both on the array's top row, so the
  loader and gate sit two cells from the stages they talk to. A
  horizontal serpentine strands stage 15 at the bottom-left and needs a
  program-length pipe, whose transit ticks would eat the speedup.
- **Computed constants.** HIGH = SHIFT + SHIFT via `W M +` instead of a
  second 7-cell literal.

### Settled by the way

sort_00/sort_01 have passed 25/25 on the server while relying on B
surviving `-` (their stage does `-` then `+` to restore A). So the
cookbook's sec.1 claim that `+ - * N & | ~ { } %` destroy B is wrong for
`-` at least, and the simulator's behaviour is the correct one. Machines
in this line still avoid depending on it where it is free to do so.

## 2026-07-24 — triangle: 1053 -> 891, and what 8x8 actually costs

Alexey hand-built an 8x8 triangle program, on the theory that the leaders'
832 = 64 x 13 means they fit the program into 8x8. The size is right and
the program passes, but measured on the simulator it takes 18 ticks, so
64 x 18 = 1152 — worse than the 9x9 x 13 = 1053 it was meant to beat.
It also taught me something my layout model had wrong: the I and O rooms
can sit flush against each other, sharing no gap.

Shortening both of its pipes to 2 cells (input into the right wall,
output out of the top wall into O's left wall) gives 15 ticks = **960**.
Kept as `submissions/triangle/alexey-triangle_8x8_960.man`, deliberately
NOT submitted — see below.

**Submitted instead: `triangle_02.man`, 9x9 x 11 ticks = 891** (live
19/19, submission fa4bb82f). The win is a scheduling trick, not a
geometry one: split into two rooms and let the downstream room preload
its constant while the upstream one computes.

    room A: @rM*+sH     ships n^2+n at tick 6
    room B: @1Mr}sH     loads B=1, then blocks on `r` — the wait is free

Blocking costs ticks only if the man is on the critical path, and he is
not: the three ops that set up the halving (`M 1 W`) leave it entirely.
13 ticks -> 11. This generalizes — any downstream room can prepare
constants, masks or counters during the upstream room's work.

### Why 8x8 tops out at 15 ticks

Two exhaustive searches, both worth keeping:

- **The arithmetic cannot be shorter than 9 instructions.** BFS over all
  of `M W + - * N % / & | ~ { }` and digits from (A=n, B=0), deduping by
  the signature on 12 values of n: nothing at depth 6, exactly two hits
  at depth 7 (`M * + M 1 W }` and `M * + M 2 W /`).
- **8x8 admits at most a 3x5 compute interior.** Exhaustive over room
  placements and legal pipe paths. (First version of this search was
  wrong: it let a pipe bend before its first cell's arrow direction. A
  pipe's cell i+1 is always cell i plus cell i's direction.)

In a 3x5 interior, 9 instructions need 4 turns, so `s` lands on step 14
and 15 ticks is the floor. 832 needs 13 ticks — `s` on step 12 — which
needs a 12-cell three-segment walk and therefore a 3x6 interior, and a
5x8 room does not fit in 8x8 in any layout the search found. Treat that
as "not found" rather than "impossible": the adjacency fact above shows
the model of legal layouts has been incomplete before.

## 2026-07-24 — IMPORTANT: our simulator accepts layouts the server rejects

Chasing the leaders' triangle score of 832 (= 64 x 13) turned up a
simulator/server divergence that can bite any problem, so read this
before trusting a local pass.

**Rooms may NOT share a wall.** `littleman.sim` happily parses

    +-+-+        two 3x3 rooms sharing the middle column
    |I|O|
    +-+-+

as two rooms. The server does not. Submitting an 8x8 triangle built on
that (submission 0eec139b) came back with

    loadError: pipe interrupted: expected '-' or an arrowhead to
    continue it, but found '|' at (6, 6)

(6,6) was the right wall of the shared-wall O room. The server never
detected O, so the pipe aimed at it ran on into the wall glyph. Local
result was 6/6 at 13 ticks; server result was a load error and a zero.

`src/littleman/sim.py` belongs to the shared line so this line does not
patch it — flagging it instead. Anyone relying on adjacency should give
each room its own wall, as the working programs already do.

**A '+' in the middle of a wall also splits differently.** Our parser
refuses a room whose edge carries '+' (it simply fails to find the room);
that at least fails locally rather than on the server.

### Where that leaves 832

Reaching 13 ticks needs `s` on walk step 12, so a 12-cell three-segment
walk, so a compute interior of at least 3x6 (2w + h >= 14). An exhaustive
parser-validated search over 8x8 finds exactly four layouts with a 3x6
interior and two 2-cell pipes, and **all four require rooms to share a
wall** — i.e. all four are server-invalid. Without sharing, 8x8 caps the
compute interior at 3x5, where 9 instructions need 4 turns, `s` lands on
step 14, and 15 ticks (score 960) is the floor.

So 832 is reachable neither by the single-room shape nor by a two-room
split (which needs >= 74 cells against 64 available). Either the leaders
exploit a rule this line has not modelled, or the server's room parser is
more permissive somewhere else. Best submitted remains triangle_02 at
891.

### Walk-length table (exhaustive, triangle's 9-instruction chain)

Earliest step the 9th instruction (`s`) can land on, by compute-room
interior. Ticks = that step + 1 with a 2-cell output pipe. The man always
starts heading east, so the first segment is horizontal and width is
worth twice height: the longest three-segment walk is 2*width + height - 2.

| interior (w x h) | `s` on step | ticks | fits 8x8? |
|------------------|-------------|-------|-----------|
| 6 x 3            | 12          | 13    | only with a shared wall (server-illegal) |
| 5 x 4, 4 x 5     | 13          | 14    | no — leaves <3 rows or cols for I/O |
| 5 x 3            | 14          | 15    | yes (14 legal layouts) — this is the 960 program |
| 4 x 4            | 14          | 15    | no |
| 3 x 5            | 15          | 16    | yes, but rotating loses 2 ticks |

So 960 is the ceiling for a single-room 8x8 triangle, and the rotated
3x5 interior is strictly worse than 5x3 — a narrow, tall room wastes the
eastward start.

## 2026-07-25 — triangle 832: the trailing cell was never required

Alexey proposed this compute room, and it turned out to be the whole
answer:

    +------+
    |@rM*+v|
    |s}W1M<|
    +------+

Interior 2x6, every cell on the walk, `s` on the last interior cell. The
man executes `s` on tick 12 and then steps straight into the wall on the
same tick. Our simulator calls that an error and ends the program one
tick before the value reaches the end of the output pipe, so it judges
0/6 with reason 'wall'. **The server does not**: submission c9cf76d1
returned 19/19, 8x8, avgTicks 13, **score 832**.

Wired into 8x8 as `submissions/triangle/triangle_04.man`: the 4-row band
under the room lets I sit at rows 4-6 and O at rows 5-7 — offset, which
is exactly what lets both pipes be 2-cell L-shapes.

### Why this was worth more than it looks

Requiring a cell after `s` was not a tidiness detail, it was a geometric
constraint that propagated: a spare cell forces a bigger interior, a
bigger interior needs more turns to cover, and every turn is a tick. All
the analysis above (the 2w + h - 2 walk bound, the "8x8 tops out at 960",
the search that found only shared-wall layouts for a 3x6 interior) was
correct *given that assumption* and wrong without it.

### Two server rules our simulator gets wrong, in opposite directions

1. **Shared walls**: sim accepts, server rejects (0eec139b failed to
   load). Sim is too permissive — a local pass can still fail to load.
2. **Wall step after the final `s`**: sim rejects, server accepts
   (c9cf76d1 scored). Sim is too strict — a local failure can still be a
   winning program.

`src/littleman/alexey_walljudge.py` handles case 2: same API as
`littleman.judge`, but a man who walks into a wall is halted instead of
killing the run, so the output pipe drains. Programs that pass the strict
judge also pass this one.

### Follow-up worth doing

Every program of ours that spends a cell on `H` or on a trailing cell
after its last `s` may be able to drop it, which can shrink the room and
therefore the footprint. Candidates: sort_03, reverse_01, tcp_00,
brackets_00, memory, max_00.

## 2026-07-25 — sort: the delay corridor is already minimal (negative result)

Tried the cheap win: shorten sort_03's delay corridor from three interior
rows to two. Footprint would drop 361 -> 324 (the height binds at 19).

It deadlocks — tick-cap, not wrong output, which is exactly the failure
the corridor prevents: `q` counts only values already parked in the
in-pipe, undercounts, and the scan then waits for values that never come.
Verified against a helper that reproduces the shipped sort_03 byte for
byte, so this is timing, not a wiring slip.

**The corridor is at its minimum.** Any real gain on sort needs `q` gone
entirely, with the ring size circulating as a value in the ring itself —
the same redesign tcp needs, not a quick edit. Recorded so nobody retries
the two-row corridor.

## 2026-07-25 — tcp_01: the v2 architecture works on the server, loses on ticks

Built and submitted the tag-through-ring rebuild: **20/20 live**
(submission 9f1985a4), after 6/6 public and 45/45 boundary stress locally.
The three architectural moves all held up:

- splitter feeds `seq` to the pump top and parks `val` in a pipe at the
  insert point (no register, no highway);
- the pump writes ONLY to the ring — the drain emits tags (−v data,
  −2000 loss, −3000 marker) and a forwarder room on the ring decodes
  them to OUTPUT and refills emitted slots with zeros;
- with no OUTPUT zone in the pump, phases lay out in execution order and
  the four-round routing stall never reappeared. One found bug — a
  missing `N` in the loss arm — cost one cell to fix.

**Score: 52.7M — worse than tcp_00's 20.0M.** Best-submission-counts, so
the team result is unharmed. The loss is arithmetic: 3844 footprint ×
13,722 server ticks. Ticks dominate: each packet runs three full ring
laps (rotate+lap, then the 15-relay realign) serialized against ~30
ticks of ring latency (22-cell return pipe + 8-tick forwarder loop). At
13.7k ticks no footprint under 38×38 breaks even against 20M.

The tick pass is the known next step: fold the realign's +1 offset into
the next packet's rotation count (drops a third of all relays), shorten
the forwarder loop and the return pipe. 3-4× is available there, and the
footprint has another ~2× of slack after that.

Also this session's plumbing lessons, now paid for twice: a pipe's first
arrowhead must back onto the source wall (a west-pointing start cannot
leave a bottom wall), and a route drawn over another room's wall column
mints a phantom pipe from that wall.

## 2026-07-25 — tcp_02: deleting the marker. 20.0M → 8.55M (2.34x)

**Live 20/20, score 8,554,029** (submission 12a6926b), after 6/6 public
and 46/46 boundary stress. First tcp result from this line that beats
tcp_00, and by a wide margin.

The profile of tcp_01 said where to dig: the realign was 46% of ring ops
and 28% of ticks, and the pump walked 16.5 cells per ring op against a
5-cell loop body. Both had the same root cause — the resident marker.
Every emitted value displaces the marker by one, so the marker has to be
put back, and putting it back costs a lap.

**The marker is unnecessary.** Slot w0 is *always* empty at packet start,
because every packet drains to completion. So don't store it. The ring
holds w1..w15 — 15 values, no sentinel:

- `d >= 1`: rotate d−1, pop the stale slot, push val, relay 15−d. Exactly
  16 ops, constant, and no drain at all: an off-head insert cannot fill w0.
- `d == 0`: emit val straight to the forwarder, then pop-and-emit while
  the head is positive. The forwarder's 0 refill lands at the tail, which
  is exactly where the freed window slot belongs — the invariant restores
  itself with no fixup. **An in-order packet costs two ring ops** (v2: ~36).

The two loop counts used to need a second register nobody had. Fixed in
the splitter, not the pump: it sends `seq` **and** `15−seq`, so with exp
in B the pump gets d from one `-` and 15−d from one `+`.

Measured: 1075 ring ops over the public cases vs 3204 (2.98x); forwarder
fast path 8 cells vs 28; footprint 1849 vs 3844; avgTicks 4626 vs 13722.

Three debug rounds, one lesson each:
1. A counted relay loop needs `m` inside it. `d` only *tests* the
   backpack, it does not decrement — a loop without `m` spins forever.
   The seed loop had one and terminated, which is why only the rotate and
   relay loops hung.
2. RIN must be able to park the whole ring (≥16 cells). When the pump
   idles between packets the forwarder keeps pushing; a 5-cell RIN
   blocked it, and the tag still queued behind those values was never
   decoded. Deadlock with the machine otherwise perfectly correct.
3. Mirroring a room vertically must swap `v`↔`^` — and is only safe when
   the room contains no handed op (`X`, `d`, `a`, `x`), since a mirror
   flips clockwise into counter-clockwise.

Layout trick worth reusing: **put every incoming pipe on the same wall.**
Then the row term in the Manhattan distance is identical for all of them
and the zone is decided purely by column — so a read cell's pipe no
longer depends on how deep in the room it sits. That is what made the
pump's nine `r` cells resolve correctly on the first audit.

Remaining headroom: width 43 binds the footprint while height is only 38;
repacking to width 38 gives fp 1444 (−22%).
