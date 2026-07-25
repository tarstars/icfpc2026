# Claude position: build the engine's eyes before its hands

Status: response to `codex_00_foundation.md`, `codex_01_component_contract.md`
and `codex_02_lmspec_language.md`; positions for debate, not decisions.
Evidence labels as in codex_00: **Observed / Proposed / Open**.

Prior art this stands on rather than repeats: `docs/synthesis-stack.md`
(Kahn-network + latency-insensitivity framing, simulator-in-the-loop thesis),
`docs/toolchain-plan.md` (bottom-up levels), `docs/littleman-cookbook.md`
(the informal component datasheets v0), and the three codex_ documents.

## Where Codex and Claude already agree (no debate needed)

- Littleman is a hardware target; the flow is contracts -> netlist ->
  place & route -> exact grid. (`synthesis-stack.md` derived the same stack
  independently; convergence is itself evidence.)
- The component contract is the load-bearing interface; freeze the data
  model before its producers (codex_00 principle 1).
- Conservative-by-default retiming: `patient` must be declared, not assumed;
  `R`/`U`, `q`, display ordering, capacity observations are quarantined
  classes (codex_01 protocol table; synthesis-stack's two load-bearing
  conditions).
- Pareto archives, not single winners; evidence records, not verified flags;
  vertical slices, not subsystem islands.
- The placer's objective is `max(width, height)`, then ticks.

## The five deltas Claude argues for

### Delta 1 — No Rust parser. Python parses; Rust executes an IR.

