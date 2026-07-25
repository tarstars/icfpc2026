# Memory: packed `memory_02` candidate

Date: 2026-07-25
Task: `20260725-memory-packed-candidate` (Claude work owner; stopped by the
Codex liveness takeover at 2026-07-25T08:31:20Z, after the candidate below was
already complete and measured).
Problem: `d0b34a23-67c1-4087-b88e-90a74404d50e` (`memory`), scored by
`max(width, height)^2 x average ticks`.

**Nothing was submitted.** `memory.py`, `memory_01.man` and `variants.json`
are untouched.

## Result

| | `memory_01` (accepted) | `memory_02` (this candidate) |
|---|---:|---:|
| dimensions | 46 x 47 | **37 x 37** |
| footprint | 2209 | **1369** |
| average ticks (public) | 9749.857143 | **4159.000000** |
| local score | 21,537,434.43 | **5,693,671.00** |

Footprint -38.03%, average ticks -57.34%, **local score -73.56% (ratio
0.2644, a 3.78x improvement)**. All 7 public cases pass under
`littleman.server_compat`.

Per-case ticks (server-compatible judge):

| case | `memory_01` | `memory_02` |
|---|---:|---:|
| fresh cell reads zero | 179 | 264 |
| write then read | 1301 | 614 |
| overwrite | 3744 | 1592 |
| boundary addresses and values | 2498 | 1156 |
| write zero, trailing write | 3776 | 1568 |
| reads only | 1269 | 926 |
| interleaved cells | 55482 | 22993 |

Only the very shortest case regresses (179 -> 264): the ring now seeds 34
zero words through a counted loop, and that fixed ~200-tick prologue is
visible when a case does almost no work. It is repaid many times over on
every other case.

Artifact: `submissions/memory/memory_02.man`, 1170 bytes, sha256
`7a780b0957e33545fa67b947de51e6e242a8795fe0e7b2c5e7a6eef0f9b23702`,
reproduced byte-for-byte by
`littleman.memory_packed.build_memory_packed()`.

## Where the ticks actually were (the measurement that drove the design)

Instrumenting `Machine._execute` on `memory_01` over the public
"interleaved cells" case:

- 125 operations (75 reads, 50 writes), `sum(k) = 6108` ring-item relays,
  average `k` 48.86.
- Total room instruction executions 162k, of which the three ring rooms
  (P3W 55,169, P3R 52,363, RELAY 44,172) account for ~93%.
- 55,482 ticks / ~6233 relayed items = **~8.9 ticks per circulating item**.

The three ring rooms run *concurrently*, so the per-item cost is the slowest
single station's lap (~8.9 ticks), not the sum of the three. That kills the
obvious "delete the relay room" idea: it would have removed a room but not a
tick. **The only lever that matters is the number of circulating items.**

Packing three values per word takes the same case from 6108 relays to 1994
(3.06x), which is where the 2.34x tick win comes from; the remaining gain is
geometry.

## Encoding: signed 21-bit fields, not an offset radix

`reports/2026-07-25-memory-packing-feasibility.md` proposed offsetting each
value by `+1_000_000` and packing base `2**21`. That works, but it forces a
19-digit `ZERO_WORD` literal for the ring seed and costs a bias add/subtract
on every access.

A cell value lies in `[-1_000_000, 1_000_000]`, which fits *exactly* in a
**signed** 21-bit field (`[-1_048_576, 1_048_575]`). So store raw two's
complement:

```
word = (f0 & MASK21) | ((f1 & MASK21) << 21) | ((f2 & MASK21) << 42)
MASK21 = 2**21 - 1
```

Consequences, all verified by test:

- Every field is masked to 21 bits *before* being shifted in, so bit 63 is
  always 0. A word is always a non-negative signed-64 integer and no
  littleman arithmetic ever wraps. (Without the mask, a negative value
  shifted into field 0 or 1 would sign-extend across the fields above it and
  corrupt them.)
