# Pathfinder machine

Updated: 2026-07-25T16:10:00Z

## Current design

The WIP generator in `src/littleman/pathfinder.py` stores each board row as a
64-bit word containing the unreached mask and three distance-modulo bit
planes.  A generated controller resets and seeds the planes, performs
backwards bitboard BFS, and then queries the planes in up/right/down/left
order.  Display commands are demultiplexed by one small router.

The controller compiler uses local fall-through routes and a spec-safe
literal allocator.  Horizontal left/right dilation is combined into one row
pass.  One counted update service handles all three target modulo planes.

## Measured checkpoint

Command:

```text
uv run python <focused seven-case judge loop>
```

The generated source is 1,289,371 bytes, parses as 7 rooms, 11 pipes, and
5 men, and occupies a 532 by 2,698 rendered grid.  All emitted frames observed
before a cap were exact.

| Public case | Result | Ticks |
| --- | --- | ---: |
| a straight shot | pass | 5,978,208 |
| around the pillars | pass | 9,323,448 |
| the long way | tick cap | 15,000,000 |
| rooms and doors | pass | 13,426,216 |
| a cluttered field | pass | 11,609,494 |
| running errands | pass | 13,242,918 |
| there and back again | tick cap | 15,000,000 |

For `the long way`, setup completed at tick 513,552 and its first 49-move
round completed at tick 12,178,116.  The next round had not emitted its first
frame at the cap.  This isolates the remaining problem to BFS throughput, not
display movement throughput or tie-breaking.

## Freshness

Before committing this WIP:

- `origin/main` was integrated at
  `3473e7bf906eeb92ff594be5a0f7db180a252ace`;
- the live problem remained graded with the 15,000,000 tick cap;
- the Pathfinder standings update was
  `2026-07-25T16:08:45.983Z` and contained no `wheezards` row.

No submission was created.

## Next action

Replace the separate vertical-down and vertical-up passes with one streaming
pass that unions the source frontiers of both neighbouring rows before one
update.  This removes 15 of the current 47 row updates per BFS wave and is the
smallest remaining change likely to clear both capped cases with private-case
margin.
