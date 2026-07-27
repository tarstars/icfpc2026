# Tarstars Plotter next-rank geometry

## Result

`submissions/plotter/tarstars_plotter_09.man` is a strict 80x125 Plotter
candidate built from the frozen `plotter_08` rooms.

| metric | `plotter_08` | candidate | change |
| --- | ---: | ---: | ---: |
| scoring footprint | 16,900 | 15,625 | -7.544% |
| public average ticks | 44,573.333 | 44,240.833 | -0.746% |
| public local score | 753,289,333.33 | 691,263,020.83 | -8.234% |

The exact candidate public ticks are
`[22996, 53468, 1078, 32188, 77579, 78136]`.  Its SHA-256 is
`25a19f4cae8d40b73bf76afe2ef5dd51fba88d7df42005c58731cd33080f8a6a`.

At the read-only standings check (`updatedAt`
`2026-07-27T01:06:10.368Z`), `wheezards` remained rank 59 at
1,097,878,080.  The tracked latest submission
`81cc6d5c-0812-4c77-93b5-d3a387b4915b` is `done`, 20/20, at that score.
Applying the local candidate/incumbent ratio to the live score projects about
1,007,478,116, 10.8 million below the current next-rank threshold
1,018,255,420.  This projection is not a hidden-case measurement.

## Geometry

The fused worker's `start` basic block is moved from the first generated band
to the last.  Named control-flow edges make that reorder semantic geometry,
and it exposes one additional legal staircase merge.  After fold and squeeze,
the worker is 26x123 instead of 26x125.

A 123-row room cannot keep both bottom pipes inside a 125-row box: a source
pipe must spend its first exterior cell moving outward before it can bend.
The candidate instead puts the two worker outputs on opposite side walls at
the same local row:

- raw address sends occur at local column 9 and bind west;
- ring sends occur at local column 13 and bind east.

With endpoints immediately outside the 26-column room, the horizontal
distance comparison is 10 versus 17 for raw output and 14 versus 13 for ring
output.  The common vertical term cancels, so both bindings are strict.

The input/setup stack, router, compact PLOT driver, SWAP, and DISPLAY occupy
the west band.  DISPLAY is lifted one row, leaving its bottom receive endpoint
on row 124.  A vertically mirrored standard relay keeps its ports on the
right; those pipes attach on the relay's right wall so the outward ring and
return remain planar.  The occupied box is rows 0..124 and columns 0..79.

## Negative evidence

Moving both `start` and `loop_check` exposed two additional staircase merges
and produced a 26x121 rectangle, but the folded component skipped
`loop_check`: a main-diagonal component case emitted only the initial address
and terminator.  The local merge predicate is therefore insufficient for
arbitrary branch-block reordering.  The `start`-only 26x123 fold passed the
same component case and was retained.

An initial full packing also shortened ROUTER-to-SWAP from 49 to 14 cells.
The display committed after only the first pixel; restoring the end-control
delay to 50 cells recovered the complete frame.  This confirms the downstream
pipe-length race remains a live constraint.

## Validation

Commands:

```text
PYTHONPATH=src uv run pytest -q tests/test_tarstars_plotter_next.py -vv
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/plotter/tarstars_plotter_09.man plotter
uv run icfpc-api --compact standings \
  0c3e3d4d-2901-45f1-81cf-5704d49c9139
```

Results:

- 64 deterministic/random fused-worker protocol segments: pass;
- 40-round exact frame oracle: pass;
- exact public suite: 6/6;
- strict preflight: READY TO SUBMIT;
- topology: 12 rooms, 14 pipes, 10 men;
- pipe lengths:
  `[2, 3, 3, 3, 3, 4, 25, 29, 36, 50, 51, 57, 111, 117]`.

## Live result

Submission `9d8d2ac2-449c-42f8-9648-43328056538e` passed all 20 live cases
at 80×125, average 64,459.7 ticks, and score 1,007,182,812.5. This is a
90,695,267.5-point (8.26096%) reduction from `plotter_08` and
11,072,607.5 below the pre-submit next-rank threshold. The exact response is
preserved in `submissions/plotter/tarstars_plotter_09-submit.json`.
