# Codex proposal: the component factory

Status: long-horizon proposal. Contract-first decomposition and bounded
parameter sweeps remain contest tools; free-form room superoptimization is
deferred below the geometry composer.

## Purpose

The component factory turns one behavioral contract into a measured family of
physical implementations. It is both:

- a compiler from process/FSM descriptions to rooms; and
- a local optimizer over implementation choices.

It does not choose global placement. It exposes enough variants and
characterization for the network synthesizer to make that choice.

## Factory inputs and outputs

Inputs:

- component contract and executable behavior model;
- implementation template or imported legacy room;
- bounded parameter domains;
- legal transformation set;
- directed, exhaustive, and randomized workloads;
- hard geometry, timing, and capacity constraints;
- optimization budget and seed.

Outputs:

- canonical implementations;
- Pareto frontier and dominated archive;
- static and dynamic characterization;
- proof/test evidence;
- counterexamples for rejected transformations;
- source maps from room cells to implementation states.

One factory run is immutable and content-addressed.

## Optimization dimensions

### Instruction and expression synthesis

- equivalent arithmetic/bitwise instruction sequences;
- alternate comparisons and sign encodings;
- in-band control tags;
- literal choice and traversal direction;
- constant folding and strength reduction;
- keeping durable state in B versus a pipe;
- BP counters versus `q` and settling corridors;
- phase-debt tracking versus full realignment.

Small straight-line regions are suitable for enumerative
superoptimization. The search domain is signed-64 semantics plus declared
register liveness, not ordinary mathematical integers.

### Register and scratch allocation

- allocate live values to A, B, BP, or scratch FIFO;
- exploit instructions that preserve B;
- choose canonical scratch queue order;
- spill and reload through a pipe-backed register file;
- duplicate cheap values to reduce rotations;
- split a process when register pressure makes one room expensive.

The allocator should use an explicit interference/liveness model derived from
the verified register-survival rules.

### State-machine transformations

- state ordering and lane ordering;
- branch inversion;
- state merging and code sharing;
- loop rotation;
- prologue separation;
- unrolling hot loops;
- specialization by bounded parameters;
- partitioning one process into patient stream stages;
- fusing adjacent stages when routing dominates.

Each transformation declares whether it preserves only behavior or also token
schedule/timing class.

### Local physical synthesis

- control-flow track allocation;
- room width/height tradeoffs;
- entry heading;
- exact port wall and offset;
- port relocation candidates;
- legal rotations/reflections;
- literal placement;
- shared harmless cells;
- reserved routing channels and forbidden halos.

The output is a set of rigid implementation variants. Global placement should
not rewrite a room without re-entering the factory.

### Representation and packing

- token encodings and tag domains;
- number of logical values per signed-64 word;
- field widths and overflow bounds;
- structure-of-arrays versus array-of-structures streams;
- counted versus sentinel framing;
- queue length and ring shape.

Packing changes the protocol implementation and often the component boundary.
It requires round-trip and boundary proofs, not just simulation.

## Search hierarchy

Use the cheapest sound method at each level:

1. **Algebraic rewrites:** canonical simplification and known idioms.
2. **Exact enumeration:** small instruction sequences, constants, local lane
   orders, and port choices.
3. **Constraint solving:** register allocation, bounded lane placement, track
   coloring, packing bounds, and small routing subproblems.
4. **Heuristic local search:** room layout, state ordering, and mixed
   transformations.
5. **Evolutionary or beam search:** larger component architecture families.
6. **Simulator-guided promotion:** exact dynamic validation for the frontier.

Search should be hierarchical rather than one enormous mutation space.

## Equivalence and timing classes

Transformations need explicit promises:

| Class | Required preservation |
| --- | --- |
| `stream_equivalent` | Same output tokens for every valid input, allowing different latency. |
| `schedule_equivalent` | Same token order and component transaction boundaries. |
| `cycle_equivalent` | Same externally visible event tick sequence for fixed routed pipe latencies. |
| `geometry_only` | Same room instructions and component protocol; only port/layout geometry changes. |

