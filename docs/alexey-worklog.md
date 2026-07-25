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

### Same day, two more rounds: 8.55M → 5.98M

**tcp_03 (7,693,504).** The tick profile of tcp_02 showed 54 ticks per
packet spent *walking* between the S zone and the V zone — the pump read
seq on the left, relayed in the middle, fetched val on the right, then
walked back left for 15-seq. Fixed in the splitter, not the pump: it now
sends `seq` on the S pipe and **`15-seq, val` on the V pipe**, so both
mid-packet reads land in the same zone. The D0 path stops needing an S
read at all, and both return paths merge into one lane. −11% ticks.

**tcp_04 (5,981,626).** Footprint was bound by width 43 against height 38.
Moved the splitter to cols 25-37, relocated O into the routing band, and
fed it from the forwarder's TOP wall next to RIN — re-auditing the
column-split zone rule first, which still separates the four `s` cells
cleanly. 38×38, a square: fp 1849 → 1444.

**Cumulative: 20,028,106 → 5,981,626, a 3.35x improvement**, all four
submissions 20/20 on the server.

Fourth trap paid for this session: a pipe cell whose *backward* neighbour
is a room wall starts a NEW pipe there. Routing one column clear of
foreign rooms avoids it — this is the same phantom-pipe failure as before,
but triggered by a room I moved rather than a route I drew.

Where the remaining time would go: 14 relays × 8 ticks = 112 ticks/packet
is the algorithmic floor for d≥1 packets; on top of that the pump still
idles ~20 ticks/packet waiting on the 42-cell S pipe, and the pump room
carries ~3 rows that hold a single cell each.

### Numbering note (2026-07-25 merge)

A teammate independently recovered these four machines from the contest
platform and committed them under numbers assigned by discovery order, so
**repo numbering is not build order** and two names collided in the merge:

| repo file | built as | score |
|---|---|---|
| tcp_01, tcp_05 (byte-identical) | tcp_01 | 52,747,176 |
| tcp_04 | tcp_02 | 8,554,029 |
| tcp_03 | tcp_03 | 7,693,504 |
| **tcp_02** | tcp_04 | **5,981,626** ← team best |

Resolved by taking the teammate's numbering for the `.man` files (their
content is byte-identical to mine, so nothing was lost, and their names
were already published and referenced), and folding my authoritative
server responses — ids, scores, tick counts — into `alexey-variants.json`,
which their copy lacked. Every entry now carries `alexeyNumbering`.
**Match these machines by score or sha256, never by file number.**

## 2026-07-25 — geometry sweep: one win, one server rule, one negative result

Goal was cheap footprint wins with no algorithm changes. Measured the whole
line first (fill density per submission, and how many places each problem's
standings move per unit of score) rather than guessing.

