# reverse-a-list pass 2 handoff (2026-07-26)

## Measured breakdown (reverse_04, full-size case, 2447 ticks)
Instrumented sim.Machine per-tick per-man: pump man MOVES 2164/2447
ticks (88%), blocked only 11 at the head-r; relay man moves 2436/2447.
Nobody meaningfully waits on pipes. Cost is pure O(n^2) lap geometry
(each output relays the whole remaining frame), so lap-shaving tops out
~1.2x; the win had to come from fewer laps.

## Approach chosen: double extraction per pass
`src/littleman/reverse_faster.py` (new, tested). Same ring protocol as
reverse_fast (frame [k, v1..vk], relay room merges input with spatial
priority), but each pass extracts the last TWO values: send head k-2,
relay k-2, fall out of the loop with v_{k-1}, M-hold it, read v_k,
print, W, print. Relays drop 120 -> 56 for n=16. X three-way on A=k-2:
>0 main; ==0 (k=2) rides the fall column through a BP-zeroing `m` and
reuses U/d/tail, sending NO head (ring left empty, so head-0 passes and
the x-parity branch were eliminated); <0 (k=1) spur reads v1 + prints
(an odd n leaves [1, v1] behind). Boot lane row1 (`@1M...v`) loads B=1
before the first head — first bug found: B=0 at boot broke the math.

## Status: VERIFIED WORKING, NOT SUBMITTED
- `submissions/reverse-a-list/reverse_05.man` written from generator.
- 15x15 (fp 225), public 8/8, fuzz 58 lists green, validate_layout OK.
- `tests/test_reverse_faster.py`: 13/13 pass (with test_reverse_fast).
- Local judge: score 74,390.6 vs reverse_04's 120,912.4 = 1.63x.
  Case ticks [100,147,157,277,122,61,504,1277] vs
  [179,259,288,503,222,78,959,2447]; full-size 1.92x.
- Live estimate: server avg was 987 at score 193,481; same tick ratio
  (~0.536) suggests ~225*529 ~ 119k, ~1.6x. TODO: variants.json entry;
  run `uv run python -m littleman submissions/.../reverse_05.man
  reverse-a-list` preflight before submitting.

## Exact next step (width 15 -> 14 = extra 1.16x, then ticks)
Width binds: relay(4) + forced gap col4 (relay->pump pipe) + pump(10).
Pump interior must go 8 -> 7 wide. Sketched route: B=2 constant (one
`-` instead of `-b-`), loop entered AT `U` with BP=k-2 (skip first m),
freeing row2 cells so `<`/idle-r shift left. Blocked each attempt on
east-side convergence: k1 spur, climb and boot lane must all reach the
idle r heading WEST without crossing s/M/W with live registers.
Options: two stacked `<` cells (col7/col8 pattern worked in v1); or put
the second print on the climb (works, done) and W on the climb too.
After that: ring transit ~26 ticks/pass idles small-k passes — measure
blocked@idle-r before shaving further.

## Traps paid for (do not rediscover)
1. A pipe BEND arrow flush against a room wall, pointing away, parses
   as a phantom pipe start (here: `<` at (6,4) made a 2-cell
   pump->relay pipe; heads bypassed the ring, corrupting pass 2+).
   reverse_04's jog-below-relay topology avoids it; I room moved to SW
   corner so the col-3 climb clears it (input flush rule).
2. sim.py line ~369: `target is not source` — self-loop pipes are
   unparseable; a relay room is mandatory. Don't chase that idea.
3. `r` never turns: any r/s approached heading N on row 1 (or S on the
   bottom row) walks into a wall. The idle r must be entered heading W.
4. k1's print s must resolve to the OUTPUT pipe — audit Manhattan
   distances from every s to both floor pipes (done for all six).
5. Ring-out needs >= 15 cells (head + 14 relays park during pass 1).
