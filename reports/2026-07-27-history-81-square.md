# History Lesson 81-square candidate

Date: 2026-07-27

## Result

`history_06` is a deterministic 81×81 successor to live `history_05`. It
emits the exact canonical 2,810-byte output and reaches footprint score
6,561, tying the current rank-13 score.

- artifact: `submissions/history/history_06.man`
- generator: `src/littleman/history_81.py:build_history_81`
- SHA-256:
  `95cadc619fa745a5fe90ed6925079e932992c6dec8f2fac6c9338771b883b899`
- bytes: 6,607
- public result: 1/1 in 1,667,288 ticks
- rooms / pipes / men: 6 / 5 / 5
- pipe lengths: `[2, 2, 2, 2, 32]`

This reduces the footprint from 6,724 to 6,561 (2.42415%). History Lesson is
footprint-only, so the tick change does not affect score.

## Joint codec search

An 81-square layout imposes two exact archive bounds:

1. 65 three-word main rows hold at most 195 radix-128 words, requiring at
   most 1,755 symbols;
2. six lookup row-pairs hold exactly 450 literal cells.

The previous dictionary needed 1,763 symbols and 456 lookup cells. The
deterministic simulated-annealing search in
`scripts/search_history_81.py` precomputes every repeated, parser-safe
substring of length 2–8 and uses exact suffix DP for every candidate
dictionary. The successful seed-804 run reached 1,754 symbols and exactly
450 lookup cells after 635,121 swaps.

The new dictionary includes a few longer high-gain entries (`Simon Pe`,
`yton Jon`) while using many cheap two-character entries. The 63 paired
lookup widths partition exactly into row payloads
`[70, 75, 75, 75, 75, 75]`; the five-cell zero-boundary pair fills the
remaining capacity in the first row.

## Geometry

The main archive drops from 66 to 65 rows and the lookup room starts at row
67. The output splitter and output room move one column left, freeing column
80 for the lookup-to-selector pipe. Its final cell is explicitly oriented
west so the vertical pipe turns directly into the selector's east wall.
This keeps the existing selector endpoint while fitting the machine in
81 columns.

## Validation

The focused suite proves:

- exact suffix-DP symbol count and 195 parser-safe main words;
- all twelve lookup rows contain exactly 75 cells;
- reference decoding equals the canonical output;
- exact generator/artifact parity and stable SHA-256;
- strict 81×81 parse, server layout, and pipe validation;
- 1/1 public output at the pinned tick count;
- unchanged `history_05` generation after the shared helper refactor.

Commands:

```bash
uv run pytest -q -n 0 tests/test_history_81.py tests/test_history_82.py \
  tests/test_history_pack.py tests/test_history_archive.py \
  tests/test_history_compact.py
uv run python scripts/preflight.py \
  submissions/history/history_06.man history-lesson
uv run --with ruff ruff check src/littleman/history_81.py \
  src/littleman/history_82.py tests/test_history_81.py \
  scripts/search_history_81.py
```

Immediately before commit, the branch was current with
`origin/main@25fe6a9`. Exact submission
`5e888ecc-91dc-4334-9706-a82eac255a71` remained done at 1/1, 82×82, score
6,724. The unfrozen `2026-07-27T01:06:10.368Z` snapshot placed `wheezards`
at rank 17; four teams tied rank 13 at score 6,561.
