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
