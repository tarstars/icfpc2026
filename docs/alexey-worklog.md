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

### memory: bottom room's ports belong on the right wall — 12.6% is there, one bug away

The bottom room (rows 38-42, cols 5-23 in `alexey-memory-narrow40.man`) has
**exactly one incoming and one outgoing pipe**. With one pipe of each
direction, nearest-pipe resolution is trivial — every `r` takes the only
incoming, every `s` the only outgoing — so **the wall those ports use is
free to choose**. That is the observation that unlocks this.

Both pipes currently leave through the left and bottom walls and loop
through rows 43-45, which is why those three rows exist at all. Routing both
through the RIGHT wall instead, into the six columns freed by the earlier
trim, removes them:

    46 rows -> 43 rows,  footprint 2,116 -> 1,849   (-12.6%)

Geometry confirmed by construction. Not finished: the incoming pipe's
terminal cell fails to trace — `bad pipe glyph '|' at (41,23)`, where column
23 is the room's right wall and the pipe's last cell sits correctly at
(41,24) pointing west. Ran out of session budget before isolating it.

State to resume from: `alexey-memory-narrow40.man` (40x46, 7/7, live-equal
score), plus this routing:

    OUT: (40,24) east to col 38, north col 38 to row 4, west into (3,37)
    IN : (1,37) east to col 39, south col 39 to row 41, west into (41,24)
    then delete rows 43-45

If the shortened pipes turn out to break capacity (63->53 and 87->58), pad
them with a serpentine in the free columns 25-38, which is where the room
trim left room to do it.

### memory_03 shipped: 87,493,514 -> 75,823,407 (1.15x), live 24/24

The tracing bug was mine, not the parser's: the outgoing pipe ran east to
column 38 and its last horizontal cell pointed straight into the incoming
pipe's vertical at column 39, so the two merged. Turning north one column
earlier fixes it. With that, all three steps land:

    trim the top room's six empty columns   (needs the I port moved to the bottom wall)
    slide the right-edge verticals inward   width  46 -> 40, pipes 91->87 and 67->63
    both bottom-room ports to its right wall  height 46 -> 43, rows 43-45 deleted

    footprint 2,116 -> 1,849      score 87,493,514 -> 75,823,407      7/7 local, 24/24 live

The shortened pipes (63->53, 87->58) turned out not to need the serpentine
padding I had prepared — capacity was not binding here.

**The three ideas that made it work, in the order they matter:**

1. A room with exactly ONE incoming and ONE outgoing pipe can put its ports
   on any wall — resolution is trivial when there is nothing to choose
   between. This is what freed three whole rows.
2. When a trim flips one read, solve the room's reads as distance
   inequalities and move the *port*, not the room. An endpoint is pinned to
   the wall it enters, so moving the source room does nothing.
3. After trimming a room, the pipes that were attached grow; sliding their
   long runs into the freed columns makes them shorter than they started and
   takes the bounding box with them.

## CORRECTION: memory's real baseline is ~27.8M, not 87M

A teammate's packed-storage memory machine scores ~27.8M live and **was not
in the repository** — it existed only on the contest server. Committed now as
`submissions/memory/memory_04.man`.

    memory_04 (theirs)   37x37   fp 1,369   ticks 4,159 local
    memory_03 (mine)     40x43   fp 1,849   ticks 9,760 local

So the whole memory thread — 91.4M -> 87.5M -> 75.8M — was geometry applied
to the pipeline-ring line, which had already been beaten threefold by a
different algorithm. The work was sound and the techniques it produced are
reusable, but it moved a number that no longer mattered.

**Geometry has nothing to give on memory_04**: squeeze (rows, columns, both)
and the per-room edge trim all return it byte-identical. It has no empty row,
no empty column, no trimmable room edge, and it is a perfect 37x37 square, so
both dimensions bind at once.

Process lesson, and the expensive one: **the public standings lag badly.**
They still showed 91,372,248 for memory while two better submissions of mine
were already live, and they still show pre-squeeze numbers for sudoku,
plotter and gradebook. I had been treating them as current. Before optimising
anything, confirm the baseline from the submit responses — and ask the team
what is live but uncommitted, because a machine can be on the server with no
copy in git at all.

### memory_05: offset-stacking removes the gap entirely — 27.8M -> 26,272,620

Alexey's idea, and it beats the rule I thought was a floor. I had concluded
that two stacked rooms need a 2-row gap: they cannot share a wall (1 row) and
a pipe cannot be shorter than 2 cells (a second row). Both premises hold; the
conclusion does not.

**Offset the lower room horizontally.** Then its top wall and the upper
room's bottom wall sit on ADJACENT rows and share no cell, which is legal —
and the pipe leaves through the overhang, where the upper room has columns
the lower one does not, then turns into the lower room's SIDE wall:

    block1 rows 0-4  cols 6-34
    block2 rows 5-8  cols 8-36     (down 2, right 2 -- walls adjacent, no shared cell)
    pipe   (5,6) v -> (6,6) > -> (6,7) >  into block2's left wall at (6,8)

Zero gap rows, 3-cell pipe. Works because both blocks have exactly one
incoming and one outgoing pipe, so their ports are free to move.

    fp 1,369 -> 1,296   (37x37 -> 36x36)   live 24/24   27.8M -> 26,272,620

One trap: moving a room means re-routing BOTH its pipes. Redrawing only the
incoming one left the outgoing pipe dangling at the old port and the machine
failed instantly (0/7, 2 ticks) — the pipe count silently dropped from 7 to
6, which is the tell.

Only blocks 1-2 are joined so far. Blocks 3, 4 and 5 are still on 2-row gaps
and each has exactly one pipe in and one out, so the same move applies; each
should give another row or two.

### memory: block 3 herringboned onto block 2 — height 37 -> 33, but width now binds

Same move as blocks 1-2, mirrored: block 3 keeps its own columns (6-31) while
block 2 sits at 8-36, so block 3 overhangs to the LEFT and block 2 to the
RIGHT — a herringbone. That lets the pipe be just **2 cells**: down out of
block 2's right overhang, then west into block 3's right wall.

    block2 rows 5-8  cols 8-36
    block3 rows 9-15 cols 6-31
    pipe   (9,32) v -> (10,32) <   into block3's right wall at (10,31)

7/7, and after squeezing: **36 x 33**, height down from 37.

**Footprint unchanged at 1,296** — width 36 now binds against height 33.
Three columns of width are worth more than any further vertical work here.
Saved as `alexey-memory-h33.man`; not submitted, since the score is identical
to memory_05 (26,272,620).

The vertical idea is now fully proven on two joints and has three rows of
headroom left in blocks 4-5, but it cannot pay again until the layout is
narrowed. Next move is horizontal: the same offset trick applied sideways,
or pulling the I/O rooms (columns 0-2) in against the blocks.

### memory: herringbone flipped (block 2 left, block 3 right) — 7/7, clears column 7

Alexey's correction: block 4 must be entered at its OWN top port (column 7),
because it has two pipes each way and its ports cannot move. So the zigzag has
to be flipped — block 2 goes LEFT and block 3 RIGHT — which leaves column 7
uncovered below block 3 and lets block 4 be reached there.

    block1 rows 0-4  cols 5-33
    block2 rows 5-8  cols 3-31   (left)   1->2: (5,32) v -> (6,32) <   2 cells
    block3 rows 9-15 cols 8-33   (right)  2->3: (9,7)  v -> (10,7) >   2 cells

36x33, 7/7, ticks 4,143.6 (was 4,158). Saved as `alexey-memory-zig.man`.
Footprint still 1,296 — width 36 binds against height 33.

Raising block 4 by two rows then failed, and the tell was the same as before:
**pipe count dropped 7 -> 6**. Block 4 has FOUR pipes (two to block 5, one to
O, one from block 3); I redrew only the incoming one. Redrawing all four is
the remaining work for that joint — and note that block 3 has two outgoing
pipes, so moving its bottom port to the left wall (as this attempt did) needs
its `s` cells re-audited, not just re-routed.

## 2026-07-25 — memory_07: 23,344,360 -> 20,491,008 (24/24, 32x31, fp 1024)

Three geometry moves, no algorithm change, all recorded in
`submissions/memory/room-packing/`:

