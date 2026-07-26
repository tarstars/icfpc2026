# Matrix 07 component fold live

- From: codex
- To: claude, alexey
- Created UTC: 2026-07-26T15:08:00Z
- Requires acknowledgement: no

Codex applied the Grade Book component method to the unclaimed Matrix
Multiply lane. The single 109×124 controller had all nine inputs and nine
outputs on its bottom wall, making its row coordinate irrelevant to
nearest-pipe selection.

The full staircase fold freed 48 controller rows. A rows-only squeeze removed
44 global rows. The first candidate was locally correct but failed the strict
input-room gate because the inherited A pipe ran along I; re-routing A away
from I and trimming it from 334 cells to its exact 256-value capacity fixed
the gate without changing any public tick count.

Live submission `6ab675e8-2cf4-4639-9c07-c475e83be70a` is done: 20/20,
115×98, average ticks 637,932.1, score 8,436,652,022.5. The prior team best
was 20,042,330,424, so the live improvement is 57.91%.

Source commit: `2c619c4` on `agent/codex-matmul-components`; terminal response
is preserved at `submissions/matmul/matmul_07-submit.json`. This lane does
not overlap Alexey's Subset Sum/Brackets work.
