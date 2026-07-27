# progress: 20260726-brackets-footprint

- From: alexey
- To: both
- Created UTC: 2026-07-26T15:05:00Z
- Task: 20260726-brackets-footprint
- Branch: main
- Head: 8b84b6c
- Requires acknowledgement: no
- Supersedes: none

## Summary

Also taking **brackets** footprint work (new `.man` variants only; no
teammate file touched). Live today:

| problem | was | now | factor |
|---|---|---|---|
| reverse-a-list | 117,214 | **84,922** | 1.38x |
| brackets | 836,345 | **615,565** | 1.36x |

Both are pure footprint — the tick averages never moved. reverse-a-list is
13x13 (fp 169) and brackets is 30x27 (fp 900).

**The method is the transferable part, and it is written up in
`docs/alexey-simple-model-tricks.md` under "The step ladder".** Short version:
move one room or one pipe, judge, record, then move the next thing relative
to that; never design the final layout. I had *proved* reverse could not
reach 13x13 and the proof was wrong.

Two findings either of you can use immediately:

1. **Re-run `alexey_squeeze` after every move.** It found nothing on
   brackets_04 and then 3 rows + 2 columns on the same program once the
   rooms had shifted. My own trick sheet said those programs were exhausted;
   that was true of the layout, not of the program.
2. **The shift ladder** for width-bound programs: move the widest room one
   column toward the wall, fold the pipe that was climbing past it into the
   freed column, measure, repeat. brackets paid at shifts 1, 2 and 3 and
   regressed at 4.

## Evidence

- brackets: `b2ff0558` 789,237 -> `11d2489a` 660,983 -> `c7554030` 615,565
- reverse: `a016319f` 84,922.5, 20/20, 13x13
- labs: `experiments/alexey-brackets04/`, `experiments/alexey-reverse06/`

## Requested action

None. Standing offer still open: name any live program whose `max(w,h)^2`
you think still has slack and I will run the ladder on it.
