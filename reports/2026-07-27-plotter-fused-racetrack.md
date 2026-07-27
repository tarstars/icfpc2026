# Plotter fused racetrack

Date: 2026-07-27
Status: live, 20/20

## Result

`plotter_08` replaces the live Plotter's ETEST, EUPD, ADDRESS, ADDRESS
relay, and compiled PLOT room with two compact protocol components. It keeps
the input, five setup rooms, router, swapper, and display unchanged.

| metric | `plotter_07` | `plotter_08` | change |
|---|---:|---:|---:|
| scoring dimensions | 152x145 | 130x130 | max -14.47% |
| footprint | 23,104 | 16,900 | -26.85% |
| average public ticks | 47,315.667 | 44,573.333 | -5.80% |
| local score | 1,093,181,162.67 | 753,289,333.33 | **-31.09%** |

The exact artifact is `submissions/plotter/plotter_08.man`, 16,003 bytes,
SHA-256
`1614d73921d512f321cb1a1a10660e75258c1ae0346f2b77bd51207be3e5c3dd`.
Scaling the measured local ratio against the live `plotter_07` score projects
approximately 1,102,033,314; that is a projection, not a live measurement.

The live submission `81cc6d5c-0812-4c77-93b5-d3a387b4915b` completed 20/20
at average 64,963.2 ticks and score 1,097,878,080. This is a 31.35% live
score reduction from `plotter_07`. The exact terminal response is preserved
in `submissions/plotter/plotter_08-submit.json`.

## Architecture and bindings

The fused 26x125 worker owns the canonical six-token ring
`(dy, E, dx, sx, 32*sy, address)`. Each pixel uses a read-only error-test
rotation and a selected update rotation, then emits the updated address
directly to the retained router. Its external bindings are:

- setup S5 -> fused setup;
- fused output -> router;
- fused ring-out -> private relay -> fused ring-in;
- router -> manual PLOT -> display address/data;
- router -> retained swapper -> display clear/commit.

The manual PLOT room is four rows tall and implements the same two-display
send protocol. The strict parser finds 12 rooms, 14 pipes, and 10 men. Exact
pipe lengths are
`[2, 3, 3, 3, 3, 4, 25, 29, 49, 56, 57, 106, 134, 220]`.

## Validation

`pytest -q -o addopts='' tests/test_plotter_racetrack.py` passes 6/6:

- 64 deterministic/random segments against the combined error protocol;
- 64 deterministic/random segments against the fused address protocol;
- frozen generator/artifact SHA and strict topology;
- all six public cases with exact ticks
  `[23091, 53753, 1173, 32568, 77959, 78896]`;
- a 40-round full-machine frame oracle covering degenerate, axial, reversed,
  corner-to-corner, and deterministic random segments.

`python3 scripts/preflight.py submissions/plotter/plotter_08.man plotter`
reports `READY TO SUBMIT`, 130x130, footprint 16,900, strict layout, 6/6
public cases, average 44,573.333 ticks, and local score 753,289,333.33.

## Freshness

The release branch starts at fetched `origin/main@47e7cf93`. The public
standings snapshot updated at `2026-07-26T23:56:10.445Z` was unfrozen and
showed `wheezards` at 20/20, rank 59, score 1,599,281,984. A direct read of
submission `c4e94257-0709-4eb4-bd4c-894721ec2294` confirmed it was `done`,
20/20, 152x145, footprint 23,104, average 69,221 ticks, and score
1,599,281,984. This evidence preceded the one authorized submission
mutation recorded in the Result section.
