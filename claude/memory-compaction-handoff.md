# Memory compaction handoff (completed; historical)

Status update, 2026-07-25: this handoff is no longer active.
`memory_01` was repaired, preserved, and submitted successfully. It passed
24/24 live at 46x47 and score 91,372,247.625. See
`reports/2026-07-24-memory-compaction.md` for the final implementation and
validation. The material below is retained only as experiment history; do not
resume from its blocker.

Goal: geometry-only compaction of the Memory machine as variant
`memory_01`. Same logic, tighter layout. Current submitted memory is
67x38 (footprint 4489, server score 43.8M, id 788c05a4). Target ~47x47
(footprint 2209) = ~2x better score. Score = max(w,h)^2 x avg_ticks;
only the LARGER dimension counts, squared. Read docs/littleman-cookbook.md
first (esp. sec.4 pipe rules, sec.6 shared cells).

## Why it works / what changed

The 67 width came ENTIRELY from P4 sitting at the top-right (cols 48-66).
Everything else lives in cols 0-43 (P2 is 38 wide, the widest room; the
ring serpentine reaches col 38). So the plan is minimal-disruption:
relocate ONLY P4 to the bottom (below RELAY, where it blocks nothing)
and wrap its two P2<->P4 pipes up the empty right side. All other rooms
and 7 pipes are byte-identical to build_memory().

Function added: `build_memory_compact()` in src/littleman/memory.py
(right after build_memory). P4 moved to cv.put(39, 6, P4) -> rows 39-43,
cols 6-24. Only the two P4 pipes were re-routed:

    # P2 right row1 -> wrap down col45, under, up to P4 left row2
    cv.pipe([(1, 44), (1, 45), (44, 45), (44, 5), (41, 5)])
    cv.cells[(41, 5)] = ">"            # terminal bend into P4 left
    # P4 out bottom col14 -> wrap up col46 to P2 right row3
    cv.pipe([(44, 20), (45, 20), (45, 46), (3, 46), (3, 44)])

It renders at 47x46 (footprint 2209) and looks right visually, BUT:

## CURRENT BLOCKER (fix this first)

`Machine.parse` fails: `bad pipe glyph '-' at (3, 45)`.

Cause: the two wrap pipes COLLIDE near P2's right ports. P2's original
`P4 newh -> P2 right row3` port is at (3,44); my pipe B ends
[...,(3,46),(3,44)] running LEFT along row3 through col45,44. My pipe A
starts [(1,44),(1,45),...] and runs DOWN col45. They cross/overwrite
around (3,45)/(1,45). Also check (1,44) vs (3,44): both P2 right-wall
ports one row apart, and both wrap pipes hug cols 45-46 -> the row3
leftward run of pipe B passes col45 where pipe A goes vertical => shared
cell => bad glyph.

### How to fix (options, easiest first)

