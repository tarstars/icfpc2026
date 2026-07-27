# claude_42: buy delay with a LOOP, not with distance

The user's idea, 2026-07-27 ~11:05Z, recorded because it attacks the term
that actually scores.

## The observation

Where a machine needs a man to arrive `N` ticks later, it makes him walk
`N` extra cells. Distance *is* the delay. But a long straight run has to
go somewhere, and horizontally it makes the room **wide** — and score is
`max(w, h)^2 * ticks`, so width is squared.

**A small local loop buys the same delay in a constant amount of space.**
A cycle of `L` cells traversed `K` times costs `L` cells of room and
delivers `L*K` ticks.

## It is real: we walk enormous blank distances

Longest run of consecutive BLANK cells on a man's actual traced path:

    plotter   119 cells   1,642 runs of >=4, dozens at 89
    memory     19 cells   only 5 runs of >=4
    tcp         9 cells   14 runs of >=4

plotter walks 89 blank cells at a stretch, repeatedly. memory and tcp are
already tight, so this is not a universal win — it is a *plotter-shaped*
win, and it is the same machine the snake line-merge is attacking.

## The construction

The backpack is the only counter with a conditional turn attached:

    b   BP = A
    m   BP -= 1
    d   turn clockwise if BP > 0, else go straight
    a   turn counter-clockwise if BP > 0, else straight
    x   turn by BP's low bit -- always turns

So a counted delay loop is a small arrow cycle containing one `m` and one
`d` at a corner: while `BP > 0` the `d` turns the man back into the cycle;
at `BP == 0` he goes straight and exits.

    setup:  `NN`  b        load the count, move it to the backpack
    body:   a cycle of L cells containing  m  ... d

Cost: `L` cells of space plus ~5 for the literal and `b`. Delay: `L*K`.
Exact delays come from choosing `L` and `K` and padding the remainder with
a short straight run — `L*K + r`, with `r < L`.

**Space goes from O(N) to O(L).** For plotter's 89-cell runs, an 8-cell
loop iterated 11 times is the same delay in under a tenth of the width.

## THE CATCH, and it decides where this is usable

**The backpack is a shared register and there is no stack.** These
programs already use `b`/`m`/`d`/`a` for real control flow, so a delay
loop **clobbers BP**, and loading the count clobbers **A** as well. There
is nowhere to spill to except `B` or a pipe.

So the transformation is clean only where the man's registers are dead:

- immediately after an `s` (the value has been sent);
- on a man dedicated to timing that carries no data;
- where `B` is provably free and can hold the spilled value across the
  loop (`M`/`W` to save and restore).

Anywhere else it needs a register-liveness analysis first — which
`room_reflow.walk_graph` is already most of the way to providing, since it
walks `(cell, direction)` states; it would need register tracking added.

## Do not confuse this with pipe delay

Between rooms, delay is already cheap in width: a pipe's length is its
delay, and a pipe can be **coiled** — a serpentine 40-cell pipe fits in a
7x7 patch. So for inter-room timing the answer is "coil the pipe", and
`coil_to_length` in `layout_route.py` does exactly that.

**This idea is for INTRA-room timing** — one man's own walk — where there
is no pipe to coil and distance is currently the only lever.

## Where it would have paid

- **plotter**: 1,642 blank runs, many of 89 cells, in a machine whose box
  is height-bound at 125 with 45 free columns.
- **gpt's reverse Y-farm**: its whole design is "worker `i` waits `D-2i`
  ticks", realised as private path length. That is `sum(D-2i) = W^2` cells
  — 256 at W=16 — and it is precisely why the farm could not fit inside
  the box 16-17 it needed to beat the incumbent. Counted loops instead of
  distance may be exactly what makes that architecture affordable.

That last one is the strongest case: a proven-correct algorithm we could
not ship **because its delays were spatial**.
