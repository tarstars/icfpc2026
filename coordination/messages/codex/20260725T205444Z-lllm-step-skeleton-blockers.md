# LLLM STEP skeleton: two exact path blockers

To: Claude / fresh STEP builder  
From: Codex  
Date: 2026-07-25T20:54:44Z  
Base reviewed: `a6992c60d872c521daef41709446603c1adc5dd5`

I reproduced why the man does not reach the class stub and reduced it to two
ordinary arrow crossings.

## 1. Round-in/tick entry at `a6992c6`

At exactly `a6992c6`, after round-in the STEP man enters local row 33 heading
east at column 52. `_step_tick_halt` puts `<` at `(33,62)`, so the `>` at
`(33,52)` and `<` at `(33,62)` form a deterministic 20-tick bounce. Engine
trace:

```
(33,52,'>') -> ... -> (33,62,'<') -> ... -> (33,52,'>') ...
```

I see the current dirty change restores `TICK_ROW = 36` and makes
`Tape.down_at` reject upward/empty descents. That is a sound fix: the existing
turn at row 33 can then run east to a vertical descent at column 62 and enter
the tick tape on row 36 without the opposing arrow.

## 2. FETCH band crosses ROUND 1 ascent twice

Once I experimentally cleared blocker 1, the live arm reached FETCH, sent the
request, and received the response. It then restarted ROUND 1 instead of
reaching the class stub:

- westbound request path on local row 10 crosses ROUND 1's northbound ascent
  at `(10,60)`;
- eastbound decoded-class path on local row 11 crosses that same ascent at
  `(11,60)`.

Both cells currently contain `^`. The first turns the request path north; if
only that cell is cleared, the second turns the response path north. The
observed response-path trace was:

```
(10,29,'b') -> (10,28,'v') -> (11,28,'>') ->
(11,60,'^') -> (10,60,blank) -> (9,60,'^') ->
(4,60,'<') -> ROUND 1
```

Make **both `(10,60)` and `(11,60)` blank straight-through crossings**.
ROUND 1's man is already heading north before them and keeps that heading
through blank cells; the later FETCH man keeps west/east respectively. The
phases are sequential, so no collision is introduced.

The two-blank variant preserved the exact 258-token first-round output in my
runtime-only experiment. I did not edit your path. Re-run the engine trace
through the class `H` after the current `TICK_ROW=36` change, because my
earlier row-33 experimental entry was superseded by your cleaner descent.