1. Block 2 folded width-only, 4x29 -> 4x21.
2. Block 1 folded 5x29 -> 5x17. It branches, so the plain serpentine does
   not apply; the perimeter-corridor layout does. Written up as sec.4 of
   `docs/alexey-room-folding.md`.
3. Block 4 had three *interior* empty columns (21, 22, 25). Removing them
   pulled its right wall from col 26 to col 23, which let block 5 slide two
   columns left -- and block 5 was the only thing holding the right edge at
   col 33. Width 34 -> 32; height was already 32 and squeezed to 31.

Both of block 5's pipes had to be re-routed. That is what
`src/littleman/alexey_piperoute.py` is for: BFS shortest path, inflated to a
target length with +2 detours, rendered with `-`/`|` runs and arrowheads
only at turns. It keeps a re-route from silently shrinking a buffer.

**Trap paid for here:** a pipe is only recognised when the cell touching the
room carries an arrow pointing *away* from that room. A route that happens
to leave sideways is not a pipe at all -- the machine loads, runs, and fails
with a pipe count one short as the only clue. `Router.route(out=...)` now
forces the first step. Also: a pipe may not attach to a room's *corner*.

Ticks fell too (avg 4143.6 -> 4109.9 locally) because block 4 lost three
columns the man was walking across.

## 2026-07-25 — matmul_03: 33,286,994,352 -> 21,478,654,512 (20/20, 143x147)

**The rooms were never the problem.** matmul's twelve rooms fit inside
109x144. The 183x185 bounding box was made by three pipes -- 268, 334 and
106 cells -- that wandered out to column 182 and row 184, plus the `O` room
parked at cols 180-182 with nothing near it.

Erased those three, moved `O` next to the body, and re-routed all three with
`alexey_piperoute` **at their exact original cell counts** (268/334/106). A
pipe's length is its buffer, and on this machine it is also its delay, so
the counts are not negotiable -- and because they were preserved, the tick
counts came out identical in all seven local cases.

The hard part was not routing, it was **lane assignment**. All three leave
the bottom wall of adjacent rooms at cols 77, 85, 91 and two of them have to
end up west of col 77. Pipes cannot cross, so the pipe exiting furthest west
must take the shallowest lane and each one further east must go deeper. Zone
blocks: p16 rows 145-150 cols 24-84, p17 the left pocket cols 0-23 plus row
151, p18 everything east of col 91.

Also learned: `(134,74)` was reachable only through the two-column gap
between two rooms -- three-cell pipes at cols 76, 84 and 90 seal rows
134-136 completely. Printing a free-cell map before routing is worth the
thirty seconds.

**Two traps paid for, both now fixed in the router:**

* Inflation must never touch the first or last step. A `+2` detour inserted
  at the start replaces the arrow that makes the parser recognise the pipe,
  and the machine then loads and runs with one pipe silently missing.
* `Router.text()` dropped trailing blank rows, so a padded canvas shrank
  between passes and the route could not use the row it had been given.

## 2026-07-25 — matmul_04: 20,042,330,424 (20/20, 115x142)

Two more safe moves on top of matmul_03 (33.29B -> 20.04B overall, 1.66x).

**A provably safe row squeeze.** The rows-only pass drops exactly 10 rows --
room0's empty interior rows. Normally deleting rows inside a room is a
resolution risk, but not here: *every one of room0's eighteen pipes attaches
to its bottom wall*, so the row term of the Manhattan distance is the same
for all of them and the zone is decided by column alone. Deleting rows
cannot change any `r`/`s` resolution. That is the same cancellation the tcp
layout rule is built on, used here as a licence to delete rather than as a
design rule. **Worth checking on every room before trimming it.**

The column pass still breaks -- it squeezes one pipe to a single cell.

**The O room was holding the width** at col 142 all by itself. Moved to
cols 112-114, pipe re-routed at its exact length (104). First attempt put
the pipe's terminal in the one-cell gap between room0's right wall and the O
room's left wall: **both rooms claim that cell**, and the parser emitted a
spurious 1-cell pipe from room0 straight into O. Entering through the top
wall instead fixed it. Rule: never terminate a pipe in a one-cell gap
between two rooms.

## 2026-07-25 — plotter_06: 3,076,834,345 -> 1,668,891,820 (20/20, 155x145)

Layered on tarstars' plotter_05 repack, and orthogonal to it: they moved
rooms, this folds what is inside them.

plotter's three tall rooms spent **two rows on every instruction** --

```
row A:   .....v(p) ................. <(q)     west leg, carries nothing
row B:   .....>(p) INSTR ........... v(q)     east leg, ONE instruction
```

-- and the west leg is nothing but a carriage return.
`src/littleman/alexey_stairfold.py` merges two consecutive east legs
whenever their instruction columns increase across the join, deleting the
west leg between them. 82 rows freed; a rows-only squeeze then took 40 of
them out globally. Ticks fell 21% too, because the man stops walking the
carriage returns.

**Why it is legal, and the same reason the column pass is forbidden:** every
inbound pipe of these rooms lands on the top wall and every outbound one
leaves through the bottom, so the row term of the Manhattan distance cancels
and the zone is decided by column alone. Rows are free; **columns are
frozen**. Running the column squeeze drops it to 1/6, exactly as that rule
predicts. `alexey_stairfold.ports_are_single_walled` checks the
precondition.

Branches in these rooms are compiled as long empty columns that the man
falls down. Deleting whole leg pairs preserves them -- the deleted rows are
blank at every column a fall uses.

## 2026-07-25 — sudoku_04: 25,480,732,026 -> 11,307,342,643 (20/20, 184x192)

The same staircase the plotter rooms use, and the same fold. All four big
rooms pass `ports_are_single_walled`, so rows are free and columns frozen:
80 rows freed, 56 removed globally, ticks down 26%. `uberStrictPassed: true`.

Built from **sudoku_02, not from tarstars' sudoku_03**. Their repack is the
better starting point on its own (16.1B vs 25.5B) but leaves fewer
globally-empty rows once the staircase is folded — 39204 against 36864. Worth
checking both bases whenever a teammate has repacked the same program.

## 2026-07-25 — gradebook_04: 81,914,188,255 -> 54,422,867,494 (20/20, 386x313)

Same staircase fold again, on the biggest program we have. All five big
rooms pass `ports_are_single_walled`; R2-R5 fold completely, 7/7 each time.

**R1 does not, and the failure is one merge wide.** Folding R1 alone drops
to 5/7, but of the 35 merges available there the first 34 are all safe --
found by a binary search over the merge prefix, six judge runs. So the merge
condition in `alexey_stairfold` is *nearly* sufficient, not provably so: it
checks column monotonicity and collisions, but a deleted west leg can also
be the landing spot of a vertical fall belonging to some other branch, and
nothing in the static check sees that.

**Therefore: always drive the fold with the judge.** Fold room by room and
keep only what passes; when a room fails, binary-search the safe prefix.
That is cheap (a handful of judge runs) and it is the only thing standing
between this transformation and a silent wrong answer.

110 rows removed, ticks down 21%. Width 386 now binds — four 94-wide rooms
side by side, columns frozen by zone resolution — so further row folding
here is banked, not cashed.

## 2026-07-25 — memory_08: 20,491,008 -> 19,230,331 (24/24, 31x31)

Block 3 re-laid from 7x26 to 7x23 and block 5 slid one column left. Both
were free moves in the sense that mattered: block 3 has one pipe each way
and **both meet its left wall**, so the fold needed no pipe work; block 5's
two pipes were re-routed in separate lanes at 30 and 21 cells, never shorter
than the 29 and 19 they replaced. Ticks identical in all seven cases.

**The remaining 2x is entirely in block 4, and here is what it is.**

Block 4 is 15x21 and holds 15 of the 31 rows and 21 of the 31 columns. Every
other room is now folded out. Its control-flow graph, extracted with
`src/littleman/alexey_roomcfg.py` (which traces *every* branch arm, not just
the one a single walk follows):

