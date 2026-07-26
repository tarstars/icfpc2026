# History Lesson 83-square release

Date: 2026-07-26

## Live result

`history_04` passed the contest server 1/1 at 83×83 and footprint score
6,889. It improves the previous 84×84 `history_03` by 167 cells (2.37%).
The next standings refresh moved `wheezards` from tied rank 28 to tied rank
19 and increased problem points from 1.81757 to 1.87838.

- artifact: `submissions/history/history_04.man`
- SHA-256: `d0b7083ffb78ceaa2b22bddc208a01b6ab1bceba0ebcbde8a8899b9ba35378ea`
- submission: `1cd10b25-d908-45b4-a210-dd316adf5e09`
- terminal response: `submissions/history/history_04-submit.json`
- accepted at: `2026-07-26T21:09:37.502Z`

## Changes

The old offline token selector rejected a candidate whenever it contained,
or was contained by, an already selected token. Replacement in the working
text already prevents conflicting occurrences, so this restriction was
unnecessary. Removing it reduces the exact suffix parse from 1,812 to 1,809
symbols. Those symbols fill exactly 201 nine-code radix-128 words.

Decimal literals must fit signed 64-bit both forward and reversed. Lookup
positions determine the main codes, so the encoder first assigns entries to
equal-width slots by chunk-start frequency and then makes three deterministic
equal-width swaps. All 201 resulting words are parser-safe without shortening
a chunk.

The replacement token set also has fewer wide packed values. Globally
width-adjacent pairs fit into six lookup row-pairs with payloads
`[73, 74, 77, 77, 77, 77]`. This gives a 14×83 lookup room. The 201 main
words need 67 data rows, giving a 69×71 main room. Stacking both rooms fills
the 83-row bound exactly.

The selector moved one column left so the lookup return pipe can retain its
left-facing terminal arrow without using column 83. The submitted artifact
contains one harmless orphan `<` at `(19, 80)`; the parser does not attach it
to a pipe and the server accepted the exact bytes. It is preserved to keep
the immutable artifact and generator byte-identical. Removing it alone would
not change the footprint or score.

## Validation

Commands:

```bash
uv run pytest -q -n 0 tests/test_history_pack.py \
  tests/test_history_archive.py tests/test_history_compact.py
uv run --with ruff ruff check src/littleman/history_compact.py \
  tests/test_history_compact.py
uv run python scripts/preflight.py \
  submissions/history/history_04.man history-lesson
```

Evidence:

- 19 focused tests passed and Ruff passed;
- exact canonical output passed 1/1 in 1,758,189 local ticks;
- footprint and local score are 6,889;
- generator output is byte-identical to the artifact;
- six rooms, five men, and five pipes of lengths `[2, 2, 2, 2, 35]`;
- server-compatible layout validation passed;
- all 201 words independently unpack to nine nonzero codes and concatenate
  exactly to the 1,809-code main stream;
- all 331 nonempty literals fit signed 64-bit forward and reversed;
- generation was deterministic under five distinct `PYTHONHASHSEED` values.

An independent read-only agent reran the codec, room-stream, layout, parser,
determinism, and exact-judge checks and found no release defect.

The mandatory freshness read at `2026-07-26T21:08:05.786Z` found the
scoreboard unfrozen and the live team baseline still at 1/1, 84×84, score
7,056. The exact baseline submission was also refreshed before release.
The unfrozen `2026-07-26T21:10:05.734Z` refresh records the accepted 6,889
score at rank 19 among 150 teams.
