# progress: port solver replays Brackets and proves the local lower bound

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T04:48:02Z`
- Task: `20260727-gpt-solvers-port-assignment`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: no

The fixed-port limitation now has an executable exact model.

Measured result:

```text
brackets_10 two-gap objective: 10 -> exact 4 cells
selected net lengths:          2, 2
brackets_11 objective:         exact 4, incumbents retained
HiGHS MIP gap:                 0.0
focused tests:                 5 passed
wall / RSS for replay:         1.31 s / 149948 KiB
```

The MILP uses one-hot endpoint candidates, exact nearest-pipe incompatibility
constraints with `(distance,row,column)` tie-breaking, distinct endpoint cells,
and source/sink pair variables. It also accepts versioned `machine_ir` JSON and
derives operation roles from the existing resolution map.

This automatically recovers the six-cell pipe reduction behind live
`brackets_11` and certifies that those two pipes cannot be shortened further:
two pipes times the server minimum of two cells is four. The next score-positive
solver variable is therefore not another endpoint move; it is a finite frontier
of equivalent middle-room landing-pad/body variants feeding placement and port
selection.

No `.man` candidate or contest mutation exists.
