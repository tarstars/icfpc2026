# Pathfinder machine

Updated: 2026-07-25T19:50:45Z

## Current design

The generator in `src/littleman/pathfinder.py` stores each board row as a
64-bit word containing the unreached mask and three distance-modulo bit
planes.  A generated controller resets and seeds the planes, performs
backwards bitboard BFS, and then queries the planes in up/right/down/left
order.  Display commands are demultiplexed by one small router.

The controller compiler uses local fall-through routes and a spec-safe
literal allocator.  Each BFS wave dilates all four neighbours in one
14-interior-row streaming pass.  During path playback, one two-lap ring scan
gathers the up/current/down rows and resolves all four directions; the old
implementation rescanned the ring for every attempted direction.

## Gated baseline

Command:

```text
uv run python scripts/preflight.py submissions/pathfinder/pathfinder_00.man pathfinder
```

The exact artifact is 967,231 bytes with SHA-256
`ba5438110af231d09d12453b9d37f31c443ed9c6c29b3697be2f4d401e591bdd`.
It parses as 7 rooms, 11 pipes, and 5 men.  Its occupied bounds are 452 by
2,034, for footprint 4,137,156.

| Public case | Result | Ticks |
| --- | --- | ---: |
| a straight shot | pass | 3,672,910 |
| around the pillars | pass | 5,561,418 |
| the long way | pass | 12,769,742 |
| rooms and doors | pass | 8,333,494 |
| a cluttered field | pass | 6,683,330 |
| running errands | pass | 8,414,468 |
| there and back again | pass | 11,117,230 |

Average public ticks are 8,078,941.714 and the local footprint-tick score is
33,423,842,186,907.43.  Composite preflight reports `READY TO SUBMIT`.

An independent adversarial replay used Claude's pure-Python reference on
eight deterministic random wall layouts.  All eight frame streams matched;
the selected shortest paths ranged from 2 to 12 moves.  The checked-in test
also exercises a tie and all four move directions.

## Freshness

Before committing this WIP:

- `origin/agent/claude` was integrated at
  `df990eb`;
- the live problem remained graded with the 15,000,000 tick cap;
- the Pathfinder standings update was
  `2026-07-25T19:50:45.751Z` and contained no `wheezards` row.

No submission had been created at this freshness checkpoint.

## Live baseline and compact candidate

`pathfinder_00` was submitted as
`f55011a1-3c3d-43ca-be41-85fca46133da`.  It passed 15/18: all public
cases and 8/11 private cases, with the other three reaching the step cap.
This confirmed that the remaining risk was tick throughput, not loading,
geometry, or frames.

`pathfinder_01` shortens the ring pipes only as far as their required setup
capacity permits, reduces scratch/update pipes to three cells, and compacts
the operation zones in every hot room.  The algorithm and token protocols
are unchanged.  Its final preflight result is:

| Metric | pathfinder_00 | pathfinder_01 |
| --- | ---: | ---: |
| occupied bounds | 452x2034 | 187x1957 |
| footprint | 4,137,156 | 3,829,849 |
| bytes | 967,231 | 500,984 |
| average public ticks | 8,078,941.714 | 3,355,635.571 |
| local score | 33,423,842,186,907.43 | 12,851,577,537,600.14 |

The worst public case is now 5,284,281 ticks instead of 12,769,742.
`pathfinder_01` is `READY TO SUBMIT`; its SHA-256 is
`a6351f2a16f8985b5177dcf560bdc824549a748c4452d498a867b3a056163dac`.

The live submission `0c04a141-a73b-443c-a274-741bfe67d857` passed 18/18.
The server measured 4,581,436.722 average ticks and score
17,546,210,849,166.055.
