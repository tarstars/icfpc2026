# Project manifest: a component library of shape-variant rooms

Status: adopted 2026-07-27 (the user's framing). This is the direction the
project should move in. It does not have to be built at once — it should be
approached in baby steps, each of which pays for itself.

## The idea

Build a solver that **optimises a room's size while preserving its
function**, and that emits **several versions of the same room in different
shapes**. Collect those versions into a **library of components**. A second
layer of optimisation then composes whole programs out of the library.

    room + unit tests  ->  mutate  ->  { variants that pass the tests }
                                          smaller, OR same area but a
                                          different width x height
                                            |
                                            v
                                     component library
                                            |
                                            v
                              program-level packer picks the shapes
                              that square up the whole machine

## Why this is the right abstraction, and not what we were doing

Everything we built until now preserves **structure**: rigid room text,
pipe endpoints, cell positions. That keeps failing, because the language
binds `r`/`s` to the *nearest* pipe by distance from the cell — connection
is positional, so geometry and wiring are entangled. Move the contents and
you silently rewire the machine. The pathfinder fold was geometrically
perfect and deadlocked for exactly this reason.

A **behavioural** contract cuts the knot. A room's unit test says only:
*given this sequence on the incoming pipes, produce that sequence on the
outgoing ones.* It says nothing about where cells sit. Below that contract
geometry is free, and a mutation is legal precisely when the tests still
pass.

## Why shape variety matters as much as size

Score is `max(width, height)^2 * avgTicks` — the **larger** side, squared.
So a packer holding both a 6x20 and a 10x12 version of one room can square
up a machine even when neither variant is smaller than the other. **Shape
diversity is a product of this pipeline, not a side effect.** A room that
only ever comes in one shape forces the whole layout to accommodate it;
that is how one 82x10,024 room makes a machine 25,797 tall.

## The pipeline, concretely

1. **Contract.** Run the whole machine on the public cases and record every
   value crossing the target room's boundary, per pipe, in order. That
   trace IS the unit test — exact, derived from real behaviour, and it
   needs no standalone harness.
2. **Mutate.** Transform the interior: shrink a hot loop's excursion, move
   a lane, reflow rows into columns, rotate by 180 degrees (a rotation
   preserves handedness; a mirror does NOT — `X`, `d`, `a`, `x` turn by
   `CLOCKWISE`/`COUNTERCW` and a reflection silently reverses them).
3. **Re-embed and replay.** Put the variant back, re-run the cases, and
   compare traces. Identical trace = same function.
4. **Keep** if the box shrank, or if the area is unchanged but the aspect
   ratio is new. Both outcomes have value.
5. **Bank** the variant in the library, keyed by contract hash and by
   `width x height`.

## Guard rails learned the hard way

- **Never shorten a pipe.** Its length is both delay and capacity; a
  shortened storage pipe deadlocks with no other symptom and still passes
  the public cases.
- **Check bindings after any move.** `room_reflow.binding_map()` and
  `bindings_preserved()` cost milliseconds and catch silent rewiring.
- **The trace is a stronger test than the judge**, because the judge only
  checks final output while the trace pins the room's behaviour at its own
  boundary. But it is only as complete as the cases that produced it.
- **Ticks are part of the contract** where a machine is timing-sensitive
  (`q`, `R`, `U`). Elsewhere they only affect score, not correctness.

## Evidence this works

The user did step 2 by hand, in a visual editor, on `memory_13`: twelve
cells moved across three rows, shortening a hot loop's excursion by five
cells each way. Identical box, identical rooms, identical pipe lengths,
**2.71% fewer ticks**, and it is live as `tarstars_memory_14`. No tool we
own could have produced it.

## Baby steps, in order

1. **Contract recorder** — trace a room's pipe boundary. (Start here; it is
   the foundation and it is independently useful for debugging.)
2. **One mutation: hot-loop excursion shrink** — the transformation the user
   performed by hand. Safe by construction: no box change, no pipe touched.
3. **Search** — apply mutations repeatedly, keep what passes, on `memory`
   first because it is small (29x30, 7 rooms) and dense in the standings.
4. **Library format** — variants keyed by contract hash and shape.
5. **Program-level packer** — consume the library. This is where the
   existing CP-SAT placer finally becomes useful, because it will at last
   have alternatives to choose between.

Steps 1-3 are hours. Step 5 is the long game.
