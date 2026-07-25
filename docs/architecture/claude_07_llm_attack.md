# Claude: attacking LLM by component decomposition (the user's factory, applied)

Status: **WORKING HYPOTHESES** as of 2026-07-25T14:45Z. The user accepts
the arguments provisionally while recording doubts — in particular around
the DSL sections (restricted subset, branch selectors, position/state
correspondence). Nothing below is a decided method: every section is a
hypothesis to be confirmed or retired by the first stream-B results (the
component refactor and the first transcribed component), and the doubts
stand until then. Originally proposed 2026-07-25T14:2xZ after the user
clarified the "component factory" intent; corrects the scope of
`claude_04` §3 and revises the `claude_00` claim that the LLM machine is
out of reach.

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

## The correspondence table: every .man concept and its DSL reflection

### State

| .man concept | DSL reflection |
|---|---|
| `A` (main hand) | `lm.A` — the accumulator; the only target of data ops |
| `B` (off hand) | `lm.B` — written only via `M()`, `W()`, `div()`; survives everything else (proven, `claude_effects.json`) |
| `BP` (backpack, write-only) | hidden field: settable by `b()`, `m()`, `bp_half()` (`]`), `q` quarantined; readable ONLY through `branch_bp()` / `branch_parity()` — the DSL has no `lm.BP` getter, mirroring the machine |
| signed-64 wrap | every DSL arithmetic call applies `wrap64`; overflow behaves identically in model and machine |

### Data operations (one call = one glyph)

| .man | DSL | Exact semantics carried |
|---|---|---|
| `0`-`9` | `digit(n)` | A = n |
| `` `123` `` | `lit(n)` | A = n; costs len(digits)+2 cells at transcription; walk direction is transcription's problem, not the model's |
| `M` | `M()` | B = A |
| `W` | `W()` | swap |
| `+ - *` | `add() sub() mul()` | wrap64; B untouched |
| `/` | `div()` | A = floor quotient, **B = remainder**; B=0 case: A=0, B keeps dividend |
| `%` | `mod()` | result takes B's sign; B=0 gives 0 |
| `N` | `neg()` | A = -A |
| `& \| ~` | `band() bor() bxor()` | two's complement on 64 bits |
| `{ }` | `shl() shr()` | `{`: 0 if B outside 0..63; `}`: arithmetic, 0 if B<0, sign-fill if B>63 |

### Control flow

| .man | DSL | Notes |
|---|---|---|
| `X` | `branch_sign()` | native three-way; arms per the branch rules above |
| `d` / `a` | `branch_bp()`, and loop constructs own their exit `d` | BP>0 test |
| `x` | `branch_parity()` | always turns; raw low bit (negative BP is not zero) |
| `H` | `halt()` | terminates the component's transaction stream |
| racetrack main loop | `forever():` block | transcribes to the verified racetrack pattern |
| relay loop (`>rsv`/`^md`) | `relay(bp_plus_1=True)` macro | expands to primitive calls; relays BP+1, exits with last value in A |
| sentinel loop | `until_negative():` macro | recv + `branch_sign` composed; the sentinel idiom |
| prologue (seeds off-loop) | `prologue():` block | executes once; transcription must keep it off the lap (the brackets bug, encoded as a rule); feeds the `prologue_ticks` metric |
| `.` and space | absent | padding is layout, not semantics |

### Pipes and I/O

| .man | DSL | Notes |
|---|---|---|
| `s` | `send(port)` | blocking; port is a NAME — geometry comes later |
| `r` | `recv(port)` | blocking; destructive; no peeking exists |
| pipe itself | named port + net in the contract | capacity/latency are net properties, declared not modeled |
| nearest-pipe resolution | **absent by design** | handled at transcription by the resolution map diff (engine-true); the model cannot express a mis-binding |
| I/O rooms | ports named at the netlist level | the DSL sees only ports |
| display ADDR/DATA/SWAP | typed sends on three ports | the ADDR->DATA->SWAP same-tick order and skew constraints live in the contract's timing class, checked at composition |
| `S`, `R`, `U`, `q` | **quarantined — not in the v0 DSL** | timing-/occupancy-sensitive (`arrival_ordered`, `occupancy_observing`); components needing them are hand-assembled with explicit evidence, per the protocol classes |

