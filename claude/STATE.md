# STATE — read this first after any context flush

Updated: 2026-07-24

## Where we are

Contest started 2026-07-24 (runs Jul 24–27). The task is the **littleman
language**: 2D ASCII-grid programs (`.man` files) where "little men" (`@`)
walk rooms executing single-character instructions, communicate via pipes
between rooms, do I/O through special I/O rooms, and draw on an LM-75
display (max 64x64, 16 colors, double-buffered).

All contest docs archived in `docs/`: textbook, language-reference (exact
semantics incl. tick order, pipe parsing/targeting rules, 64-bit wrapping),
grading, rules, api. All 16 problem specs + public tests in
`data/small/problems/` (fetched via public API; needs a browser User-Agent,
plain urllib gets 403).

Key scoring insight: score = max(width,height)² × avg ticks → COMPACT
programs matter as much as fast ones. Points: test-fraction (up to 1) +
ranking vs other teams (up to 1) per problem. Must pass ≥1 private test to
be eligible (API currently reports privateTestCount 0 for all — likely
just not disclosed). Rounds share one program run — no reset between
rounds; judge withholds later input until earlier output is produced.

## Ground truth I must not forget

- Repo root: `~/prj/icfpc2026`. My area: `claude/`. Don't touch `codex/`.
- Bulk data goes ONLY through the symlinks (`artifacts/`, `outputs/`,
  `yt_work/`, `data/generated/`, `data/external/`) backed by the USB disk
  labeled `medium_data`. Before ANY bulk write:
  `python3 scripts/check_external_storage.py --required-free-gib <GiB>`
  If it fails — stop, don't improvise a local directory.
- Policies live in `AGENTS.md`; shared status in `docs/current-state.md`.
- Never search inside `~/prj/arc00` or `~/prj/arcadia`.
- YT cluster root: `//home/delivery_ml/research/tarstars/icfpc2026` — use for
  CPU work >~1h; credentials not yet probed.
- Current branch: `agent/initialize-contest-workspace` (main is `main`).

## In progress

Nothing mid-flight. Last action: initialized this `claude/` area
(2026-07-24).

## Toolchain (working)

- Python project at repo root, uv-managed (`uv run pytest`, 27 tests).
- `src/littleman/sim.py` — full simulator (no display support yet).
- `src/littleman/judge.py` — round gating, streaming compare, scoring.
- CLI: `uv run python -m littleman <prog.man> <slug>` judges against
  `data/small/problems/<slug>.json`.
- `submissions/triangle/triangle.man` — VERIFIED 6/6, 14 ticks, score 1134.

## Next action

1. Cross-check triangle in the web editor, submit it (needs team API key —
   user must register), record submission id.
2. Memory: implement unpacked ring + head pointer per the design discussed
   (see journal 2026-07-24); measure, then decide on 3-per-word packing.
3. Display support in simulator (needed for palette/plotter/history-lesson).
4. Longer term: codegen/assembler layer emitting compact 2D layouts.

## Open questions

- What language/stack will the task favor? (Decide only after reading it.)
- Is YT access working for this project? (Probe before the first big job.)
