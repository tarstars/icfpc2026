# Alexey research line — worklog

Append-only. Companion files: `docs/alexey-protected-files.md` (files this
line never edits), `docs/alexey-simple-model-tricks.md` (digest for
cheaper models). Focus: **space (footprint) optimization** of solved
programs.

## 2026-07-24 — sort_03: footprint 729 → 361, server score 3.46M → 1.46M

- Analyzed `sort_02` (27×24): width was driven by the ring-return pipe
  looping out to col 26 purely to reach 16 cells of capacity (n ≤ 16,
  one value per pipe cell), and by the input room sitting above a
  full-width delay corridor.
- Rebuilt the same machine compactly in
  `src/littleman/alexey_sort_ring2.py` (new file; `sort_ring.py`
  untouched):
  - input room feeds the pump's **left wall** at the entry row
    (−3 rows);
  - scan block shifted 5 columns left; climb col 10, descent col 11;
  - delay corridor reduced to 3 rows, load path joins row 3 eastbound,
    emit-climb rejoins via a straight-through `>` at (3,10);
  - relay reduced to 4×6 (2×4 interior loop; `@` placed so the man hits
    `r` before the first `s` — otherwise it injects a spurious 0);
  - ring-return folded into a 21-cell serpentine under the pump.
- Timing invariant kept (the fragile part): every circulating value must
  be inside the ring-return pipe before `q` executes. Estimated walks
  (~27 ticks post-load, ~55 ticks post-scan) vs worst transit (~19/~35),
  then verified empirically.
- Validation: 7/7 public via judge; 8 worst-shape + 300 randomized
  cases in `tests/test_alexey_sort_ring2.py`; full suite 69 passed
  (`tests/test_api_client.py` needs httpx, now installed).
- Submitted `submissions/sort/sort_03.man` (sha256 `3a56a95d…`):
  **25/25, width 18 × height 19, area² 361, avgTicks 4032.52, score
  1,455,739.72** (submission `cea48dba-bac0-4f99-bb19-7580c712535b`,
  full response in `submissions/sort/alexey-sort_03-submit.json`).
  Previous best `sort_02`: 3,460,708.8 → **2.38× better**.
- Catalogue: `submissions/sort/alexey-variants.json`.

### Environment notes (this machine)

- `uv` is not installed here; use the pyenv env `claude`
  (`pyenv local claude` is set; `.python-version` is kept out of git via
  `.git/info/exclude`, not `.gitignore`).
- Run everything as `PYTHONPATH=src python3 …` (pytest, judge CLI,
  generators). API CLI:
  `PYTHONPATH=src python3 -c "from icfpc_api.cli import main; import sys; sys.argv=['icfpc-api', …]; main()"`.
- Installed into the `claude` env: `httpx`, `typing_extensions`,
  `python-dotenv`.

### Possible next steps

- Same treatment for reverse-a-list (`reverse_00`, 28×24 → likely ≈18×19
  with the identical skeleton; server 1.95M).
- memory (67×38, score 43.8M): footprint 4489 dominates; canvas
  compaction is the big lever.
- tcp (38×41, 20.0M): ring is paired-value; same folding ideas apply.

## 2026-07-24 — merged teammates' work, pushed

- `origin/main` was 4 commits ahead (plotter v2, toolchain plan,
  littleman cookbook, synthesis stack). Zero file overlap with this
  line, so `git merge --no-ff origin/main` was clean.
- Full suite after merge: 75 passed. Pushed as `6572bea`.
- Protected-files list extended with the teammates' new files
  (`docs/littleman-cookbook.md`, `docs/toolchain-plan.md`,
  `docs/synthesis-stack.md`, `claude/plotter-plan.md`,
  `src/littleman/plotter.py`).
- The cookbook is now the authoritative semantics reference; the
  trick sheet points at it instead of duplicating register rules.
