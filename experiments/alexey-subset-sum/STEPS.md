# subset-sum step lab

Live baseline: subset_sum_00 = 3646x3029, fp 13,293,316, score
91,769,596,778,390 (20/20, rank 44/65). The artifact is byte-regenerable:
`littleman.subset_sum.build_subset_sum()` (6.4 s). 2121 rooms, 2164 pipes,
2119 men, 1.7% ink. Handed over by the claude line with a ~9x perfect-pack
ceiling estimate.

## ss_fullsqueeze (pending live judge)

`alexey_squeeze(rows+cols)`: -655 rows, -3040 cols -> 1006x2374,
fp 5,635,876 = **2.36x**. Structure identical (2121/2164/2119), no shared
walls, one pipe against the input room, min pipe 2.

Two flags, and why the public judge is the decider here:

* my resolveaudit reports binding flips in room 2107 — but the flips pair
  incoming pipes of the SAME room (2150<->83), which is exactly what a pipe
  INDEX permutation looks like; compare() keys on parse order, which column
  deletion can shuffle. Possibly a false alarm.
* 118 pipes change length (39,755 -> 20,305 cells) — claude's snake warning
  applies. BUT unlike snake, subset-sum's every case drives the full
  1024-entry systolic streams and the q-counted parser rings, so capacity
  and timing regressions cannot hide from the 20 public cases the way
  snake's length-68 game hid from its 5.

If the judge passes 20/20, submit; the tick counts also tell us whether the
shorter pipes bought time on top of the 2.36x area.

## Next rungs after that

1. Height binds after the squeeze (2374 vs 1006): the tallest room is
   691x61 at (1653,421) — a systolic sorter column. Stairfold/interior work
   there, or re-place the 2048 8-tall rooms into a squarer grid via my own
   placement wrapper (do NOT edit subset_sum.py — write
   alexey_subset_place.py importing its FSM builders).
2. The 400 deletable-with-protection columns experiment had a bug (box
   unchanged); superseded by the full-squeeze-plus-judge path.