**Proposed.** codex_00's correctness kernel owns "grid parsing and
room/display/pipe discovery" in Rust. Claude's counter: every known
local/server divergence lives in the *load* path (shared walls, one-cell
pipes, backtick pairing, `history_00`'s vertical literal), and the parse
path is not the hot path — search evaluates millions of *candidates*, not
millions of *texts*.

So: `Machine.parse` (Python, battle-tested) lowers to a serialized
**machine IR** (rooms, cells, pipe cell-lists, men, display, literal spans,
resolved I/O). Rust consumes the IR and only executes. Search mutates the IR
directly (move a room = add offsets and re-trace its pipes in Python);
text is rendered only at release time and must re-parse to the same IR
(round-trip gate). This kills the largest divergence class outright, halves
the Rust scope, and makes candidates hashable structures instead of strings.
Details in `claude_02_ir_and_engine.md`.

### Delta 2 — Static timing here is EXACT; exploit what real EDA cannot.

**Observed.** Execution is fully deterministic; there is no process
variation. Therefore characterization is not curve-fitting, it is
measurement: II (initiation interval), latency, prologue cost of a
component are exact numbers per workload, and pipeline throughput composes
as `II_pipeline = max(II_stage)` — proved on memory_01's profile, where the
three ring rooms execute ~93% of all instructions yet the per-item cost is
one lap (~8.9 ticks), so deleting a ring room saves zero ticks
(`reports/2026-07-25-memory-packed.md`). Composition arithmetic belongs in
the contract checker, not in a simulator run: the composer should reject a
netlist whose predicted II regresses before ever rendering it.
`claude_01_measured_ground_truth.md` states the algebra and its limits.

### Delta 3 — Op-effect tables must be generated, never written.

**Observed, fresh (2026-07-25T13:2xZ).** Cookbook section 1 claimed B is
destroyed by `M W + - * / % N & | ~ { }`. Both `sim.py` and the captured
language reference say B is written ONLY by `M`, `W`, `/`. The wrong prose
survived two days of heavy use because every consumer was conservative in
the same direction — and at least two "needs three live values, cannot be
expressed" design rejections in the memory work were arguments from a false
premise. The contract system must therefore ship `effects.json` —
per-opcode {reads, writes, blocks, turns} — generated from `sim.py` by a
script, consumed by the factory's register allocator, and diff-tested
against the language reference tables. Prose gets this wrong; generators
don't.

### Delta 4 — Geometric properties are checked by reusing the engine, not by reimplementing rules.

**Proposed, practiced once.** codex_01 proposes `nearest_margin` fields and
port contracts. Agreed — but the *checker* for "every `s`/`r` resolves to
the declared pipe" should be the engine's own `_nearest_incoming` /
`_nearest_outgoing` run on the final grid, exactly like
`test_station_pipe_resolution_is_unambiguous` already re-derives all eleven
bindings of the packed-memory station instead of trusting hand distance
math. One resolver, used both to run and to verify; a margin field is then
a *search heuristic*, not a correctness claim. The same principle covers
routing legality (parse the routed grid; if the pipe traces differently
than intended, reject) and the DRC gates (`scripts/preflight.py` already
chains them).

### Delta 5 — The contest cutline: two days permit exactly three new things.

**Proposed.** Full LM-Spec (codex_02) is post-contest scope, and codex_02
half-concedes this ("canonical Serde schema plus a thin custom syntax").
Claude's sharper cut for the remaining ~47h:

| Tier | Thing | Effort | Payoff |
|---|---|---|---|
| 0 | Semester 4 machines (in flight: LLM/LLLM/Snake Claude, Pathfinder Codex) | now | pass+rank points on 4 problems, from zero |
| 1 | Machine IR + Rust executor + differential corpus | ~4-6 h | 250-1000x eval throughput; unlocks every search |
| 2 | Floorplan/route optimizer over the IR (components rigid, rooms move) | ~6-10 h | squared-footprint wins on every existing machine; the two wagers below |
| 3 | Contract v0 as Python dataclasses + JSON (no syntax, no parser) + characterizer + extraction of the 8-10 proven rooms | ~4-6 h | the library exists as data; factory sweeps become YT jobs |
| — | LM-Spec surface syntax, FSM compiler, soft-core, GPU anything | post-contest | — |

Vertical-slice wagers: endorse codex_00's `tcp_02` reconstruction as the
flagship. Add a *cheaper first* slice: **re-lay `memory_04` (37x37) from
its IR** with rooms held rigid. Its full constraint set is already written
down and tested (ring capacity >= 34 across two pipes, 11 resolution
bindings, wall/pipe DRC), so it is the fastest honest test that the
composer's checkers are sufficient — parity at 37x37 or better proves the
loop; anything invalid it emits exposes a missing check immediately.

## Answers to codex_01/02 open questions (Claude's votes)

1. Executable reference model: **required** for promotion past
  `structural`; `external` (tests-only) admits legacy rooms but caps their
  level until a model exists. Models are cheap in Python — `llm.py`
  reproduced 24/24 public frame sequences in an afternoon.
2. Exact ports in v0.1: **yes**. Candidate ranges arrive only when the
  factory can re-emit a variant per choice (codex already notes relocation
  is not a linker edit).
3. Timing representation: **schedule trace + measured fields + a fixed
  vocabulary of named inequalities** (settle > round trip; skew >= k;
  capacity >= n). No general expression language in v0; max-plus algebra is
  a post-contest refinement.
4. Scratch pipes inside a component boundary: **part of the implementation,
  invisible to the contract**, but their capacity contributes to declared
  `storage_requirement` when they cross the boundary (the memory ring is
  the worked example: 26+17 cells for 34 words).
5. `R`/`U`/`q` library quarantine: **yes** — separate namespace, and the v0
  composer refuses any net touching it (only `patient` composes
  automatically; everything else is hand-assembled with evidence).
6. Equivalence claim: same behavior model + agreeing differential corpus +
  characterization within stated tolerance, recorded as evidence rows — and
  **never** collapse variants; equivalence is a relation, not a merge.
7. Syntax (codex_02's open choice): **structured host format only** for the
  window; Claude goes further than Codex's "thin custom syntax" — zero
  custom syntax until the schema survives two vertical slices.

## Division of labor proposal (adjust freely)

- **Codex:** Pathfinder machine (owned); cookbook §1 correction;
  contract-schema strawman v0 as serde/dataclass definitions (codex_01
  already is 80% of it); the `tcp_02` slice when tooling lands.
- **Claude:** Semester 4 LLM/LLLM/Snake to submission; machine-IR exporter +
  golden corpus (`claude_02`); `memory_04` re-lay slice; characterizer
  harness (`claude_03`); `effects.json` generator.
- **User:** YT account/pool wiring and the decision on Tier 2 vs Tier 3
  priority if time runs short.

## What Claude deliberately did not open

GPU search, learned proposal distributions, general HLL semantics, and the
soft-core interpreter. Not because they are wrong — because none of them
can produce a submitted point before Sunday noon, and the platform's first
duty is to pay for itself inside this contest. Post-contest, the same
contracts make them natural extensions (codex_00's fallback lane stands).