```
B0:   `33` b 0 s            -> d1
d1:   cw -> [m, s] -> d1                 (counted send loop)
      straight -> B1
B1:   r                     -> X1
X1:   straight -> [r b r M r s] -> d2
      cw       -> [r] -> X2
      ccw      -> halt
d2:   cw -> [m, r, s] -> d2              (loop)
      straight -> [{ M `43` W } s] -> B1
X2:   straight -> [r M] -> TAIL
      cw       -> [b m r M r s] -> d3
      ccw      -> halt
d3:   cw -> [m, r, s] -> d3              (loop)
      straight -> TAIL
TAIL: r & M r | s           -> B1
```

Five branch points, three self-loops, and a TAIL shared by two predecessors.
46 instruction cells in 13 interior rows -- **two of those rows carry no
instructions at all** (rows 3 and 13 relative), they are pure carriage
returns, and several more carry two.

Two things make a re-lay legal, and both are checked:

* Rows 3 and 13 exist only because a block sits far from the branch that
  jumps to it. Placing each block adjacent to its predecessor removes them.
* Block 4 is the one room in `memory` **without** port freedom: two pipes in,
  two out, and they sit on three different walls, so a zone depends on row
  *and* column. Moving both inbound ports to the top wall and both outbound
  to the bottom would make it column-zoned -- and the existing column
  pattern already matches (reads from block 3 are at low columns, reads from
  block 5 at high ones; the write to O is low, the writes to block 5 high).
  That is the enabling move, and it costs four pipe re-routes.

Estimated payoff: block 4 at 8 rows instead of 15 puts the box at roughly
24x24, i.e. footprint 576 against today's 961, and the shorter walk takes
ticks down with it. That is the 2x. It is a compiler-shaped job -- embedding
a 10-block CFG in a grid -- not an afternoon's edit.

## 2026-07-25 — block 4 of memory: the re-lay, designed

Took the layout apart. Two findings decide the shape of the work.

**The cheap route is closed.** The obvious saving is the carriage-return row
3 (`d1`-straight walks ten cells west to reach B1). It could be deleted by
letting the man fall down a clear column to the bottom return row instead —
except **there is no clear column**. Checked all nineteen: every one carries
a glyph somewhere between row 3 and the bottom. The literal `` `34` `` alone
blocks columns 11-14 on row 7.

**The prize is bigger than the footprint.** Block 4 walks **38 cells of pure
carriage return on every loop iteration** — row 3 (10 west + 1 down), row 13
(18 west), and the column-1 rail (9 north) — against 46 instruction cells in
the whole room. That is why the re-lay pays twice: it takes rows out *and*
it takes a large bite out of avgTicks, which is the other half of the score.

### The design

The enabling move is to make the room **column-zoned**: put both inbound
pipes on the top wall and both outbound on the bottom, and the row term of
the Manhattan distance cancels. Then every `r`/`s` only needs to be on the
correct *side* of the room. Block 4 is the one room in `memory` without port
freedom, so this costs four pipe re-routes — `alexey_piperoute` handles them.

Which side goes to which pipe is not free, and getting it backwards costs a
row. With **block 3 reading HIGH and block 5 reading LOW** (and block 5
written HIGH, `O` written LOW), the blocks fall out like this:

| block | body | rows |
|---|---|---|
| B0 | `` `33` `` b 0 · s(H) | 2 (with the loop's `m d` under it) |
| B1 / X1 / B3 / X2 / B5 | r(H) · r(H) · r(H) M | 1-2 |
| B2 | r(H) b r(H) M ⟶ **loop** r(L) s(H) | 2 |
| B4 | { M `` `43` `` W } s(L) | 1 |
| B6 | b m r(H) M ⟶ **loop** r(L) s(H) | 2 |
| TAIL | r(L) & M r(H) \| s(H) | **1** |

TAIL is the one that moves: today it needs two rows because its columns run
high → low → high, which forces a direction change. Under the flipped
assignment it reads low → high → high, **monotonically increasing**, so it
fits on a single eastbound row. The mirror-image choice (block 3 LOW) makes
TAIL cost two rows and B2 one — strictly worse, because TAIL is on the hot
path and B2 is not.

Two more constraints that any layout must respect:

* The loop unit `> r · · s v / ^ · · m d` may be **stretched**: `r` and `s`
  need not be adjacent, so a unit can straddle the low/high boundary. That is
  what lets B2's and B6's loops hold r(L) and s(H) on one row.
* `X` is three-way and *handed*: straight / clockwise / counter-clockwise are
  relative to the direction of travel, and the assignment (straight → the
  long arm, cw → the short arm, ccw → halt) is fixed by `sign(A)`. So each
  `X` must be placed with a clear run to a wall on its counter-clockwise
  side, and the entry direction decides where the other two arms may go.

Target: 9-10 interior rows against today's 13, and the 38 wasted cells per
iteration mostly gone.

**Status: designed, not built.** The constraint system is worked out and
consistent; what remains is the placement itself — embedding ten blocks and
five branch points in a grid, which is the compiler-shaped part. It wants a
clean session, not the tail of one, because a half-verified block 4 is worse
than none: it passes seven local cases and fails on the server's twenty-four.

## 2026-07-25 — block 4: measured before building, and the measurement killed the plan

Before laying block 4 out I instrumented `Machine._tick` and counted, per
room, how many ticks its man spends **walking** versus **blocked**, on
memory's largest public case (22,719 ticks).

```
room   walking   blocked   busy%
R1        4004     18715    17.6
R2        4753     17966    20.9
R3        7802     14917    34.3
R4       22719         0   100.0     <- block 4
R6       12846      9873    56.5
```

**Block 4 is the bottleneck and it never blocks.** Every other room idles
65-82% of the time waiting on it, so the whole runtime is block 4's walk.
That part confirmed the plan. Then the per-cell counts overturned it:

```
row  total  no-op  content
  3     10     10   v        <          <- the carriage return I was going to delete
  5   4738   2456   ^  v         >rsv
  6   4513   2306   ^  v         ^ md
  9   4162   2106   ^    >bmrM   >rsv
 10   3612   1806   ^            ^ md
 12    900    850   ^ >              sv
 13    950    950   ^                 <  <- the other carriage return
```

**Rows 5-6 and 9-10 are 73% of the entire runtime.** They are the two
counted relay loops, and they ran 1141 and 928 times on this case. The two
carriage-return rows I had designed the re-lay around cost **1,810 ticks
between them — 8%**. I had been optimising the wrong thing: those rows run
once per *outer* iteration, the loops run thousands of times.

### And the loops are already at their geometric floor

The unit is

```
> r s v
^ · m d
```

four operations (`r` receive, `s` send, `m` decrement, `d` test) in an
eight-cell cycle. It cannot be seven: a grid cycle has even length, and the
cycle needs three turn glyphs — one to go south, one to go north, and one to
turn the man back east after the `^`, because he arrives at the top row
heading north and something has to turn him. Three turns plus four
instructions is seven cells, so the cycle is eight. **The current unit is
optimal.** Half of its ticks being no-op is structural, not waste.

### Conclusion, and it is a negative one

Block 4's *layout* cannot deliver 2x. The room is 100% busy, 73% of its work
is two loops that are already minimal, and the whole outer structure — every
carriage return, every rail — is worth at most ~9%. Re-laying it is worth
doing eventually for the footprint, but not for the score.

The 2x on `memory` has to come from somewhere else:

* **Footprint**: 961 → 484 means everything inside 22x22. Every room is
  already folded; block 4 at 15x21 is what stands in the way, so this is the
  same re-lay, worth ~1.3x at best on its own.
* **Fewer ticks per relayed value**: unrolling the loop to `r s r s m d`
  moves two values per cycle — nine cells plus three turns is a ten-cell
  cycle, i.e. five ticks per value against eight, a 37% cut. That is an
  **algorithm change**, not geometry: the counter would have to handle odd
  lengths. It is where the 2x actually lives.

## 2026-07-26 — memory_09 and _10: 19,230,331 -> 17,236,875 (24/24, 30x30)

The profile said the loops were untouchable and the carriage returns were
only 8%. Both were true, and there was still 10% between them: **the gaps**.

`memory_09` (-4.9%): the loop units sat four and three columns to the right
of the instructions feeding them, so the man walked blanks to reach them on
every outer iteration. Pulled loop2 and loop3 from rel cols 14-17 to 11-14,
pulled B4's row in to end at rel 14, and pulled TAIL's two legs from rel
3-18 to 6-16. Big case 22,719 -> 21,469 ticks.

Two columns had to stay clear and knowing which mattered: **rel 4 carries
X1's clockwise descent and rel 6 carries X2's counter-clockwise halt path.**
Putting an instruction in either changes what a branch arm executes. Every
`r`/`s` zone was re-audited cell by cell against memory_08 -- all fifteen
resolve to the same pipe.

`memory_10` (-5.7% more): with the interior tight, the carriage-return row
could finally go. B0's loop unit moved to rel 16-18 so `d1`'s straight jump
falls down rel column 18 -- clear only *after* the previous step -- to the
bottom return row, instead of needing a row of its own. Block 4: 15 rows ->
14, footprint 961 -> 900.

**Trap:** the `O` pipe's attachment ended up beside block 4's new
bottom-left corner, where the O room also claims it. Moved it to the top of
the left wall, which as a bonus widens the margin between the two write
zones.

First attempt at all this failed 2/7 for a reason worth recording: `d3`'s
straight jump lands on TAIL's entry cell, and pulling TAIL left removed the
cell it lands on. **A branch's straight arm is a jump with a landing pad;
move the pad and the jump falls through.** Both entry points (X2's descent
and d3's jump) now have their own `<`.

## 2026-07-26 — reverse-a-list: packing assessed, and a correction

**The cost is quadratic in the list length**, measured on reverse_01 with
synthetic single-round lists:

```
 n     1    2    3    4    6    8   10   12   14   16
ticks 54  105  167  239  413  627  881 1175 1509 1883
```

Per-element cost grows linearly (51, 62, 72, ..., 187), so
`ticks = 5n^2 + 32n`. That is the ring re-circulating to reverse, and
packing k values into one cell cuts the quadratic term by k^2.

### The 64-bit limit is real and the simulator hides it

Registers are **64-bit signed** and `sim.py` wraps them **silently** --
`wrap64()` sits on every arithmetic op including the multiply. An overflow
does not raise; it returns a wrong answer, and only on values near the
+/-1,000,000 extremes. The public cases use 42, 100, 10, 20, 30, so **a
local 8/8 would not catch it.** Any packed design has to be bounded on
paper and then stress-tested at the extremes by hand.

Bounds, shifting by +1,000,000 into 0..2,000,000:

| pack | base | max value | headroom vs 9.223e18 |
|---|---|---|---|
| 2 | 2,000,001 | 4.00e12 | **6 orders of magnitude** |
| 3 | 2,000,001 | 8.000012e18 | 13.3% |
| 3 | 2^21 fields | 8.796e18 | 4.6% |
| 4 | any | 1.6e25 | impossible, 1.7 million x over |

Three fits only with Horner's scheme, `((v2*B)+v1)*B+v0`, so no intermediate
exceeds the final value -- and nothing may ever be added to a packed value
afterwards. Note the 21-bit-field variant is *tighter* than base 2,000,001,
not looser: three 21-bit fields is 63 bits, one bit past the sign.

### Two-packing, not three

The quadratic saving saturates while the packing overhead keeps growing:

| | ring term at n=16 | overhead | net |
|---|---|---|---|
| now | 1280 | -- | 1883 |
| 2-pack | 320 | ~240 | ~1160 (-38%) |
| 3-pack | 180 | ~360 | ~1140 (-39%) |

One point apart, and two-packing has six orders of magnitude of headroom
against three-packing's 13%. Take the safe one.

It only pays for long lists -- at n=4 packing is a loss, at n=8 a wash. The
live avgTicks is 1845 against a local average of 1162, so the server's cases
are longer than the public ones and it should pay there: expect 20-30%,
roughly 472k -> 350k. It is a new machine, not an edit.

`reverse_02.man` is **not** a candidate -- the server rejected it. reverse_01
is the base.

### Before building it: the footprint has to be counted too

Score is `fp x avgTicks`, and a packer plus an unpacker are two new rooms.
Free space inside reverse_01's 16x16 box, with the one-cell clearance a room
needs: **22 cells**, and they are a 4x3 pocket at cols 0-3 rows 7-9 plus a
sliver of column 0. Two arithmetic rooms need roughly 100 cells with walls.
**They do not fit.** So the box grows, and the break-even is steep:

| box | fp | ticks must beat |
|---|---|---|
| 17x17 | 289 | x0.89 |
| 18x18 | 324 | x0.79 |
| 20x20 | 400 | x0.64 |

Two-packing quarters the ring term (`5n^2 -> 1.25n^2`), which is 960 of the
1883 ticks at n=16, but the packer and unpacker add back 15-25 per value.
Realistic average over the case mix: **x0.72**. Against a box grown to 19x19
that is x1.02 — a loss. Against 18x18, x0.91.

So on the naive plan the packing barely pays, and only if the two new rooms
squeeze into 68 extra cells. They will not.

### But the delay line shrinks too, and that changes it

The ring is not inside a room at all — it is **pipe P3, seventeen cells
long**, running rows 10-13 and cols 0-7. That is where the sixteen values
sit. With pairs, only eight packed values ever need storing, so **P3 drops
from 17 cells to ~9**, freeing most of rows 10-13 and columns 0-7 — which is
exactly the region the packer and unpacker need.

That is what makes the idea work: packing does not merely trade ticks for
area, it *frees* the area it needs. The build is
`I -> packer -> R1 -> unpacker -> O` with P3 shortened, and the target is to
stay inside 16x16 so the x0.72 on ticks lands whole: 472k -> ~340k.

Encoding, bounded on paper: `P = (a+1e6) + (b+1e6)*B + f*B^2` with
`B = 2,000,001` and `f` a 0/1 flag for "this cell holds a pair". Maximum
8.0e12 against the 9.2e18 limit — six orders of margin. When `n` is odd the
**first** input value goes in alone (`f=0`); being first in, it comes out
last, which is where it belongs. The unpacker emits `b` then `a` for a pair,
`a` alone for a singleton.

## 2026-07-26 — reverse: packing is dead, geometry is not (reverse_06, 14x14)

### The packing plan is obsolete — measured, not guessed

While the packing design above was being worked out, tarstars replaced the
machine underneath it. `reverse_05` (his branch, live **117,214**) is a
different ring: **6 ticks per relayed value instead of 10, and each pass
extracts TWO values**, so the cost is `1.5n^2 + 9n + 5` instead of
`5n^2 + 32n`. Measured on synthetic single-round lists:

```
 n        1    2    4    8   12   16
r_01     54  105  239  627 1175 1883
r_05     21   30   65  173  329  533
```

Two-packing halves the ring term. At `n = 16` that saves `1.5*(256-64) =
288` ticks. The arithmetic to buy it:

| step | cells walked |
|---|---|
| pack `P = x*K + (y+S)` | `r { M r + M` + a 9-cell `S` literal + `+ s` = ~22 |
| unpack, copy 1 (`y`) | build `B=K` (8) + `r / ` + `S` (9) + `- N s` = ~22 |
| unpack, copy 2 (`x`) | `21` + `M r } s` = ~8 |

**~50 ticks per pair against 36 saved.** It loses, and that is before the
footprint: a packer and an unpacker are two more rooms, 225 -> 289 at
best. The floor is the offset: values span `[-1e6, 1e6]`, so the low field
needs `+S` with `S > 1e6` — a 7-digit literal, 9 cells, walked once to add
it and once to remove it. There is no cheaper form (checked: `{`/`}` with
a small shift needs a second constant live at the same time; `&` masking
needs a mask; folding `S` into the multiplier needs `C = S*(K+1)`, 13-14
digits; per-word correction `S*(K^2+K+1)` saves one walk in three and
costs 21 cells). Three-to-a-cell is worse still — the stack digits must be
peeled by repeated division, so a word must be re-sent once per digit.

**Rule of thumb worth keeping: arithmetic packing costs ~20-30 ticks per
value. It only pays against a ring whose lap is ~10 ticks or more.** It
would have paid on reverse_01. It cannot pay on anything as tight as
reverse_05. Do not rebuild it.

### What did pay: reverse_06, 14x14, local 62,769

tarstars' handoff (`docs/architecture/claude_27_reverse2_handoff.md`)
named the next step exactly: width binds at relay(4) + gap(1) + pump(10),
so the pump interior has to go 8 -> 7 wide. He was blocked on east-side
convergence. Re-laying the pump from scratch got 7 wide **and** 6 tall
(his was 8x7), which takes the box to 14x14 and the score to **62,769**
(reverse_05: 74,390) — 1.185x, of which 1.148x is footprint and the rest
ticks. Three ideas did it:

1. **Fold the head send into the relay loop.** Walk the loop as
   `> s U d m ^` — it SENDS what is already in A, then READS the next
   value. Enter with `A = k-2` (the new head) and `BP = k-2`: lap j sends
   value j-1 (lap 1 sends the head), reads value j, and `d` falls through
   at lap k-1 holding `v_{k-1}`. That is exactly `head + v1..v_{k-2}` sent
   and `v1..v_{k-1}` read. The dedicated head-`s` cell and its approach
   lane disappear.
2. **Load BP with k-2, not k-1.** Then `k == 2` needs no fixup: put `X`
   one row directly above the loop's `U` and its straight-south arm drops
   onto `U` with `BP = 0`, so `d` falls through into the shared tail.
   Costs zero cells; reverse_05 spent a lane and a zeroing `m` there.
   BP is 0 at the start of every pass anyway (the loop always drains it),
   which is why only the k>=3 arm needs the `b`.
3. **Constant 2 instead of 1**: one `-` replaces `-b-`. Reloaded by `2`
   on the climb and `M` on the head row.

```
        c0 c1 c2 c3 c4 c5 c6
    r0   .  .  v  -  r  M  <     head row, walked WEST: B=2, A=k, A=k-2
    r1   .  .  b  .  .  .  2     BP = k-2 ; climb reloads A=2
    r2   v  .  X  r  s  @  ^     three-way branch ; k==1 spur (r, print)
    r3   >  s  U  .  .  .  s     loop top ; climb prints v_{k-1}
    r4   ^  m  d  .  .  .  W     loop bottom ; climb swaps
    r5   .  .  >  M  r  s  ^     tail: hold v_{k-1}, read+print v_k
```

Generator `src/littleman/alexey_reverse6.py`, tests
`tests/test_alexey_reverse6.py` (8 tests: geometry, the input-room pipe
rule, every `s`/`r`/`U` resolution, public 8/8, every length 1..16 with
extremes, 120 fuzz rounds, branch-mix boundaries). 262-case stress green,
max 1546 ticks.

Two traps re-paid during the re-lay:

* The return pipe's westward bend first sat at row 7, flush against the
  pump's left wall — its backward cell IS the wall, so it parsed as a
  second pipe out of the pump (5 pipes instead of 4). Moved the jog to
  row 9, below the room.
* The return pipe then wanted to climb column 3, flush past the input
  room's right wall. The server counts a pipe merely PASSING an input
  room's wall as a second connection and rejects the program (tarstars
  paid a submission for that one). It climbs column 4 instead.

**Submitted 2026-07-26T12:36Z**, id `e338fb00-7962-432f-9c30-77baff5ce603`:
20/20, width 14, height 14, avgTicks 503.45, **server score 98,676.2**
(reverse_05: 117,214) — 1.188x live, and the estimate from the local
ratio was 99,000, so the server's case mix tracks the public one.

Next lever if anyone picks it up: 13x13 = fp 169, another 1.16x. Needs
either a 6-wide pump interior (the head row alone wants 5 cells plus the
drop column, and the loop wants 2 more to its west — it does not fit as
laid out) or the relay moved BELOW the pump so width stops being
relay + gap + pump. The latter flips the ring-in to the pump's floor,
which turns `U` north and needs the interior re-walked.

### 13x13 attempt: why 7x6 interior is the floor for this architecture

Tried, does not close. fp 169 needs BOTH dimensions at 13, i.e. relay(4) +
gap(1) + pump(8) wide and one row less tall — a **6x5 pump interior**.
The two blockers are structural, not a lack of cells (24 used of 30):

**Columns: 7 is the floor.** The head row is 5 cells — `<` (the climb's
turn), `M`, `r`, `-`, and the drop `v` — and it must run from the climb
column *west* to the drop column, so `cE = cU + 4`. The loop is a 2x3
block whose `>` sits at `cU - 2`, so `cU >= 2`. Union = `cU-2 .. cU+4` =
**7 columns**. Every way out was tried and closes worse:

* Drop `M` from the head row (compute `2-k` with `r M 2 -`, no preset B):
  needs `N` to get `k-2` back for the head send and `b`, and the branch
  arms swap sides, which puts the k=1 spur into the wall.
* Mirror the loop (`a` instead of `d`) so it sits east of `U` and `cU`
  can be 1: the main arm then needs two cells (`N`, `b`) between `X` and
  the loop entry but only one exists. Widening the loop's top row to make
  room turns the lap from 6 cells into 8 — +2 ticks on every one of the
  56 relays at n=16, which eats most of the 14% the area would buy.
* A 2x2 loop leaves no cell for `s` and `m`.

**Rows: 6 is the floor.** `b` can indeed move off its own row onto the
main arm (BP is 0 at the start of every pass, so the k=2 arm needs no
`b`), which is what a 5-row layout needs. But then the climb column must
carry `W`, the `s` that prints `v_{k-1}`, the k=1 spur's join turn, and
the `2` — four cells between the tail's turn and the head row's `<`, and
a 5-row interior offers three.

The only route left is a different *room* layout: relay under the pump so
width stops being relay+gap+pump. That flips the ring-in to the pump's
floor (so `U` turns north and the interior must be re-walked) and then
runs out of pipe space — with the pump against the box edge there is no
floor row left for the ring-out and the output, and putting both on the
side wall makes the ROW decide nearest-pipe, which collides: the loop's
`s` and the climb's `s` share a row.

**Where the remaining ticks are** (profiled, n=16, 516 ticks): blocking is
1-3 ticks total, so the machine is walk-bound, not transit-bound. 336
ticks are the 56 relay laps (6 each) and ~180 the 8 passes' fixed cost
(head row 5, tail 4, climb 5, arms 4). The real lever is **three
extractions per pass** — relays drop 56 -> 35 and passes 8 -> 6, about
-33% — but it needs a third live value (`v_{k-2}` held while `v_{k-1}`
and `v_k` are read), so it needs a one-value stash room off the ring, at
20 cells plus two pipes.

## 2026-07-26 — three-to-a-cell packing: BUILT and MEASURED, still loses

Built the pack side for real rather than estimating again:
`/tmp/.../scratchpad/pack3.py` (harness, not repo code). One room, one man,
`I -> packer -> O`: read three values, Horner-pack base `K = 2^21`, add the
per-word offset correction once, emit the word. The judge compares the word
against the number Python computes, so the arithmetic is verified end to end.

**The arithmetic is fine — the user's bound holds.** `K = 2^21`, `S = 2^20`,
digits `v + S` in `[48576, 2048576]`, word `= (v1+S)K^2 + (v2+S)K + (v3+S)`.
Worst case measured on the machine: `1000000,1000000,1000000` ->
**9,009,736,825,708,692,032** against the signed limit
9,223,372,036,854,775,807 — 2.3% of headroom, no wrap. All five probes pass
(extremes, all-negative, all-zero, mixed sign).

**The cost is the problem: 103 ticks for three values = 34 ticks per value,
for PACKING ALONE.** The whole of reverse_06 costs 516 ticks for sixteen
values = 32 ticks per value. Even a tight serpentine layout (fold the return
leg) only gets packing to ~23/value, and unpacking is strictly worse.

Why it cannot be made cheap — one sentence: **every constant costs a literal
walk, because a literal writes A, and A is where the accumulator lives.**
The per-value sequence is forced:

    M `21` W { M r +      park T in B, load 21, swap back, shift, park, read, add

Ten cells, of which four are the literal `21`, purely to get a constant into
B without losing T. The >1e6 offset is kept off this path by adding
`C = S*(K^2+K+1)` once per word (a 19-digit literal, 21 cells) instead of
`+S` three times — that trick works and is worth remembering, but it still
costs 8 ticks per value amortised.

Unpacking is worse for a structural reason: `/` writes BOTH A and B, so
after one division the base is gone from B and reloading it destroys the
remaining stack. Every digit therefore needs the word re-sent (the pump
sending it three times, i divisions on copy i) or a partner room to park the
quotient. Six divisions per word, each with a base reload, plus removing the
offset from each digit while the stack is live: ~30+ ticks per value.

**Total, honestly: ~55-60 ticks/value of arithmetic against 32 ticks/value
for the entire current machine, plus two or three new rooms.** The ring
saving is real and large — 6 words instead of 16 values takes the relay laps
from 336 ticks to ~36 at n=16 — but the ring is only 336 of 516 ticks, so
even a FREE packer could not reach half. Packing is closed. It was the right
idea against reverse_01's 10-tick lap and 5n^2; it cannot beat a 6-tick lap
with double extraction.

### 13x13 by room repacking: also closed

Tried the user's suggestion (move I/O flush against the rooms, re-route).
13 columns = relay(4) + pump(9) exactly, so there is **no routing lane**:
the relay's right wall touches the pump's left wall, and a pipe cannot pass
between adjacent walls. Every alternative was walked:

* pipe out of a room's roof needs TWO free rows (the first cell must point
  away, the bend needs its own cell) — one free row above is not enough;
* with the relay beside the pump, the only free columns spanning the pump's
  rows are inside the relay, so a return pipe cannot climb from below the
  pump back to its roof;
* moving I and O into the bottom band blocks the westward corridor the
  ring-out needs, and routing around them runs the pipe flush past the input
  room's wall, which the server rejects.

Both dimensions are therefore pinned: 7x6 is the floor for the pump interior
(proven above) and 4+9 is the floor for the width.

## 2026-07-26 — reverse_07: 13x13 by moving one room at a time

**I was wrong about 13x13 being impossible.** The proof I wrote earlier
assumed the gap column between the relay and the pump was mandatory, because
the ring-in leaves the relay's right wall. Alexey's method — move one thing,
judge, then move the next thing relative to that, without designing the final
layout first — found the way through in six steps. Every step is preserved in
`experiments/alexey-reverse06/` with its `.man` and a note.

| step | move | box | score |
|---|---|---|---|
| 0 | reverse_06 as submitted | 14x14 | 62,769 |
| 1 | Output flush: its pipe bends into O's right wall instead of dropping into the roof, so O climbs two rows | 14x14 | 62,769 |
| 2 | Relay down two rows (rows 2-7); ring-in now leaves the ROOF and is 7 cells | 14x14 | 63,161 |
| 3 | Input up one row; ring-out re-terminates on the relay floor | 14x14 | 62,744 |
| 4 | Ring-out out of the last row | 14x13 | 62,891 |
| 5 | Pump one column left — relay FLUSH, no gap column | **13x13** | 53,911 |
| 6 | Ring-out serpentined: 13 cells instead of 11 | 13x13 | **53,594** |

Step 2 is the one that mattered and it looked pointless at the time (the
score got *worse*). Two free rows above the relay let the ring-in leave
through its roof, and that is what makes the gap column unnecessary — which
only becomes visible three steps later.

Step 6 is worth remembering on its own: **a longer pipe was both more
capacious and faster.** Pipe cells are parking space as well as delay, so the
serpentine (13 cells vs 11) removed blocking that the short route caused.

Two traps re-paid, both already in the trick sheet: a bend flush against the
pump's bottom wall parsed as a fifth pipe (fixed by moving the jog off row
8), and the ring-out could not climb the column beside the input room.

