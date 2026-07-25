# NEW INSTRUCTION: `Y` (Split) — announced mid-contest at /split

Detected 2026-07-25 ~15:1xZ (user spotted the page). Content served by
`GET https://icfpcontest2026.com/api/v1/split/docs` (public, no auth).
The language-reference page does **not** mention `Y` — /split is the sole
authoritative source, and it *contradicts* the reference on collisions.

## Verbatim reference ("Y, precisely")

> - `Y` splits the little man in two. The copies are born on the cells to
>   his left and his right — left and right relative to his heading as he
>   enters the `Y` — each heading away from the `Y`. The original man does
>   not continue past the `Y`; only the two copies remain.
> - Both copies carry the original little man's registers, including his
>   backpack.
> - The tick after they were born, the copies execute the instruction they
>   were born on and then move.
> - Little men act in creation order, every tick. On a split, the copy
>   born to the **right** takes over the splitting man's place in that
>   order; the copy born to the **left** becomes the newest little man and
>   acts after all others.
> - **Y is unconditional**. It is executed even if a birth cell is blocked
>   by another man or a wall.
> - If the birth cell is a wall, the program halts with an error.
> - If the birth cell is another little man (including a little man
>   blocked on an instruction), both little men die. This is *not* an
>   error.
> - If two little men in the same room collide, they both die. This is
>   not an error. This includes two men arriving on the same cell in the
>   same tick, and two adjacent men moving through each other (swapping
>   cells) in the same tick.
> - If two little men are spawned on the same cell by two split
>   instructions they both die. This is not an error.
> - The maximum number of live little men is 65536. Exceeding this limit
>   is an error and ends your program.

Demo program from the page (copies head up/down after entering `Y`
heading east — left copy relative to east = north):

```
+------+
| >  H |
|      |
|@Y    |
|      |
| >  H |
+------+
```

## Semantics notes (derived, to encode in the simulator)

- Birth cells: for heading east, left = the cell above the `Y`, right =
  the cell below; copies head north and south respectively ("away from
  the Y"). Symmetric for other headings.
- Execution order is now explicitly *creation order*, with the split's
  right copy inheriting the parent's slot and the left copy appended
  last. Our sim's man-index order must model insertion accordingly.
- **Collision rule CHANGED vs the language reference**: the reference
  (still live, re-checked) says colliding men "both stop"; /split says
  they "both die" — removed, not left as obstacles — and adds two cases
  our sim does not detect at all: same-cell same-tick arrival, and
  adjacent men swapping through each other. /split is the newer, more
  specific text; treat it as authoritative and verify empirically on the
  server before relying on either behavior.
- Wall birth = error (unlike LLM's freeze; this is base littleman).
- 65536 live-men cap.

## Impact assessment

- **Existing artifacts: zero impact.** Every shipped machine is
  one-man-per-room; collisions and splits never occur.
- **Semester 4: zero impact.** LLM/LLLM interpret fixed op subsets that
  exclude `Y`; their "well-formed programs" guarantee holds. Builders not
  affected; no redesign mid-build.
- **Our simulator: does not know `Y`** (steps on it = bad-op error) and
  implements stop-not-die collisions without the swap/same-cell cases.
  Any Y-based design needs sim support first: op + death-removal +
  swap/same-cell collision + spawn-conflict + creation-order insertion +
  the cap.
- **Opportunity (why this was released ~21h before the end): dynamic
  parallelism.** One `@` can fan out into 2^k workers inside a single
  room — parallel sweeps, worker farms, systolic lines — where today we
  pay one room per man plus pipes between them. The biggest-footprint
  problems are exactly the multi-worker ones: gradebook (386x423 live),
  sudoku (184x248), matmul (183x180), subset-sum (3646x3029!). Collapsing
  multi-room worker farms into one room attacks the squared term
  directly. This likely resets the leaderboard on those problems for
  every team that exploits it; assume competitors will.

## Proposed sequencing (user to confirm)

1. Unchanged: Semester 4 submissions first (in flight).
2. `Y` support in the simulator + directed tests (sim.py is
   integrator-owned: Codex implements or transfers the path; Claude can
   prototype in a subclass meanwhile). Verify die-vs-stop on the server
   with a cheap practice-problem probe if possible.
3. One targeted Y-redesign on the best ratio problem (candidates ranked:
   subset-sum and gradebook by footprint slack; sudoku by worker
   symmetry) — before generic composer polishing, since a successful
   Y-rebuild dwarfs geometry-only gains.

## RESOLVED: die-semantics confirmed in the official editor (user experiment)

2026-07-25 ~15:2xZ, the user built and ran this map in the contest editor
(the organizers' own simulator, the same implementation that animates the
/split demo):

```
+-------------------+
|     >     v       |
|                   |
| >   Y             |
|                   |
|     >          v  |
|@Y<                |
|  ^             <  |
|                   |
|                   |
|                   |
| >         ^       |
+-------------------+
```

Observed: the man divides at `Y`, copies travel the arrow loops, meet, and
**annihilate — both die when they meet** (removed, program continues), and
a copy reaching the second `Y` reproduces again. This matches /split's
death rule and contradicts the reference's stale "both stop".

Evidence level: Observed in the official client simulator by the user.
Residual risk that the server-side judge differs is small and is covered
by probe 1 (Y acceptance in the judge pipeline); probe 2 (collision
discrimination) is now OPTIONAL — the question it was built to answer is
answered.

Consequence: our simulator's Y implementation should adopt /split
wholesale: die-not-stop removal, same-cell and swap-through detection,
spawn-conflict deaths, creation-order insertion, 65536 cap.
