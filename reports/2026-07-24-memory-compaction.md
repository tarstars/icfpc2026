# Memory: Geometry-Only Compaction

Date: 2026-07-24

Problem: `d0b34a23-67c1-4087-b88e-90a74404d50e` (`memory`), scored by
`max(width,height)^2 × average ticks`.

## Change

The baseline was 67×38 because its 19-cell-wide head-pointer room sat to the
right of the main machine. `memory_01` moves only that room below the FIFO
ring. Its two connections wrap around the right and bottom of the unchanged
machine in separate corridors:

- the request pipe uses column 45 and row 46;
- the return pipe uses row 45 and approaches the parser on column 44.

The rooms, instructions, ring capacity, and command protocol are unchanged.
Separating both bottom rows fixed the pipe crossing in the original work in
progress while preserving a 47-cell maximum dimension.

## Local validation

The exact artifact has SHA-256
`68d5fb3d73f21c7171ad59dde0f6b22a493cbba297f7bc1f8dcbab04cad92089`,
dimensions 46×47, and footprint 2,209. It passed all seven public cases at
ticks `[179, 1301, 3744, 2498, 3776, 1269, 55482]`, average
9,749.857142857143, and local score 21,537,434.42857143.

The baseline footprint was 4,489 and its local score was
43,756,206.85714285. Geometry compaction therefore reduced footprint by
50.79% and local score by 50.78%; the 17 extra ticks occur only in the
first public case.

## Live result

Submission `22931081-bd2d-4c19-a733-b8035e5bf0af` passed all 24 live cases
at 46×47, average 41,363.625 ticks, and score 91,372,247.625. The API
standings immediately before submission reported a best score of
181,952,075.875, so the accepted candidate improved that score by 49.78%.
The unfrozen standings snapshot at `2026-07-24T21:22:11.313Z` placed
`wheezards` 25th of 85 rows with 1.7 points.

The exact source, full server response, and comparison metadata are preserved
in `submissions/memory/`.
