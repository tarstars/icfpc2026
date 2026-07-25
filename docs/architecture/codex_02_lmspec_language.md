# Codex proposal: LM-Spec, a language for components and networks

Status: post-contest language proposal. The contest-window decision is
structured Python dataclasses plus JSON only; no custom surface syntax until
the schema survives two composer/component vertical slices.

Working name: **LM-Spec**. File extensions are provisionally `.lmc` for
component definitions and `.lmn` for networks.

The first version should not try to be a convenient general-purpose language.
Its job is to make component composition unambiguous and machine-checkable.

## Language layers

LM-Spec should contain four related declaration kinds:

1. `protocol` — token types, transaction framing, and stream discipline.
2. `component` — behavioral interface and logical properties.
3. `implementation` — room state machine, physical ports, timing/capacity,
   legal transforms, and evidence requirements.
4. `network` — instances, nets, external I/O, workload, and optimization
   objectives.

The syntax is human-authored, but it compiles into a canonical serialized IR.
Tools should exchange the IR, not depend on formatting or comments in source.

## Example

This example is illustrative, not a frozen grammar:

```text
lmspec 0.1

type Packet = record {
  seq:  range<0, 47>,
  value: range<1, 999>,
}

protocol Counted<T> {
  stream = [count: range<0, 64>, item: T * count]
  ownership = single_producer_single_consumer
  backpressure = allowed
}

component TaggedForwarder {
  input  tagged: Counted<i64>
  output result: Counted<i64>

  behavior = model("littleman_models.tcp:forwarder")
  determinism = patient

  property sentinels_are_negative
  property values_fit_i64
}

implementation TaggedForwarder.compact for TaggedForwarder {
  params {
    settle: range<0, 32> = 4
  }

  room main {
    registers {
      A: token
      B: expected
      BP: loop_count
    }

    state idle:
      tagged.recv -> A
      branch sign(A) {
        negative -> decode_tag
        zero     -> forward
        positive -> forward
      }

    state forward:
      result.send A
      goto idle

    state decode_tag:
      ...
  }

  port tagged {
    direction = in
    candidates = west[3..8]
    operations = [recv]
    nearest_margin >= 1
  }

  port result {
    direction = out
    candidates = east[3..8]
    operations = [send]
    nearest_margin >= 1
  }

  timing {
    class = patient
    initiation_interval <= 20 ticks
    tagged.capacity >= 2
  }

  transforms = [translate, rotate_180]
}

network TcpCandidate {
  instance split: InputSplitter.compact
  instance pump: WindowPump.tagged(window = 16)
  instance out: TaggedForwarder.compact

  connect split.packets -> pump.packets {
    capacity >= 33
  }
  connect pump.tagged -> out.tagged

  objective lexicographic {
    pass_all(workload = "tcp-boundary-v1")
    minimize score_estimate
    minimize max_dimension
  }
}
```

## Type system

Version 0.1 needs a small type system:

- `i64` with required signed wrapping;
- `bool`;
- bounded integer `range<lo, hi>`;
- enumerations and tagged unions;
- fixed tuples and records;
- `stream<T>`;
- protocol wrappers such as `Fixed<T,N>`, `Counted<T>`,
  `Sentinel<T,S>`, and `Round<T>`;
- display commands `Addr`, `Color`, and `Swap` as ordinary typed streams with
  additional side constraints.

Records are logical. A serialization declaration maps one logical value to one
or more signed-64 pipe tokens:

```text
encoding PackedRecord for Record {
  words = 2
  encode = model("littleman_models.memory:encode")
  decode = model("littleman_models.memory:decode")
  property round_trip
  property every_word_fits_i64
}
```

Encoding choice is an optimization dimension. It must be visible in the
network hash and component contract.

## Behavioral descriptions

LM-Spec should support three behavior sources:

1. `model(...)`: an executable reference function, initially Python and later
   optionally Rust/Wasm.
2. A restricted process body over typed streams and local state.
3. `external`: a contract defined by tests and evidence only, for importing
   legacy rooms.

The restricted process language should allow:

- blocking receive and send;
- fixed and bounded loops;
- local signed-64 arithmetic and bit operations;
- branches;
- persistent local variables;
- explicit round or transaction boundaries.

It should not initially allow arbitrary recursion, dynamic allocation, shared
mutable state, or implicit concurrency inside one process.

## Implementation language

The implementation body is closer to RTL than to the behavioral process:

