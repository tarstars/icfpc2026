# Reverse fresh-farm solver baseline

Date: 2026-07-27

## Result

`reverse_fresh_23.man` is a complete multi-round `Y`-based Reverse-a-List
machine. It passed all eight public cases under the organizers' vendored WASM
engine, including all one-, two-, and three-round workloads.

The exact program is 23x23 and 516 bytes:

```text
SHA-256 b9d8784b5e96e56e826a55b6950ce75d64ee05b6587824d2c494ff1f9f46cb15
```

Public ticks to the score-defining final correct output emission:

```text
[175, 94, 152, 238, 138, 154, 280, 420]
average = 206.375
```

Using the project grading definition,

```text
score = max(width,height)^2 * average_ticks
      = 23^2 * 206.375
      = 109172.375
```

The current accepted Reverse score is 84423.95, so this exact artifact is a
correct research baseline, **not a submission candidate**.

## Architecture

The controller receives `n` with `U`, stores it in the backpack, and traverses
a two-`Y` cycle. It creates exactly `n` workers with backpack values
`n, n-1, ..., 1`. Each worker receives one list element from the common input
pipe, enters a seven-tick countdown stage once per backpack unit, sends the
value, and halts. Later input values have smaller backpack values and therefore
emit first. The controller returns to the input receive and repeats for the
next round.

This avoids the fixed-farm lifecycle bugs:

- no workers remain blocked from a shorter previous round;
- no worker-index rotation or wraparound exists;
- no sentinel padding or reset network is needed;
- all workers from a completed round halt.

## Why preserve a losing artifact

The machine freezes the semantics of the fresh-farm idea in a small, reproducible
form. It is the correct starting point for automated search. Solver work can now
change one layer at a time:

1. search six-tick countdown-stage geometries with strict output ordering;
2. search split-cycle phase and worker-entry routes jointly;
3. enumerate room/I/O placement under fixed square limits;
4. reject candidates analytically unless `M^2 * ticks < 84423.95`;
5. validate survivors against all public multi-round cases in organizer WASM.

The immediate winning frontiers are:

```text
M=23 -> average ticks <= 159.59
M=22 -> average ticks <= 174.43
M=21 -> average ticks <= 191.44
M=20 -> average ticks <= 211.06
```

Thus a 20-square version of the current timing would win without a tick change,
while a 23-square version needs a substantially faster schedule.