### Deliberately absent (the layer split is the point)

| .man concept | Where it is handled instead |
|---|---|
| 2D grid, room rectangles, footprint | transcription + composer (layout is an output, not an input) |
| arrows `> < ^ v` | the transcription of control structure; never written by hand in the model |
| man position/movement/ticks | implicit: one call ≈ one glyph ≈ one tick on the walked path; cost estimate = call count + routing overhead |
| literal walk direction, vertical backtick pairing | transcription rules + parse gate |
| shared-cell tricks | transcription-only optimization; the DSL may not rely on it |
| walls, `wall`/`bad-op`/`no-pipe` errors | unreachable arms transcribe to unrouted corridors (shared assertion); the rest are made unwritable by construction |
| multi-room machines, men interaction | the netlist layer: one DSL program per room, composition by contracts |
| server-vs-local divergences | load gates (`preflight`), not the model |

Reading the table backwards is the design argument: everything with
geometric meaning is absent from the DSL and owned by a checked layer
below; everything with semantic meaning is present with machine-exact
behavior. The model can therefore be wrong only in ways the trace tests
catch, and the transcription can be wrong only in ways the gates catch.

## Position as program counter: the correspondence, and why `goto` becomes `state`

The machine's program counter IS the man's (cell, heading) pair — control
flow is movement. The DSL's program counter is its position in the call
sequence. The correspondence:

- Each semantic DSL call transcribes to one glyph cell; the interpreter
  "standing at a call" corresponds to the man standing on that glyph.
  Geometry adds semantically-empty cells between them (spaces, arrows,
  merge cells) — the walked path visits them, the model does not, and
  that is fine because they are no-ops by definition.
- The precise CFG node is **(cell, heading)**, not cell: one physical cell
  crossed by two paths in different headings is two nodes. Shared-cell
  layout may map two call sites onto one side-effect-compatible cell — a
  transcription compression that leaves model semantics untouched.
- The operational check of the correspondence is trace equality: same
  port-consumption and emission order = same walk, up to no-op cells.

**Is the machine goto-shaped? Yes.** Arrows are unconditional jumps,
`X`/`d`/`x` conditional ones; the native CFG is arbitrary, including
irreducible flow. The structured DSL covers a subset. So the user's
instinct is right that something goto-like is needed — but raw `goto X`
is the wrong construct:

- validation collapses: with goto, every label needs a full dataflow
  analysis; the join-invariant discipline that makes arms checkable
  locally is exactly what goto dissolves;
- transcription collapses: structured constructs map to a small pattern
  library; arbitrary jump graphs turn single-room layout into a general
  graph-drawing problem;
- and empirically the winners are structurally simple: every shipped room
  is straight lines, a few loops, one or two branches — the shipped
  cleverness lives in encodings and in layout, not in control flow.

**The right construct is `state` — goto with obligations.** A component
body may be declared as an explicit FSM: named states, each with a
straight-line (or lightly branched) DSL body, each with a **mandatory
entry invariant** (what A/B/BP mean, what is in flight on each port), and
explicit transitions naming which test moves where. That recovers the
machine's full flow (including irreducible graphs) while keeping checking
local: a transition is valid iff the source's exit state satisfies the
target's invariant — dataflow reduced to per-edge assertions.

This is not invented here twice over: codex_02's implementation-language
sketch is exactly this (`state idle: ... goto idle` with `assert at
loop_head` blocks), and the Grade Book machine proved rooms-generated-
from-FSMs at scale before any of this vocabulary existed (its FSM-room
compiler produced the machine that a later geometry pass improved 15.97%).

The construct also captures the machine's position-as-information idioms
honestly: Snake's "the man's corridor IS the flag" — one bit stored in
*which corridor the man walks*, costing zero registers — is, in DSL
terms, simply two states with different continuations. Position-as-state
= FSM state; the trick stops being folklore and becomes a declared state
with an invariant.

Boundary honestly stated: the DSL (with `state`) is for authoring new
components. Existing hand-written rooms are not decompiled into it; they
enter the library as `external` implementations (grid + evidence), per
codex_01's escape hatch.
