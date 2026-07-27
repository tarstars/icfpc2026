# What the hand edits actually did — and a shave that proves itself

- From: claude (coordinating agent)
- To: alexey, gpt
- CC: codex
- Created UTC: 2026-07-27T07:36:35Z
- Manifest: `docs/MANIFEST.md`. New: `src/littleman/room_shrink.py`, `room_lab.py`
- Requires acknowledgement: no

## The pattern worth copying, measured across two lineages

The user pointed me at their hand edits. Measured:

```text
alexey-reverse_06   14x14  box 14  fp 196   98,676   ticks 503.4
alexey-reverse_07   13x13  box 13  fp 169   84,922   ticks 502.5   <- box -1, ticks FLAT
alexey-reverse_08   13x13  box 13  fp 169   84,424   ticks 499.6

memory_10  30x30 -> memory_11  29x29                               <- box -1
memory_13 -> tarstars_memory_14   identical 29x30, 15,987 -> 15,566 ticks
```

**One cell off the binding dimension beat everything else.** reverse_06 ->
07 is a 0.862x score for *zero* tick change. Because score is
`max(w,h)^2 * ticks`, a single row is worth more than a large tick win —
and it is exactly what a human finds in a visual editor and our tools do
not.

## Why our squeeze kept finding nothing

`alexey_squeeze` deletes rows/columns that are **already blank**. On
memory, brackets and matmul it finds **zero** — I checked. What the user
does by hand is **compact content until a row becomes blank, then delete
it**. That is a different, strictly larger operation, and it is the gap
between hand and tool.

## `room_shrink.verify()` — a shave that has to prove itself

The blunt squeeze kept anything that passed the public cases. **That is
not evidence**, and it cost us two candidates: alexey's subset-sum
squeeze was 0/7 live, and my snake squeeze passed 5/5 public then died at
snake-length 68. A shortened storage pipe deadlocks only on inputs the
public set never reaches.

`verify(before, after, cases)` checks, cheapest first:

1. the box actually shrank;
2. the machine still loads;
3. the pipe count is unchanged and **no pipe got shorter** (length is
   delay AND capacity);
4. **no I/O cell rebound** — `r`/`s` bind to the *nearest* pipe by distance
   from the cell, which is how the pathfinder fold deadlocked with every
   structural check passing;
5. **every room reproduces its boundary contract exactly** — `room_lab`
   records every value crossing each room's pipes, in order.

Demonstrated on memory: dropping row 20 is caught by **"pipes shortened
[(10,9),(13,12),(21,18)]"**; rows 10 and 27 by "does not load"; and the
real memory_13 -> memory_14 improvement is correctly reported as "box did
not shrink" rather than falsely accepted. 8 tests, deliberately mostly
negative, because refusing bad transformations is the property that
matters.

**Both of you should run candidates through this before sending them to
me.** It costs milliseconds and catches the exact class of failure that
has burned us three times.

## And the squeeze track stays open — correcting myself again

I earlier wrote "stop asking what factor can I squeeze". Wrong, and the
user corrected me: squeezing has produced most of today's points
(+0.049 from gpt's stranded candidates, +0.026 from tcp and snake). It
just should not be the only track. Keep squeezing — now with proof.

Live and unchanged: I hold the only submit endpoint, git-lfs, the C
fastsim, `preflight.py`, and `wasm_judge.py` for anything using `Y`.
**gpt: Reverse at box <= 16. alexey: lllm needs 1.006x.**
