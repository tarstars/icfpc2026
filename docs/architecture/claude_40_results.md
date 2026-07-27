# claude_40: main results, 2026-07-27 (final day)

Written at ~08:00Z, four hours before submissions close at 12:00Z.

## Live score changes shipped today

| problem | before | after | factor | rank | points |
|---|---|---|---|---|---|
| matmul | 8,436,652,022 | **5,931,034,966** | 1.42x | 53 -> 51 | +0.0263 |
| sudoku-validity | 11,307,342,643 | **9,290,407,668** | 1.22x | 74 -> 72 | +0.0230 |
| snake | 848,516,029 | **808,967,647** | 1.05x | 34 -> 33 | +0.0159 |
| tcp | 1,490,670 | **1,357,416** | 1.10x | 30 -> 29 | +0.0099 |

**About +0.075 points.** Two of the four were other agents' finished work
that nobody had submitted; two were mine.

Also submitted and correctly discarded: `tarstars_sort_09` scored 805,244
against a live 802,302. Only the best submission counts, so a worse one
costs nothing — which is why the right policy is to submit when in doubt.

## The most valuable thing I did was not building

**gpt's matmul and sudoku candidates were finished and unsubmitted**
because gpt has no contest API access. Fetching, judging, gating and
submitting them took about ten minutes each and returned **+0.049** —
better than anything I built from scratch all day.

**Codex ran out of tokens holding 20+ branches**, and the *last commit* on
two of them was a built, validated, never-submitted artifact. One was worth
a rank on tcp. `scripts/stranded.py` sweeps every ref for
`submissions/*.man` with no sibling `-submit.json`; that is how it was
found.

**Lesson: ask who cannot ship, and go collect from them.**

## The field is moving faster than we are

Measured at 04:00Z and again at 07:50Z, with no submissions from us in
between:

    history 14 -> 17 (of 155)     lllm 18 -> 22        llm 35 -> 40
    pathfinder 45 -> 48           matmul 50 -> 52      memory 16 -> 17
    reverse 40 -> 42              snake 33 -> 35       plotter 58 -> 60

Total **24.750 -> 24.695**. Standing still costs rank in the endgame; the
architecture work below is the right long game but it does not defend a
position today.

**Triangle is rank 1 of 266** and has been all day.

## Findings that changed how we work

1. **`Y` is a real instruction our simulator never implemented.** gpt's
   Reverse machine scored 0/8 `bad-op` under `preflight.py` and 8/8 under
   the organizers' engine. Our own `claude/official-sim/NOTES.md` had
   documented `Y` and we never closed the gap, so **every `Y` machine has
   been invisible to our verification all contest**. Fixed by
   `scripts/wasm_judge.py`.

2. **`layout_ir` is not lossless.** `render(parse(t)) != t` on **12 of 88**
   artifacts. llm loses **353,369 cells**; history_06 — our live 81-square
   — loses 4,221. Every solver-shaped tool sits on this, and the failure
   mode is a machine missing instructions that still parses, still loads,
   and dies only in the judge. **This is the blocker under the whole solver
   stack.**

3. **The solver was frozen, not exhausted.** `Conn.exact` came from a
   layout-wide timing flag, so one `q` anywhere pinned every pipe: on llm,
   **231 of 231** pipes were length-exact when **6** touch a timing room.
   And an exact *length* was modelled as an exact Manhattan *distance*,
   which is a category error — a path at distance `d` can be `d`, `d+2`,
   `d+4`. Both fixed.

4. **Connection is positional, and that is why reshaping breaks.** `r`/`s`
   bind to the *nearest* pipe by distance from the man's own cell, so
   moving contents silently rewires the machine. A pathfinder fold that was
   geometrically perfect — box 1873 -> 813, pipe multiset byte-identical —
   deadlocked with all five men blocked on `r`. **462 of 497** of that
   room's I/O cells belong to a pipe whose cells straddle a cut line.

5. **Leaderboard clusters are ideas** (the user's framing). Grinding inside
   a cluster is nearly worthless; the payoff is at boundaries. matmul at
   **1.42x bought 2 ranks**; snake at **1.05x bought 1**.

6. **Routing is 12-66% of every tick.** Traced on memory: man 4 spends 66%
   of its steps on arrows and blanks, man 3 spends 53%. That budget is
   available without touching the algorithm or the box.

7. **The search landscape is flat then cliff-shaped.** memory's emptiest
   interior column still holds **six** glyphs, and slides are score-neutral,
   so six neutral moves must precede any gain. Greedy and annealing see no
   gradient — which is exactly why our tools found nothing and a human who
   can plan six moves found it by eye.

8. **Radix 128 packs nine symbols**, not eight; `128^9 - 1` is exactly
   `2^63 - 1`. The old test asked whether the radix *power* fit rather than
   the largest *value*, hiding a whole token slot while codex's live
   81-square already used it.

## Tools built

- `scripts/board.py` — every graded problem, our rank, the climb curve.
  (`standings` takes the problem UUID; a slug silently returns nothing.)
- `scripts/stranded.py` — sweep every ref for unsubmitted artifacts.
- `scripts/wasm_judge.py` — the organizers' WASM as judge; required for `Y`.
- `room_reflow.py` — strand analysis, `binding_map`, `bindings_preserved`.
- `room_lab.py` — behavioural contracts + **interface metadata** (which
  socket reaches which pipe, and `signature()` that ignores where it sits).
- `room_shrink.py` — shave a row/column only with proof.
- `room_compact.py` — path-aware, behaviour-preserving slides.
- Solver packages A/B/C — per-pipe timing, CP-SAT parity relaxation,
  `coil_to_length`.
- ~60 new tests, deliberately weighted toward the negative cases.

## Where I was wrong, corrected

- Told gpt a Reverse round can be 17 values. It cannot — I counted the
  length prefix; `max(len(out))` is 16. **gpt read the spec, I read the
  data, and gpt was right.**
- Told gpt break-even was box 20.8. It is **16** — I had compared their
  public-case ticks against a live average derived from the hidden set.
- Told the team to "stop asking what factor can I squeeze". Overcorrection:
  squeezing produced most of today's points.
- Called the pathfinder binding problem fatal, then a missing hand-off. It
  is a hand-off in general and **unsatisfiable for that particular room**,
  since a pipe has one endpoint pair and its cells straddle every cut.
- Measured zero blank rows in llm where gpt measured 2,448. My test was too
  strict; theirs was right.

## Open, in priority order

1. **`layout_ir` lossless** — blocks everything solver-shaped.
2. **lllm needs 1.006x** for a rank (+0.0167), the cheapest on the board.
   Its box is one room, 78x305; no deletable row exists, so it needs real
   compaction.
3. **The component library** — `docs/MANIFEST.md`, `claude_38` (Rust MCTS),
   `claude_39` (the transformation family).
4. **history 80-square** — symbols solved (1,724 <= 1,728) but lookup
   plateaus at 463 against a 444 budget.
5. **gpt's Reverse at box <= 16** — the idea is proven at 1.52x fewer
   ticks; only the geometry is missing.
