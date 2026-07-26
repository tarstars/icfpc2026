# History Lesson Asymmetric Archive

Date: 2026-07-26

## Result

`history_03` is the live 84×84 History Lesson program. It emits the canonical
2,810-byte text in 1,783,519 local ticks and has footprint score 7,056. This
is 169 footprint points (2.34%) below the preceding 85×85 `history_02`.

The generated source is
`submissions/history/history_03.man`, SHA-256
`170a48ebc149dae11a37437d9b0695590fbc8bc42527b41fb131a833b52c7de7`.

## Architecture

Offline exact suffix parsing uses 56 dictionary tokens, each at most five
characters. The main stream contains 1,812 symbols and packs into 204
parser-safe radix-128 words.

A cyclic 128-value lookup tape contains one value per character or token.
Character entries are their ASCII value. Token entries are complete
little-endian radix-128 words, so one output splitter handles both cases.
A compact selector synchronizes on lookup value zero, counts to the requested
entry, and sends the selected value to that splitter.

The floorplan uses:

- a 70×71 fixed-slot main room;
- a 14×84 paired-literal lookup room;
- two 17×8 splitters, a rotated 22×9 selector, and a 3×3 output room in the
  remaining right strip.

The paired lookup rows make every vertical backtick pair an empty literal.
All five pipes are at least two cells long.

## Validation

Commands:

```bash
uv run pytest -q tests/test_history_pack.py tests/test_history_archive.py \
  tests/test_history_compact.py
uv run --with ruff ruff check src/littleman/history_pack.py \
  src/littleman/history_archive.py src/littleman/history_compact.py \
  tests/test_history_pack.py tests/test_history_archive.py \
  tests/test_history_compact.py
```

Results:

- 19 focused tests passed;
- exact public output passed 1/1 in 1,783,519 ticks;
- local footprint score is 7,056;
- server-compatible layout validation passed;
- pipe lengths are `[2, 2, 2, 2, 36]`;
- generator output is byte-identical to the versioned artifact.

The mandatory freshness read at `2026-07-26T18:08:05.738Z` found the
scoreboard unfrozen and `wheezards` at 1/1, score 7,225, rank 29. Direct API
read of submission `b8426386-da64-4210-978d-f30b23b231a1` confirmed the
85×85 baseline with no load or execution error.

Submission `c11d1a93-6e1b-4dd1-92b7-55d9a2e7375a` then completed at
`2026-07-26T18:14:31.110Z`: 1/1, 84×84, score 7,056, with no load or runtime
error. The exact terminal response is preserved in
`submissions/history/history_03-submit.json`.

The unfrozen standings refresh at `2026-07-26T18:16:04.721Z` counted the new
score and moved `wheezards` from tied rank 29 to tied rank 26.
