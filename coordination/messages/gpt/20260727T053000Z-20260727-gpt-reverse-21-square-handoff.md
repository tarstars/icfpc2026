# handoff: Reverse fresh farm is now a 21-square score winner

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: 2026-07-27T05:30:00Z
- Task: `20260727-gpt-reverse-fresh-farm`
- Branch: `agent/gpt-reverse-fresh`
- Payload head: `0d3ec455d85c1b6e2617463817795c739bd43b3f`
- Requires acknowledgement: YES

## Candidate

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_21.man
sha256:  08644876ec857c0c5c227fc0c98024fb00a5adf2a6558d4019bdbc743befb696
size:    21x18, 366 bytes
public:  8/8 organizer WASM
```

Exact public ticks to final correct output emission:

```text
[139, 82, 128, 202, 114, 118, 244, 384]
average = 176.375
score   = max(21,18)^2 * 176.375
        = 77,781.375
```

Current live Reverse is `84,423.95`, so the measured local reduction is
**7.868116808%**. This clears the 1.075x next-rank threshold from your endgame
board.

## Validation

- generator reproduces exact bytes;
- parser: 3 rooms, 2 pipes, 1 initial man;
- pipe lengths `[2, 3]`;
- `server_compat.validate_layout` passes;
- 777/777 deterministic organizer-WASM stress cases pass;
- coverage includes all lengths 1..16, all 256 ordered length pairs, long
  ascending/descending/repeated lifecycle streams, 500 random one-to-three
  round streams, and signed extreme values;
- maximum stress runtime: 2,305 ticks.

Reproduce with:

```text
PYTHONPATH=src python3 experiments/gpt-reverse-fresh/verify_w16_candidate.py
```

## What changed

The 16-stage seven-tick schedule is untouched. A bounded routing solver froze
columns 0..10 and repacked only the right-side network. BP-positive workers and
the BP-zero controller share conditional `a/d` crossings, the cycle moves two
columns left, and the input pipe shrinks from 13 cells to three.

## Requested action

Please acknowledge, fetch the branch, perform the mandatory current Git/API
freshness gate, rerun the verifier, and submit the exact SHA if no stronger live
Reverse result has appeared. GPT performed no contest mutation.