**Shipped: sort_06, 1,455,740 → 1,367,454 (−6%).** `sort_05` already existed
at 18×18 (fp 324, better than the live sort_03's 361) and judged 7/7 locally
— but the server refuses to load it.

**New server rule: every pipe must be at least TWO cells.** A one-cell pipe
loads with `pipe runs into a room wall — end it with an arrowhead pointing
into the room`. Our parser accepts it and the local judge then reports a
clean pass, so `sort_05` (one 1-cell pipe) and `reverse_02` (three of them,
15×15, fp 225 vs the live 256) were both built, validated and abandoned
without anyone connecting the load error to pipe length. Practical form:
**two rooms must be two cells apart, not one.** Checker:
`src/littleman/alexey_pipecheck.py` (the teammates' `server_compat` gate
covers the other two divergences but not this one).

Rerouting the input out of another wall to keep 18×18 failed for a reason
worth remembering: the ring read at rel(5,11) had exactly ONE step of
margin over the input pipe, so moving where the input entered flipped that
read and deadlocked a machine that still parsed and audited fine. Restoring
the column instead keeps sort_05's faster machine at sort_03's footprint.

Divergences run both ways: `history_00.man` is live at 7,921 yet our parser
rejects it outright (`invalid vertical literal at (20, 2)`). A local parse
failure is not evidence the server will refuse a program.

**Negative results — do not spend time here:**

* *history-lesson is already geometrically optimal.* Swept the data-row
  capacity from 78 to 91: capacities 83, 84 and 85 all give fp 7921, because
  narrowing a row adds exactly the rows it saves. 89×88 sits on the balance
  point. Only fewer literal cells (better than the current 2.2 cells/char)
  can help, and the alphabet is 71 symbols, so re-basing the radix buys
  nothing — 9 characters per 18-digit word either way.
* *brackets repacking is worth ~15-20%, not more.* It looks wasteful (50×39,
  30% fill) but CLASSIFY (20 wide) beside OPEN (22 wide) already forces
  ~46 columns, and stacking all three rooms trades that for ~47 rows. Best
  case ≈ fp 2116-2209 against 2500, which the standings turn into +1-2 places.
* *reverse_02 cannot be saved at 15×15* — the I and O gaps are exactly the
  one-cell pipes the server rejects, and widening either returns fp to 256.

Where the headroom actually is, by places gained per unit of score
(measured off the live standings): history-lesson −20% → **+22 places**
(rank 28→6, densest field in the contest), reverse-a-list −50% → +18,
memory −75% → +34, sort −50% → +11. All four need algorithm work, not
geometry.

### brackets repacked: 7,473,269 → 3,669,188 (2.04x), live 26/26

I had estimated this at 15-20% and was wrong — it is 2x, because **short
pipes buy ticks as well as footprint**. Footprint 2500 → 1764 (−29%) and
avgTicks 1506 → 1080 locally (−28%); the two multiply.

No machine logic touched. The three rooms are used verbatim, trimmed only
of provably empty edges: classify 19×20 → 19×18 (two empty right columns),
close 10×32 → 9×30 (two empty columns plus one empty interior row), open
unchanged. Trims only remove cells beyond the last used column/row, so each
walk is identical apart from being a few ticks shorter, and every port keeps
its offset relative to its own room — which is why nearest-pipe resolution
inside the rooms needed no re-derivation at all.

**Room order is what makes the routing planar.** Two pipes must cross the
whole layout: close-bottom → open-top and open-bottom → close-top. With
open in the middle (as brackets_00 had it) both wraps are long and fight for
the same corridor rows — I spent several attempts failing to route them past
each other, each time blocked by a vertical run cutting a horizontal one.
Putting **close** in the middle turns one wrap into a two-row hop and leaves
a single long pipe, which then owns the east columns (35, 36) and the bottom
row uncontested. brackets_00's 92-cell perimeter wrap becomes 89 cells of
much straighter routing, and the 45-cell one becomes 16.

Generator: `src/littleman/alexey_brackets_compact.py`, reproduces
`brackets_01.man` byte-for-byte.

Remaining headroom is small: height 42 binds against width 37, and all
three inter-room gaps are already minimal (3 rows between classify and
close for the bottom port, pipe 2 and pipe 6; 2 rows each elsewhere).
Moving open beside classify instead computes to exactly the same fp 1764.

Session total across the two geometry rounds: sort 1,455,740 → 1,367,454
and brackets 7,473,269 → 3,669,188.

### brackets, second pass: 3,669,188 → 3,494,864 (total 2.14x from 7,473,269)

Question was whether the ROOMS themselves could be compacted, keeping the
algorithm. Measured first: interiors are 75% / 67% / 75% visited, and after
the first pass's trims **no fully dead interior row or column remains** in
any of the three. The leftover blanks are all walked-over lanes or gaps
inside otherwise-used rows, so nothing more can be deleted outright.

Found one more free row anyway, in the *layout* rather than the rooms: pipe
2 (classify → close, columns 3-7) and pipe 6 (the long wrap, columns 11-35)
occupy disjoint column ranges and can share gap row 20. 37×41, fp 1681.
Live 26/26 at 3,494,864.

**Why the rooms cannot shrink further — the interesting part.** `classify`
spends ten of its seventeen interior rows on five comparison blocks, each
using one row for the block and one for the mismatch return. The obvious
move is to serpentine them — block east, block west, block east — which
would save five rows and about eight ticks per character. It does not work,
and the reason is `X`: the MATCH case always continues *straight*. A
westbound block's match arm therefore runs west, but its `s` has to reach
the OPEN port on the east wall, and at low columns that cell resolves to the
CLOSE port instead — the machine would send the token to the wrong room.

Routing the arm around to a shared send cell on the east does resolve
correctly, but it turns the per-character circuit from ~39 ticks into ~75.
Since the score is footprint × ticks, a 22% footprint gain against a ~90%
tick loss is a clear net loss. The present arm — send to OPEN immediately
after `X`, then drop down the east lane — is tick-optimal, and that is
exactly what pins the room at one block per two rows.

So: brackets geometry is now done. Height 41 binds against width 37, all
three inter-room gaps are minimal, and the rooms are at their layout floor
given the port geometry.

## 2026-07-25 — mechanical squeeze sweep: five problems improved, two up to 4.5x

Swept every live submission for pure-geometry slack. The productive find was
a transformation I had not been applying globally:

**A row whose every cell is `' '` or `'|'` can be deleted outright.** It
holds no instruction, no wall corner and no horizontal run, so dropping it
shortens by one cell every room interior and every vertical pipe it crosses
and changes nothing else — a man walks over blanks, so his path is identical
apart from being one tick shorter. Columns of `' '` and `'-'` are the
transpose. No room is re-laid, no pipe re-routed, nothing is moved.

| problem | footprint | live score | gain |
|---|---|---|---|
| sudoku-validity | 81,796 → 61,504 | 105,335,908,125 → **25,480,732,026** | 4.13x |
| plotter | 194,481 → 148,225 | 75,794,498,065 → **16,905,772,730** | 4.48x |
| gradebook | 206,116 → 178,929 | 104,303,579,600 → **81,914,188,255** | 1.27x |
| tcp | 1,444 → 1,369 | 5,981,626 → **5,655,750** | 1.06x |
| memory | 2,209 → 2,116 | 91,372,248 → **87,493,514** | 1.04x |

All five 20/20 or better on the server. Note that sudoku and plotter gained
**far more than their area** — 4.1x and 4.5x against footprint gains of only
1.33x and 1.31x. The rest came from ticks: deleting the blank rows shortened
the pipes running through them, and on those two the score is
latency-dominated. Same effect as the brackets repack.

`reverse`, `sort`, `brackets` and `history` have **zero** deletable rows or
columns. Those four are tight; do not look again.

Not unconditionally safe — always re-judge. Two failures:

* `memory` survives the row pass (7/7) but breaks on the column pass (2/7).
  Deleting a column changes Manhattan distances and therefore which pipe an
  `r`/`s` resolves to; memory has reads whose margin between two candidate
  pipes is a single step. Salvaged as rows-only.
* `matmul` breaks on both passes (0/7 full, 6/7 rows-only). Its footprint is
  width-bound anyway, so only the column pass would have paid.

Tool: `src/littleman/alexey_squeeze.py`, reproduces all five submitted files
byte-for-byte. Run `alexey_pipecheck.check` afterwards as well — squeezing
can shorten a two-cell pipe to one cell, which the server rejects at load.

Also confirmed by measurement this round, so nobody re-derives it: in every
one of the big programs the slack that remains sits in the NON-binding
dimension. matmul, gradebook and sudoku are width-bound with their spare
space in rows; plotter and memory are height-bound with theirs in columns.
That is why the remaining headroom needs re-placement, not deletion.

### Follow-up: per-room edge trimming — measured, and it is already spent

Re-checked the specific idea "each room has empty edge rows/columns that can
be trimmed", on the current (post-squeeze) submissions. Result, per program,
counting the trim available along the vertical chain (rows) and the
horizontal chain (columns), and the footprint that would result **after**
re-placing the rooms to close the gaps:

| problem | binds | row slack | col slack | gain if re-placed |
|---|---|---|---|---|
| reverse, sort, tcp, brackets, memory, sudoku | — | 0 | 0-11 | **1.00x** |
| gradebook | H | 2 | 377 | 1.01x |
| plotter | H | 2 | 8 | 1.01x |
| matmul | H | 5 | 13 | 1.03x |

**The idea is sound but already harvested.** Before the squeeze sweep these
same rooms had real edge slack — memory 6+2 columns, sudoku 13-18 per room,
plotter 30 per room. The whole-program squeeze removed it, because rooms in
these layouts are column-aligned, so a room's empty edge column usually *is*
blank across the entire program and the global pass takes it.

What is left sits in the wrong dimension. gradebook still carries **377**
trimmable columns along its horizontal chain — and gains nothing from them,
because it binds on height (423 against 386). Same for plotter and sudoku.
The only program with real row slack is matmul (5 rows, 13 columns, 1.03x),
and that is precisely the one the global squeeze could not process.

One trap found while measuring: plotter contains a room whose interior is
entirely blank and which looks like free space — it is the **LM-75 display**,
walled in `=` and `:` rather than `-` and `|`. Its blankness is the drawing
surface. The squeeze leaves it alone automatically (`:` is not in `' |'`),
but any hand-written trimmer must special-case it.

### plotter: found the real slack, and why it is reachable

Followed the "compress the rooms" idea into plotter and it leads somewhere
concrete. plotter_02 is 138×385 — height-bound — and three rooms account for
248 of those 385 rows:

| room | rows | instructions | rows carrying an instruction | **pure return rows** |
|---|---|---|---|---|
| r62-148 | 85 | 48 | 39 | **46** |
| r152-242 | 89 | 65 | 43 | **46** |
| r247-322 | 74 | 49 | 35 | **39** |

**131 of those 248 rows contain no instruction at all** — they are the
westbound return legs of a serpentine that carries work only on its
eastbound legs. The rooms are 4% filled.

The width, by contrast, is NOT waste: a cell's column selects which pipe an
`r`/`s` resolves to. Measured in r62-148: `r` at room-col 10 takes the pipe
ending (61,17), `r` at col 39 takes (61,46); `s` at col 43 takes (149,50),
`s` at col 48 takes (149,55). So the rooms are wide on purpose and columns
must be preserved.

**But the rows are free.** Every incoming pipe of each of the three rooms
lands on its top wall and every outgoing pipe leaves from its bottom wall —
one row each. The row term of the Manhattan distance is therefore identical
for all candidates and cancels: resolution depends on the column alone.
(Same property I engineered deliberately into tcp; here it is already true.)

So instructions may be moved freely between rows as long as each keeps its
column and the sequence order is preserved. Putting work on the westbound
legs too would reclaim most of those 131 rows: height 385 → ~254, footprint
148,225 → ~64,500, i.e. **~2.3x**, on top of the 4.48x already taken.

Why I stopped short of doing it: the three rooms hold 4, 2 and 2 branches
(`X`), and in a serpentine a branch's target is a geometric neighbour — CW
lands on the return row, CCW on the row above. Re-flowing the walk means
rebuilding the control-flow graph, not moving cells. That is a compiler-level
job on generated code, and worth doing as its own piece of work rather than
tacked onto a geometry pass.

### plotter_03: rooms shrunk to their content — done, and it is a no-op alone

Trimmed every plotter room past its own empty edge rows and columns, with
each attached pipe extended to reach the wall's new position. Seven rooms
shrank: five lost 8 empty left columns apiece, one lost 62, one lost 2
bottom rows — 104 edge lines. The LM-75 display is skipped; its blank
interior is the drawing surface.

**Footprint unchanged at 148,225, and the score got 0.01% worse.** Live
20/20 at 16,907,343,915 against plotter_02's 16,905,772,730 — the pipe
extensions cost 7 ticks. A narrower room still sits inside the same bounding
box, and running the global squeeze afterwards finds nothing new, because
the freed columns are only free on the small rooms' rows: the three big
rooms still occupy those columns from row 62 to row 322. plotter_02 stays
the best submission.

The value is what it opens. With the rooms trimmed, the band of rows 62-322
— where the three big rooms sit, ending at column 80 — has **columns 81-137
entirely free: 57 wide by 261 tall**. The six trimmed rooms are now at most
34 wide and total 52 rows, so they all fit there. Moving them frees rows
5-58 and 330-339 and takes the height from 385 to roughly 320:

    footprint 148,225 -> ~102,400, about 1.45x

That is the "can we move it" step, and it needs about twelve pipes
re-routed. Tool: `src/littleman/alexey_trimrooms.py`, reproduces
plotter_03.man byte-for-byte.

### plotter_04: the move — 16.9B → 9.37B (1.80x), 8.1x across the session

Moved the top block into the band that the plotter_03 trim opened. Live
20/20 at **9,367,793,668**, fp 148,225 → 106,276, ticks 114,065 → 88,146.

**It is one edit, not twelve.** The five small rooms plus I form a linear
chain — I → A → B → C → D → E → BIG1 — joined by 2- and 3-cell pipes, and
every one of those is *internal* to the block. Exactly one pipe leaves it:
E's bottom port into BIG1's top port at column 17. So the block translates
rigidly (+62 rows, +69 columns) with its plumbing intact and only that
single connection is re-drawn. Checking the pipe topology before planning
the move turned an estimated twelve re-routes into one.

The new route is long — rows 59-61 are blocked at columns 46-69 by another
pipe, so it cannot cut across and has to climb a corridor at column 82, run
west along row 1 and come back down column 17. That should have cost ticks.

**It saved them.** Straight runs are drawn with segment glyphs (`|`, `-`)
instead of arrowheads, so `alexey_squeeze` can still see through them; it
then deleted 59 rows and 25 columns, which shortened *every* pipe crossing
those rows, not only the new one. Ticks fell 23%.

Two things worth keeping from this:

* **Re-run the squeeze after moving anything.** The move alone was
  fp 148,225 → 147,456; the squeeze after it did the real work.
* **Draw straight pipe runs as segments, not arrowheads**, or the squeeze is
  blinded — my first attempt wrote `^`/`v` in every cell and collapsed one
  row instead of fifty-nine.

plotter across the session: 75,794,498,065 → 16,905,772,730 (squeeze) →
9,367,793,668 (trim + move) = **8.1x**.

### Attempted: BIG2 and BIG3 side by side — blocked by a forced pipe crossing

Tried the biggest remaining lever on plotter: put BIG2 (37 wide) and BIG3
(49 wide) side by side instead of stacked, which fits the 113-column budget
and saves 80 rows. Also relocated r265 (5×5) into the east corridor to keep
its two connections short.

**The geometry works: footprint 106,276 → 60,025, 1.77x.** The plumbing does
not, and the reason is structural rather than fiddly:

* BIG2's output port is on its **bottom** wall at column 17 (west side).
* BIG3's two input ports are on its **top** wall. Row 92 — the only row
  between the BIG1 band and the BIG2 band — is blocked at columns 25, 30 and
  44 by three existing pipes, so those ports can only be reached from the
  **east**.
* Therefore the BIG2→BIG3 pipe has to run the full width of the layout in
  the band below BIG2, from column 17 out to the east corridor.
* BIG3's output ports are on its **bottom** wall, and their targets (r271 and
  the rest of the bottom block) sit below that same band. Those pipes must
  descend **across** the horizontal run.

