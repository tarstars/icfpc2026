# Packet Reassembly 29x28 square repack

Date: 2026-07-27

Status: fully gated candidate; not submitted from this branch.

## Result

`submissions/tcp/tarstars_tcp_11.man` repacks the live
`tarstars_tcp_10` machine from 30x30 to 29x28. It keeps E, I, O, C, and R
byte-identical, rotates P clockwise, and adds a one-cell transient entry so
the VM's fixed east-facing spawn joins the rotated execution path. All 35
normalized `r`/`s` bindings are unchanged.

The important packing step is moving C four columns right. This opens a
five-cell direct C-to-E return and shortens P-to-C to twelve cells while
leaving the two-cell I/O and three-word-ring pipes intact.

| Property | `tarstars_tcp_10` | `tarstars_tcp_11` |
| --- | ---: | ---: |
| dimensions | 30x30 | 29x28 |
| footprint | 900 | 841 |
| rooms / pipes / men | 6 / 7 / 4 | 6 / 7 / 4 |
| average public ticks | 972.167 | 943.167 |
| local score | 874,950.000 | 793,203.167 |

The local score reduction is 9.343029%. The public tick total falls from
5,833 to 5,659, or 2.983027%, while the footprint falls 6.555556%.

Public ticks are:

| Case | `tarstars_tcp_10` | `tarstars_tcp_11` | Delta |
| --- | ---: | ---: | ---: |
| in-order stream | 432 | 377 | -55 |
| single max-displacement swap | 1,326 | 1,161 | -165 |
| drain burst | 1,212 | 1,201 | -11 |
| loss case | 391 | 470 | +79 |
| shortest stream | 32 | 32 | 0 |
| block-reversed n=32 | 2,440 | 2,418 | -22 |
| **Total** | **5,833** | **5,659** | **-174** |

Applying the exact local ratio, `0.9065697087`, to the current live
`tarstars_tcp_10` score of 1,490,670 projects 1,351,396.27. This is only a
projection, but it is 45,766.53 below the current rank-28 threshold of
1,397,162.8.

## Validation

- exact generator/artifact parity;
- SHA-256
  `08b01eb131db4c42d7f076a3f4f4663a94a863a9452ff3f14c2dd637baf05dac`;
- 798 bytes;
- strict parser and server-compatible layout validation;
- 29x28 occupied dimensions and footprint 841;
- pipe lengths `[2, 2, 2, 2, 5, 5, 12]`;
- six rooms, seven pipes, and four men;
- identical normalized resolution for all 35 `r`/`s` instructions;
- all six public cases with the exact tick vector above;
- six directed boundary workloads;
- 768 deterministic differential streams, all baseline-pass/candidate-pass;
- 57 focused TCP tests passed;
- composite preflight: `READY TO SUBMIT`.

The focused commands were:

```text
uv run pytest tests/test_tcp_square.py \
  tests/test_tcp_repack.py tests/test_tcp_hotpath.py tests/test_tcp_fast.py -q
uv run python scripts/preflight.py \
  submissions/tcp/tarstars_tcp_11.man tcp
```

## Freshness

Before staging, the branch was rebased onto `origin/main` at
`e6ed1423a7fb0cda17d1f3db79e82e8831b08244`. A fresh API read confirmed
submission `3c6ab7f4-bded-4d49-9ec4-ee1d13995650` remains done at 20/20,
30x30, 1,656.3 average ticks, and score 1,490,670. The unfrozen Packet
standings snapshot updated at `2026-07-27T01:38:10.263Z`; `wheezards`
remained rank 29 and rank 28 remained 1,397,162.8.
