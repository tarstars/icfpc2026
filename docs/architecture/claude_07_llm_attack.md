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

## How Python stays implementable in .man (the restricted subset)

"Prototype in Python, implement in .man" fails if the prototype uses
Python's freedoms — unlimited locals, random access, call stacks. So the
method uses **two Python layers with different obligations**:

1. **Contract layer** (the seven components with queues): only boundaries
   must be faithful — token streams, blocking recv/send, no peeking.
   Internals are arbitrary Python; their job is to pin *what*, not *how*.
2. **Implementation model** per component: written in a restricted subset
   that maps one-to-one onto machine capability. This is the layer that
   answers "can this be built."

The restricted subset is the machine's own discipline, enforced in Python:

| Rule | Machine reality it mirrors |
|---|---|
| State is exactly `A`, `B`, and a write-only counter `bp` | the register file; B written only by `M`/`W`/`/` (proven, `claude_effects.json`) |
| No other named values — bulk state lives in FIFO rings, consume-and-reappend | pipes are the only memory; random access = full rotation + index compare |
| Branches only on `sign(A)`, `bp > 0`, `bp & 1` | `X`, `d`/`a`, `x` are the only tests |
| Loops only as counted `bp` countdowns or sentinel-terminated streams | the two loop idioms we have |
| One arithmetic step = one machine op, with its quirks (`/` yields quot+rem, `%` takes B's sign, shifts clamp) | the opcode table |
| Ports: blocking `recv`/`send` in program order, nothing else | `r`/`s`; `q`/`R`/`U` quarantined |

Concretely this is a ~15-line embedded DSL: a class whose methods are the
opcodes (`.M() .W() .add() .div() .recv(port) .send(port) .b() .m()
.branch_sign()`), holding `A`/`B` as its only data. You *cannot* hold a
third live value, because there is nothing to bind it to — the
impossibility is structural, not reviewed. A model written this way is a
glyph sequence by construction: transcription to a room is one glyph per
call, and the remaining work is purely geometric (layout, turns, literal
placement).

This is not speculative — it is how `memory_04` was actually built. The
write-formula candidates were eliminated *in the model* because they
needed three live values; the surviving mask/or form fits A+B; the HEAD
row `>@Mrsr-M`34`W%s…` reads as a 1:1 transcript of its model calls. The
funnel caught infeasibility before any ASCII existed.

Checks that catch "unimplementable" early, in order of bite:

1. **Register pressure**: at every model step, live values ⊆ {A, B, bp}.
   The DSL makes violations impossible to write; for hand-written models,
   `toolchain-plan` Level 3 (symbolic tracker, fed by `claude_effects.json`)
   automates the audit.
2. **Branch shape**: every conditional reduced to sign/parity on permitted
   registers (comparisons become subtraction + sign — legal precisely
   because B survives `-`).
3. **Queue discipline**: every ring pass consumes and re-appends a fixed
   count (cookbook §5's canonical-order rule), checked by counting.

What the subset deliberately does not model: geometry. Layout cost, pipe
bindings, literal walk-direction, shared-cell tricks all appear only at
transcription, and are guarded there by the existing assembly gates
(resolution map, DRC, preflight) plus the boundary-trace equality test.
A model can therefore be implementable but *expensive* — the budget
arithmetic above is what makes that acceptable for LLM (70x margin).

Under contest-first, transcription stays manual (proven fast: the memory
station took hours) and `toolchain-plan` Level 1 (block-graph -> room
assembler) stays post-contest. The subset is what makes manual
transcription mechanical enough to be boring — which is the point.

## Branching in the DSL: three selectors, no general `if`

The machine has exactly three tests, so the DSL has exactly three branch
constructs and refuses to invent a fourth:

| Construct | Machine op | Arms |
|---|---|---|
| `branch_sign()` | `X` on sign(A) | negative / zero / positive (three-way) |
| `branch_bp()` | `d` / `a` on BP > 0 | taken / straight |
| `branch_parity()` | `x` on BP low bit | odd / even (always turns) |

There is deliberately **no `if_(a < b)`**: a comparison must be
materialized the way the machine does it — `sub()` then `branch_sign()` —
so its true cost is visible in the model. If an arm still needs the value
the comparison destroyed, the model is forced to duplicate it upstream or
re-derive it, which is precisely the register-pressure decision that kills
or shapes designs (`memory_04`'s write formula was chosen this way).

Rules that keep arms honest:

1. **Arms re-converge or terminate.** An arm ends in a join, an `H`, a
   park-on-`r`, or `unreachable(reason)` — the last transcribes to an
   *unrouted corridor*, so violating the stated invariant crashes into a
   wall: the model's assertion and the machine's are the same assertion.
2. **Join invariants are declared.** Every join states what A/B/BP mean on
   arrival (`join(A="dead", B="mask")`); both arms are checked against it
   dynamically on every trace (statically later, via the Level-3 tracker).
3. **Arm coverage is measured.** The DSL counts arm hits per branch across
   the trace corpus: every routed arm must be exercised, and an
   `unreachable` arm hit even once fails the model before any ASCII
   exists.

Worked example — the packed-memory P2 dispatch (tag parked in BP so one
`d` branches an otherwise straight-line room):

```python
lm.recv("in"); lm.send("out")            # tag through
lm.b()                                    # BP := tag (0=READ, 1=WRITE)
lm.recv("in"); lm.send("out")            # k through
with lm.branch_bp() as (write_arm, read_arm):
    with read_arm:                        # BP == 0: straight on
        lm.recv("in"); lm.M(); lm.lit(43); lm.sub(); lm.send("out")
        lm.recv("in"); lm.recv("in")      # drop x and trailing shift
    with write_arm:                       # BP > 0: turned
        ...
# transcribes to memory_04's actual P2 header row: >@rsbrsd ...
```

Geometry mapping is a small pattern library, one per construct: the
X-fork with the cookbook's standard merge, the X with an unrouted
assertion arm, the `d`-at-corner conditional turn (loops own their `d`
via the loop constructs), and the `x` parity fork. Nesting is legal but
each fork pays a corridor and a merge, so idiomatic code flattens into
dispatch ladders — and the strongest idiom is **branch elimination by
encoding**: memory's `-(k+1)` involution let one instruction path serve
both READ and WRITE because the *data* carried the case. In the DSL that
is just straight-line code over sign-encoded values, which is why the
encoding layer, not the branch layer, is where the best designs win.

Honest note: as an interpreter the DSL executes only the taken arm per
run; whole-branch confidence comes from corpus coverage (rule 3) plus the
join checks, with the symbolic tracker as the later static upgrade.
