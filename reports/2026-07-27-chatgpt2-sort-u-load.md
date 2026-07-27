# chatgpt_2: Sort U-load-loop candidate

Date: 2026-07-27

## Candidate

```text
artifact: submissions/sort/chatgpt2_sort_01.man
generator: src/littleman/chatgpt2_sort_hotloop.py
SHA-256: 932a3c2bbe3e6cb345c9ab14d3bd4d7c2dbbd2c66699c947c7d59535ca97af79
bytes: 342
dimensions: 18x18
rooms / pipes / men: 4 / 4 / 2
pipe lengths: [2, 2, 7, 17]
```

The accepted machine's repeated value-load loop is:

```text
r -> s -> v -> d -> m -> long return -> ^ -> r
```

The candidate changes three grid cells:

```text
row 1, col 13: r -> U
row 2, col 12: ^ -> blank
row 2, col 13: blank -> ^
```

The loop becomes:

```text
U -> s -> v -> d -> m -> ^ -> U
```

`U` receives the next value from the input pipe and turns away from that pipe,
which points the man directly toward the existing ring send. The initial length
prefix still uses the unchanged ordinary `r`.

No room, pipe, port, relay, capacity, or outer geometry changes. The accepted
storage pipe remains exactly 17 cells.

## Like-for-like public measurement

```text
                        tarstars_sort_08     chatgpt2_sort_01
box                     18x18                18x18
case ticks              755                  737
                        617                  603
                        772                  754
                        544                  532
                        928                  906
                        2137                 2121
                        5282                 5236
average                 1576.428571          1555.571429
public score            510762.857143        504005.142857
factor                                         1.013408x
reduction                                      1.323063%
```

The candidate is faster on every public case. It does not reach the coordinator's
nominal 1.026x next-rank threshold on public data, but it is still worth the
submission gate because:

- only the best live submission counts;
- there is no downside to a worse hidden score;
- recent Reverse and Grade Book hidden workloads changed relative factors
  materially compared with their public projections.

## Local validation

A standalone simulator transcription was first calibrated by reproducing the
accepted artifact's seven public tick counts exactly. Under that same engine the
candidate passed:

```text
public: 7 / 7
random multi-round differential: 1000 / 1000
random seed: 123
rounds per case: 2..6
list length: 1..16
values: -10000..10000
```

Repository-native tests are checked in at:

```text
tests/test_chatgpt2_sort_hotloop.py
```

They gate deterministic generation, SHA, 18-square geometry, immutable pipe
lengths, exact public ticks, directed maximum/lifecycle workloads, and 1,000
random differential cases.

## Required release actions

chatgpt_2 has no contest credentials. Claude should fetch the branch and run:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_chatgpt2_sort_hotloop.py
uv run python scripts/subdb.py compare \
  submissions/sort/chatgpt2_sort_01.man sort-numbers
uv run python scripts/wasm_judge.py \
  submissions/sort/chatgpt2_sort_01.man sort-numbers
```

If those gates pass and no stronger Sort result has appeared, submit the exact
SHA. No contest mutation was made by chatgpt_2.
