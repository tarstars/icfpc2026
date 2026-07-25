# Codex original proposal: investigation roadmap and debate agenda

Status: long-horizon roadmap. The contest-window order is now the
user-validated `claude_05_contest_plan.md`, reconciled from the Codex side in
`codex_03_rust_toolchain.md` and `codex_06_yt_search.md`. In particular,
Semester 4 verification and a Python geometry composer precede any Rust
executor; a Rust parser, custom LM-Spec syntax, free-form superoptimization,
and GPU work are deferred.

## Strategy

Build the platform through vertical slices that each reproduce or improve a
known machine. Do not start the HLL, Rust simulator, global router, component
factory, and YT launcher as independent projects.

The central sequence is:

```text
contract
  -> one imported component
  -> one reconstructed netlist
  -> one exact Rust evaluation path
  -> one local optimization
  -> one distributed search
  -> broader language and library
```

Each milestone has a decision gate. A partial tool that cannot reproduce a
known artifact does not unlock the next stage.

## Stage 0: freeze the experimental contract

Deliver:

- canonical schemas for component, implementation, port, net, placement,
  route, characterization, evidence, and workload;
- content-hash rules;
- versioned JSON/RON examples for one relay and recovered TCP;
- promotion levels from structural to release;
- one neutral decision record after Codex/Claude review.

Gate:

- the schema can represent `tcp_02`, its capacity/phase constraints, and the
  43×38 versus 38×38 lineage without storing unexplained free-form prose;
- it can also represent one display driver with an explicit skew constraint.

This stage should settle data semantics, not surface syntax.

## Stage 1: Rust correctness and static-analysis kernel

Deliver:

- Cargo workspace and canonical data types;
- `.man` parser with language-reference and observed-server policies;
- exact simulator for a bounded but representative feature set;
- intent-resolution and structural checks;
- Python/Rust differential harness and mismatch minimizer;
- stable JSON CLI.

Gate:

- every preserved small fixture matches Python state-by-state;
- all preserved `.man` files parse or fail with the expected classification;
- public output/frame/tick results match for a representative set including
  pipes, displays, literals, collisions, and signed-64 boundaries;
- benchmarks show enough speedup to justify using Rust for bulk evaluation.

Do not optimize the simulator before the exact engine is trustworthy.

## Stage 2: imported component library

Deliver:

- automatic extraction of rooms and pipes from structural generators;
- exact port declarations and intent checks;
- generated component harnesses;
- first catalog families: relay, stream transform, tag codec, FIFO/ring,
  display drivers;
- exact byte-for-byte reconstruction tests.

Gate:

- recovered TCP is represented as named component instances and nets;
- the representation regenerates one preserved artifact exactly;
- changing allowed pipe lengths preserves behavior across a timing-perturbation
  harness where the contracts claim patience.

## Stage 3: geometry-only netlist compactor

Deliver:

- placement legality and routed-cell index;
- deterministic router;
- component translation and route rip-up/rebuild moves;
- bounding-square objective;
- exact parse/judge promotion;
- experiment manifests and Pareto archive.

Gate:

- starting from the known 43×38 TCP room programs, the tool finds a valid
  38-square or better layout, or produces a precise report identifying which
  modeling/search restriction prevents rediscovering the known result;
- it rejects an under-capacity and an under-delayed route;
- it preserves exact room code and passes the boundary suite.

This is the first tool expected to improve real solutions.

## Stage 4: component-body factory

Deliver:

- FSM/lane IR;
- symbolic register and scratch-FIFO tracking;
- state/track layout variants;
- small instruction superoptimizer;
- component Pareto archive;
- factory feedback requests from network synthesis.

Gate:

- reproduce Grade Book's accepted FSM worker;
- generate a strictly smaller or differently shaped equivalent variant;
- show the network placer selecting different worker shapes for different
  global envelopes;
- preserve behavior under generated harness and full-machine tests.

## Stage 5: YT scale-out

Deliver:

- immutable Rust worker package;
- local/YT parity smoke test;
- consolidated task/result/frontier tables;
- deterministic independent search chains;
- local revalidation and run manifest.

Gate:

- a 1,000-seed TCP or Grade Book layout search completes with traceable row
  counts and no duplicate evaluation under identical cache keys;
- the reduced frontier revalidates locally from exact manifests;
- at least one useful counterexample or improved candidate demonstrates that
  distribution added value beyond launcher overhead.

## Stage 6: native LM-Spec implementation authoring

Deliver:

- typed protocols and process bodies;
- lowering to FSM/component IR;
- source maps and architecture-level diagnostics;
- raw-grid import escape hatch;
- standard component library.

Gate:

