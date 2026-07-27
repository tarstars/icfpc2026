# claude_41: backlog at 11:00Z, one hour before submissions close

## Live right now

Board: **24.7 of 32**, rank ~39 overall, 16/16 problems fully passing,
**triangle rank 1 of 266**.

Shipped today, all verified like-for-like before submitting:

| problem | before | after | factor |
|---|---|---|---|
| brackets | 484,533 | **376,793** | 1.286x |
| matmul | 8,436,652,022 | **5,931,034,966** | 1.42x |
| sudoku | 11,307,342,643 | **9,290,407,668** | 1.22x |
| snake | 848,516,029 | **808,967,647** | 1.05x |
| tcp | 1,490,670 | **1,357,416** | 1.10x |

**Three of the five were finished work nobody had submitted.** That
remains the highest-return activity of the whole contest.

## MARKED FOR IMPROVEMENT: tcp ("Packet Reassembly") — the user's call

Live `tarstars_tcp_11`, 29x28, box 29, **1,357,416, rank 29/104**.

The user is right that it is airy, and the numbers back it:

    room area 527 + pipes 30 = 557 of 841 cells  ->  only 66% used
    ideal square for that content: 24x24
    row occupancy: [19,8,19,19,17,11,11,16,22,18,6,5,5,17,21,19,...]
                                              ^^^^^^^ rows 10,11,12

**Rows 10-12 hold 6, 5 and 5 glyphs** — the gap between room 0 (rows
0..9) and room 4 (rows 14..27). Room 1 spans rows 0..16 on the right,
room 5 sits at rows 17..21.

A 24x24 pack would be `(24/29)^2 = 0.685x` -> about **930,000**.

**Why it is a good target:** tcp is **not timing-sensitive** (0 of 7 pipes
length-exact), so pipes may lengthen freely, and `layout_ir` round-trips
it **byte-exact** — the two preconditions the solver needs.

**Why the solver did not take it today:** `place_and_route` reaches only
29x29, no better than the hand layout, and reports why —

    conn 0: 2 cells still shared (2 right-angle CROSSINGS,
    which no single-layer router can price apart)

So the **placer is not the limit; the router is.** Two pipes need to cross
at right angles and a single-layer grid router cannot separate them. That
is a concrete, bounded routing problem — not a vague "make it smaller".

**Next step for whoever picks this up:** teach the router to resolve
right-angle crossings (detour one pipe around the other, which is free
here because no pipe is length-exact), then re-run `place_and_route`. The
budget says 24x24 is reachable and it is worth roughly 1.46x.

## Open work, in priority order

1. **`layout_ir` is not lossless** — `render(parse(t)) != t` on 12 of 88
   artifacts; llm loses **353,369 cells**, and history_06, our live
   81-square, loses 4,221. Every solver-shaped tool sits on this. A
   re-emitted machine missing instructions still parses, still loads, and
   dies only in the judge.
2. **The router cannot price right-angle crossings** — the specific thing
   blocking tcp above, and probably others.
3. **Our loader is too permissive.** `reverse_02`, `reverse_03`,
   `sort_05`, `triangle_03` pass locally and the organizers **refuse to
   load them** ("pipe runs into a room wall", "input room has more than
   one outgoing pipe", "pipe interrupted"). Any generative search will
   produce unsubmittable machines until `sim.Machine.parse` enforces
   these.
4. **`validate_io_pipe_counts` is too strict** — mine. It rejects
   `matmul_05`/`matmul_06`, which the WASM loads and passes 7/7.
5. **`Y` is unimplemented in `sim.py`/`fastsim`** — `bad-op` on any
   splitting machine. The official spec is now captured
   (`docs/language-reference-updates-2026-07-27.md`); the WASM is the
   stopgap.
6. **`wasm_judge.py` cannot judge display problems** (lllm, llm, palette,
   pathfinder, plotter, snake) — it now refuses rather than answering
   wrongly. Fixing it means passing frames through `harness.mjs` and
   reading `frameJudge:{matched,total}`.
7. **The component library** — `docs/MANIFEST.md`, `claude_38` (Rust
   MCTS), `claude_39` (the path-aware transformation family). The long
   game, and the right one.

## Cheapest remaining points, measured

    lllm        1.006x  ->  +0.0167   box comes from ONE 78x305 room
    brackets    22x22   ->  +0.032    assigned to chatgpt_1
    pathfinder  1.053x  ->  +0.0172   biggest per-rank value on the board
    sort        1.026x  ->  +0.0070
    history     1.025x  ->  +0.0065   80-square: symbols solved (1,724 <=
                                      1,728), lookup stuck at 463 vs 444

## Closed today, worth not re-deriving

- **The wall rule**: one grace tick — the man enters, the fatal fires next
  tick after pipe-shift and emit, no drain. Now implemented in `sim`,
  `fastsim` and the C extension.
- **`preflight.py` over-accepted** on wall; the organizers' WASM is the
  oracle for value problems.
- **Rust is certified** for `run_official` below ~1.2M ticks/case.
- **`scripts/subdb.py compare`** makes the like-for-like comparison the
  easy one — the bug that bit four of us in both directions.
