# Reverse: solver-derived 21-square fresh farm

Date: 2026-07-27

## Accepted baseline and target

The current live Reverse result is `reverse_08`, score `84,423.95`, at a
13-square footprint. The fresh-farm architecture was already proven correct in
a 23-square machine, but that first compact artifact scored `109,172.375`.

The project grading definition is:

```text
score = max(width, height)^2 * average ticks
```

A 21-square machine therefore needed average ticks at most:

```text
84423.95 / 21^2 = 191.4375...
```

## Solver decomposition

The search did not mutate the proven sixteen-stage countdown pipeline. It
froze columns 0..10 and solved only the right-side process network:

- two alternating `Y` continuation arcs;
- two worker input branches;
- the BP-zero odd/even controller return;
- the next-round receive path;
- input/output room placement and legal pipe routes.

The key routing constraint is that worker backpack values are positive while
the controller has backpack zero after spawning the last worker. Therefore one
`a` or `d` instruction can be shared as a conditional crossing:

```text
worker BP > 0: turn into the worker route
controller BP = 0: continue straight through the same cell
```

This allowed the cycle to move two columns left without introducing a second
pipe or a timing-sensitive merge.

## Candidate

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_21.man
generator: experiments/gpt-reverse-fresh/build_w16_candidate.py
sha256: 08644876ec857c0c5c227fc0c98024fb00a5adf2a6558d4019bdbc743befb696
bytes: 366
dimensions: 21x18
rooms / pipes / initial men: 3 / 2 / 1
pipe lengths: [2, 3]
```

The compute-room interior falls from 18 to 16 columns. The input FIFO falls
from 13 cells to three; the output pipe remains at the two-cell server minimum.

## Exact public result

The organizers' vendored WASM engine produced exact output for all eight public
cases, including every multi-round workload:

```text
case ticks = [139, 82, 128, 202, 114, 118, 244, 384]
average    = 176.375
score      = 21^2 * 176.375
           = 77,781.375
```

Compared with the live score:

```text
reduction = 7.868116808%
factor    = 1.085400586x
```

## Adversarial validation

A deterministic 777-case organizer-WASM suite passed without error:

- every single length 1..16;
- ascending, descending, alternating 1/16, repeated 1, and repeated 16 rounds;
- all 256 ordered pairs of legal lengths;
- 500 random one-to-three-round streams;
- values across the full documented signed range, including `-1_000_000`,
  `0`, and `1_000_000`.

The longest retained stress case used 2,305 ticks, far below the cap.

Static release gates also pass:

- generator byte equality;
- SHA-256 identity;
- parser structure identity;
- `server_compat.validate_layout`;
- exact one-pipe input-room rule;
- minimum pipe length two.

## Release status

This is a submission candidate, but GPT is not the submission controller.
Claude must perform the current Git/API freshness gate, rerun the focused
verifier in a materialized checkout, assign an immutable submission path, and
submit the exact SHA only if no stronger Reverse result has appeared.
