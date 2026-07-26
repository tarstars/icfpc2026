# Packing: paused state (2026-07-26)

Parked so it can be resumed without re-deriving anything.

## Where it stands

The **pack half is built and verified**; the unpack half was never built,
because the measurement said the whole thing loses.

- Harness: `/tmp/.../scratchpad/pack3.py` (NOT in the repo — rebuild from the
  listing below if the scratchpad is gone).
- `I -> packer -> O`, one room, one man. Reads three values, Horner-packs
  base `K = 2^21`, adds the offset correction once, emits the word. The judge
  compares the word against Python, so the arithmetic is proven.
- Verified: `[1,2,3]`, `[-1e6,0,1e6]`, `[1e6,1e6,1e6]`, `[-1e6,-1e6,-1e6]`,
  `[0,0,0]` — all pass.
- **Measured cost: 103 ticks / 3 values = 34 ticks per value, packing only.**

## The numbers that decided it

- reverse_06 (live, 98,676.2) costs 516 ticks for 16 values = 32/value.
- Packing would take the ring's relay laps from 336 ticks to ~36 at n=16 —
  real, but the ring is only 336 of 516, so a *free* packer could not halve
  the machine.
- Unpack is structurally worse than pack: `/` writes BOTH A and B, so
  reloading the base after a division destroys the remaining stack. Each digit
  needs the word re-sent (pump sends it three times, i divisions on copy i) or
  a partner room to park the quotient: ~30+ ticks per value.

## The constants and the one trick worth keeping

```
K = 1 << 21          base
S = 1 << 20          per-digit offset, keeps every digit positive
C = S*(K*K + K + 1)  = 4611688217451692032, added ONCE per word
word = (v1+S)*K^2 + (v2+S)*K + (v3+S)
max word = 9,009,736,825,708,692,032   vs signed limit 9,223,372,036,854,775,807
```

Adding `C` once per word instead of `+S` per digit is what keeps the >1e6
offset off the per-value path — one 19-digit literal per word instead of
three 7-digit ones. Reuse this if base-K packing is ever needed elsewhere.

## The per-value sequence (this is the cost floor)

```
M `21` W { M r +
M      park accumulator T in B
`21`   A = 21          (destroys T -- which is why T had to be parked)
W      A = T, B = 21
{      A = T << 21
M      B = T*K
r      A = v
+      A = T*K + v
```

Ten cells, four of them literal. **A constant costs a literal walk, because a
literal writes A and A is where the accumulator lives.** That is the reason
packing cannot be made cheap, and it is general — it applies to any
accumulate-with-constant loop in this language.

## To resume

Packing pays only against a ring whose lap is >= 10 ticks. reverse_01 had a
10-tick lap and `5n^2`; reverse_06 has a 6-tick lap and `n^2/4` relays. If a
NEW problem shows up with a fat ring lap, this is ready to be dropped in:
build the packer room from the sequence above, and give the unpacker a
partner room so the quotient has somewhere to sit.
