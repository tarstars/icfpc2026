# Codex decision: IR-first tooling, Rust only on measured need

Status: contest-window decision, reconciled with
`claude_00_position.md` and the user-validated
`claude_05_contest_plan.md` on 2026-07-25.

## Decision

The contest toolchain is verification-first and composer-centric:

```text
.man
  -> Python Machine.parse
  -> complete machine IR
  -> Python geometry composer and static checks
  -> Python exact judge on Pareto finalists
  -> render .man
  -> Python reparse/IR equivalence
  -> preflight and submission
```

Rust is conditional. Build a Rust IR executor only if profiling a real
composer workload shows that exact evaluation is the remaining bottleneck.
Do not build a Rust `.man` parser during the contest.

This reverses the earlier proposal in this file, which included `lm-parse`
and treated a full Rust correctness kernel as Stage 1. Parser speed was not
measured as a bottleneck, while the project's costly compatibility failures
have occurred in parsing and load validation. Duplicating that path now
would add risk without demonstrated contest value.

## Reconciliation of Claude's five deltas

### Delta 1: Python parses; Rust may execute a complete IR — endorsed with a gate

`Machine.parse` remains the authoritative structural extractor. The machine
IR must contain every execution-relevant result of parsing; retaining the
source grid is not a substitute for lowering if a downstream executor has no
parser.

The 2026-07-25 adversarial review found three blockers in IR v0:

- `R`/`U` inputs are serialized by pipe index, losing destination-cell
  reading-order priority;
- display pipe records omit ADDR/DATA/SWAP side;
- literal spans and direction-dependent literal values are absent.

Consequently IR v0 is suitable for geometry inspection followed by Python
render/reparse, but not yet for a parser-free executor. The exporter remains
`errata`/gold-candidate until those fields and the priority regression are
covered.

Required release gate:

```text
parse(text) -> IR0
compose(IR0) -> IR1
render(IR1) -> text1
parse(text1) -> IR2
assert execution_semantics(IR1) == execution_semantics(IR2)
```

### Delta 2: exact static timing — endorsed within declared domains

Littleman execution is deterministic, so latency, initiation interval, route
length, and fixed-schedule constraints are exact for a fixed workload and
machine. For components declared `patient`, geometry-only moves can often be
priced by route-length arithmetic and rejected by DRC, capacity, and
resolution checks without simulating every candidate.

This is not a global retiming theorem. `q`, `R`/`U`, display skew, finite
capacity, multi-stream races, wall termination, and round barriers remain
timing-sensitive. Contracts must state the inequalities or require an exact
judge.

### Delta 3: generate opcode effects — endorsed, with provenance

Register effects should come from executable probes and source inspection,
not a hand-maintained prose list. Generated output is **engine-derived**, not
correct by definition; known simulator/server differences still require
reference or live evidence.

The current effect probe correctly supports the conclusion that only `M`,
`W`, and `/` write B, corroborated by the accepted `brackets_00` behavior.
Its direct pipe-array initialization leaves sparse counts inconsistent and
does not test nonzero `q`, so that generator must be repaired before broader
protocol claims are promoted.

### Delta 4: reuse the engine for geometry checks — endorsed

The composer must query the same parser/resolver used by execution for:

- room, pipe, display, and literal discovery;
- actual `s`/`r`/`q` binding;
- `R`/`U` incoming priority;
- routed trace and two-cell pipe legality;
- shared-wall and final-wall compatibility checks.

Declared margins remain useful search heuristics and diagnostics. They do not
replace re-deriving the final binding from the rendered program.

### Delta 5: contest cutline — endorsed

Before submissions close, fund exactly:

1. correct Semester 4 machines and adversarial verification;
2. a Python machine IR and geometry composer;
3. the minimal component contract/characterization data consumed by that
   composer.

Defer custom LM-Spec syntax, a Rust parser, soft-core, free-form component
superoptimization, and GPU work. The user's clarification is important:
contract-first decomposition of a hard machine into independently testable
components is a primary construction method; only blind/free-form room
superoptimization is demoted below global composition.

## Contest-window implementation

### Tier 0: verification and machine IR

- Complete the IR fields above.
- Preserve original coordinates and stable IDs for rooms, men, ports, pipe
  cells, displays, literals, and instruction sites.
- Store resolved binding order explicitly.
- Keep a golden corpus of preserved submissions and targeted semantic
  witnesses.
- Compare final rendered programs through the exact round-controller judge
  and server-compatibility gates.

### Tier 1: Python composer

Operate on rigid component rooms and routed nets. Initial moves:

- translate one room;
- swap compatible room positions;
- select a declared port;
- rip up and reroute one net.

Cheap feasibility checks:

- room/display overlap and forbidden attachment;
- connected pipe trace of at least two cells;
- route capacity and declared delay inequalities;
- engine-derived instruction-to-pipe resolution;
- bounding-square change.

Evaluate exact cases only for the surviving Pareto set. The parity benchmark
is reconstruction of `memory_04` at 37×37 or better with all checks green,
followed by the high-slack live machines named in `claude_05_contest_plan.md`.

### Tier 2: conditional Rust executor

Trigger only after a recorded profile shows exact execution dominates a real
search after static rejection and arithmetic pricing. Timebox the first
implementation. It consumes versioned IR; it does not parse `.man`.

A minimal future workspace is enough:

```text
rust/
  crates/
    lm-ir       # serde schema and validation
    lm-exec     # deterministic tick engine
    lm-diff     # trace comparison with Python
    lm-cli      # batch JSON interface
```

Required parity includes man state, signed-64 registers, pipe occupancy,
display state, output/frame stream, errors, and tick count. Parallelism is
across candidates/cases, never an unproved reorder within one tick.

## Promotion gates

A fast path is usable for search only after:

1. schema validation and stable content hashes;
2. directed tests for wrap, collision, blocking send, `R`/`U` priority,
   display ordering, literals, wall freeze, and round completion;
3. differential traces against Python on every preserved artifact plus a
   generated corpus;
4. an end-to-end benchmark showing material wall-clock benefit;
5. Python exact judge and preflight remaining mandatory before submission.

No speedup or parity claim is accepted without a reproducible command,
versioned workload, and preserved summary.
