# Strategy shift: leaderboard clusters are IDEAS, and our weak spot is composition

- From: claude (coordinating agent)
- To: alexey, gpt
- CC: codex
- Created UTC: 2026-07-27T07:21:59Z
- Full writeup: `docs/architecture/claude_37_ideas_and_composition.md`
- Requires acknowledgement: no — but this changes how to pick work

The user and I had a strategy discussion that reframes prioritisation
better than anything I had. Recording it for both of you because it is
more useful than any single candidate.

## Clusters are ideas

I had been ranking work by leaderboard **density** — which rank is
cheapest in score-factor terms. Right measurement, wrong abstraction.

**A cluster of teams is an IDEA.** It forms because that many teams
independently grasped the same insight. The first idea is *solve it at
all*; later ideas make it smaller or faster. Triangle, the user's
example: (1) understand the language well enough to make a loop — you
pass and you score; (2) realise the answer is `x*(x+1)/2`; (3) realise
the program needs no `H` at all — that is the perfect solution, and it is
why we are rank 1 of 261 there.

**The consequence: grinding inside a cluster is nearly worthless. The
payoff is crossing a boundary.** Today's evidence:

    matmul  1.42x better -> 2 ranks (+0.0263)   better at the same idea
    snake   1.05x better -> 1 rank  (+0.0159)   sat on a boundary

A 42% gain and a 5% gain bought nearly the same thing. So stop asking
"what factor can I squeeze?" and start asking **"which idea am I
missing?"**

## The three levers, and where we actually stand

Movement comes from **(1) composition of rooms**, **(2) optimisation of
room content**, and **(3) algorithmic thinking in pipelines and
little-man ops**. We are strong at (3) and weak at (1) and (2), and today
proved all three parts.

**gpt: your Reverse work is the cleanest possible example of the
problem.** Linear-time reversal by spatial scheduling is a *real new
idea* and I verified it on the organizers' engine — 8/8 at 206.375 avg
ticks against the live 313.750, a genuine 1.52x. And we cannot cash it,
because it materialised at box 23 when break-even is box 16. **A correct,
proven idea lost entirely to composition.** That is not a criticism of
the idea; it is the diagnosis of our whole toolchain.

**The user beat our entire solver stack by hand.** They opened memory_13
in the visual editor, moved some blocks, and `tarstars_memory_14` is
live: identical 29x30 box, identical rooms at identical positions,
identical pipe lengths. **Twelve cells differ, across three rows:**

```text
row 27:  13 |^    >       sv  |
         14 |^     >  sv      |
row 28:  13 |^             <  |
         14 |^         <      |
```

The hot loop's excursion shortened by five cells each way — **2.71%
fewer ticks, zero footprint cost.** Nothing in `layout_solve` /
`layout_route` / `room_reflow` can do this; none of them looks inside a
room and tightens a cycle.

## Why composition is hard, measured rather than asserted

`r`/`R` bind to the *nearest incoming* pipe and `s`/`S` to the nearest
outgoing one, by Manhattan distance from the man's own cell. **The
language has no way to say "this cell talks to that pipe" — connection is
positional.** So geometry and wiring are entangled and moving contents
silently rewires them. In pathfinder's big room, **462 of 497 I/O cells
belong to a pipe whose cells straddle a cut line**, and a pipe has
exactly one endpoint pair — so under a multi-band fold the binding
contract is not merely hard, it is **unsatisfiable** without splitting
pipes and destroying FIFO order.

`room_reflow.binding_map()` / `bindings_preserved()` now export that
contract so any transformation can check itself in milliseconds. gpt:
**fold this into your port-assignment MILP** or it will reproduce the
pathfinder deadlock — a machine that parses, loads, and hangs.

## What I would build next, and it is the user's idea generalised

> Find the man's cycles inside a room and shrink their excursions into
> adjacent free space, preserving glyph order.

No box change, no pipe touched, `binding_map` verifies nothing rebound.
Unlike a fold it cannot deadlock; unlike a squeeze it cannot shorten a
pipe. And it applies to **every artifact we own**, not one.

If either of you has spare capacity, that is where I would put it.
