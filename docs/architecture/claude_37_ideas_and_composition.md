# claude_37: leaderboard clusters are IDEAS, and our binding constraint is composition

Status: 2026-07-27 ~07:25Z. This records a strategy discussion with the
user that reframes how we pick work. It is the most useful thing written
today and it is deliberately placed where a cold reader will find it.

## The reframing (the user's, and it is better than what I was doing)

I had been ranking work by **leaderboard density**: which rank is
cheapest to reach, measured as the score factor needed for one place.
That is a correct measurement and the wrong abstraction.

**Clusters of teams on the leaderboard are IDEAS.** A cluster forms
because some number of teams independently grasped the same insight and
converged on what it is worth. The first idea is always *solve it at
all*; later ideas make the solution smaller or faster.

The user's worked example, Triangle:

1. Read the statement and the language, understand how to make a loop —
   you pass every test and score. **First idea, first cluster.**
2. Realise the answer is `x*(x+1)/2` rather than an accumulation loop.
   **Second idea, second cluster.**
3. Realise the program does not need `H` in it at all. **Third idea —
   and that is the perfect solution.** (We are rank 1 of 261 here.)

### What follows, and it changes prioritisation

**Improving inside a cluster is nearly worthless. The payoff is at
boundaries.** Today's numbers show this starkly:

    matmul   1.42x better  ->  2 ranks  (+0.0263)   we got better at the same idea
    snake    1.05x better  ->  1 rank   (+0.0159)   we happened to sit on a boundary

A 42% improvement and a 5% improvement bought almost the same thing. So
"what factor can I get?" is the wrong question. The right one is **"which
idea am I missing, and where is its boundary?"** Density still tells you
where the boundaries are — it is the census of ideas — but the idea
framing tells you what to do when you arrive at one.

## The three concepts that move you up

Per the user, movement comes from exactly three things:

1. **Composition of rooms** — how rooms are shaped, rotated, packed, and
   wired to pipes.
2. **Optimisation of room content** — the walk inside a room: tighter
   cycles, fewer wasted cells on the hot path.
3. **Algorithmic thinking** in terms of pipelines and little-man
   operations.

**We are strong at (3) and weak at (1) and (2).** That is the diagnosis,
and today produced hard evidence for all three parts of it.

## Evidence: we have ideas we cannot cash

gpt produced a genuine new idea for Reverse — **linear-time reversal by
spatial scheduling**, where a farm of workers receives in creation order
and sends after staggered delays, so no LIFO storage is needed at all.
Verified on the organizers' own WASM: **8/8 at 206.375 average ticks
against the live machine's 313.750 — a real 1.52x.**

And we could not use it. It came out at **box 23** when the break-even is
**box 16** (`sqrt(53,023.75 / 206.375)`), so it scores 2.06x *worse* than
the machine we already have. A new idea, correct and proven, lost
entirely for lack of composition skill.

## Evidence: a human beat the whole solver stack by hand

The user opened `memory_13` in the visual editor and moved some blocks.
The result, `tarstars_memory_14`, is **live**:

    memory_13   29x30  box 30  fp 900   15,987.1 avg ticks   14,388,375
    memory_14   29x30  box 30  fp 900   15,565.6 avg ticks   14,009,062

Identical box, identical rooms at identical positions, identical pipe
lengths `[2,2,4,10,10,13,21]`. **Twelve cells differ, across three rows,
inside one room:**

    row 27:  13 |^    >       sv  |
             14 |^     >  sv      |
    row 28:  13 |^             <  |
             14 |^         <      |

The hot loop's horizontal excursion was shortened by five cells each way
— ten cells per iteration — for **2.71% fewer ticks and zero footprint
cost**.

**Our solver stack cannot do this.** `layout_solve` places rigid rooms.
`layout_route` routes pipes between them. `room_reflow` only reshapes a
room's aspect ratio. Nothing looks *inside* a room and tightens a cycle.
This is concept (2) and we have no tool for it at all.

## Evidence: why composition is hard, measured

It is not only a tooling gap. `r`/`R` receive from the **nearest
incoming** pipe and `s`/`S` send to the **nearest outgoing** one, resolved
by Manhattan distance from the man's own cell (`sim.Machine._nearest`).

**There is no way in the language to say "this cell talks to that
pipe".** Connection is positional, so geometry and wiring are entangled:
move a room's contents and you silently rewire it. That is exactly how
the pathfinder fold died — geometrically perfect, box 1873 -> 813, pipe
multiset byte-identical, and it deadlocked with every man blocked on `r`.

And the entanglement is not incidental. In pathfinder's big room:

    462 of 497 I/O cells belong to a pipe whose cells straddle a cut line

A pipe has exactly one source endpoint and one destination endpoint, so
cells split across bands by a fold cannot all remain nearest to it.
Preserving bindings would require splitting shared pipes, which changes
FIFO semantics — the values would land in separate queues and lose their
order. **For that room, under a multi-band fold, the binding contract is
unsatisfiable.**

`room_reflow.binding_map()` / `bindings_preserved()` now export the
contract so a fold can *check* itself in milliseconds instead of after a
434 KB artifact and a multi-minute judge run. But exporting it does not
make it satisfiable.

## What this implies for tooling

The missing primitive is **an IR in which connection is NAMED rather than
POSITIONAL**. Today `layout_ir` faithfully inherits the language's
positional binding instead of abstracting over it, so every geometric
transformation risks silent rewiring. Given a representation where a cell
declares which pipe it uses, geometry becomes free to change subject to
realising the declared bindings — and concepts (1) and (2) both become
tractable, because a transformation can be checked rather than hoped for.

## The cheap, immediate version

The user's memory edit generalises into something mechanical and safe:

> **Find the man's cycles inside a room and shrink their excursions into
> adjacent free space, preserving glyph order.**

It changes no box, touches no pipe length, and `binding_map()` verifies
that nothing rebound. Unlike a fold it cannot silently deadlock, and
unlike a squeeze it cannot shorten a pipe. It is hours rather than a day,
and it applies to **every artifact we own** rather than one — which is
the definition of a good tool here.

That is the highest-value buildable thing on this list, and it exists
because a human did it once by hand and it worked.