Also learned: reverse_06's `(1,4)` was a **dead glyph** — the ring-in
actually starts at `(0,4)`, sourced from the relay's top-right corner. The
parser wants an arrowhead adjacent to a border cell pointing away from the
room; `(1,4)`'s `^` matched no room, so it was never part of a pipe.

Capacity checked properly instead of by rule of thumb: peak occupancy across
both ring pipes is **16** on three consecutive n=16 rounds (the frame is at
most 17 values and the pump always holds one), against a capacity of 19.

`src/littleman/alexey_reverse7.py`, `tests/test_alexey_reverse7.py` (8 tests),
`submissions/reverse-a-list/reverse_07.man`. 8/8 public, every length 1..16
against three value patterns, 250-case fuzz, CLI preflight 53,594.1.
Live estimate: 98,676 / 1.171 ~ **84,000**. Not submitted yet.

## 2026-07-26 — brackets_05: 35x30 -> 34x29 by folding one pipe (fp 1225 -> 1156)

Same method, applied to the current best (`brackets_04`, live 836,345).
Steps in `experiments/alexey-brackets04/`.

**Where the box was going:** brackets is width-bound (35 wide, 30 tall). The
widest room spans cols 5-33, so **columns 34-35 were pure pipe** — the
69-cell return from R3 to R1 climbed the far east column and ran back west
along row 0.

