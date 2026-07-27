# History Lesson 82-square candidate

Date: 2026-07-27

## Result

`history_05` is a reproducible, live 82×82 successor to the accepted
83×83 `history_04`. It emits the exact canonical 2,810-byte output, passes
the strict parser and server-layout gates, and has footprint score 6,724.
This is 165 cells (2.40%) below the live score of 6,889.

- artifact: `submissions/history/history_05.man`
- generator: `src/littleman/history_82.py:build_history_82`
- SHA-256:
  `2c949d5b456dda5c72bd07970b4b0ca017cd2c01f8f72a32ee59189876a32d39`
- bytes: 6,736
- local public result: 1/1 in 1,701,676 ticks
- rooms/pipes/men: 6/5/5
- pipe lengths: `[2, 2, 2, 2, 34]`

## Live result

Submission `5e888ecc-91dc-4334-9706-a82eac255a71` completed at
`2026-07-26T23:42:11.673Z`: 1/1, 82×82, and score 6,724. This is a
2.395% live footprint reduction from `history_04`. The exact API response
is preserved in `submissions/history/history_05-submit.json`.

## Joint codec and slot search

An 82-column paired lookup can carry at most
`6 row-pairs × 76 cells = 456` literal cells. An 82-row stacked floorplan
allows only 66 three-word main rows, or 198 radix-128 words and 1,782
symbols. The dictionary and lookup order therefore have to satisfy both
bounds at once.

The search universe was every substring of length two through five occurring
at least twice in the canonical text. Starting from `history_04`, a
seed-`20260727` deterministic 30,000-step single-token replacement search
used the exact suffix-DP piece count as its primary objective and rejected
token sets whose minimum adjacent-width pairing cost exceeded 456. The
retained 56-token tuple is pinned in `history_82.py`; rerunning exact DP gives
1,763 symbols.

The 127 real lookup values plus the zero boundary are sorted into minimum-cost
equal-width pairs. A deterministic exact partition places their 456 cells
into six bins of exactly 76. Equal-width code-position swaps then make every
packed main literal signed-64-safe in both traversal directions. The result
uses 196 main words, plus two inert zero padding words, in 66 rows.

## Validation

Commands:

```bash
uv run pytest -q -n 0 tests/test_history_82.py tests/test_history_pack.py \
  tests/test_history_archive.py tests/test_history_compact.py
uv run --with ruff ruff check src/littleman/history_82.py \
  tests/test_history_82.py
uv run --with ruff ruff format --check src/littleman/history_82.py \
  tests/test_history_82.py
uv run python scripts/preflight.py \
  submissions/history/history_05.man history-lesson
```

Evidence:

- 24 focused History tests passed;
- independent suffix DP confirms the pinned dictionary minimum is 1,763;
- all 196 words unpack exactly to the main code stream;
- every one of the 127 nonzero lookup entries decodes to exactly one
  character or pinned token, with no missing or duplicate entry;
- reference decoding equals the canonical output;
- every archive literal fits signed 64-bit both forward and reversed;
- all twelve lookup rows carry exactly 76 cells;
- generator output is deterministic and byte-identical to the artifact;
- strict parse found six rooms, five pipes, and five men;
- server-compatible layout validation and the exact public judge passed.

## Freshness

Immediately before the candidate commit, `git fetch origin` found both the
branch base and `origin/main` at
`d9cf874c6480de1d43f7cd780f64a0bc06cf9681`.

The unfrozen History standings snapshot updated at
`2026-07-26T23:28:10.280Z` records `wheezards` at 1/1, score 6,889, tied
rank 20 among 151 rows. An authenticated read of exact baseline submission
`1cd10b25-d908-45b4-a210-dd316adf5e09` reconfirmed `done`, 1/1, 83×83,
score 6,889, with no load or runtime error.
