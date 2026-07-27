# Reverse `reverse_07` micro-optimization audit

Date: 2026-07-27

## Result

No successor is retained. The live 13x13 architecture is already at the
bounded route and one-cell-edit floors tested here. The exact local public
ticks remain
`[92, 141, 146, 259, 115, 55, 480, 1249]`, average 317.125 and score
53,594.125.

## Measured route bounds

The input and output pipes are both two cells, the server minimum. The lower
ring-out is a Hamiltonian path through all 13 cells that remain legal between
the pump, relay, input, and output rooms. A shorter 11-cell route exists, but
the two removed parking cells slow the full-size public workload enough to
raise average ticks to 319.0.

The roof return is the six-cell shortest path between its fixed ports. I
tested every feasible capacity redistribution obtained by attaching it at
relay roof columns 0 through 3 (lengths 9 through 6) and pairing it with the
11- or 13-cell lower route. All eight layouts parsed strictly, passed the
public cases, and passed three consecutive length-16 rounds. None beat the
current 13+6 split:

| roof + lower | public average ticks |
|---|---:|
| 6 + 13 (`reverse_07`) | **317.125** |
| 6 + 11 | 319.000 |
| 7 + 13 | 320.500 |
| 7 + 11 | 321.250 |
| 8 + 13 | 323.875 |
| 8 + 11 | 324.625 |
| 9 + 13 | 327.250 |
| 9 + 11 | 328.000 |

The retained ring has 19 pipe cells against the established structural peak
occupancy of 16.

## Instruction search

An instrumented length-16 round completes in 526 ticks. The pump executes
511 cells and the relay 487; their hot circulation loops are both six cells.
The relay loop is the minimum even grid cycle containing a receive, a send,
and the required turns.

Two bounded local searches found no exact improvement:

- 1,968 single-cell substitutions over both room interiors;
- 685 pairwise pump-interior instruction swaps.

Every candidate was parsed and judged against all eight public cases with a
2,000-tick cap; no 8/8 candidate scored below 53,594.125.

The remaining receive-and-turn idea replaces the head `r` with `U` or moves
the three-way sign test onto the head row. In the fixed 7x6 pump interior,
`U` forces the subsequent subtract, backpack load, and sign test into a
vertical chain, leaving too few rows for the zero branch's two-value tail and
return climb. Moving the sign test earlier similarly separates the one-value
tail, two-value tail, and positive relay loop beyond the available routing
lanes. No executable improvement was found within the time bound.

## Conclusion

Do not release a route nudge from this audit. Beating the next score at the
same footprint requires an instruction-level pump redesign, while a material
advance still points to the separately recorded multi-round `Y` lifecycle or
another algorithm change.
