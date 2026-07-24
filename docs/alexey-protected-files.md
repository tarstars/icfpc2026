# Alexey-specific: protected files (do not edit)

Session note for Alexey's research line (2026-07-24). To avoid merge
conflicts with teammates, **none of the files below may be modified** in
this line of work. All new documentation, notes, catalogues, and results go
into **new** files, preferably prefixed `alexey-` (docs) or added as new
variant files (submissions). Committing new files, including contest
solutions, is fine.

Snapshot of tracked files at session start (git `main` @ 2bc008d):

## Policy / shared state (never touch)

- `AGENTS.md`, `README.md`
- `docs/current-state.md`, `docs/storage-and-compute.md`
- `docs/api-tools.md`, `docs/api.md`, `docs/grading.md`,
  `docs/language-reference.md`, `docs/rules.md`, `docs/textbook.md`
- `claude/README.md`, `claude/STATE.md`, `claude/journal.md`,
  `claude/thinking.md`
- `codex/` (entire directory — other assistant's area)

## Data and reports

- `data/small/problems/*.json` (all 16 specs + index)
- `reports/2026-07-24-history-lesson.md`
- `reports/2026-07-24-packet-reassembly.md`
- `reports/2026-07-24-sort-pipeline.md`

## Source and tests

- `src/littleman/`: `__init__.py`, `__main__.py`, `brackets.py`,
  `canvas.py`, `history.py`, `judge.py`, `max_element.py`, `memory.py`,
  `reverse.py`, `sim.py`, `sort.py`, `sort_ring.py`, `tcp.py`
- `src/icfpc_api/`: `__init__.py`, `cli.py`, `client.py`
- `tests/` (all existing test files)
- `scripts/check_external_storage.py`
- `pyproject.toml`, `uv.lock`, `.gitattributes`, `.gitignore`,
  `.env.example`

## Submissions (immutable by project rule anyway)

- `submissions/*/` existing `.man` files, `variants.json`, `README.md`,
  `manifest.json` for: brackets, history, max-element, memory,
  reverse-a-list, sort, tcp, triangle

## Where new work goes instead

- New docs/notes: `docs/alexey-*.md`
- New solution variants: new `.man` files in the relevant
  `submissions/<problem>/` (e.g. `sort_03.man`) — never overwrite old ones
- Variant metadata: since shared `variants.json` files are protected in
  this line, record variant metadata in `docs/alexey-worklog.md` or a
  per-problem `alexey-variants.json` (new file)
- New generator code: new modules like `src/littleman/alexey_*.py`
- New tests: new files like `tests/test_alexey_*.py`
