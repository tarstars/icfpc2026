# Memory: station return shortcuts

Date: 2026-07-27
Status: submitted and accepted

## Result

`memory_12` is a six-cell geometry-only successor to the exact recovered
counted `memory_11`. It keeps the complete machine, room geometry, pipes, and
29-square footprint unchanged.

| Property | `memory_11` | `memory_12` |
| --- | ---: | ---: |
| SHA-256 | `c9e2dea8…41a4` | `e63c3e20…592e` |
| Bytes | 794 | 794 |
| Dimensions / footprint | 29×29 / 841 | 29×29 / 841 |
| Public ticks | `[295,625,1557,1117,1547,919,21507]` | `[292,608,1510,1082,1512,908,20656]` |
| Public average ticks | 3,938.143 | 3,795.429 |
| Public score | 3,311,978.14 | 3,191,955.43 |

The measured public score reduction is 3.62390%.

The exact artifact was submitted once as
`397eaeb4-1236-4e0f-8b2d-b2ac089050f4`. The server reported 24/24,
29×29, average ticks 18,372.291666666668, and score
15,451,097.291666668. This is 3.63214% below the counted `memory_11`
score of 16,033,454.75.

## Changes and invariants

The READ decoder now sends one cell earlier and turns onto the existing
column-2 return. WRITE sends at the first cell whose nearest outgoing pipe is
the ring, then uses a new short return. One additional arrow lets WRITE and
the one-time ring-seeding exit join the main loop through the same column-2
return.

The older lower-right return remains present because ring initialization
still descends through it. No old operation was deleted except the superseded
READ send. `memory_hotpath.apply_memory11_hotpath` checks the immutable parent
hash and every expected parent glyph before applying the transform.

Parsing proves the candidate still has seven rooms, seven pipes, five men,
and pipe lengths `[2,2,4,10,10,13,21]`. Every pipe cell is byte-for-byte
unchanged. The new READ send selects the output pipe; the new WRITE send
selects the ring by a two-cell Manhattan margin.

## Validation

- deterministic parent-to-child reproduction and exact candidate hash;
- `server_compat.validate_layout` and `alexey_pipecheck`;
- all seven public cases with exact tick assertions;
- 100 seeded valid streams up to the 1,000-token limit against a plain-memory
  oracle;
- eight 500-token address-stride streams using all directed extreme values;
- the inherited packed-memory encoding, public, boundary, repeated-write,
  ring-distance, and all-cell gates;
- preflight verdict `READY TO SUBMIT`.

The two-word station unroll remains the next algorithmic iteration. Its
parity-tail count algebra has been independently proved over 68,000 model
cases, but it is not part of this low-risk release.
