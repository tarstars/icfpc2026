# Claude: attacking LLM by component decomposition (the user's factory, applied)

Status: Proposed 2026-07-25T14:2xZ, after the user clarified the intent of
the "component factory" bullet. Corrects the scope of `claude_04` §3 and
revises the `claude_00` claim that the LLM machine is out of reach.

## The correction

`claude_04` §3 demoted "a components factory which optimizes components,"
reading it as *free-form superoptimization of room interiors*. The user's
actual intent was different and better: **when a problem is too complex to
write directly, decompose it into components with declared contracts, then
run two parallel streams — compose the big program from the contracts while
separately implementing each component's internals.** That is not the
weakest bullet; it is the composition methodology itself, and it is how the
successful machines were already built informally (memory_04's
P1/HEAD/P2/STATION/RELAY each had a declared token protocol, was audited
separately, and was composed afterwards). The demotion stands only for the
superoptimizer reading; the decomposition reading is adopted as the
primary attack on LLM below.

## Why LLM looked infeasible, and what changed

The earlier judgment ("out of reach this session") assumed a monolithic
hand-build. Three things changed: the LLLM machine (in flight) supplies
the template for program storage, dispatch and drawing; the validated
reference (`llm.py`, 24/24 frame-exact) exists to be *refactored along
component boundaries*, giving every contract an executable spec before any
littleman is written; and the B-survival correction plus the packed-record
idiom shrink the state machinery. Under decomposition the problem becomes
seven bounded components, five of which are LLLM-grade machinery we have
already built once.

## What LLM adds over LLLM (the whole delta)

Up to 3 rooms/men (one per room; collisions impossible — proven);
up to 2 pipes, <= 20 total pipe cells, values -9..9; blocking `s`/`r` with
static nearest-pipe bindings; pipe cells drawn 6/14 by occupancy, animated
cell-by-cell; wall hit freezes everything after a full tick; program over
when all men halt or any wall is hit. Tick order: pipes shift, men execute,
men move.

Two facts keep this small: **every geometric question is static** (rooms,
pipe traces, and every `s`/`r` cell's binding are fixed at load, so they
are setup-time computations, not runtime ones), and **all interaction is
through pipe occupancy** (each pipe has exactly one sending and one
receiving man, so execution order within a tick cannot matter — the
reference proves this by passing 14/14 without modeling simultaneity).

## The netlist (stream A)

Storage rings (packed records, one signed-64 word each unless noted):

- `CELL` ring, 256 records: (char, static color, flags: wall/pipe/interior,
  binding pipe-id for s/r cells).
- `PIPE` table, <= 20 records in source-to-dest order: (grid address,
  occupied flag, value+9).
- `MEN` table, 3 x (packed addr/heading/halted/blocked + A + B as full
  words — 9 circulating tokens).

Components and their contracts (token streams on every edge):

| # | Component | Consumes | Produces | Novelty |
|---|---|---|---|---|
| 1 | LOADER (setup) | `W H c0..` from I | CELL records, W/H to GEOM | LLLM template |
| 2 | GEOM (setup) | CELL ring | wall flags/colors; room rectangles | **new: rectangle trace** |
| 3 | PIPETRACE (setup) | CELL ring + rectangles | PIPE table in flow order; pipe cells recolored 6 | **new: arrow-following** |
| 4 | BIND (setup) | rectangles + PIPE table | binding ids written into CELL records | new but trivial (<= 2 pipes => one Manhattan compare) |
| 5 | INIT-FRAME (setup) | CELL ring + MEN | 256 DATA + men overdraw + SWAP | LLLM template |
| 6 | EXEC (runtime) | k, CELL/PIPE/MEN | mutated state + DELTA queue | LLLM dispatch + pipe transfer arm |
| 7 | DELTA-DRAW (runtime) | DELTA queue | ADDR/DATA pairs + SWAP=1 | LLLM patch driver |

Frame updates are deltas only: vacated cells restore their static color
from CELL, entered cells draw 9, pipe cells flip 6/14 when occupancy
changes — bounded by 3 men + 20 pipe cells per committed frame.

## Budget arithmetic (why correctness-first composition is affordable)

Per interpreted tick: pipe-shift pass ~20x8 ticks + 3 ring scans for
opcode fetch ~3x2.3k ≈ **7.2k machine-ticks**; x100 interpreted ticks/case
≈ 720k; setup scans and frame deltas add noise. Tick cap is 50,000,000 —
a ~70x margin even before optimization, so every component may be written
dumb-and-correct (extra ring passes are free at this scale).

## Stream B: executable contracts before littleman

1. Refactor `llm.py` into `LLMComponents` — the same seven stages with
   explicit queues between them — and require it to stay 24/24 frame-exact
   plus fuzz-clean. The refactor IS the contract validation: if the
   decomposition cannot reproduce the monolith in Python, no amount of
   littleman will save it.
2. Record every boundary's token stream over the public + fuzz corpus.
   Each littleman component's acceptance test is then mechanical:
   **driven with the recorded input stream (engine pipe injection, no
   harness rooms), it must emit the recorded output stream exactly.**
3. Implement components in parallel — one subagent per component, exactly
   the user's two-stream picture — against those traces; composition at
   the end is the already-proven assembly discipline (resolution
   certificates, capacity checks, preflight).

## Risks, named

- **GEOM and PIPETRACE are the novel components** (rectangle tracing and
  arrow-following in littleman). Fallbacks: split into more, dumber passes;
  budget says even a 10x-cost implementation fits. These two are on the
  critical path and get built first after the contracts freeze.
- Character ambiguity is the reason GEOM must be geometric: `+`/`-` are
  ops inside rooms and wall glyphs on borders; `>` is a heading inside and
  a pipe arrowhead outside. Classification is by region, never by char.
- Freeze-boundary frames (the tick a wall is hit completes in full) are
  where the fuzz corpus concentrates; the LLLM fuzz generator extends to
  pipe-bearing programs before any submission (gap already flagged to
  Codex for scope review).

## Sequencing

Starts the moment the LLLM machine lands (components 1, 5, 6-dispatch, 7
descend from it directly). Target: contracts frozen + Python refactor
validated within ~2h of that; parallel component builds after; assembly
and fuzz gate before submission. This slots into the validated plan as the
Sat-morning P0 item, unchanged in the timeline.
