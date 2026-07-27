# Reverse: solver-derived 20-square single-Y farm

Date: 2026-07-27

## Result

The previous solver candidate used a two-`Y` alternating cycle in a 21x18
program. A topology search over the worker-factory process network found that
one `Y` is sufficient if the continuation loop takes six ticks:

```text
Y -> m -> d -> ^ -> blank -> > -> Y
```

A worker is born once per loop. The continuation decrements BP at `m`; `d`
loops while BP is positive and exits south at zero. The proven countdown chain
costs seven ticks per backpack unit, so each later worker is created six ticks
later but has one fewer seven-tick stage. It therefore emits exactly one tick
before its predecessor.

This removes the alternating cycle, one worker receive branch, parity-dependent
controller returns, and one interior column.

## Exact candidate

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_20.man
generator: experiments/gpt-reverse-fresh/build_single_y_candidate.py
sha256: a94a74bc0d422648579f718a6221aff10e0d22dc0eb397751f721457f59ae28d
bytes: 348
dimensions: 20x18
rooms / pipes / initial men: 3 / 2 / 1
pipe lengths: [2, 3]
```

## Score

The project grading definition is:

```text
score = max(width,height)^2 * average ticks
```

Organizer-WASM public ticks to final correct output emission:

```text
[148, 85, 134, 211, 120, 127, 253, 393]
average = 183.875
score   = 20^2 * 183.875
        = 73,550
```

The current accepted Reverse result is 84,423.95, so the candidate is:

```text
12.880172036% lower
1.147844324x better
```

It supersedes the 21x18 two-Y candidate, which scored 77,781.375.

## Validation

The organizers' vendored WASM engine passed all eight public cases and a
1,277-case deterministic adversarial suite:

- every legal single-round length 1..16;
- ascending and descending length sequences;
- 32 alternating 1/16 rounds;
- 32 repeated full-size rounds;
- 64 repeated singleton rounds;
- all 256 ordered pairs of legal lengths;
- 1,000 random one-to-five-round streams;
- signed extreme values including `-1_000_000`, `0`, and `1_000_000`.

All 1,277 cases produced exact output. The longest used 4,705 ticks.

Static release gates:

- deterministic byte-identical generation;
- SHA-256 identity;
- parser structure `3 / 2 / 1`;
- `server_compat.validate_layout` passes;
- exact one-pipe input-room rule;
- minimum pipe length two.

## Solver lesson

The winning variable was not geometric endpoint placement. It was process
topology. Replacing a two-state alternating factory with a one-state recurrence
simultaneously reduced width and simplified reset semantics. A useful solver
stack should therefore search in this order:

1. finite process-network topology;
2. phase/throughput inequalities;
3. instruction realization;
4. room and pipe placement;
5. exact simulation.

Starting with rectangle placement would never have discovered the single-Y
recurrence.

## Release status

GPT performed no contest mutation. Claude is the current coordinator and sole
submission controller. Claude must repeat Git/API freshness and focused release
validation, then submit the exact SHA only if no stronger Reverse result has
already appeared.
