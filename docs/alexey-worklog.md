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

## 2026-07-24 — reverse_01: footprint 784 → 256, server score 1.95M → 472k

Generator `src/littleman/alexey_reverse2.py` (new file; `reverse.py`
untouched). Not a repack of reverse_00 — two machine changes removed the
rows, and both are reusable on any ring machine:

1. **Ring size in B, no `q`.** `q` misses values still in flight, which
   is the only reason reverse_00 carried a 4-row delay corridor. The
   pump now holds j in the off hand: `W b M` at the branch, `1 W - M`
   after the emit. Tracked counters cannot race — an early `r` just
   blocks. The decrement re-establishes B with an explicit `M`, so it
   does not depend on whether `-` preserves B (the cookbook and the
   simulator disagree there; this machine is correct either way).
2. **Test-before-relay skip loop.** `>rsv / ^ md` relays BP+1, so the
   old machine primed BP = j-2 and needed a separate j == 1 bypass lane
   plus a merge cell. Reaching the `d` first relays exactly BP times, so
   BP = j-1 covers every j including 1. Bypass lane, merge, and one `m`
   all gone.

Also: `@` moved onto an empty cell of the emit row, so the startup walk
(A=B=BP=0, heading east) falls through no-op cells into the load
prologue and no cell is spent on it; input and output both attach to the
pump's left wall; 17-cell serpentine ring-return under the pump.

- Validation: 8/8 public (avg 1162 ticks, local score 297,536), pipe
  resolution audited for all 7 send/receive cells, ring capacity
  asserted, 10 worst-shape + 250 randomized cases in
  `tests/test_alexey_reverse2.py`.
- Submitted `submissions/reverse-a-list/reverse_01.man` (sha256
  `e7666c52…`): **20/20, 16×16, area² 256, avgTicks 1845.1, score
  472,345.6** (submission `2168dd65-77a6-4168-83bc-6b2bb7d3d600`).
  reverse_00 was 1,950,905.6 → **4.13× better**.
- Catalogue: `submissions/reverse-a-list/alexey-variants.json`.

Gotcha worth repeating: the first render parsed as 5 pipes, not 4. The
ring-return's northward bend sat directly above the relay's top-left
corner, and corner attachment is legal, so the tail parsed as its own
pipe. Ending the leg one column earlier fixed it. Always assert the
pipe count.

### Next candidates

- memory (67×38, footprint 4489, 43.8M) — biggest remaining prize.
- tcp (38×41, 20.0M) — paired-value ring; both upgrades above apply,
  and its `q`-counted design has a corridor to delete.
- sort_03 could drop its corridor the same way (its ring size is also
  derivable), but the counter would have to survive the min-scan.

## 2026-07-24 — analysis: is a compacted 16-stage pipeline worth building?

Question raised: sort_00/01's systolic pipeline has 16 nearly-empty
rooms; compacted, shouldn't it beat the ring on ticks? Measured both on
identical single rounds (ticks to last output):

| n  | pipeline sort_01 | ring sort_02 | ring sort_03 |
|----|------------------|--------------|--------------|
| 1  | 1071             | 100          | 57           |
| 2  | 1119             | 202          | 135          |
| 4  | 1221             | 462          | 347          |
| 8  | 1444             | 1226         | 1015         |
| 12 | 1656             | 2274         | 1967         |
| 16 | 1877             | 3638         | 3235         |

The tick intuition is right only for n >= 12. The pipeline is linear
(53.7 ticks per token — that is one stage's cycle time, since stages run
in parallel and throughput is what matters) on top of a **1017-tick
fixed overhead** (~19 token-slots: 16 flush tokens plus the depth of the
16-stage chain). The ring is quadratic but starts near zero, so it wins
below n = 12 and loses 1.7x at n = 16. Public rounds are mixed-size, so
the average is not dominated by n = 16.

Where the 53.7 ticks go: the stage room is 14x20 with a 24-cell shared
return track (row 12 west, then col 2 north). A compact stage needs ~17
instruction cells (r, X, the reset chain `0 M 1 N s`, `-`, X, and the
three compare arms `+ s` / `+ s` / `W s + M`) plus routing, so ~30 cells
-> a 6x6 interior at best, and its return walk still costs ~10-14 ticks.
Realistic cycle: 15-20 ticks, i.e. a 3x speedup, not more.

Break-even against sort_03 (361 x 4032.52 = 1.456M):

| stage speedup | server ticks | break-even footprint | max dimension |
|---------------|--------------|----------------------|---------------|
| x2            | 2294         | 635                  | 25            |
| x3            | 1529         | 952                  | 31            |
| x4.5          | 1019         | 1428                 | 38            |
| x6            | 764          | 1904                 | 44            |

Sixteen rooms of 8x8 in a 4x4 grid with one-cell pipe gaps is already
35x35 = 1225, before the loader, gate and dispatcher (currently 12x45
and 15x56, both literal-heavy). So the achievable pair is roughly
footprint 1225-2000 at a 3x speedup = **1.9M-3.1M, worse than the
1.46M sort_03 already scores**. Winning would need footprint ~900 AND a
5x+ speedup simultaneously.

**Verdict: do not build it.** Footprint is squared and ticks are linear;
16 rooms cannot pay for themselves here. Recorded so nobody re-derives
it.

### The better lever for sort

Apply the reverse_01 treatment to the ring: no `q`, no delay corridor.
The obstacle is that sort's min-scan already uses B for the candidate
minimum, so the ring size cannot ride in B as it does in reverse_01.
Fix: circulate the count as an extra value in the ring itself — read it
first each cycle, re-send it last. That removes 3 corridor rows
(361 -> ~256-289) and the per-cycle corridor walk. Estimated score
~800-900k, i.e. 1.6-1.8x better, at a fraction of the pipeline's risk.