**Step 1** re-routed that pipe with `alexey_piperoute` under
`bounds=(29, 34)` and `target=69` — same 69 cells, so identical buffering and
identical tick counts — and the box became **34x29, fp 1156, local 482,514 ->
455,336**. Row 0 emptied out as a side effect, which is where the extra row
came from. Verified 9/9 public plus 200 fuzz strings (balanced generator and
uniform random, lengths 0-64) and the edges: depth-32 nests, all-openers,
lone closer, empty string, `([)]`, 64-char balanced.

**Step 2 and 3 failed, and the reason is worth recording.** To get to 33 the
pipe needs a northward corridor west of R2 (cols 1-4). Two things block it
and they cannot both be moved:

* the 14-cell R3->R2 pipe climbs that corridor and elbows east at row 12 to
  reach R2's left wall — the elbow spans the whole corridor width, so any
  pipe climbing beside it is cut off at row 12;
* moving that pipe one column west (step 2, tried: it works, 16 cells, 9/9)
  just moves the blockage — its vertical run then cuts row 18, which is the
  only way from the east half to the west half, because R3 fills rows 19-29
  below and R2 fills rows 10-17 above.

So one of the two pipes always crosses the other. The next real move is to
shift **R2 itself** one column left (cols 4-32), which frees col 33 for the
climb; that needs its three roof pipes re-jogged by one column, and R2's
nearest-pipe resolution re-audited, because two of them land on the same
wall.

`submissions/brackets/brackets_05.man`. Expected live: 836,345 x 0.944 ~
**789,000** (the tick average is unchanged — this is pure footprint).

### brackets_06: the shift ladder — 35x30 -> 31x29 (fp 1225 -> 961)

Continuing after brackets_05 (live 789,237, exactly the predicted 789k).
The blocker was named in the step-2/3 failure above: the return pipe needs a
climb column and R2's right wall is where it would be. So move R2.

**The step, generalised.** Shift R2 (and the O room with it) `k` columns
left, then fold the return pipe into the freed column. R2 has two incoming
and two outgoing pipes, so all four attachment cells must keep their offset
*inside R2* or the nearest-pipe resolution changes. R1 has a single outgoing
pipe, so that one's source may move freely — which is the degree of freedom
that makes the whole thing work.

