# handoff: exact 23-square multi-round Reverse fresh-farm baseline

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: 2026-07-27T05:13:00Z
- Task: `20260727-gpt-reverse-fresh-farm`
- Branch: `agent/gpt-reverse-fresh`
- Head: `ba827add8fe3d0c13b0ec8fcc6098d186928b3d0`
- Requires acknowledgement: no

## Result

I recovered and committed the exact multi-round fresh-farm machine rather than
leaving another `.man` only in scratch storage.

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_23.man
sha256:  b9d8784b5e96e56e826a55b6950ce75d64ee05b6587824d2c494ff1f9f46cb15
size:    23x23, 516 bytes
public:  8/8 under organizer WASM
```

Ticks to the score-defining final output emission:

```text
[175, 94, 152, 238, 138, 154, 280, 420]
average 206.375
score   23^2 * 206.375 = 109172.375
```

The current live Reverse score is 84423.95. **Do not submit this artifact.** It
is a correctness-frozen baseline for solver search, not a score improvement.

## Preserved evidence

```text
experiments/gpt-reverse-fresh/build_candidate.py
experiments/gpt-reverse-fresh/reverse_fresh_23.man
experiments/gpt-reverse-fresh/run_until_expected.mjs
experiments/gpt-reverse-fresh/verify_candidate.py
experiments/gpt-reverse-fresh/benchmark.json
reports/2026-07-27-gpt-reverse-fresh-baseline.md
```

`verify_candidate.py` reproduces the artifact byte-for-byte and passes all
public one-, two-, and three-round cases in the organizers' vendored WASM.

## Next task

I am switching from hand layout to solver work. The frozen baseline gives a
clean objective:

```text
M=23 -> avg <=159.59
M=22 -> avg <=174.43
M=21 -> avg <=191.44
M=20 -> avg <=211.06
```

I will first build an enumerative/constraint solver for countdown-stage shape,
split-cycle phase, and I/O placement. It will analytically reject layouts that
cannot beat the current live score before invoking organizer WASM.

No contest mutation occurred.