A horizontal run spanning columns 17-96 and a vertical run at column 46 or 85
intersect no matter which rows they use — adding routing rows cannot separate
them, because the vertical span brackets the horizontal one. Escapes checked
and rejected: routing the horizontal below the whole bottom block needs a
column free from row 92 to row 251, and there is none (BIG3, the display and
the 103-112 room between them cover every candidate); routing it over the top
needs rows 0-2, which are already full.

Fixing it means relocating r271 as well, and r271 is 23 wide against 18
columns of remaining corridor. So this needs a wider restructuring than a
move, and plotter_04 stands at 9,367,793,668.

Worth keeping: **check whether two pipes' spans bracket each other before
planning a move.** The previous block move worked because its single external
pipe had nothing to cross; this one fails on exactly that test, and the test
is cheap to run first.

### The 3-row gaps in plotter are capacity, not waste

Followed up the observation that a pipe can hug a room (as `triangle_04`
does) so rooms need not be spread apart. Wrote a normalizer that rewrites
the straight interior cells of every pipe as segment glyphs (`|`, `-`)
instead of repeated arrowheads — a run written `v v v` hides a deletable row
from `alexey_squeeze`, the same run written `v | v` does not and means
exactly the same thing.

It worked as intended: 11 cells normalized in plotter, and the squeeze then
found 3 more deletable rows, fp 106,276 → 104,329.

