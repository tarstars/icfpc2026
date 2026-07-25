# Claude: the block-graph notation (user's design, formalized)

The user's proposal: write programs as labelled straight-line blocks with
explicit transitions, test them by INTERPRETATION (no geometry), and
optimize layout separately.

```
(mark K) @ 1 (if A B C)
(mark A) W 2 - (goto K)
(mark B) W 3 / (goto K)
(mark C) W 4 * (goto K)
```

This is basic blocks + a control-flow graph. Three independent
derivations now agree on it: `toolchain-plan.md` Level 1 ("block graph ->
room"), codex_02's `state`/`goto` implementation language, and this.

## The theorem that makes it safe: any well-formed block graph is implementable

The user asks for "a special instrument to check we can somehow implement
it". The strong answer: **the check is local, because a universal layout
always exists.**

Key fact, from cookbook §6: two corridors of the SAME man may cross at a
cell that is harmless to both traversals — and a SPACE is harmless to
every traversal in every direction. There is one man per room, so no
simultaneity exists. **Therefore corridors may cross freely at spaces:
littleman routing is NOT planarity-constrained** (unlike PCB/EDA routing,
which is the analogy that would have scared us off).

Constructive universal layout (the always-works fallback):

1. lay each block as one horizontal run in its own row band, in any order;
2. reserve a routing channel of empty columns to one side;
3. route every edge as: leave the block, go to the channel, travel
   vertically, re-enter the target's row. Crossings land on spaces.

Area is O(B x (W + E)) for B blocks, W widest block, E edges — crude, but
it always succeeds. So **feasibility is never the question; only cost
is.** The optimizer's job is to beat the fallback, not to find a solution.

## What the checker must verify (all local, all cheap)

1. every `goto`/`if` target exists; every mark defined once;
2. every block ends in a terminator (`goto`, `if*`, `H`) — no silent
   fallthrough;
3. **join invariants**: a mark reachable from several predecessors must
   agree on what A/B/BP mean. Optional annotation
   `(mark K :A dead :B mask)`, checked by the interpreter across all
   traces. This is the failure that bit `claude_11b` (interpreted
   arithmetic clobbering host B);
4. literals well-formed; no quarantined ops (`R`/`U`/`q`) unless declared;
5. branch arity matches the op: `if` = 3 targets (X: neg/zero/pos),
   `if-bp` = 2 (d/a: taken/straight), `if-par` = 2 (x: odd/even).

## Branch mapping (physically determined, worth pinning)

`(if NEG ZERO POS)` compiles to `X`, whose three outcomes leave the cell
in three FIXED relative directions (heading east: A>0 turns down, A<0
turns up, A=0 continues). The compiler chooses placement to reach each
target from its physically determined exit; the author never thinks about
it. Same for `d`/`a` (taken = a turn, straight = fallthrough) and `x`.

## Where this plugs into existing work

- It is exactly the input format `claude_12`'s room assembler wants; the
  `Lane` builder API is the Python-embedded form of this text syntax.
  Same IR, two surfaces.
- Existing Python models (`StepModel`, `CycleModel`, the LOADER
  reference) become *compilable* instead of hand-transcribed.
- The DSL discussion (`claude_07`) argued for A/B/BP discipline and three
  branch selectors; this supplies the missing surface notation and,
  crucially, the `goto`/`mark` layer that makes irreducible control flow
  expressible without hand-drawn corridors.

## Deliverable

`src/littleman/blockgraph.py`: parse, structural-check, and INTERPRET
block graphs (A/B/BP + pipe callbacks, `sim.wrap64` semantics) so an
algorithm can be written and tested with zero geometry — then handed to
the assembler for layout.