- implement a nontrivial existing stream component without raw room text;
- generated component behavior matches its model across timing perturbations;
- integrate it into an existing netlist and reproduce full-machine behavior.

## Stage 7: soft-core and higher-level synthesis

Investigate both:

- a general bytecode soft-core for fast correctness baselines;
- specialized dataflow synthesis for scoring.

Gate for soft-core:

- one generic machine executes two different bytecode programs;
- program changes do not require geometry changes;
- footprint/tick cost is characterized honestly.

Gate for specialized synthesis:

- one problem-level process description lowers to a network of library and
  generated components with no hand-authored `.man`.

## Benchmark suite

Use several machines because no single benchmark exercises the full stack:

| Benchmark | What it tests |
| --- | --- |
| Triangle | Tiny exact semantics, multi-man timing, display/output edge behavior. |
| Reverse | Ring capacity, `q` settling, corridor timing, geometry compaction. |
| Sort | Repeated stages, in-band count tokens, round reset. |
| TCP | Protocol tags, phase debt, capacity, feedback, measured architecture/geometry lineage. |
| Grade Book | FSM generation, repeated workers, broadcast/ack, large square balancing. |
| Plotter | Stream pipeline, display skew, arithmetic state, long routes. |
| Memory | Packed representations, random access protocol, ring-dominated cost. |
| Subset Sum | Very large generated programs and scalability limits. |

Every tool benchmark reports wall time, evaluations per second, memory,
candidate validity rate, exact best metrics, and reproducibility hash.

## Immediate concrete next actions

1. Review these Codex notes alongside independent `claude_*.md` proposals.
2. Create a neutral vocabulary/ADR for component, implementation, instance,
   port, protocol, characterization, and evidence.
3. Write canonical schema examples for a relay and TCP; do not build a parser
   first.
4. Define the Python/Rust differential trace schema.
5. Create a minimal Cargo workspace with `lm-core`, `lm-parse`, and `lm-cli`.
6. Reproduce parser behavior on the known server-difference fixtures.
7. Import TCP's structural generator and express exact ports/nets.
8. Build the smallest geometry-only move/evaluate loop.
9. Probe YT access only when a local deterministic search workload exists.

## Questions for the second high-level model

### Model of computation

1. Is a deterministic bounded Kahn-style process network the right default, or
   is another formal model better for full pipes, `q`, display scheduling, and
   round barriers?
2. Which subset admits a useful proof that pipe retiming preserves behavior?
3. Should timing-sensitive components be first-class in the same language or
   isolated behind explicit adapters?

### Component boundary

4. What is the minimal component contract that still prevents wrong-pipe,
   under-capacity, phase, and display-skew bugs?
5. Should version 0.1 require exact port offsets, or support relocatable port
   ranges immediately?
6. Can scratch storage pipes remain internal to a component without making its
   bounding shape too rigid?
7. What equivalence evidence is realistic for component variants: symbolic
   execution, bounded model checking, exhaustive domain checks, differential
   fuzzing, or a layered mixture?

### Language

8. Should the initial authoring format be a custom DSL, RON/JSON schema,
   embedded Rust, or embedded Python?
9. Where should explicit A/B/BP allocation enter the language?
10. How should token encodings and representation alternatives be expressed
    without turning the type system into a theorem prover?
11. Is a process DSL the right top-level language, or should we begin with a
    soft-core ISA and add synthesis later?

### Physical synthesis

12. Which routing/floorplanning formulation gives the best first vertical
    slice: channel routing, simulated annealing, CP-SAT, SAT/SMT, or a hybrid?
13. How should the optimizer represent crossovers/relay rooms when the logical
    netlist is non-planar?
14. What static timing abstraction is useful enough to reject bad candidates
    without pretending to replace simulation?
15. Can we derive safe incremental simulation after a local geometry move?

### Search and YT

16. Which search spaces are best sharded independently on YT?
17. What candidate representation minimizes worker startup and transfer cost?
18. When would GPU ranking outperform CPU heuristic search given the likely
    corpus size?
19. How should Pareto frontiers from many stochastic chains be merged without
    overfitting public workloads?

### Project strategy

20. Is TCP the best first vertical slice, or would Grade Book expose the
    component language sooner?
21. What is the smallest platform increment likely to improve a contest
    candidate before the full architecture exists?
22. Which features should be explicitly postponed to prevent the project from
    becoming a multi-week compiler rewrite before producing value?

## How to resolve disagreement

For each disputed design choice, record:

- competing proposals;
- expected benefit;
- smallest discriminating experiment;
- required artifact and metric;
- decision date and evidence.

Do not merge positions by prose compromise alone. Use experiments where the
choice affects correctness, performance, or implementation effort.
