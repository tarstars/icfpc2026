# STATE — read this first after any context flush

Updated: 2026-07-24

## Where we are

Pre-contest. The ICFPC 2026 task has **not** been published. The workspace
scaffold is done (layout, policies, external storage, Git LFS). No language,
toolchain, or solver exists yet — deliberately.

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

Wait for contest materials. The moment they arrive:

1. Archive the original statement + inputs with checksums (bulk copies go to
   `artifacts/`, small reviewable pieces to `data/small/`).
2. Distill constraints, scoring, and the submission interface into
   `docs/current-state.md`.
3. Pick the smallest toolchain that fits; write parser/validator + tiny
   fixtures FIRST, then a deterministic baseline, then optimize.
4. Set up one reproducible submission command; record it here.

## Open questions

- What language/stack will the task favor? (Decide only after reading it.)
- Is YT access working for this project? (Probe before the first big job.)
