# claude_38: a randomized Rust room optimizer (MCTS over edit sequences)

Status: design, 2026-07-27. This is the engine `docs/MANIFEST.md` needs —
the thing that does at scale what the user does by hand in the visual
editor. It is written to be picked up cold.

## The measured target

    alexey-reverse_06  14x14  fp 196  98,676  ticks 503.4
    alexey-reverse_07  13x13  fp 169  84,922  ticks 502.5   box -1, ticks FLAT
    memory_10 30x30 -> memory_11 29x29                      box -1

One cell off the binding dimension, ticks unchanged, **0.862x score**.
Because score is `max(w,h)^2 * ticks`, that single row beat every tick
optimisation we have done all contest.

## THE structural fact that dictates the algorithm

Our squeeze deletes rows that are **already blank**. On memory, brackets
and matmul it finds **zero**. The human operation is larger: *compact the
content until a row becomes blank, then delete it.*

Now measure what that costs. memory's column occupancy is

    [6, 19, 13, 22, 20, 15, 20, 17, 19, 18, 20, 17, 17, 21, 23, 24,
     22, 19, 25, 25, 17, 24, 13, 12, 20, 15, 16, 17, 7]

**The emptiest interior column still holds six glyphs.** A slide is
score-neutral — the man walks the same cells in the same order, so ticks
and box are unchanged. The reward arrives only when the sixth glyph
leaves and the column can be deleted.

**So the search landscape is flat for six moves and then drops off a
cliff.** Greedy hill-climbing sees zero gradient. Simulated annealing at
any sane temperature sees zero gradient. That is precisely why our tools
found nothing here and a human — who can *plan* six moves — found it
immediately.

This is the argument for **MCTS**: it is a search over *sequences* with
delayed reward, which is exactly the shape of this problem. Any method
with lookahead would do; the one thing that will not work is a
single-move greedy improvement test, and that is what we have been
building.

## Why a genetic algorithm is the wrong tool *at this level*

A GA's power is recombination, and there is no natural crossover on a 2D
grid program: splicing the left half of one room into the right half of
another almost always yields a walk that runs into a wall. Mutation-only
GA is just annealing with extra bookkeeping, and it inherits the flat
landscape.

**A GA does fit one level up**, and that is worth remembering: over
*parameterised generators* (codex's `history_81.py` is one) or over
*library compositions*, where a genome is a list of choices rather than a
grid, crossover is meaningful. Use it there, not here.

## Why Rust, and what already exists

The inner loop needs millions of candidate evaluations. We already have
`rust/` — `littleman-fastsim-rust`, a 1,044-line `engine.rs` built as both
`cdylib` and `rlib` and exposed to Python as `littleman._fastsim_rust`.
cargo 1.75 is on the box. The optimizer should be a new binary in that
crate, reusing the engine rather than reimplementing the semantics.

### The inner loop must NOT replay the whole machine

Today `room_lab.record_all` runs the entire machine per candidate. That is
right for a final check and far too slow for a search.

**Standalone room harness.** The contract already records every value
crossing the room's boundary, per pipe, in order. So the room can be
simulated *alone*: feed the recorded inbound values on each incoming pipe,
run, and compare the outbound sequence. No surrounding machine, no other
rooms, no I/O rooms. That is the single biggest speedup available and it
falls straight out of the contract we already have.

## Fitness, in strict order

Hard constraints (reject, do not penalise):

1. the room still loads and every man's walk terminates as before;
2. **the interface signature is unchanged** — `room_lab.describe()`; which
   socket reaches which pipe, ignoring where it sits. This is the check
   that catches the pathfinder-fold class of failure (`r`/`s` bind to the
   *nearest* pipe by distance, so moving cells silently rewires);
3. **the behavioural contract replays exactly**.

Then optimise, lexicographically:

4. minimise `max(width, height)` of the room — squared in the score;
5. minimise walk length on the hot path — ticks;
6. **reward a width x height not already in the library.** Shape diversity
   is a product, not a side effect: a packer holding both a 6x20 and a
   10x12 of one room can square up a machine when neither is smaller.

## Move set

- **Slide** — swap a non-arrow glyph with an adjacent blank on the same
  straight run of the walk. Behaviour-preserving *by construction* (same
  cells, same order, same tick count), so it needs no replay to validate.
  Implemented in Python already: `room_compact.slides_toward`.
- **Delete an empty row/column** — the payoff move.
- **Reroute a spur** — move a turnaround inward, shortening an
  out-and-back excursion. This is the transformation the user performed by
  hand on memory (12 cells, 3 rows, 2.71% fewer ticks).
- **Reflow** — move a run of the walk to a different row/column and
  reconnect with arrows. The general and dangerous one; gate it behind the
  contract.
- **180-degree rotation** of a sub-block. NOTE: a rotation preserves
  handedness but a MIRROR does not — `X`, `d`, `a`, `x` turn by
  `CLOCKWISE`/`COUNTERCW` and a reflection silently reverses every one of
  them.

## Output

A component library keyed by `(contract digest, interface signature,
width x height)`. Several shapes per behaviour is the deliverable, not one
smallest room. A later packer consumes it — and that is where our CP-SAT
placer finally earns its keep, because it will at last have alternatives
to choose between.

## Build order

1. Standalone room harness in Rust (contract in, outbound sequence out).
2. Slide + delete moves, exhaustive over small rooms, to validate the
   harness against the Python results already in `room_compact`.
3. MCTS over edit sequences, with the flat-then-cliff landscape in mind:
   the tree policy must not prune neutral moves, since every winning line
   begins with several of them.
4. Library store and the diversity term.
5. Packer.

Steps 1-2 are the foundation and are testable on their own. Do not start
at step 3.
