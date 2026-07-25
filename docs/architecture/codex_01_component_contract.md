# Codex proposal: component contracts and variants

Status: long-horizon schema proposal. During the contest, implement only the
fields consumed by the Python composer and component boundary tests; the full
schema is deferred.

## Component, implementation, and instance

These terms must not be conflated:

- A **component** is a versioned behavioral contract such as
  `fifo_relay<T>` or `tagged_window_pump`.
- An **implementation** is one physical realization of that contract: room
  code, local control-flow geometry, ports, timing characterization, and
  evidence.
- An **instance** selects one implementation, parameter values, orientation,
  absolute placement, and routed nets inside a program.

Two implementations may be functionally equivalent but have different port
walls, dimensions, latency, initiation interval, or required pipe capacity.
The optimizer chooses among them in the context of the whole network.

## Five layers of contract

### 1. Behavioral contract

The behavioral layer describes the component as a stateful stream transducer:

- named input and output streams;
- token types and serialization order;
- transaction or epoch boundaries;
- initial and persistent state;
- round/reset behavior;
- valid input assumptions;
- output relation or executable reference model;
- determinism and liveness conditions.

Example:

```text
component compare_swap<i64>:
  input  left:  stream<i64>
  input  right: stream<i64>
  output low:   stream<i64>
  output high:  stream<i64>

  transaction:
    consume left(x), right(y)
    emit low(min(x,y)), high(max(x,y))
```

The contract is about observable streams, not registers or room instructions.

### 2. Protocol contract

The protocol layer makes serialization and blocking assumptions explicit:

- token sequence within one transaction;
- fixed, bounded, sentinel-delimited, or externally counted length;
- whether a component may read ahead;
- whether it may emit before consuming the full transaction;
- maximum burst and occupancy;
- single-producer/single-consumer ownership;
- backpressure expectations;
- whether inputs are consumed in a fixed order;
- whether output order is independent of channel latency.

Useful protocol categories:

| Category | Meaning |
| --- | --- |
| `patient` | Blocking only delays progress; it does not change token values or order. |
| `timed` | Correctness requires a latency, phase, or settling inequality. |
| `arrival_ordered` | `R`/`U` or another ready-first behavior makes arrival order observable. |
| `occupancy_observing` | `q` or a capacity-dependent branch observes queue state. |
| `display_scheduled` | Correctness depends on ADDR/DATA/SWAP arrival ordering. |
| `round_synchronous` | The component relies on external round boundaries or an acknowledgement barrier. |

The default must be conservative: an unannotated component is not assumed to
be retimable.

### 3. Logical timing and capacity contract

Timing is partly a function of input size and partly a function of the routed
machine. Record both symbolic requirements and measured characterization.

Required fields:

- `latency`: minimum/maximum or a symbolic function from transaction start to
  first and last output;
- `initiation_interval`: minimum ticks before accepting another transaction;
- `rate`: tokens consumed and produced per phase;
- `burst`: maximum consecutive sends before receiving or yielding;
- `storage_requirement`: minimum FIFO cells for every logical net;
- `settling_requirement`: inequalities such as
  `delay_path > feedback_round_trip`;
- `skew_requirement`: inequalities among multiple input or display routes;
- `deadlock_assumptions`: environment behavior needed for progress;
- `tick_model`: an estimate plus the benchmark set on which it was fitted.

Timing claims need a provenance label:

- `proved`: derived from a symbolic schedule or exhaustive bounded check;
- `measured`: observed on named workloads and layout;
- `estimated`: an optimization heuristic only;
- `unknown`: forces exact simulation before promotion.

### 4. Physical contract

The physical layer says how the implementation can legally exist on the grid.

For the room body:

- exact grid and border;
- width, height, occupied cells, and forbidden halo;
- spawn location and initial heading;
- legal rotations/reflections;
- literal-axis and backtick constraints;
- control-flow entry headings and shared-cell assumptions;
- maximum men per room and collision assumptions.

For each port:

- logical name and stream direction;
- Littleman direction: incoming to or outgoing from the room;
- exact wall/offset or a set/range of legal candidates;
- adjacent external segment coordinate relative to the room;
- instruction sites that use the port;
- allowed operation classes (`s`, `S`, `r`, `R`, `U`, `q`);
- required nearest-selection margin from every instruction site;
- maximum pipes on the wall and forbidden competing ports;
- minimum and maximum route length if constrained;
- capacity and latency requirements inherited from the protocol.

An exact port example:

```text
port ring_out {
  direction: out
  wall: south
  offset: 27
  operations: [s]
  users: [(18, 27)]
  nearest_margin: 2
  capacity_min: 34
}
```

A relocatable port may declare candidates:

