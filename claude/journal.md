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