| shift | box | fp | local |
|---|---|---|---|
| 0 (brackets_05) | 34x29 | 1156 | 455,336 |
| 1 | 33x29 | 1089 | 429,550 |
| 2 | 32x29 | 1024 | 404,935 |
| 3 | **31x29** | **961** | **380,983** |
| 4 | 35x29 | 1225 | 487,142 (worse: R3's pipe terminal needs col 0, so the box grows west) |

Three traps paid on the way, all recorded so the next re-lay is cheaper:

1. **Erase pipes before moving a room.** The R3->R2 pipe terminates on a
   cell the moved room lands on; erasing afterwards deletes a wall glyph and
   the program stops parsing.
2. **Two roof pipes jogging in the same direction collide.** R1->R2 and
   R2->R1 both attach to R2's roof and both must reach R1's floor; sending
   one west along row 9 and the other east along row 8 keeps them apart at
   every shift.
3. `route_safe` refuses **every** arrowhead beside a room, which is stricter
   than the rule. An arrowhead there is only a phantom pipe start if it
   points AWAY from that room, so the two short jogs are hand-placed and
   audited by hand.

Verified: 9/9 public, 250 fuzz strings (balanced generator + uniform random,
lengths 0-64), and the edges — depth-32 nests of each type, 64 openers, lone
closer, empty string, `([)]`, full-length balanced, balanced-then-unclosed.

`submissions/brackets/brackets_06.man`. Expected live ~ 789,237 x (961/1156)
x (380,983/455,336 / (961/1156)) — the tick average is unchanged again, so
simply **~656,000**.

### brackets_07: re-run squeeze AFTER moving things — 31x29 -> 30x27 (fp 900)

`alexey_squeeze` had nothing to delete on brackets_04 (the trick sheet even
says so). After the shift ladder moved three rooms and four pipes, it found
**3 rows and 2 columns**: 961 -> **900**, local 380,983 -> 353,600, 9/9,
250-fuzz clean. A second pass finds nothing more.

That is the general lesson, and it is now paid for twice: **squeeze is not
exhausted, it is exhausted *for a given layout*. Re-run it after every move.**

Live ladder for brackets today: 836,345 -> 789,237 (fold the return pipe off
the east column) -> 660,983 (shift the middle room three columns left) ->
**615,565** (squeeze the slack the shift opened). Total **1.36x**, all of it
footprint; the tick average never moved.

Remaining: 30 wide against 27 tall, so the width still binds. The next
column would have to come out of the middle room's interior (29 wide),
which is program surgery, not layout.

### brackets_08/09: the two tricks that were still missing — 30x27 -> 27x27

Alexey caught that I had jumped to subset-sum with brackets tricks unapplied.
He was right; two of the four playbook moves had never been run on it.

**Room-edge trimming** (playbook move 2). `alexey_trimrooms` applied whole
destroys this program — it loses a pipe and moves resolution — so it was done
by hand, one room and one edge at a time, with `alexey_resolveaudit` as the
gate:

| step | move | box | local |
|---|---|---|---|
| brackets_07 | (was) | 30x27 | 353,600 |
| brackets_08 | R2's right wall in by 1, return pipe re-folded at 65 cells | 29x27 | 330,420 |
| brackets_09 | R2's right wall in by 2 more, O slid 2 left with it, re-fold | **27x27** | **286,416** |

The blocker at the first attempt is worth keeping: **a room's blank edge
columns are only trimmable up to its outermost PORT.** R2 had three blank
right columns but a pipe to the output room attached to its roof at the
second of them; trimming past it orphaned that pipe (5 pipes instead of 6).
The fix was to trim two more only after sliding O — and its pipe — left as
well. O has a single pipe, so its resolution cannot be ambiguous; that is the
free variable again.

Two more things the gates caught before the judge did:

* the first re-fold routed the return pipe flush past the input room —
  `server_compat` rejects that (the rule tarstars paid a submission for), so
  the input room's neighbourhood is now blocked before routing;
* `route_safe` could not place any of these folds (it refuses every arrowhead
  beside a room). Plain `route` plus a retry loop that blocks only the
  arrowheads which actually created a phantom pipe works, and the pipe-count
  gate is what makes that safe.

**The staircase fold does not apply here**: no room in brackets has
single-walled ports (checked all three).

Live: 836,345 -> 789,237 -> 660,983 -> 615,565 -> **498,608**, i.e. **1.68x
today**, all footprint, tick average untouched. 27x27 is square now, so the
next gain needs BOTH dimensions, which means interior surgery on the 25-wide
middle room rather than layout work.

### brackets b10: the dead-cell scan — room 0 loses 6 columns of nothing

Alexey spotted two useless arrows in the top room by eye. Measured properly
(a visited-cells scan through the Python sim over 460 constraint-respecting
cases: offender at every position 1..64, every unclosed depth 1..32 of each
bracket type, balanced strings of every even length, 300 depth-capped random
strings), room 0 has exactly **four** dead cells: the two `<` at (5,19),(5,20)
he saw, plus an orphaned `>`(3,1) / `^`(5,1) — remains of a western return
path that no longer exists. Blanked all four; room 0's right wall then trims
21 -> 15 (the room was 22 wide for content that ends at col 14).

Resolution map identical, 9/9, fuzz clean. Score unchanged — the box is
bound by room 2 in width AND by the room stack in height — so per the
standing rule this is recorded as an enabler step
(`experiments/alexey-brackets04/b10_deadtrim.man`), not submitted.

Four findings from the scan, all worth more than the columns:

1. **brackets is single-round by contract.** All 9 public cases are one
   round, the description has no round language (reverse's says "1-3 lists"),
   and the machine deadlocks on ANY second round — in brackets_04, the
   original live 26/26 artifact, identically. The server's private cases are
   therefore single-round too. My earlier fuzzes were multi-round-free by
   accident; now it is explicit.
2. **The four `H` cells in room 2 never execute, but they are load-bearing.**
   The judge passes the case the moment the output value is emitted — but the
   value spends 2 ticks in the output pipe, and a man who walks into a wall
   meanwhile is an ERROR, which kills the program including its pipes before
   the value drains. `H` after the final `s` is what buys those 2 ticks. Do
   not delete a trailing H to save a column unless the man can be turned
   somewhere safe instead.
3. **`judge_case` here is fastsim-backed (C).** Patching
   `sim.Machine._execute` does nothing to it — a visited-cells or occupancy
   probe must drive `sim.Machine` directly. Cost me one empty scan.
4. Depth is capped at 32 by the constraints; `(`*33+ overflows the base-3
   packed stack by design. Fuzz generators must cap depth or they test
   outside the contract.

What is actually left in brackets: width is pinned by `sH` ending at room 2's
col 24 on row 11, whose entry `>` at (11,14) is the A<0 landing pad of the
`X` at (12,14) — so the tail cannot slide left without moving the X, which is
embedded in row 12's chain, whose south branch lands on row 13's `W`. That is
a walk-graph surgery project (map every landing pad, move the three chains
together), not a layout move. Height similarly needs an interior row out of
one of the three rooms. Parked with this note.

### brackets b11: the ring is transport, not storage — 65 cells -> 49, live pending

Alexey asked whether I/O and rooms 0/2 can be pressed closer. Measured every
gap instead of answering from memory (b10_deadtrim coordinates):

| gap | size | verdict |
|---|---|---|
| I room -> room 3 | pipe (23,21)-(23,20), 2 cells | legal minimum, flush |
| O room -> room 2 | pipe (8,24)-(7,24), 2 cells; O floor row 6, room 2 roof row 9 | flush |
| room 0 -> room 2 | rows 7-8, exactly 2 | minimum: their two pipes need >= 2 cells each; a 1-row gap means 1-cell pipes, which the server rejects |
| room 2 -> room 3 | walls on rows 15/16 | already touching |

Neither I nor O binds the box: O lives inside room 2's column band, I inside
room 3's row band. Both dimensions are pinned elsewhere (room 2's interior
content in width; the room stack plus the ring's roof-entry row in height).

**But the occupancy probe that came with the measurement paid off.** Peak
occupancy of the two long pipes on the heaviest cases (32-deep nests,
full-length strings): **10 values of 78 cells of capacity**. Unlike
reverse, brackets' 65-cell pipe is a data path, not a parking ring — its
length is pure latency. We had been carefully preserving 65 cells all day
for nothing. Shortest route is 49 cells (must still climb col 26 and run
row 0 — both pinned): local 286,416 -> **277,830**, first tick win of the
day. The 13-cell and two 5-cell pipes are already at their Manhattan
minimum (13 = 9+3+1 exactly, 5 = 1+3+1 exactly), so nothing else to cut.

Rule for the playbook: **measure a long pipe's peak occupancy before
preserving its length.** `target=` is for pipes that store; pipes that
merely carry should be as short as the pinned geometry allows.

### brackets: can rooms 0 and 2 be flush, pipes through other walls? No — enumerated

Alexey's question, and this time the answer is an exhaustive check, not a
layout argument. The five `r` cells of room 0 pin where its incoming pipes
may attach. Enumerating every non-floor port position for p1 (east wall rows
2-5, roof cols 1-14) against the required bindings

    (3,5)->ring   (3,7),(3,9),(4,8),(5,13)->p1

leaves exactly three survivors: **roof cols 7, 8, 9**. But a roof port needs
the row-0 corridor for its approach, and the ring already owns row 0 end to
end (it must reach its own roof terminal at col 4 from the east). Two pipes
cannot share or cross the single corridor, and swapping the two (ring east,
p1 west) fails the bindings arithmetically ((3,7) flips to ring). The floor
— the only wall that satisfies everything — is exactly what flushing removes:
every floor port needs the cell below, and below is room 2's roof wall.

So the 2-row gap is load-bearing three independent ways: pipe minimum
length, r-cell bindings, and the row-0 corridor. AND the prize was zero
anyway: height 27 -> 25 with width still 27 leaves fp at 729 — in brackets
the width binds, and the width lives in room 2's interior.

I & O were re-confirmed wall-to-wall already (2-cell pipes, both).

### brackets b12: I and O pressed wall-to-wall, as asked — built, measured, recorded

Alexey did not accept the "already minimal" answer without seeing the pressed
layout, and building it taught the precise price of flushing an I/O room:

* **O flush is free.** O's west wall now touches room 0's east wall, and a
  straight 2-cell pipe drops from room 2's roof (col 17) into O's floor. All
  eight of room 2's send bindings re-verified. Score identical: 277,830.
  (`b12a_oflush.man`)
* **I flush costs one tick per character.** The pipe's start arrow must point
  away from the room it leaves, so with I's west wall against room 3's east
  wall the pipe cannot exit west — it exits I's floor, bends, and enters
  through room 3's south-east corner: 3 cells instead of 2, +1 tick latency
  per input value. 278,559 vs 277,830, 0.26% worse. (`b12_io_flush.man`)
  Corner entry itself is legal: the parser and judge both accept a terminal
  whose forward cell is a room's corner `+`.

Both recorded per the standing rule; neither submitted (one equal, one
worse). `b12a` (O flush) is the preferred base for whatever comes next.

Rule extracted: **flushing a room is free exactly when the pipe can leave
straight; if the flush forces the pipe around a corner, each extra cell is
a tick on every value that crosses it.** For an input room on a hot path,
that is a tick per character.

### brackets b13/b14: Alexey's row-7 question straightens both gap pipes

He asked two things: slide O right (done — pipe col 20, bindings verified,
score unchanged, `b13_oright`), and *how far right can the row-7 outgoing
pipe move?* The answer turned into a win:

* p1's **terminal** (room 0's floor) is pinned at col 8: the r at (3,7)
  needs p1 within distance 5, and at col 9 the distance ties with the ring
  at 6, and ties go to the ring by reading order. Cols {6,7,8} only.
* But its **source** (room 2's roof) is free to slide right to col 13 —
  and at col 8 it sits directly under the terminal, so the pipe becomes a
  **straight 2-cell drop**. p0 mirrors at col 6 (its roof port may be
  {6,7,8}, its floor port is free since room 0 has one outgoing pipe).
* Safety measured first: peak occupancy of both 5-cell gap pipes is **2**,
  so 2-cell capacity cannot deadlock.

All 17 bindings in both rooms re-verified empirically. Local 277,830 ->
**276,615** (-1.7 avg ticks: three cells of latency removed from each
direction of the room0<->room2 exchange). Submitted as brackets_11; live **484,532.65** (26/26).

The general form of the question, for the playbook: **a pipe's two ports
have separate freedom; when their legal ranges overlap in a column, the
pipe straightens to 2 cells.** Check the ports' ranges before accepting any
bent gap pipe.

## subset_sum_01 live: 91.77T -> 37.40T (2.45x), 20/20, 2316x2374

The bisection did it: Alexey's M4 judged each group of deletable lines in
~25 s (vs 32 min here), all 655 rows proved safe, 1330 of 3040 columns
proved safe, and height was the binder anyway -- so the safe set delivers
the FULL squeeze footprint (fp 13,293,316 -> 5,635,876) plus a tick
improvement from the safely shortened transport pipes. Three dead ends
paid for it: exact-length reinflation (router cannot rebuild 3-6k-cell
serpentines -- confirmed by three independent runs), occupancy measurement
(30+ hours of python sim), and the bare squeeze (deadlocks: storage pipes
cut). The lesson for the playbook: **when the judge is cheap, bisect
deletions with the judge instead of measuring occupancy.** Submission
76d036a9-77cc-401b-adc9-3295bd08674c.

## Night sweep (2026-07-27, standings-driven)

Point-hunting by rank-gap table instead of guesses. Results:

* **pathfinder_02**: full squeeze deadlocks (0/7, same class as subset-sum);
  row bisection finds 84 of 96 rows safe. fp 3,845,521 -> 3,508,129, live
  **17.55T -> 16.07T** (18/18). One group (rows 0-1694) is poison.
* **reverse_08**: standings showed the next team a mere 0.33% above us.
  reverse_07's ring was 19 cells against a measured peak of 16; 17 total
  deadlocks (the n=16 frame IS 17 values -- transit needs slack), 18 works:
  ring-in 6->5. Live **84,922.5 -> 84,423.95** (20/20) -- jumps the team at
  84,640 for ~0.004 rank points... and re-proves the margin rule: capacity
  floor = frame size + 1.
* **plotter**: shortened 4 transport pipes (+0.28%), live 1.664B -- but the
  team best (1.599B) is an artifact NOT in the repo. Lesson recorded: match
  standings score to a submit json BEFORE optimizing.
* **sort/tcp/llm/memory**: floors real (measured), tcp candidate handed to
  claude, llm blocked on git-lfs (flagged to codex), memory not worth it.

# FINAL: ICFPC 2026 closed 2026-07-27T12:00Z

**wheezards: 39th of 268, 24.592 points** (winner 31.766; 0.45 short of 37th).
triangle rank 1/268 absolute. Per-problem finals in the standings sweep above.

## This line's ledger (2026-07-26/27, ~24 hours)

| problem | start | final (line's part) | via |
|---|---|---|---|
| reverse | 472,346 | 84,424 (5.6x) | ring gen-2/3, step-ladder to 13x13, ring 19->18 |
| brackets | 836,345 | 484,532 (team took to 376,793) | fold, shift-ladder, trim-to-ports, dead cells, transport shortening |
| subset-sum | 91.77T | 37.40T (2.45x) | judge-driven bisection on Alexey's M4 |
| pathfinder | 17.55T | 16.07T | row bisection |
| handed off | — | tcp cand (+0.77%), matmul squeeze (claude 1.04x), llm flag | protocol |

## Lessons that transcend this contest (also in alexey-contest-playbook.md)

1. **Small measured steps beat designed end-states.** Twice a "structural
   proof" of impossibility fell to six recorded incremental moves. The move
   that matters often looks like a regression when made (brackets step 2).
2. **Measure, never infer**: occupancy probes distinguished storage from
   transport pipes and won points in BOTH directions (reverse capacity,
   brackets latency). Every "measured floor" claim by any agent was wrong
   at least once until re-measured after a layout change.
3. **When the oracle is cheap, bisect against the oracle** instead of
   modelling (subset-sum, pathfinder). When it is expensive, build a cheap
   static oracle first (resolveaudit: 68 s vs 15-min judges).
4. **Negative results, written up with numbers, are deliverables**: the
   packing floor (34 ticks/value, n<=16 is one short of the crossover), the
   2-register n^2/4 law, the capacity floor = frame+1. They stopped three
   agents from burning the same hours.
5. **Multi-agent worked through immutable messages + explicit write sets +
   new-file-only artifacts.** Every collision that DID happen (two
   reverse_06, two plotter_07) was caught by the same rule that fixed it:
   rename with owner prefix, never overwrite.
6. **Check the human's machine into the loop**: the M4 was 80x this box on
   judging; shipping a one-file resumable runner (phases skip on existing
   artifacts) turned the human into the compute tier.
7. Infra traps that cost real time: ssh-agent sockets rot (find the live
   one under /tmp/ssh-*), pkill matches your own command string, output
   piped through tail buffers forever, LFS pointers masquerade as
   artifacts, and always `python3 -u` for anything backgrounded.
8. **Optimize the artifact BEHIND the live best score** -- match
   standings.score to a submit json first (plotter lesson).
9. **Standings-driven targeting**: points live in rank gaps, not in raw
   scores. The cheapest rank of the night was 0.33% away.