```text
port ack_out {
  direction: out
  candidates: south[8..20]
  operations: [s]
  nearest_margin: 1
}
```

The component factory must produce a new implementation variant after choosing
a candidate. Port relocation is not an invisible linker edit because it may
change nearest-pipe semantics.

### 5. Evidence contract

Every implementation carries evidence rather than a boolean “verified” flag:

- component and implementation semantic hashes;
- generator identity and source revision;
- exact room-grid hash;
- parser version and parse result;
- symbolic register/queue checks;
- intent-resolution checks;
- reference-model test corpus hash;
- exhaustive bounds, if any;
- randomized seeds and counts;
- timing/capacity measurements;
- known server-compatibility checks;
- known counterexamples and unsupported transformations.

Evidence is append-only. A new tool version creates new evidence; it does not
rewrite history.

## Proposed serialized model

The human language can compile to a canonical schema. The exact syntax remains
open, but these entities should be stable:

```text
ComponentContract
  id
  version
  type_parameters
  ports[]
  behavior_model
  protocol
  timing_requirements
  properties[]

ComponentImplementation
  contract_id
  implementation_id
  parameters
  room_grid | generator
  physical_ports[]
  legal_transforms[]
  static_metrics
  characterization[]
  evidence[]

Network
  instances[]
  nets[]
  external_io
  display
  workload_profile

PlacedNetwork
  selected_implementations[]
  placements[]
  routed_nets[]
  predicted_metrics
  validation_state
```

Canonical serialization should be content-addressable. A normalized contract,
implementation, network, and workload profile each receive separate hashes.

## Net contracts

A net is more than `(source, destination)`:

```text
net records {
  from: parser.records
  to: worker.records
  token: roster_record
  protocol: counted
  count_source: parser.n
  capacity_min: 33
  latency:
    class: patient
  route:
    min_cells: 33
    max_cells: unconstrained
}
```

Required net checks:

1. One producer and one consumer unless an explicit broadcast/merge component
   exists.
2. Token types and framing agree.
3. Direction and physical port classes agree.
4. Routed length satisfies pipe parser minimum and capacity.
5. Timing and skew inequalities hold.
6. Nearest-pipe intent remains correct after every route is attached.
7. No route crosses a room, display, literal constraint, or another pipe.
8. I/O and display side restrictions hold.

## Component variant frontier

Do not rank component implementations with one scalar before placement.
Retain non-dominated variants over at least:

- width;
- height;
- maximum dimension;
- occupied cells;
- byte count;
- first-output latency;
- last-output latency by workload;
- initiation interval;
- input/output burst;
- required external pipe capacity;
- port-wall demand;
- selection margin;
- timing-sensitivity class;
- robustness evidence.

A 20×8 room and an 11×15 room are both useful: the best choice depends on the
rest of the floorplan. Similarly, a slower component with ports on opposite
walls may beat a faster unroutable one.

## Composition safety levels

Proposed promotion levels:

| Level | Meaning |
| --- | --- |
| `structural` | Parses; ports and routes are legal; intent checks pass. |
| `protocol` | Token schemas, ownership, framing, capacity, and stated timing inequalities compose. |
| `behavioral` | Component reference models compose on directed tests. |
| `differential` | Generated `.man` matches the composed oracle over a named corpus. |
| `release` | Exact artifact passes public, adversarial, server-compatibility, hash, and provenance gates. |

The optimizer may explore structural candidates cheaply. Only release-level
artifacts are candidates for submission.

## Initial library extraction order

Extract components from existing, measured machines before inventing generic
ones:

1. I/O rooms, relay rooms, and display ADDR/DATA/SWAP drivers.
2. Deterministic 1-in/1-out stream transforms.
3. Counted and sentinel FIFO relays.
4. Compare, sign dispatch, tag encode/decode, and small reducers.
5. Pipe-backed register files and ring memories.
6. Input normalizers, broadcast splitters, collectors, and ack barriers.
7. Generated FSM rooms from Grade Book, Matrix, Sudoku, and Plotter.
8. Packed record codecs from Memory and TCP.
9. Specialized systolic stages from Sort and Subset Sum.

Each extraction must reproduce at least one existing room byte-for-byte before
the component is generalized.

## Open questions

1. Should a component contract require an executable reference model, or may a
   declarative relation plus tests suffice?
2. Should ports be exact in version 0.1, postponing candidate offsets until
   the component factory is reliable?
3. Is timing best represented as inequalities, timed automata, max-plus
   algebra, or a simpler schedule trace plus measurements?
4. How much of the scratch-pipe state is part of a component boundary?
5. Should `R`/`U` and `q` components live in a separate explicitly
   timing-sensitive library?
6. What evidence is sufficient to claim two implementations equivalent?
