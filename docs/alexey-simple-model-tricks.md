# Alexey-specific: littleman trick sheet for smaller models

Purpose: a compact, self-sufficient digest so a cheaper model (Opus/Sonnet)
can work on this contest without re-reading the big docs each session.
Maintained by the assistant; append new tricks as they are discovered.
Full semantics live in `docs/language-reference.md` — open it only for
exact edge cases (tick order, pipe targeting, literal parsing).

**Companion (read it too, it is authoritative):**
`docs/littleman-cookbook.md`, written by a teammate — register discipline
(which ops destroy B, `/` giving quotient+remainder, BP being write-only),
loop idioms, shared-cell rules. This file stays focused on **space golf,
workflow, and this machine's environment** and does not duplicate it.

## Contest rules in one breath

- ICFPC 2026, live 2026-07-24 → 07-27. Language: **littleman** — 2D ASCII
  grid programs (`.man`), little men `@` walk rooms, execute 1-char
  instructions, communicate via pipes, I/O через I/O-комнаты, дисплей
  LM-75 (64×64, 16 цветов, double-buffered).
- **Score = max(width, height)² × avg ticks** (lower = better); some
  problems footprint-only. So the SQUARE of the max dimension dominates —
  a 27-wide × 24-tall program pays 27², shaving 3 columns saves 21%.
- Values: signed 64-bit, wrapping. Deterministic. Tick cap usually 5M.
- Rounds share ONE program run — no state reset between test rounds; the
  judge withholds later input until earlier output is produced. The
  machine must return to a clean idle state after each round.
- Points per problem: test fraction (≤1) + rank vs teams (≤1). Best
  submission counts; ≤5 pending.

## Workflow (commands that work)

- Judge locally: `uv run python -m littleman <prog.man> <slug>` — slug is
  the file name in `data/small/problems/` (e.g. `sort-numbers`).
- Tests: `uv run pytest` (fast).
- Submit/poll: `uv run icfpc-api` (see `docs/api-tools.md`; creds in
  `.env`). ALWAYS capture the full submit JSON response (an id was once
  lost to output truncation).
- Verify the problem id from `data/small/problems/<slug>.json` before
  submitting.
- Project rule: submitted `.man` files are IMMUTABLE — new attempt = new
  numbered variant file (`sort_03.man`), never edit an old one.
- Alexey line: do not edit any file listed in
  `docs/alexey-protected-files.md`; write results to new `alexey-*` files.

## Proven machine idioms (reuse, don't reinvent)

- **Shrinking-ring machine** (reverse-a-list, sort_02): values circulate
  in a pipe ring between a pump and a relay; `q` (queue-length) + `]`
  count parked values; each pass extracts one element (min-scan for sort,
  tail for reverse); ring shrinks each pass. Generator:
  `src/littleman/sort_ring.py`, `src/littleman/reverse.py`.
- **Pipeline-of-rooms** (memory): keep each room SMALL so nearest-pipe
  resolution is trivial; stations do one step each; serpentine ring of
  storage cells. See docstring of `src/littleman/memory.py`.
- **Streaming, no storage** (max-element): keep the running aggregate in
  `B`, compare with `X`, never store the list. Put the loop counter ON
  the return row so the prologue enters the loop with `BP = n`.
- **Base-k packed stack** (brackets): pack stack digits 1..3 base-3 into
  one 64-bit word (depth 32; base-4 would overflow). Pop+match = ONE
  division: remainder ≠ expected → mismatch, quotient = popped stack.
  Push without literals: `M r W + + +` (x*3 + d via adds).
- **Command encoding** k / −(k+1): the involution `N(x)+1` lets one entry
  row forward both command kinds correctly (memory).
- **Radix-92 text packing** (history-lesson, footprint-only): each byte →
  nonzero digit `c−31`; offline DP packs digits into ≤18-decimal-digit
  words minimizing rows × literal cells; decode by repeated `/ 92`.
- **Bresenham on flat addr** (plotter design, unbuilt): line drawing with
  `addr = 32y + x`, steps ±1 / ±32, keep `E = 2*err` so all tests are
  plain comparisons — see `claude/thinking.md` tail before building.

## Sharp edges (bugs we already paid for)

1. **Prologue cells must be OFF the racetrack.** If initialization cells
   sit on the loop path, they re-seed state every lap.
