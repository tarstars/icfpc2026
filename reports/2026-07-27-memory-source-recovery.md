# Recovery of the counted `memory_11` source

Date: 2026-07-27

## Result

The source behind the user's manual Memory submission has been recovered and
preserved as `submissions/memory/memory_11.man`.

| Property | Value |
| --- | ---: |
| SHA-256 | `c9e2dea84fa3b6d809cfe85a02abfcf7e614349d5488432e776fdd256fbb41a4` |
| Bytes | 794 |
| Dimensions | 29×29 |
| Footprint | 841 |
| Local public cases | 7/7 |
| Local public ticks | `[295, 625, 1557, 1117, 1547, 919, 21507]` |
| Local public score | 3,311,978.142857143 |

The authenticated API confirms exact submission
`89c637e7-7601-4637-a36f-07b94afeb12f`: 24/24, 29×29, average ticks
19,064.75, and score 16,033,454.75. Its exact response is preserved as
`submissions/memory/memory_11-submit.json`.

## Provenance

The contest editor stores sparse Little Man canvases in browser Local Storage
under `littleman:v2:files:<id>`. A read-only copy of the browser's LevelDB was
decoded and restricted to the `icfpcontest2026.com` origin. Editor files 12,
13, and 15, all named as downloaded Memory versions, contained identical
29×29 sparse canvases. Normalizing their occupied coordinates produced the
same 794-byte source and SHA-256 above.

The browser HTTP cache also retained a zstd-compressed response for the
session-authenticated dashboard-submissions endpoint. Decoding that response
identified the UUID, timestamp, dimensions, and score; an independent
bearer-authenticated API read then confirmed all terminal metadata.

No authentication cookie, session token, browser history, unrelated storage
record, or credential was copied into the repository or this report.

## Validation against the lineage

`memory_11` passes the server-compatibility layout validator and all seven
public cases. Relative to preserved `memory_10`:

| Property | `memory_10` | `memory_11` |
| --- | ---: | ---: |
| Dimensions | 30×30 | 29×29 |
| Footprint | 900 | 841 |
| Public ticks | `[298,630,1566,1124,1554,922,21610]` | `[295,625,1557,1117,1547,919,21507]` |
| Local score | 3,561,942.86 | 3,311,978.14 |

The local score improvement is 7.01765%, consistent with the live reduction
from 17,236,875 to 16,033,454.75.
