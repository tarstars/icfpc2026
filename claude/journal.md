# Journal — append-only

## 2026-07-24

- Reviewed the freshly initialized workspace (scaffold by Codex): layout,
  AGENTS.md policy, external `medium_data` storage, Git LFS.
- Initialized `claude/` as my context-flush-safe area: README.md (structure),
  STATE.md (re-entry snapshot), thinking.md (scratch), journal.md (this).

- Contest is live (Jul 24–27). Read https://icfpcontest2026.com/textbook —
  it's an SPA, so extracted the content from assets/textbook-9zWRf841.js.
  Archived reconstruction with all example programs and an instruction
  table to docs/textbook.md. Task: the "littleman" 2D ASCII language.
- Captured the rest of the contest docs from SPA bundles: language
  reference (exact semantics), grading, rules, API. Fetched all 16
  problem specs + public tests via the public API (needs browser UA) into
  data/small/problems/. Updated docs/current-state.md with contest facts.
- Built the littleman simulator TDD-style with uv/pytest: core engine,
  pipes/IO, literals, backpack, judge harness with round gating and
  footprint-tick scoring, CLI (python -m littleman). 27 tests green.
  Triangle solution verified: 6/6 public cases, 14 ticks, score 1134.
- Memory solved: pipeline-of-rooms machine (P2 parse -> P3w/P3r ring
  stations, P4 head-pointer loop, relay+init, 107-cell ring serpentine).
  Key ideas: rooms small so nearest-pipe resolution is trivial; command
  encoding k / -(k+1) with the involution N(x+1) so one entry row
  forwards correctly for both ops; `>rsv/^ md` loop relays BP+1 and
  exits with last value in A. 7/7 public tests, score 43.8M. v1
  unoptimized (footprint 4489 dominates; compaction + loop unrolling
  + 3-per-word packing are the levers).
- SUBMITTED both solutions, full marks on private tests too:
  triangle 0efa32a5 19/19 (9x9); memory 788c05a4 24/24 (67x38).
  Both problems are now score-golf: footprint x ticks vs other teams.
- Triangle optimized: n²+n then >>1 (rM*+M1W}s, 9 ops) in a 2x7
  interior: 81 x 13 = 1053 (was 1134). Submitted ff8567e2, 19/19.
  Argued floor: halving needs constant-load + W + op (3 cells), so
  8 instructions impossible; 8-wide room can't hold 13 cells.
- Reverse-a-list solved with shrinking-ring machine (pump+relay, 28x24):
  8/8 public, local 1.31M, submitted (server score 1.95M; id lost to
  tail-truncation — capture full submit JSON next time). New project
  rule adopted: .man files immutable, variants.json catalogue per
  problem. Teammate shipped Sort (pipeline, 25/25); ring skeleton is a
  candidate sort_02 (est ~1M vs their 34M local).
- sort_02: shrinking-ring min-scan (27x24, footprint 729), 7/7 local
  score 2.24M vs pipeline sort_01 ~31M local -> 14x better. Submitted
  799f0c93: 25/25, server score 3.46M. Catalogued in variants.json.
- max-element (practice): streaming max, no storage (running max in B),
  14x14 canvas, 10/10, score 29.6k. Halts after single output. New
  idiom: loop counter m ON the return row so prologue enters with BP=n.
- Brackets solved: base-3 packed stack (digits 1-3, depth 32 fits 64
  bits where base-4 would not), match+pop in ONE division (rem!=0 =
  mismatch, quotient = popped stack), push = M r W + + + (no literal).
  Three rooms: classify chain + OPEN/CLOSE stations, [S,p] circulating.
  Debug lessons: prologue cells must be off the racetrack (re-seeding
  bug); pipes must START with the arrowhead adjacent to the source wall
  (terminal arrowhead may be a bend, Canvas.pipe needs manual patch);
  teammate's stricter vertical-backtick pairing forbids X/W between
  aligned literal columns. 26/26 live 5690cc53, server 7.47M.
- Handoff written for less-powerful continuation: docs/littleman-
  cookbook.md (all verified idioms: register discipline, loop idioms,
  X geometry, pipe rules, FIFO discipline, shared cells, displays,
  debug ladder), claude/plotter-plan.md (full room-by-room plotter
  spec with build order), STATE.md rewritten as board + priorities.
  plotter.py flagged as broken sketch - rewrite from plan.
- Toolchain hierarchy written to docs/toolchain-plan.md with per-level
  APIs, implementation notes anchored to existing code, tests, and
  build order: L2 pipe-intent checker (1h) -> L3 symbolic reg/queue
  tracker (2-3h) -> L4 idiom macros -> L1 lane assembler (1d) ->
  L6 debugger; L5 dataflow compiler deferred post-contest. Principle:
  checks before generators.
- Wrote docs/synthesis-stack.md: top-down analysis of the user's
  three-tier compiler-stack idea. Core reframe: target is hardware
  synthesis (HLS + place&route), not software compilation; the
  "linker" is really place-and-route and is the flagship (footprint
  dominates). Latency-insensitivity (Carloni) gives correctness-
  separability under two conditions (no R/U; rigid small components =
  cookbook rule); cost does NOT separate (phase-ordering). Fork A
  soft-core (breadth/insurance for matmul/sudoku/subset-sum) vs Fork B
  synthesis (score); library serves both. Includes netlist schema and
  a pragmatic router build order (semi-auto compactor first = 80/20).
  Meets toolchain-plan.md at the netlist interface. ROI verdict: full
  stack net-negative this contest; harvest bottom+middle now.
- Plotter progress: adopted simpler v3 architecture (single Bresenham
  worker ring + 3-driver chain, vs the 11-room v2). Built ADDRDRV/
  DATADRV/SWAPDRV; VALIDATED ADDRDRV in isolation ([3,6,1,-1]->[2,5,0]),
  committed with test. Key driver idioms: forward token unconditionally
  BEFORE the X branch (lanes carry no sends, man parks on r); worker
  emits addr+1 so one X splits plot/end without addr=0 ambiguity;
  end/return lanes turn LEFT into a clean corridor; SWAPDRV discard
  returns via row3+left-riser to avoid crossing its swap-send. Wrote
  claude/plotter-worker.md: full v3 spec incl. Bresenham-on-addr
  reformulation and the honest finding that the 6-value/2-condition
  per-iteration lap needs a scratch pipe (memory-style) or a TEST/UPDATE
  room split. Worker build remains.
- Memory compaction started (memory_01, geometry-only). Relocated P4
  from top-right (cols48-66, sole cause of width 67) to the bottom,
  wrapping its 2 pipes up the right. Renders 47x46 (footprint 2209 vs
  4489, ~2x) but parse fails: the two wrap pipes collide near P2's
  right ports (bad glyph at (3,45)). Wrote claude/memory-compaction-
  handoff.md with the exact fix (route pipe B up col44 into P2 row3 with
  terminal '<' bend, keeping it disjoint from pipe A's col45), the
  7/7 verify checklist, submission steps (id d0b34a23...), and the
  follow-on 3-per-word packing idea. build_memory unchanged/submitted.