- A cleared memory is the plain word `0`, so the ring seeds with 34 zeros
  and needs no wide literal.
- Field 2 occupies bits `[42,63)` with bit 62 as its sign; bit 63 stays
  clear, so the third field is not a special case.

Address decode is one instruction: `A = addr`, `B = 3`, `/` leaves the word
index `addr // 3` in A and the field index `addr % 3` in B simultaneously.
With `shift = 21 * (addr % 3)`:

- **read**: `value = (word << (43 - shift)) >> 43`. The left shift parks the
  field's sign bit in bit 63; the arithmetic right shift (`}`) sign-extends
  it back. No mask, no bias, 2 instructions.
- **write**: `word' = (word & ~(MASK21 << shift)) | ((v & MASK21) << shift)`.

Both forms only ever need **two live quantities at a time**, which is the
whole reason they fit in A and B. Every algebraically equivalent formulation
I tried (`old + (nf - of) * 2**shift`, divide/remainder peeling with `/`,
`hi*Q + nf*P + lo`) needs three live values at some step and cannot be
expressed without an extra room or an extra pipe.

## Architecture: one station on the ring

```
I -> P1 -> HEAD -> P2 -> STATION -> O
                         STATION <-> RELAY      (the 34-word ring)
```

`memory_01` had three rooms on the ring (write station, read station,
relay). This candidate has one, plus the minimal relay that exists only
because **a pipe may not have the same room as its source and its
destination**, so a ring cannot close through a single room.

Rooms and the token stream between them:

| room | in | out |
|---|---|---|
| `P1` | `op, addr, [value]` | `[tag, w, w, shift, x, shift]` |
| `HEAD` | the above | `[tag, k, shift, x, shift]` |
| `P2` | the above | `[tag, k, 43-shift]` or `[tag, k, NOTMASK, nfP]` |
| `STATION` | the above + ring | ring, output |

Three ideas made the rooms small:

1. **`tag` lives in the backpack.** `P1` and `P2` both need to branch on
   read-vs-write, but the discriminator has to survive a dozen arithmetic
   ops that destroy A and B. `b` stores it in the write-only backpack and a
   single `d`/`a` near the end of an otherwise straight-line room performs
   the branch, so the two arms share the whole decode prefix.
2. **`HEAD` carries the head word index in A across laps.** `memory_01`
   used a separate room plus a delay pipe as a one-value register. A
   racetrack man's registers survive a lap, so `M` before the first `r`
   (B survives `r` and `s`) is enough. `hw` starts at 0, which is the
   correct initial value, so there is no prologue to keep off the lap.
3. **B survives the relay loop.** The loop `>rsv` / `^ md` only executes
   `r s v d m ^ >`, none of which touch B. So the station loads its one
   decode/mask constant into B *before* relaying and still has it when the
   target word arrives in A. That is what lets a single room both relay and
   act.

`P2` exists only because building `~(MASK21 << shift)` and
`(v & MASK21) << shift` needs `shift` twice, and no single room can hold the
mask, the shift and the value at once.

Per operation the station:

- READ: `r(tag)`, `X`, `r(k)`, `b`, `r(43-shift)`, `M`, relay `k+1` words
  (the target ends up in A and has already been forwarded unchanged),
  `{ M `43` W }`, `s` to the output pipe.
- WRITE: `r(tag)`, `X`, `r(k)`, `X` (`k == 0` skips the loop through an
  inline stub), `b m`, `r(NOTMASK)`, `M`, relay `k` words, then
  `r(ring) & M r(nfP) |` and `s` back into the ring.

## Layout and pipe resolution

Final box 37 x 37 (footprint 1369), rooms:

| room | rows | cols |
|---|---|---|
| I | 1-3 | 0-2 |
| P1 | 0-4 | 6-34 |
| HEAD | 7-10 | 6-34 |
| P2 | 13-19 | 6-31 |
| STATION | 22-36 | 6-29 |
| RELAY | 30-33 | 31-36 |
| O | 34-36 | 0-2 |

