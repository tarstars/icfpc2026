# Packet Reassembly 30x30 repack

Date: 2026-07-27

Status: submitted and accepted.

## Result

`submissions/tcp/tarstars_tcp_10.man` is a room-preserving repack of
`tcp_09`. It retains all six room interiors, including the two proven
controller return shortcuts, and preserves the logical binding of every one
of the 35 `r`/`s` instructions.

The layout stacks E, P, and C with offset walls and routes their pipes through
the exposed strips. This reduces the occupied square from 31x31 to 30x30.

| Property | `tcp_09` | `tarstars_tcp_10` |
| --- | ---: | ---: |
| dimensions | 31x31 | 30x30 |
| footprint | 961 | 900 |
| rooms / pipes / men | 6 / 7 / 4 | 6 / 7 / 4 |
| average public ticks | 966.333 | 972.167 |
| local score | 928,646.333 | 874,950.000 |

The local score reduction is 5.782216%. The average public tick cost rises
0.603656%, while the footprint falls 6.347555%.

Public ticks are:

| Case | `tcp_09` | `tarstars_tcp_10` |
| --- | ---: | ---: |
| in-order stream | 406 | 432 |
| single max-displacement swap | 1,240 | 1,326 |
| drain burst | 1,210 | 1,212 |
| loss case | 474 | 391 |
| shortest stream | 36 | 32 |
| block-reversed n=32 | 2,432 | 2,440 |

## Validation

- exact generator/artifact parity;
- SHA-256
  `6cf6a21d6b38d12214c628aa614570a2dc4ec136b27e12ecff359b9bdb244765`;
- 791 bytes;
- strict parser and server-compatible layout validation;
- pipe lengths `[2, 2, 2, 2, 4, 14, 15]`;
- byte-identical room interiors and identical normalized bindings for all 35
  `r`/`s` cells;
- six inherited boundary streams;
- 768 deterministic differential streams: 768 baseline-pass/candidate-pass,
  with no failures in either machine;
- 44 focused TCP tests passed;
- composite preflight: `READY TO SUBMIT`, 6/6 public cases.

## Freshness and live result

The branch was rebased onto `origin/main` at
`3d8fab2e0d493d4fa2c97822ecaeb0c2d34c7107` before staging. A fresh contest
API read confirmed that submission
`95c909b1-1449-4b28-9c7d-9612462bad36` remains done at 20/20, 31x31,
1,639.05 average ticks, and score 1,575,127.05. The unfrozen standings read
placed `wheezards` rank 29; rank 28 was 1,397,162.8.

Submission `3c6ab7f4-bded-4d49-9ec4-ee1d13995650` passed all 20 live cases
at 30×30, average 1,656.3 ticks, and score 1,490,670. The exact response is
preserved in `submissions/tcp/tarstars_tcp_10-submit.json`. This is an
84,457.05-point (5.362%) reduction from `tcp_09`; the private tick ratio was
slightly weaker than the public projection. It remains above the current
rank-28 threshold.

## Rejected precursor

A P+C fusion prototype was also made correct with five rooms, six pipes, and
three men. Its unchanged room dimensions force a bounding dimension of at
least 31, and its core was already slower on simple public cases. It therefore
failed the score gate and was not preserved as a candidate artifact.