2. **Pipes: the arrowhead must be ADJACENT to the source wall** at the
   start; the terminal arrowhead may be a bend. `Canvas.pipe` sometimes
   needs manual patching of the generated pipe.
3. **Vertical backtick literals**: the server parser pairs backticks in
   aligned columns more strictly than our sim — no `X`/`W` between
   aligned literal columns; use fixed-width slots so pairs align.
4. **Ring capacity**: a pipe holds ~its length in values; verify worst
   case fits (tcp needed ≥32, measured 38). Paths feeding `q` must be
   longer than a full ring round trip, or counts race.
5. Output truncation loses submission ids — pipe submit responses to a
   file.
6. Public API fetches need a browser User-Agent (plain urllib → 403).

## Space-golf checklist (footprint optimization)

- Footprint is `max(w,h)²`: only shrinking the LARGER dimension pays;
  aim for a square aspect.
- Interior whitespace inside rooms is pure cost — repack instruction
  cells; a room needs only its cells + walls + door gaps.
- Merge rooms when pipe-resolution allows; every wall pair costs 2 rows
  or columns.
- Literal constants are expensive (1 cell per decimal digit + backticks);
  prefer computing constants (`+ +` doubling, reuse of inputs) over long
  literals.
- After geometry changes, ALWAYS re-judge all public cases — moving cells
  changes walk timing, and tick counts shift.
- Bound check: triangle's argued minimum was 9 ops / 2×7 interior — think
  about the information-theoretic floor before golfing blindly.
- **Fold pipes, don't stretch them**: pipe capacity = its cell count, so
  a serpentine in dead space gives the same buffer as a wide loop
  without growing the bounding box (sort_03: 27×24 → 18×19 this way).
- **Feed I/O through side walls at the row where the machine needs it**
  instead of stacking I/O rooms above/below — saves whole row bands.
- Room walls can't be shared and a pipe needs ≥2 cells, so an I/O room
  beside a machine room costs exactly 2 columns of gap.
- Exiting a room's bottom wall costs one extra row (the first pipe cell
  must point away from the wall; a bend can't be the first cell). Exit
  through a side wall when the row budget is tight.
- Crossing paths through an EMPTY cell inside a room is free (the man
  keeps direction); use straight-through `>` cells to merge two paths
  entering a cell from different directions (sort_03's (3,10) serves
  the eastbound corridor and the northbound emit-climb at once).
- When shrinking delay corridors, re-derive the timing budget: every
  circulating value must be back in the q-counted pipe before `q` runs.
  Estimate walk ticks vs transit ticks (pipe cells + relay wait +
  travel), keep ≥8 ticks of margin, then stress-test hard.
- Minimal relay is 4×6 (2×4 interior loop). Place `@` so the man
  executes `r` before the first `s`, or it sends a spurious 0 (A=0)
  into the ring.

## Verification pattern for geometry changes

1. Rebuild via generator, print, eyeball the ASCII.
2. Judge all public cases (`judge_problem`).
3. Stress: `judge_case` on synthetic rounds at the constraint boundary
   (max n, all-equal, reverse-sorted, extremes, 2–6 rounds) plus a few
   hundred randomized cases — see `tests/test_alexey_sort_ring2.py` as
   the template.
4. Submit only after 100% local + stress; capture the full submit JSON
   to a file (`… > submissions/<p>/alexey-<v>-submit.json`).

## This machine (Alexey's box) — environment

- No `uv`. Use pyenv env `claude` (already `pyenv local claude`;
  `.python-version` is excluded via `.git/info/exclude` — do not commit
  it, do not edit `.gitignore`).
- Everything runs as `PYTHONPATH=src python3 …`:
  - tests: `PYTHONPATH=src python3 -m pytest -q`
  - judge CLI: `PYTHONPATH=src python3 -m littleman <prog.man> <slug>`
  - API: `PYTHONPATH=src python3 -c "from icfpc_api.cli import main;
    import sys; sys.argv=['icfpc-api', <args…>]; main()"`
- `httpx`, `typing_extensions`, `python-dotenv` are installed in the
  `claude` env; creds live in `.env` (never print/commit).

## Session hygiene for small models

- Read `docs/current-state.md` + this file first; skip the textbook.
- Don't re-derive solved machines — the generators in `src/littleman/`
  are ground truth; run them instead of hand-editing ASCII.
- One experiment = one new variant file + one metadata note; measure
  (local judge) before and after every change.
- If the sim and server disagree, suspect edges 2–3 above first.
