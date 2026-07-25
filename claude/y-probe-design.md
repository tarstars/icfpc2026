# Y-probe design: settle die-vs-stop on the server with two safe submissions

Goal: resolve the /split-vs-reference contradiction on collisions (die vs
stop) and confirm `Y` is live server-side, using submissions that can only
fail cases, never lower a score (grading: "Submitting will never lower
your score"; Memory best 27,753,851 stands regardless).

Insight that motivates trusting /split but demands proof: in valid base
littleman a collision was UNREACHABLE before Y (one `@` per room; men
never leave rooms), so the reference's "both stop" was dead text and
/split's "both die" is the first live definition. Probe anyway.

## Architecture

`GATE` room spliced between `I` and the proven memory_04 pipeline:
`I -> GATE -> P1(memory_04) -> ...` — GATE has exactly one incoming and
one outgoing pipe (zero nearest-pipe ambiguity) and ends as a relay
racetrack (`> r s v / ^ <`) parked on blocking `r`. Blocking makes the
composition latency-insensitive: if the relay man survives to the loop,
the whole machine behaves as memory_04 with added input latency and must
pass 24/24.

## Probe 1 — Y navigation (control experiment)

`@` man walks onto `Y`. Copy U parks in a harmless arrow-square loop (no
pipe ops, off all lanes). Copy D walks a corridor into the relay
racetrack. Expected: 24/24 under ANY collision semantics.
Decision value: Y accepted at load? birth geometry as documented? copies
carry registers? If this fails, Y is not live (or geometry differs) and
Probe 2 is uninterpretable.

## Probe 2 — collision (the measurement)

Same, plus: U walks into a second `Y` heading north; its copies A (born
west cell, heading W) and B (born east cell, heading E) are routed via
tunable jogs to arrive on cell X **on the same tick** (same-cell arrival
is covered by both the old text "touches" and the new "die"; avoid the
swap case, which only /split defines). D's corridor crosses X strictly
later (>= 2 ticks), then enters the relay loop.

- die semantics: A,B removed; X free; D relays; **24/24**.
- stop semantics: corpse blocks X; D touches it and stops; **0/24**.
- Y rejected: load error / error field in the response.

## Construction requirements (implementer follows these exactly)

1. **Mini-sim first** (in `src/littleman/split_probe.py`): a ~100-line
   simulator of ONLY {arrows, spaces, Y, @-nop, same-cell collision} with
   a `mode` flag (`die` | `stop`), plus the /split ordering rule (right
   copy inherits parent slot, left appended). No pipes. Use it to verify
   the choreography tick-by-tick in BOTH modes.
2. **Parametric layout with jogs.** Encode the GATE room as code with 2-3
   integer jog parameters (extra corridor cells for A and for D); write a
   tiny loop that searches jog values until: A and B enter X the same
   tick; D reaches X at least 2 ticks after; no two live men ever share a
   cell before X except at X. Assert all three in a test.
3. **Choreography sketch to start from** (interior coords; adjust freely,
   the tuner decides): `@`(4,1)E, Y1(4,2); U born (3,2) via `>` runs east
   row 3 to `^`(3,6) then north onto Y2(2,6); A born (2,5) W with jog
   (`<`,`v` path down cols 4-5), B born (2,7) E (`v` down col 7, `<`
   along row 7, `^` at (7,6)); X=(6,6) a SPACE cell on D's lane; D born
   (5,2) S with a delay serpentine on the west side, east along row 6
   through X, then into the racetrack rows 8-9. Cells on D's lane must be
   harmless for D eastbound (spaces or `>`); A/B approach X vertically so
   their arrows never sit on D's lane.
4. **Plumbing check without Y**: generate a stand-in GATE where the Y
   cells are replaced by a plain straight path for one man into the relay
   loop (no split, no colliders); the FULL machine (stand-in GATE +
   memory_04) must pass 7/7 public Memory cases under the real judge and
   `scripts/preflight.py`. This validates pipes/bindings/geometry with
   the base simulator, which does not know Y.
5. **Artifacts**: `submissions/memory/memory_05_probe_y_nav.man` and
   `submissions/memory/memory_06_probe_y_collision.man`, generated
   byte-for-byte by `split_probe.py`, both parseable by `Machine.parse`
   (Y parses as a grid char; only execution would choke, and the server
   is the executor we are probing). Nothing existing is modified;
   memory_04 generator is imported read-only.
6. **No submission by the implementer.** Claude submits and reads the
   responses.

## Decision tree after submission

| P1 result | P2 result | Conclusion |
|---|---|---|
| 24/24 | 24/24 | Y live; collisions DIE (adopt /split wholesale) |
| 24/24 | 0/24 | Y live; collisions STOP (reference wins; /split die-rule wrong or swap-only) |
| error/load fail | — | Y not live server-side yet; re-probe later |
| 0/24, no error | — | choreography or geometry assumption wrong; debug with mini-sim before concluding anything |

Record the raw responses under `submissions/memory/` per convention and
update `claude/split-instruction-20260725.md` with the verdict.
