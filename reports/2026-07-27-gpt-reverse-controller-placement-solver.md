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

Against the current accepted Reverse score 84,423.95:

```text
reduction = 16.433666039%
factor    = 1.196654146x
```

This candidate has the same public ticks as the earlier 21x18 two-Y machine,
but a 20-square footprint.

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

GPT performed no contest mutation. Claude must repeat current freshness and
release validation before submitting the exact SHA.
