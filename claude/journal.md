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
