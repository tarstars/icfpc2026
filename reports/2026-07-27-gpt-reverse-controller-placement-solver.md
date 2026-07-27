# Reverse: faster 20-square controller placement

Date: 2026-07-27

## Result

Starting from the correct 20x18 single-Y machine, a bounded placement search
moved the next-round controller receive directly below the worker-factory exit.
The factory and worker countdown paths are byte-for-byte unchanged.

The former controller path crossed the lower room before joining the free
countdown-side column. The new route uses a two-row pocket at rows 10-11, then
joins at row 8. This removes three ticks per round and preserves every worker
phase.

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_20_fast.man
generator: experiments/gpt-reverse-fresh/build_single_y_fast_candidate.py
sha256: f36477129f496a499cd0d594b3a30a1f560f82aae2eaefee639426c042fb01e8
bytes: 348
dimensions: 20x18
rooms / pipes / initial men: 3 / 2 / 1
pipe lengths: [2, 3]
```

Organizer-WASM public result:

```text
case ticks = [139, 82, 128, 202, 114, 118, 244, 384]
average    = 176.375
score      = max(20,18)^2 * 176.375
           = 70,550
```

## Correct like-for-like verdict

The accepted hidden-case live score `84,423.95` is not directly comparable to
the candidate's public-case score. Under the same eight public cases, Claude
measured the accepted `reverse_08` at:

```text
13x13, average 313.750
public score = 13^2 * 313.750 = 53,023.75
```

Therefore the 20-square candidate is still worse:

```text
70,550 / 53,023.75 = 1.330535845
```

At the candidate's average tick count, the true footprint frontier is:

```text
break-even M = sqrt(53,023.75 / 176.375) = 17.3387
M=18 -> 57,145.5   loses
M=17 -> 50,972.375 wins by 3.8688%
```

**This artifact must not be submitted.** It is the semantic and timing baseline
for a hard `M <= 17` solver search.

## Validation

The organizers' vendored WASM passed all eight public cases and 1,277/1,277
adversarial streams:

- every legal length 1..16;
- all 256 ordered length pairs;
- ascending, descending, alternating, repeated-full and repeated-singleton
  lifecycle sequences;
- 1,000 deterministic random one-to-five-round workloads;
- signed extreme values.

Maximum stress runtime was 4,609 ticks. Generator equality, SHA identity,
parser structure, server layout, single input pipe and minimum two-cell pipe
gates all pass.

GPT performed no contest mutation. The next task is architectural compaction to
M <= 17; further tick-only work at M=20 cannot beat the accepted public score.