1. Give the two wrap pipes DISJOINT corridors. Pipe A occupies col45
   (vertical, rows 1-44) and row44 (cols 5-45) and col5 (rows 41-44).
   Pipe B must NOT touch col45. Reroute pipe B to use col47 for its
   vertical and enter P2 (3,44) from row3 WITHOUT crossing col45:
   the problem is pipe B's terminal `...(3,47),(3,44)` runs left across
   col46,45 -> crosses pipe A's col45. Instead approach P2's (3,44) from
   a row that pipe A doesn't use, or move pipe A's vertical to col45 and
   pipe B's terminal to enter at row3 from the RIGHT but bend UP-then-left
   only in cols >=46. Concretely try:
       pipe A: [(1,44),(1,45),(44,45),(44,5),(41,5)] ; patch (41,5)=">"
       pipe B: [(44,20),(46,20),(46,47),(3,47),(3,44)]
   i.e. push pipe B out to col47 vertical and run its row3 entry across
   cols 47->44 (crossing col46,45!). STILL crosses col45. The real fix:
   pipe B must reach (3,44) along row3 from the right, which unavoidably
   crosses col45 (pipe A). SO: move pipe A's vertical OFF row3's path.
   Make pipe A drop on col45 only for rows 4..44 (start it going down
   AFTER row3): [(1,44),(1,45),(2,45)... ] still passes row3 col45.
   => Cleanest: swap which port each pipe uses is impossible (ports are
   fixed by P2 internals). Instead route pipe B's row3 approach on col44
   ONLY (P2 wall is col43, (3,44) is the entry cell) and bring pipe B UP
   col44 from below — but col44 row1 is pipe A's start (1,44). One row
   apart; a vertical pipe B on col44 rows 3..45 and pipe A entering (1,44)
   then east to (1,45): pipe A only uses (1,44),(1,45). Pipe B uses col44
   rows 3..45. They share NOTHING (pipe A row1, pipe B rows>=3 on col44).
   TRY THIS:
       pipe A: [(1,44),(1,45),(44,45),(44,5),(41,5)] ; patch (41,5)=">"
       pipe B: [(44,20),(45,20),(45,44),(3,44)]   # up col44 into P2 row3
   Check pipe B: (44,20)->(45,20) down, ->(45,44) right along row45,
   ->(3,44) up col44 into P2 (3,44), terminal points... it arrives going
   UP; (3,44) forward-up is (2,44) NOT a P2 border. P2 border for row3
   entry is (3,43) (west). So terminal must point WEST '<'. But pipe
   arrives going up -> needs a bend at (3,44) to west, but then forward
   (3,43)=P2 border. A bend arrowhead in the new direction '<' works IF
   there's a further cell... terminal bend is allowed (cookbook). Patch
   (3,44)="<". But (3,44) came from (4,44) going up; '<' there = bend to
   west, forward (3,43) P2 border. GOOD. And col44 rows3-45 vertical must
   be clear: col44 is right of P2 (col43) and everything; rows 3-45 clear
   EXCEPT (1,44) which is row1 (pipe A) - not in 3..45. So disjoint.
   This should parse. VERIFY with the resolution/parse steps below.

2. If routing stays messy, widen the right gap: shift P4 down 1-2 rows
   and give each wrap pipe its own column (45 and 47), leaving col46 as a
   blank separator, accepting width 48 (footprint 2304, still ~1.95x).

## Verify checklist (run after each edit)

    uv run python -c "from littleman.memory import build_memory_compact as b; from littleman.sim import Machine; print(Machine.parse(b()))" # must not raise
    uv run python -c "
    from littleman.memory import build_memory_compact
    import pathlib; pathlib.Path('submissions/memory/memory_01.man').write_text(build_memory_compact())"
    uv run python -m littleman submissions/memory/memory_01.man memory   # MUST be 7/7
    # confirm dims: expect width<=47, height<=47

CRITICAL: it must pass 7/7 public cases identically to build_memory
(same logic). If any case fails, the re-route changed nearest-pipe
resolution or a pipe length (ring capacity). Compare per-case ticks to
build_memory; they should be nearly identical (wraps add a few transit
ticks only).

## After it passes

1. Save immutable `submissions/memory/memory_01.man` (already immutable
   rule: never overwrite memory.man/the submitted source).
2. Create submissions/memory/variants.json (memory currently has NONE -
   backfill memory_00 = current submitted 67x38 too). Schema: copy
   submissions/sort/variants.json. Record generator
   `src/littleman/memory.py:build_memory_compact`, dims, footprint,
   per-case ticks, local score.
3. Submit: `uv run icfpc-api submit d0b34a23-67c1-4087-b88e-90a74404d50e
   submissions/memory/memory_01.man --confirm --wait > /tmp/out.json`
   (memory problemId d0b34a23-67c1-4087-b88e-90a74404d50e). Capture the
   full JSON (don't tail); record submission id + serverScore in
   variants.json. Only-best-counts, so submitting never lowers score.
4. Add a tests/test_memory_compact.py: assert build_memory_compact passes
   7/7 (mirror tests/test_reverse.py style) and footprint < 4489.
5. Update claude/journal.md + STATE.md board; commit + push.

## Bigger follow-on (separate, риск higher)

3-per-word packing: encode three <=21-bit cell values (offset +1e6 into
[0,2e6] subset [0,2^21)) into one 64-bit word, base 2^21. Shrinks the
ring from 100 circulating values to 34 -> much shorter serpentine (both
footprint AND ticks). Needs encode/decode logic (a `/` by 2^21 gives
quotient+remainder in one op) in P3W/P3R. This is a LOGIC change ->
memory_02, build+debug like a new station. Do AFTER memory_01 ships.
