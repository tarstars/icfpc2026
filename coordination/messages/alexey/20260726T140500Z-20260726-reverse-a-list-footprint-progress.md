# progress: 20260726-reverse-a-list-footprint

- From: alexey
- To: both
- Created UTC: 2026-07-26T14:05:00Z
- Task: 20260726-reverse-a-list-footprint
- Branch: main
- Head: 3d66f16
- Requires acknowledgement: no
- Supersedes: none

## Summary

Two negative results, both **measured on a built machine**, so nobody has to
re-derive them. Both are in `docs/alexey-worklog.md` under 2026-07-26 and
summarised in `docs/alexey-simple-model-tricks.md`.

**1. Value packing is closed for tight rings.** I built the pack side of
three-to-a-cell packing as a real littleman machine and judged it: the
arithmetic is correct (`K = 2^21`, worst-case word 9.01e18 against the
signed limit 9.22e18 — 2.3% headroom, verified on the extremes), but it
costs **34 ticks per value to pack**, against 32 ticks per value for the
whole of reverse_06. Unpacking is structurally worse: `/` writes both A and
B, so reloading the base after a division destroys the remaining stack, and
every digit needs the word re-sent or a partner room. The rule to keep:
**a constant costs a literal walk, because a literal writes A and A holds
the accumulator.** Packing only wins against a ring whose lap is >= 10
ticks.

Reusable piece if anyone does need base-K packing: add
`C = S*(K^2+K+1)` once per word instead of `+S` per digit — it keeps the
>1e6 offset off the per-value path.

**2. reverse-a-list is at its floor at 14x14.** 7x6 is the minimum pump
interior (the head row is 5 cells and must run from the climb column west to
the drop column, and the loop's 2x3 block needs two more columns west of
that; the climb column must carry `W`, a print, the k=1 join and the
constant reload, which needs 6 rows). 13 columns would be relay(4) +
pump(9) with **no routing lane** — adjacent walls admit no pipe, a roof pipe
needs two free rows, and routing around the I/O band runs flush past the
input room's wall.

## Evidence

- `3d66f16` measurement write-up
- `5cbec97` why 13x13 does not close on the interior side
- reverse_06 live: `e338fb00-7962-432f-9c30-77baff5ce603`, 20/20, 98,676.2

## Requested action

None required. Standing offer from my claim message: I have capacity and my
strength is footprint geometry — if either of you has a live program whose
`max(w,h)^2` still has slack, name it and I will take it. `alexey_squeeze`
finds mechanical slack in seconds; the room-folding and pipe-routing
recipes are in `docs/alexey-room-folding.md`.
