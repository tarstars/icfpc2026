# handoff: `chatgpt1_reverse_09` reaches the score-positive 17-square frontier

- From: chatgpt_1
- To: claude
- CC: alexey, chatgpt_2, gpt, codex
- Created UTC: `2026-07-27T09:45:00Z`
- Task: `20260727-chatgpt1-reverse-17`
- Branch: `agent/chatgpt-1-solvers`
- Requires acknowledgement: YES

## Exact artifact

```text
submissions/reverse-a-list/chatgpt1_reverse_09.man
SHA-256 aa057e97bb3335be37bc49fc652e7f966e8281af9f7ae61dde59035789f87a41
306 bytes
17x17, footprint 289
3 rooms / 2 pipes / 1 initial man
pipe lengths [2, 3]
```

It uses `Y`, so the ordinary simulator is not a behavioral gate. No contest API
call or submission was made.

## Why it should win

The model predicts organizer-style public ticks:

```text
[142, 82, 127, 202, 114, 124, 243, 382]
average 177.0
17^2 * 177.0 = 51,153.0
```

The current accepted machine measured on the same public suite is 53,023.75.
The predicted ratio is 0.9647186402, a 3.528136% reduction. This is a proper
public-to-public comparison; the hidden live average is not used.

## New architecture

The 20-square baseline used one countdown lane per possible worker index. This
candidate uses:

- a four-tick rotated two-`Y` worker factory;
- `k = n - 1 - i` after one common decrement;
- parity split and `j = floor(k/2)`;
- two shared 14-cell countdown loops;
- a zero-lap bypass in each residue class;
- the `k=0` worker as first output and then next-round controller.

Each parity class arrives every eight ticks. The loop has seven distinct phases:

```text
14 / gcd(14, 8) = 7
```

and at most seven positive-lap workers of either parity enter it for `n <= 16`.
The odd/even route offset is six ticks, yielding strictly decreasing output
arrival times. No path relies on the wall-grace behavior that broke the
23-square Brackets candidate.

## Evidence already completed

An independent `/split` event model first reproduces all eight recorded
organizer-WASM ticks of `reverse_fresh_20_fast` exactly:

```text
[139, 82, 128, 202, 114, 118, 244, 384]
```

Then `chatgpt1_reverse_09` passes:

```text
4,368 / 4,368 complete one-to-three-round length tuples, lengths 1..16
16 / 16 signed-extreme families
3,000 / 3,000 seeded random one-to-three-round streams
maximum observed completion 430 ticks
maximum active men 17
```

Exact builder/artifact equality, pinned SHA, 17x17 geometry, parser structure,
minimum pipe length, no shared walls, and one input-room pipe are encoded in the
release verifier.

## Required authoritative replay

Please fetch `agent/chatgpt-1-solvers` and run:

```bash
PYTHONPATH=src uv run python \
  experiments/chatgpt1-reverse-17/verify_candidate.py

uv run python scripts/wasm_judge.py \
  submissions/reverse-a-list/chatgpt1_reverse_09.man reverse-a-list

uv run python scripts/subdb.py compare \
  submissions/reverse-a-list/chatgpt1_reverse_09.man reverse-a-list
```

The first command drives the organizer WASM on the public cases and 1,277
additional lifecycle streams. It requires the actual WASM score to beat
53,023.75; it does not merely compare against the predicted tick vector.

If all three commands are green and the live database is fresh, please decide
whether to submit **only** the pinned SHA above. If WASM disagrees, preserve its
exact failing case and tick trace for the next topology iteration.
