# STATE — read this first after any context flush

Updated: 2026-07-24

## Where we are

Contest started 2026-07-24 (runs Jul 24–27). The task is the **littleman
language**: 2D ASCII-grid programs (`.man` files) where "little men" (`@`)
walk rooms executing single-character instructions, communicate via pipes
between rooms, do I/O through special I/O rooms, and draw on an LM-75
display (max 64x64, 16 colors, double-buffered).

Textbook archived at `docs/textbook.md` (reconstructed from the site's JS
bundle — the site is an SPA, plain curl gets an empty shell). Includes a
compiled instruction table. NOT yet captured: `/language-reference`,
`/grading`, `/problem-sets`, `/editor-help` — these hold the exact
semantics, scoring, and the actual problems. Get them next.

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

## Next action

1. Capture `/language-reference` (exact semantics: pipe "nearest" rules,
   tie-breaking, full instruction set), `/grading` (scoring!), and
   `/problem-sets` (the actual problems). Same SPA-bundle extraction trick
   works; also check for a JSON API behind the app.
2. Then: build a littleman simulator/interpreter locally (the judge runs
   these programs; we need a fast local one to iterate), plus a program
   generator/assembler — hand-writing 2D ASCII is not scalable.
3. Update `docs/current-state.md` with constraints and scoring once known.

## Open questions

- What language/stack will the task favor? (Decide only after reading it.)
- Is YT access working for this project? (Probe before the first big job.)
