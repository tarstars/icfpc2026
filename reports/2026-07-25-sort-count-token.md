# Sort: In-Band Remaining-Count Token

Date: 2026-07-25

## Result

`sort_05` applies the recovered Packet Reassembly lesson "put control in the
data stream" to the current Sort winner. It passes all public and deterministic
stress tests and improves the measured local score by **16.20%**:

| Variant | Dimensions | Footprint | Public average ticks | Local score |
|---|---:|---:|---:|---:|
| `sort_03` | 18×19 | 361 | 2,571.86 | 928,440.43 |
| `sort_05` | 18×18 | 324 | 2,412.00 | 778,062.86 |
| Change | | −10.25% | −6.22% | **−16.20%** |

The exact public case ticks for `sort_05` are:

```text
1038, 854, 1080, 758, 1388, 3302, 8390
```

This is a validated local candidate, not a live submission.

## Protocol change

`sort_03` asks `q` how many values are parked in the return pipe before every
selection pass. Since `q` cannot see values still travelling through the
outgoing pipe and relay, its walker must cross a three-row settling corridor
before probing the pipe.

`sort_05` carries the remaining count in the FIFO behind the values:

1. Load `n` values while retaining `n` in B.
2. Send `n - 1` behind the values and scan exactly `n` values using BP.
3. Requeue every value except the selected minimum.
4. Emit the minimum. The decremented count is now the FIFO head.
5. Receive that token; zero returns to input, while a positive value begins
   the next pass.

Blocking receive provides the phase synchronization. The program needs
neither `q` nor a timing corridor.

## Geometry change

The protocol change removes the three-row corridor but does not automatically
shrink the bounding square: the original return route still reached row 18.
The final program folds its return pipe through the free shelf below the pump
and attaches at the pump's bottom wall. This changes the box from 18×19 to
18×18.

Pipe proximity was audited as semantics. An earlier prototype attached the
return pipe at the pump's right wall; the scan's `r` was then closer to the
input pipe and deadlocked on lists longer than one. The bottom attachment
makes every ring receive select the return pipe and keeps the load receive
selecting input.

## Validation

- Generator/artifact equality:
  `littleman.alexey_sort_ring3:build_sort_count_token` reproduces
  `submissions/sort/sort_05.man` byte-for-byte.
- Seven of seven public cases pass under the local judge.
- The layout passes `littleman.server_compat`.
- Eight worst-shape workloads pass, including maximum-length sorted,
  reverse-sorted, duplicate, and ±10,000 cases.
- Three hundred seeded randomized workloads pass with 2–6 rounds, lengths
  1–16, and values spanning the documented domain.
- The maximum observed stress-case completion time is 18,920 ticks.

The regression is `tests/test_alexey_sort_ring3.py`; metadata and exact hashes
are in `submissions/sort/alexey-variants.json`.