The existing variant catalog's `algorithm`, `component`, and `geometry-only`
distinction should become a first-class lineage edge.

For latency-sensitive networks, `stream_equivalent` is insufficient. The
network synthesizer must request a stronger class or revalidate the full
network.

## Pareto archive

The factory stores all non-dominated implementations under configurable
objectives. It should also retain selected dominated variants when they have a
qualitatively different port signature or stronger evidence.

Example frontier key:

```text
(width,
 height,
 max_dimension,
 first_output_latency,
 last_output_latency_profile,
 initiation_interval,
 external_capacity_required,
 port_signature,
 timing_class,
 evidence_level)
```

The archive must record why a variant was removed:

- exact duplicate;
- dominated under the same contract and port signature;
- failed parse;
- wrong intent;
- behavioral mismatch;
- capacity/timing failure;
- exceeded tick or source-size cap.

## Factory loop

```text
contract + template
  -> enumerate/propose transformation
  -> compile room
  -> static legality checks
  -> symbolic protocol/register checks
  -> component harness simulation
  -> characterize timing/capacity
  -> update Pareto archive
  -> schedule deeper tests for promising variants
```

Static failures should be very cheap. Full adversarial simulation belongs only
after a candidate survives structural and symbolic gates.

## Component harnesses

Every component needs an automatically generated harness:

- legal I/O rooms and pipes;
- configurable pipe lengths and capacities;
- deterministic input schedule;
- output capture;
- optional backpressure;
- timing perturbations within contract bounds;
- trace comparison to the behavior model.

The harness should deliberately vary pipe lengths. This tests whether a
component's claimed latency-insensitivity is real.

For timing-sensitive components, generate boundary cases:

- minimum and maximum allowed route lengths;
- pipe full/empty transitions;
- worst skew;
- exact settling inequality boundary;
- maximum burst and parked occupancy.

## Initial factory benchmarks

### Relay and stream transform

Goal: establish the harness, exact equivalence, port relocation, and Pareto
archive on tiny components.

### Reverse/Sort ring pump

Goal: reproduce known corridor, capacity, and phase rules; compare `q`-based
and in-band-count implementations.

### TCP pump and forwarder

Goal: separate protocol-level optimization from geometry, preserve tag and
window invariants, and characterize feedback latency.

### Grade Book FSM worker

Goal: stress state ordering, track coloring, right padding, and repeated
instances. The existing baseline and compact implementations provide exact
targets.

### Display pixel driver

Goal: represent and test ADDR/DATA skew as an explicit timing contract.

## Library organization

Proposed catalog hierarchy:

```text
components/
  protocols/
  primitives/
  stream/
  storage/
  arithmetic/
  control/
  display/
  codecs/
  problem_specific/
  imported/
```

Generic status is earned. A component begins under `imported/` or
`problem_specific/`; it moves into a generic family only after its behavior,
parameters, and environment assumptions are explicit.

## Cost-model feedback

The network synthesizer should be able to request new variants:

```text
request:
  contract = grade_worker/v2
  prefer max_height <= 80
  require output_port.wall in [south, east]
  permit initiation_interval <= 1.10 * current
  reason = "global width is binding"
```

This closes the synthesis loop:

```text
network placement report
  -> component-shape/timing request
  -> factory search
  -> new frontier
  -> re-place network
```

Without this feedback, a locally optimal component can make the whole machine
unroutable or enlarge its bounding square.

## What the factory should not do

- Declare equivalence from public cases alone.
- Optimize a component against one fixed global placement.
- Hide port changes behind the same implementation ID.
- Treat estimated ticks as measured timing.
- Discard slower or differently shaped frontier variants.
- mutate immutable submitted artifacts.
- Search unbounded parameter spaces without a deterministic budget.
