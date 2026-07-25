# Codex proposal: synthesizing large programs from components

## Goal

Given a typed logical netlist and component implementation frontiers, produce
a legal, reproducible `.man` whose exact score and validation evidence are
known.

This is joint **implementation selection, floorplanning, routing, retiming,
and validation**. Calling it a linker understates the problem.

## Inputs

- logical component instances and typed nets;
- implementation frontier for each instance;
- physical port candidates;
- capacity and timing constraints;
- legal component transforms;
- I/O and display constraints;
- workload profile and hard tick cap;
- optimization objectives;
- optional human placement hints.

## Outputs

- selected implementation per instance;
- absolute placement and orientation;
- selected physical port per logical port;
- routed pipe cells;
- inserted relays, barriers, or crossing components;
- exact `.man` and structural manifest;
- predicted and exact metrics;
- validation evidence and lineage.

## Objective

For footprint-tick problems:

```text
score = max(width, height)^2 * average_ticks
```

The optimizer must preserve the factors separately. A useful internal
objective is multi-stage:

1. reject invalid or failing candidates;
2. respect source-size and tick caps;
3. minimize predicted score;
4. retain near-optimal alternatives with smaller maximum dimension, stronger
   timing margin, or stronger evidence.

Rectangular area remains useful for overlap and density, but it is not the
contest footprint.

## Synthesis stages

### 1. Graph analysis

Compute:

- strongly connected components and feedback cycles;
- high-fanout/fanin points requiring explicit split/merge components;
- planarity pressure and likely crossings;
- storage/capacity-critical nets;
- latency-sensitive nets and skew groups;
- repeated isomorphic subgraphs;
- component shapes that dominate likely bounding dimensions.

This analysis guides initial placement and component-frontier pruning.

### 2. Implementation selection

Do not select each component independently. Candidate choice depends on:

- port walls and offsets;
- width/height aspect;
- timing and burst behavior;
- route capacity demand;
- whether a feedback cycle becomes critical;
- how repeated instances pack.

Use a small beam or constraint model to carry several implementation
combinations into placement.

### 3. Floorplanning

Provide three modes:

1. **Row/channel baseline:** common component heights, left-to-right flow, and
   dedicated routing channels. Reliable and fast.
2. **Hierarchical floorplan:** place strongly connected or protocol-coupled
   groups as macros, then place macros globally.
3. **Free 2D compaction:** annealing or large-neighborhood search over
   coordinates, orientations, component variants, and grouping.

Initial placement should target a square envelope, not merely short wires.

### 4. Port assignment

Choose physical candidates jointly with placement. The assignment solver must
consider:

- instruction-to-port selection margins;
- number of pipes per wall;
- route direction and bend feasibility;
- display-side restrictions;
- pipe capacity and latency;
- congestion and crossing pressure.

Port assignment may request a new component variant from the factory.

### 5. Routing

Use a deterministic legal router first:

- grid occupancy with room/display halos;
- directed A*/Lee search;
- bend glyph and arrowhead legality;
- minimum two-cell pipes;
- channel reservations;
- congestion costs;
- rip-up and reroute;
- exact parser validation.

Routing order should prioritize:

1. timing-sensitive and capacity-critical feedback nets;
2. display and I/O nets;
3. highly constrained ports;
4. ordinary patient streams.

For non-planar topology, the router may insert an explicit relay/crossover
room from the library. A visual pipe crossing is never allowed.

### 6. Retiming and capacity adjustment

After a legal route:

- lengthen nets that require storage;
- redistribute delay across latency-insensitive cycles;
- shorten critical feedback paths;
- satisfy settling and skew inequalities;
- add explicit relay/barrier components where raw pipe length is insufficient
  or too geometry-dependent.

Every change is reflected in the placed-netlist hash.

### 7. Physical compaction

Legal local moves include:

- slide component until a room/route/halo constraint becomes tight;
- swap sibling components;
- rotate/replace one implementation;
- reroute one net;
- move I/O into slack;
- fold a long pipe through unused space;
- balance width and height;
- remove surplus delay while preserving a proved margin.

This stage should be able to optimize an already generated machine without
changing component room code.

## Timing and cost estimation

Static timing is a screening model, not an exact judge.

Represent:

- component service time and initiation interval;
- routed pipe latency;
- pipe capacity;
- transaction token counts;
- feedback-cycle mean;
- barriers and acknowledgements;
- observed blocking profiles.

For patient acyclic pipelines, max-plus or event-schedule estimates may be
accurate. Cyclic, occupancy-observing, arrival-ordered, and display networks
need simulator calibration.

Promising candidates receive:

1. component-level schedule checks;
2. selected small full-network workloads;
3. complete public/adversarial evaluation;
4. final exact promotion gate.

## Incremental scoring

A move often affects only:

- the bounding box;
- a few route lengths;
- a port-selection margin;
- one feedback cycle;
- cases whose dynamic schedule reaches that cycle.

Maintain an invalidation graph so the optimizer can reuse:

- unchanged component characterization;
- unchanged route legality;
- unaffected workload results;
- previous trace prefixes where safe.

Any reuse optimization needs an audit mode that occasionally recomputes from
scratch and compares.

## Search moves and algorithms

Recommended move set:

- translate;
- rotate/reflect when legal;
- component implementation replacement;
- macro regroup;
- sibling reorder;
- port candidate replacement;
- route rip-up/rebuild;
- route waypoint perturbation;
- delay/capacity insertion or removal;
- relay/crossover insertion or deletion;
- bounding-box squeeze;
- component-factory request.

Recommended search progression:

1. deterministic compaction to a local legal minimum;
2. multi-start row/channel layouts;
3. annealing or large-neighborhood 2D search;
4. parallel independent chains;
5. learned or solver-assisted proposals only after a result corpus exists.

## Robustness objective

Public average ticks are an incomplete workload model. Retain and report:

- worst-case tick margin;
- capacity margin;
- nearest-port margin;
- timing-inequality margin;
- behavior across generated valid workloads;
- sensitivity of predicted score to workload weights.

A slightly worse public score with strong hidden-case margins may be the safer
submission. The archive should preserve both.

## Structural manifest

Every generated program should have a machine-readable manifest:

```text
program_hash
netlist_hash
placed_netlist_hash
component_instances:
  - contract
  - implementation
  - parameters
  - room_grid_hash
  - placement
  - orientation
nets:
  - logical endpoints
  - physical port cells
  - route cells/hash
  - length/capacity
  - timing class and margins
static_metrics
dynamic_evaluations
tool_versions
```

This makes downloaded or hand-edited `.man` files comparable to generated
lineages and prevents “unknown winning geometry” from recurring.

## Existing-program compaction

There are two import modes:

1. **Annotated import:** an existing structural generator already names rooms,
   placements, and routes. Convert it directly to a netlist.
2. **Recovered import:** parse a `.man`, identify rooms/pipes, and assign
   generated IDs. Behavior and port contracts remain `external` until
   annotated.

Recovered import can safely perform geometry-only moves while keeping room
grids immutable. It must still validate nearest-port behavior because moving
rooms changes distances.

## First benchmark

For recovered TCP:

1. Import the five-room/six-pipe structural generator.
2. Declare exact ports and capacity/timing constraints.
3. Reproduce `tcp_03` exactly.
4. Restrict moves to room translation and pipe rerouting.
5. Ask the compactor to find a 38-square or better layout.
6. Verify byte-for-byte reproduction if it finds the known `tcp_02`, or retain
   a different valid layout with exact measurements.

Success is not merely finding 38×38. The run must explain which constraints
were binding and be reproducible from the manifest and seed.
