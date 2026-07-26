# Reverse-a-list: `Y`-spawned spatial reversal

Date: 2026-07-26

Status: one-round core verified against the organizers' exact vendored WASM engine; reusable multi-round machine remains to be built.

## Result

`experiments/gpt-reverse-y/reverse_y_one_round.man` creates one controller and sixteen workers from a single `@` using a linear chain of sixteen `Y` instructions.

The controller is creation-order slot zero and consumes the length token. Workers 0..15 block on the same input pipe. Once values arrive, the input FIFO releases one value per tick, so worker `i` receives at `t+i`.

The worker read cells lie on a rising diagonal. They walk east to one common column. The horizontal distance falls by one cell per worker while the receive time rises by one tick, so every worker reaches the common column on the same tick. The workers then move south as a one-cell-spaced train. The bottom worker reaches the common `s` first, therefore the train is emitted in reverse order.

This is linear-time reversal by scheduling; no stack, packed accumulator, ring rotation or per-value relay is used.

## Organizer-WASM evidence

The exact artifact was loaded and run through:

```text
node claude/official-sim/harness.mjs
```

For every `n = 1..16`, with deterministic distinct inputs:

- the exact output was the reversed list;
- no load error or fatal error occurred;
- the sixteen-value run completed in 78 ticks including an intentionally oversized startup input pipe;
- the generated runner timeline grew from one man to seventeen and then cleaned the active output train by collision at the terminal `H`.

The exact artifact is 58x30, 927 bytes, SHA-256:

```text
1c196713ef3ea1a9d449c25a5704ae1664205c9e212324188130f12e77627507
```

The 58-cell width is not architectural. It comes from a straight 41-cell startup pipe used only to ensure the linear splitter chain finishes before input arrives. A balanced four-level splitter or a folded delay pipe removes that dimension.

## Timing identity

For worker `i`, sequential receive time and geometric distance satisfy:

```text
receive_i = t + i
horizontal_i = H - i
```

All workers enter the common vertical lane at `t+H`. Their rows also increase with `i`, so vertical distance to `s` decreases with `i`. Hence send times are strictly:

```text
worker n-1, worker n-2, ..., worker 0
```

for every prefix length `n` without inspecting `n` in the workers.

## Multi-round options

The remaining issue is worker lifecycle. Public tests carry up to three rounds. Three viable continuations are:

1. Reusable farm: after `s`, route by a four-level `x`/`]` tree keyed by a worker index in BP back to the sixteen read slots.
2. Fresh farm: spawn exactly `n` workers with a BP-counted continuation, then park each completed worker at a private `H`; the next generation annihilates the previous corpses after its output, which is safe for at most three rounds.
3. Fixed farm plus dummy fill: a helper pipe supplies sentinels to workers `n..15`, allowing all sixteen workers to clean up each round.

The reusable binary-return tree appears smallest; the fresh counted farm appears easiest to prove.

## Score implication

The live program is 13x13 at about 502.5 average ticks and score 84,922.5. The leaderboard's roughly 15.3k result is consistent with this `Y` strategy: a 19x19–22x22 room at roughly 35–50 average ticks reaches the observed range.

No submission was made and no existing Reverse artifact was modified. Alexey retains Reverse ownership and submission authority.