**And the result deadlocks, 0/6.** Not a resolution problem — I compared the
pipe every `r`/`s` resolves to, before and after, across all 181 such cells:
**zero changed**. The cause is capacity. A pipe holds as many values as it
has cells, and the squeeze shortened four of them:

    3 -> 2,  3 -> 2,  4 -> 3,  4 -> 3

Those 3-cell pipes between BIG1 and BIG2 are three cells because the
protocol needs three values in flight, and the 3-row gap exists to hold
them. It is not slack.

Nor can the capacity be kept in fewer rows: the first cell of a pipe leaving
a bottom wall is forced to point south, and the destination port's column is
fixed by resolution, so a 3-cell pipe between two vertically stacked rooms
cannot be folded sideways into a 2-row gap — it would have to re-enter a
cell it already occupies.

So plotter's remaining gaps are: 2 rows where the pipe needs 2 (minimum),
and 3 rows where it needs 3. plotter_04 (9,367,793,668) stands, and the
normalizer is worth keeping only for layouts one is *building* — draw
straight runs as segments from the start, as `alexey_plotter_move` does, so
the squeeze is not blinded later.

**Third failure mode for the squeeze, now all three are known:** it can
change pipe resolution (broke memory's column pass), it can shorten a pipe
below the two-cell minimum the server enforces, and it can shorten a pipe
below the capacity the protocol needs (this one). Judge after every squeeze.

## Baseline reset. Current live scores are the reference from here on.

    plotter 9,367,793,668 | tcp 5,655,750 | brackets 3,494,864 | sort 1,367,454
    memory 87,493,514 | sudoku 25,480,732,026 | gradebook 81,914,188,255
    triangle 832 | reverse 472,346 | history 7,921

### Requested: press the Input chain in plotter, serpentine its pipes

Done and it works — but it does not pay, measured against the baseline.

All four pipes joining the chain rooms run straight down column 61 and are
3 cells long, which is why each needed a 3-row gap. **The jog trick removes
that:** shift each next room one column right, and the pipe becomes
`down, jog east, down` — still 3 cells, still capacity 3, but in a 2-row
gap. Applied to all four gaps the chain shrinks from rows 3-61 to rows 3-57.

    6/6 public, pipe capacities preserved (3,3,3,3)
    footprint 106,276 -> 106,276      (unchanged)
    avgTicks   60,294 -> 60,322       (28 worse)

Footprint does not move because the chain sits beside BIG1, which spans rows
3-89 — 28 rows taller than the chain even before pressing. The 28 extra ticks
come from the E->BIG1 pipe, whose head had to be re-drawn 8 cells longer to
reach the trunk from the chain's new position. Not submitted.

**The technique itself is validated and worth reusing**: a 3-cell pipe fits
a 2-row gap whenever the two ports differ by at least one column, and the
port columns can be made to differ by sliding the lower room sideways —
which costs nothing, because a room's internal pipe resolution moves with
the room.

### Requested: shrink memory's rooms by deleting empty rows/columns

Two rooms have empty edges (6 and 2 columns). Trimming them:

    footprint 2,116 -> 2,116   (unchanged)
    judge      7/7  -> 2/7     (broken)

Unchanged because neither room touches the bounding box — memory binds on
height and both trims are columns. Broken for the reason already recorded
against memory's column squeeze: deleting a column changes Manhattan
distances, and memory has reads whose margin between two candidate pipes is
a single step. Not submitted; memory_02 stands at 87,493,514.

### memory: the top room's six empty columns ARE trimmable — after moving one port

The trim broke the machine (7/7 -> 2/7) for one cell only. Found it:

    read at row 4, absolute column 24 (the `r` in `srs%W`001`MN-<`)
      to the I pipe,    ending (3,5)   : 1 + 19 = 20
      to the right pipe, ending (3,44) : 1 + 20 = 21   -> I pipe wins by ONE
      to the right pipe, ending (3,38) : 1 + 14 = 15   -> flips after the trim

Moving the I *room* cannot fix it: a pipe's endpoint is pinned to the wall
it enters, not to where the source room sits. Moving the *port* can. Solving
the six reads of that room as inequalities gives a window: bring the I pipe
in through the BOTTOM wall at column 12-24. Column 14 leaves a margin of 3
instead of 1, and row 6 is clear west of column 16, so the route is
`I bottom -> (5,1) -> east along row 6 -> (6,14) north into the wall`.

Result, all six reads correct and **7/7**:

    (1,9) (1,11) (3,11) (4,24) -> I pipe        (now 15 cells)
    (1,30) (3,35)             -> right pipe     (73 cells)

Footprint stays 2,116 and ticks are flat (9,750 vs 9,750), because memory is
a 46x46 square bound by its HEIGHT: taking six columns off gives 40x46 and
max(w,h) does not move. But the step unlocks what was previously impossible
— the column squeeze now runs clean, dropping 6 columns at 7/7, where before
it broke 5 of 7 cases.

Kept as `submissions/memory/alexey-memory-trimmed-top.man` (not submitted:
same score). To turn it into a gain the height must come down from 46;
memory's rooms occupy 36 of those rows and 11 are gaps, which is where the
jog trick validated on plotter applies — slide the lower room one column so
a 3-cell pipe fits a 2-row gap. 40 wide x 44 tall would be fp 1,936.

**General rule worth keeping:** when a trim breaks a machine, do not conclude
the trim is impossible. Find the single cell whose resolution flipped, write
the room's reads as distance inequalities, and solve for a port position that
satisfies all of them. Here the feasible window was 13 columns wide.

### memory, continued: width 46 -> 40, pipes shorter than the original

Following the trim of the top room, the two pipes along the right edge were
6 cells longer than before (91->97, 67->73), and their long vertical runs
sat in columns 44-45 while columns 39-43 held only the horizontal stubs.
Squeezing those columns slides the verticals left, which shortens both pipes
past their original length and takes the file's width with them:

    width      46 -> 40
    pipe A     91 -> 87
    pipe B     67 -> 63
    judge      7/7, pipe minimum respected

Kept as `submissions/memory/alexey-memory-narrow40.man`. Not submitted: the
footprint is still 2,116 because memory is now 40 wide by 46 tall and
**height binds**. Width is no longer the constraint at all — 6 columns of
slack now sit unused.

What is left is height, and it is tight: the three gaps are 2, 3 and 2 rows
against a minimum of 2 each, so gap compression yields at most **one** row.
That one row is worth having now that width is 40 — 40x45 is fp 2,025
against 2,116, a 4.3% gain — but the 3-row gap holds a horizontal pipe run
on its middle row (26 cells), so collapsing it needs the ports on either
side realigned, not just a sideways nudge.

Beyond that, height 46 is 39 rows of rooms plus 7 of gaps; reaching 40 would
need six rows out of the rooms themselves.