The station is the only room with two incoming and two outgoing pipes, so it
is the only place nearest-pipe resolution can silently go wrong. Attachments:
command in on the **top** wall at interior column 2, ring out on the
**right** at interior row 1, ring in on the **right** at interior row 2,
output on the **left** at interior row 13. Every `r` and `s` was placed by
computing both Manhattan distances, and
`test_station_pipe_resolution_is_unambiguous` re-derives all eleven of them
from the parsed machine with `_nearest_incoming` / `_nearest_outgoing`
rather than trusting the hand arithmetic (cookbook section 4).

**Ring capacity.** The 34 words have to be parked somewhere, so the two ring
pipes together must hold all of them. They are 26 + 17 = 43 cells, so the
outbound pipe deliberately serpentines through the free column band beside
the station instead of taking the 11-cell direct route. Deadlock is
impossible: the total is conserved at 34, so if the 26-cell outbound pipe is
full the 17-cell inbound one cannot also be, and the relay can always drain.

## Failed and rejected alternatives

- **Removing the relay room to save its ticks.** Measurement showed the ring
  rooms pipeline, so the per-item cost is one lap, not three. Rejected
  before implementation on the strength of the profile.
- **Offset (`+1_000_000`) base-`2**21` packing**, as proposed in the
  feasibility report. Correct, but needs a 19-digit seed literal and a bias
  add/subtract per access; the signed-field form is strictly cheaper.
- **`new = old + (nf - of) << shift`.** Needs `old`, `shift` and the delta
  live at once. Computing the old field unsigned fixes the carry problem but
  not the register pressure.
- **Peeling with `/` (`q, lo = divmod(old, P)`).** `/` yielding quotient and
  remainder in one step is attractive, but reassembling needs `q`, `BASE`,
  `nf`, `P` and `lo`, i.e. two extra rooms on the ring path -- which would
  have raised the per-item lap cost, the one number that matters.
- **A wide first layout** (47 x 37, footprint 2209) that reached the same
  4159 average ticks. Same score as `memory_01`'s footprint by coincidence;
  compacting the ring band into the free columns beside the station took it
  to 37 x 37 with no change to behaviour.
- **`@` inside a relay lap.** The first relay room re-entered its own `@`,
  which is a nop, so the man kept his heading and walked into the wall. `@`
  must sit off the lap.

## Validation

```
uv run pytest tests/test_memory_packed.py -q          # 60 passed
uv run pytest -q                                      # 245 passed
uv run python -m littleman submissions/memory/memory_02.man memory
```

The 60 focused tests cover:

- encoding: directed boundary values in all three fields, full-domain
  strides, field independence over 4000 seeded random triples, signed-64
  safety (`wrap64` fixpoint, bit 63 clear) over the extremes plus 2000
  random triples, the zero word, address coverage, and proof that the two
  unused padding fields of word 33 cannot alias a real cell;
- layout: deterministic generation, byte-for-byte artifact match,
  `server_compat.validate_layout`, room/man/pipe counts, ring capacity
  >= 34, and the empirical pipe-resolution audit above;
- behaviour against a plain Python oracle: all 7 public cases, six seeded
  random operation streams, all 100 cells written then read back,
  worst-shape ring distances (addresses stepping ~17 words each time),
  boundary values in every field position, and repeated overwrite of one
  cell;
- an immutability guard that `memory_01.man`'s sha256 is unchanged.

## Expected live score (projection, not a measurement)

`memory_01` measures 9749.857 average ticks locally and 41,363.625 on the
server, a 4.243x ratio from the private cases. Applying the same ratio to
`memory_02`'s 4159.000 gives roughly 17,650 server ticks and a score near
**24.2M**, against the accepted 91,372,247.625. This is an extrapolation from
one data point and must not be quoted as measured.