- explicit A, B, and BP lifetimes;
- explicit receive/send sites;
- finite-state blocks;
- branch outcomes;
- scratch FIFO reads/writes;
- literals with traversal direction;
- optional raw instruction fragments;
- assertions at block boundaries.

Example assertion:

```text
assert at loop_head {
  A = dead
  B = expected
  BP = remaining
  scratch = [dy, error, dx]
}
```

This lets the compiler perform register allocation where possible while still
supporting hand-directed implementations.

Version 0.1 should compile to the existing finite-state-room approach, with a
raw-grid escape hatch:

```text
implementation LegacyPump for WindowPump {
  grid = artifact("submissions/tcp/tcp_02.man", room = "pump")
  behavior = external
  ports = ...
  evidence = ...
}
```

## Ports and pipe attachment

Logical code refers only to named ports. An implementation maps each port to:

- exact wall/offset;
- a finite candidate set;
- or a constrained range.

The compiler chooses an attachment, emits the room/grid change if necessary,
and then proves:

- every `s`/`r`/`q` resolves to the declared pipe;
- every `S`/`R`/`U` sees the declared set;
- the nearest-selection margin satisfies the contract;
- pipe direction and parser rules hold;
- no port touches a forbidden display corner;
- literal and control paths remain valid.

The language should never let a network author specify an absolute pipe cell
inside a component. That is an implementation detail.

## Timing language

Timing needs both classification and constraints:

```text
timing {
  class = timed
  first_output <= input_count * 14 + 20
  initiation_interval <= input_count * 12 + 8
  capacity(storage) >= input_count + 1
  require settle_path > round_trip(storage) + 2
  require skew(data, address) >= 3
}
```

Symbolic expressions may refer to:

- bounded component parameters;
- transaction sizes;
- routed pipe lengths;
- path sums;
- component characterization fields.

The compiler need not prove every expression in version 0.1. It must at least
preserve the constraint, identify what is proved versus measured, and reject a
layout when a required inequality is false.

## Network semantics

The default network model is deterministic blocking streams. Constructs that
make arrival timing observable require explicit declarations:

```text
connect_many [a.out, b.out] -> merge.in {
  policy = reading_order_ready
  timing_sensitive = true
}
```

Broadcast and merge should normally be components, not special wire behavior.
This keeps the physical cost and scheduling visible.

Network declarations may specify:

- component instances and parameters;
- logical connections;
- input/output/display bindings;
- capacity/timing constraints;
- workload profiles;
- objectives and hard bounds;
- allowed implementation families;
- placement hints that are optional unless marked `require`.

## Intermediate representations

Recommended lowering pipeline:

```text
LM-Spec source
  -> typed AST
  -> behavioral process IR
  -> scheduled process/FSM IR
  -> register-and-scratch allocation IR
  -> component physical IR
  -> logical netlist IR
  -> placed/routed netlist IR
  -> exact grid
```

Every lowering emits a content hash and optional source map. Debuggers should
be able to map a runtime man/cell back to component, FSM state, and source
declaration.

## Diagnostics are part of the language

The tools should report architecture-level failures:

- “`pump.ring_in` resolved to `ack_in`; nearest distances 7 and 6”;
- “route provides 31 cells; protocol requires at least 34”;
- “display data can arrive two ticks before its corresponding address”;
- “component variant is behaviorally valid but cannot rotate because literal
  3 would be read backwards”;
- “network is non-planar under selected port walls; one relay/crossover
  component is required”;
- “tick estimate is based on public workload only and is not a proof.”

ASCII coordinates alone are insufficient for a component system.

## What to freeze first

Before debating surface syntax, freeze:

1. canonical port model;
2. protocol/framing model;
3. timing/capacity constraint vocabulary;
4. component/implementation/instance identity;
5. evidence and characterization records;
6. netlist schema.

The source language can evolve while these IR contracts remain versioned.

## Open design choices

- Custom parser versus a structured host format such as RON for version 0.1.
  A custom language is nicer for FSMs; RON is faster for schema iteration.
- Whether behavior models should run through a Python bridge, Wasm ABI, or a
  simple line-oriented protocol.
- Whether bounded loops are expanded during scheduling or remain first-class.
- Whether implementation source may contain relative coordinates, or only
  state blocks plus compiler-controlled layout.
- Whether timing constraints should use a general expression language or a
  fixed set of named forms.

Codex currently favors a canonical Serde schema plus a thin custom syntax.
That keeps the data model testable before investing in parser ergonomics.
