# Backlog, decomposed from today's results

Every task below is derived from a measured result on 2026-07-27, not from
speculation. Each has the evidence that produced it, an acceptance test,
and an estimate. Ordered by value per unit of work.

## A. The line-merge line (this produced 3 of today's 11 wins)

The method: many rooms are **snakes** — each logical instruction line
occupies two grid rows, a code row (`> ops v`) and a U-turn row
(`v ... <`). Merging line B's ops onto the end of line A deletes both
intervening rows. Iterate to convergence.

Results: **pathfinder 3.0x** (1873 -> 1130), **sudoku 1.379x** (131 ->
117), **lllm 1.202x** (311 -> 303, by the related merge+rail technique).

### A1. Band-aware op repack  — the measured ceiling
**Evidence.** On sudoku only 8 of 50 code rows merged. **20 were blocked
because row B's `s`/`r` sits LEFT of row A's last op**, and an I/O op
cannot move rightwards out of its nearest-pipe band without rewiring.
The agent verified this is a structural ceiling, not a tuning problem.
**Task.** Permit an I/O op to move across bands by *also* moving the pipe
endpoint it binds to, keeping the pairing intact.
**Accept.** sudoku merges >20 of 50 rows; `interface_preserved` stays `[]`.
**Worth.** sudoku alone 117 -> ~75 is a further ~2.4x. Probably applies to
every snake we have.

### A2. Parameterise the line-merge tool
**Evidence.** `scratchpad/pf2/iter*.py` hardcodes pathfinder's geometry
(walls at columns 80/262, `range(81,262)`). Porting it cost a subagent
real time on sudoku and again on plotter.
**Task.** One tool taking `(artifact, room_index)`.
**Accept.** Reproduces the pathfinder, sudoku and lllm results unchanged.
**Worth.** Multiplies every future application; small.

### A3b. Multi-room co-merge  — plotter's measured ceiling
**Evidence.** plotter merged only 2 rows, not the ~45 I predicted, and the
agent showed my premise was wrong: **room 0 is not the sole height bound.**
The left column (rooms 2-7 over rows 8-81, rooms 9/10 at 86-91, and the
fixed 27-row display at 98-124) is equally tall. A snake merge deletes
GLOBAL rows, so every column must be deletable at that row -- only
rows {2, 64-69, 94} are pass-through outside room 0, and only two line up
as a legal code/return/code triple.
**Task.** Merge SEVERAL rooms at the same global rows simultaneously.
Parity does align (e.g. A=28 is a valid merge in both room 0 and room 4).
**Accept.** plotter reaches box ~110 (a further ~1.25x).
**Worth.** Machinery already exists at `scratchpad/plmerge.py`, which is a
multi-room port of `pf2/iter6`.
**Dead ends confirmed, do not repeat.** Deleting display/input room rows
changes the canvas and fails 0/6 wrong-output. Free re-layout of plotter
"reaches 129 and cannot be routed at any margin"; floorplan-preserving
compaction moves it only 185 -> 183.

### A3. Snake detector
**Evidence.** I checked "is it a snake?" by eye three times today
(pathfinder, sudoku, plotter — all yes). memory and tcp are not.
**Task.** A predicate over `room_reflow.walk_graph`: does the interior
alternate code row / U-turn row?
**Accept.** Correctly classifies all 16 live artifacts.
**Worth.** Turns a manual judgement into a sweep; ~1 hour.

### A4. llm — line-merge does NOT apply. Serpentine the mega-pipes instead.
**Evidence (verified, both candidates deadlocked at the 50M tick cap).**
llm's giant room IS the same snake and merges 10,024 -> 8,360 rows. But
**only 73 of 25,797 rows carry no pipe cell.** Two mega-pipes blanket the
entire height -- **pipe 230 is 12,597 cells over rows 13,416-25,729, pipe
5 is 10,164 cells over rows 224-10,264** -- so essentially every row
deletion shortens a pipe. Runs shortened **153 of 231 pipes**, mean 17.6%,
worst 480 -> 26. llm is `timing_sensitive`, and that is the deadlock.
gpt's 2,448 vertical-continuation rows have the same defect: reproduced
exactly, and they cost 8,884 pipe cells.
**The actual lever.** Re-route pipes 5 and 230 as serpentines at EXACTLY
their current length (a comb adds 2w cells per 2 rows, and the canvas is
1.17% occupied), then repack rooms in 2D. Rooms sum to 25,187 rows of
height in a 749-wide canvas, so a 3-column packing bounded by the
10,024-row giant room lands near **box 10,100, about 6.5x**.
**Reusable result.** A clean literal rule pathfinder lacked: the giant room
has exactly **4 backtick columns (29, 34, 63, 68), each holding only
backticks and spaces**, plus 38 fully-empty columns. Reserve tick-only
columns and place digits only in non-tick columns, and vertical pairing is
provably content-invariant.
**Also.** An independent CFG checker (`scratchpad/llm/cfgeq.py`, no
simulation) caught a genuine bug in the agent's own merge -- `r` became `M`
in rooms 17, 58, 76, 85. **Build the checker; do not trust the transform.**

## B. Register pressure — the real constraint, found twice today

**The backpack has no read port.** `b` writes it, `m`/`]` modify it, `q`
loads it from a pipe count, and `d`/`a`/`x` read it *only* as a branch
condition. It cannot be moved to A or B.

That single missing op is what makes both of the following conditional.

### B1. Register liveness analysis
**Evidence.** Both B2 and B3 below are safe exactly where A/B/BP are dead,
and we currently cannot tell.
**Task.** Extend `room_reflow.walk_graph` (already a `(cell, direction)`
graph) to track which registers are live at each state.
**Accept.** For any cell, reports live/dead for A, B, BP.
**Worth.** Unblocks B2 and B3; the prerequisite for both.

### B2. Delay loops instead of delay distance
**Evidence.** `docs/architecture/claude_42_delay_loops.md`. Measured:
plotter's man walks **119 blank cells at a stretch, with 1,642 runs of
>=4**; memory tops out at 19 and tcp at 9.
**Task.** Replace a straight delay run of N cells with an arrow cycle of L
cells containing `m` and a corner `d`, counted by the backpack: `L*K + r`
ticks in `L` cells. **Space O(N) -> O(L).**
**Accept.** A machine whose delay run is replaced keeps its tick count and
loses width; contract unchanged.
**Worth.** Plotter-shaped. **And it is what gpt's Reverse Y-farm needed** —
its delays are private path lengths totalling `W^2 = 256` cells at W=16,
which is exactly why a proven 1.52x algorithm could not fit its box.

### B3. Split a tall room into several shorter ones
**Evidence.** Men cannot cross walls, so a split means splitting the WALK
between two men, handshaking over a pipe. Room B's `@` starts blocked on
`r` — the pattern already used everywhere.
**Task.** Cut at a low-crossing line; room A `s`-sends live state, room B
`r`-receives and continues; a second pipe for the return.
**Blocked by.** **BP cannot be transferred** (no read op), so this is legal
only where BP is dead — hence B1.
**Accept.** llm's 82x10,024 room becomes four 82x2,506 side by side:
box 10,024 -> 2,506, a **0.0625x** factor.
**Worth.** Potentially the largest single transformation available, and
**strictly more general than line-merging**, which only works on snakes.
**Caveat.** `strand_profile` gives strand COUNT, not traversal FREQUENCY.
One strand crossed 10,000 times is one strand and ten thousand handshakes.
Measure both.

## C. Correctness debt that silently costs submissions

### C1. `layout_ir` is not lossless
**Evidence.** `render(parse(t)) != t` on **12 of 88** artifacts. llm loses
**353,369 cells**; history_06, our live 81-square, loses 4,221.
**Why it matters.** A re-emitted machine missing instructions still parses,
still loads, and dies only in the judge. Everything solver-shaped sits on
this.
**Accept.** 88/88 round-trip, and `layout_gate` refuses anything that does
not.

### C2. Our loader is too permissive
**Evidence.** `reverse_02`, `reverse_03`, `sort_05`, `triangle_03` pass
locally; the organizers **refuse to load them** ("pipe runs into a room
wall", "input room has more than one outgoing pipe", "pipe interrupted").
**Why now.** Any generative search will emit unsubmittable machines.
**Accept.** `sim.Machine.parse` raises on all four.

### C3. `Y` unimplemented in `sim`/`fastsim`
**Evidence.** `bad-op` on any splitting machine, so gpt's whole Y-farm line
was invisible to our fast judge all contest. Official spec now captured in
`docs/language-reference-updates-2026-07-27.md`.
**Accept.** `reverse_fresh_23.man` judges 8/8 at avg 206.375, matching the
WASM.

### C4. `wasm_judge` cannot judge display problems
**Evidence.** It decides on `outputSettled`, which flips true even with
corrupted frames — proved on `palette_00`. It now refuses on lllm, llm,
palette, pathfinder, plotter, snake.
**Accept.** Pass frames through `harness.mjs` and read
`frameJudge:{matched,total}`.

### C5. `validate_io_pipe_counts` too strict
**Evidence.** Mine. Rejects `matmul_05`/`matmul_06`, which the WASM loads
and passes 7/7.
**Accept.** Both load; no currently-valid artifact starts failing.

## D. Layout solver

### D1. Router cannot price right-angle crossings
**Evidence.** tcp is **66% used** with an ideal square of 24 against a live
box of 29. `place_and_route` reaches only 29x29 and reports "2 right-angle
CROSSINGS, which no single-layer router can price apart". **The placer is
fine; the router is the limit** — which corrects M2's "L0 is exhausted".
I tried detour-breaking and it made channel 1 worse (2 shared -> 36);
reverted.
**Accept.** tcp routes at box <= 26.

### D2. Room re-packing (the user's observation)
**Evidence.** pathfinder's rooms are stacked in a column with width 267
barely used; everything below row 941 could sit to the RIGHT of room 0.
Box 1130 -> ~942, about 1.44x. An agent is on it now.
**Accept.** Re-placed machine, `interface_preserved` `[]`, preflight 7/7.

## E. Process, which produced 8 of 11 wins

**Eight of today's eleven live improvements were other agents' finished
work that only needed someone able to judge and submit it.** gpt had no
API access; codex ran out of tokens mid-branch; codex_3's runtime could
not execute the repository at all.

### E1. Keep `scripts/stranded.py` in the loop
Sweeps every ref for `submissions/*.man` with no submit record. Found
codex's tcp win.

### E2. Keep `scripts/subdb.py compare` as the gate
Measures candidate and live machine with the same judge in the same run.
It is the fix for the bug that bit four of us in **both** directions —
comparing a public-case number against a live hidden score.

### E3. Handoff protocol for agents that cannot execute
codex_3's model, which converted twice: **a generator, a decisive command,
and an explicit warning not to trust their own unverified numbers.** Eleven
minutes from handoff to live. Two failure modes to fix in it: document the
flags the parser actually takes, and commit every file the script imports.
