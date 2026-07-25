# Codex position: a synthesis platform for Littleman

Status: original provisional proposal. For the contest window, the
user-validated decisions in `codex_03_rust_toolchain.md` and
`codex_06_yt_search.md` supersede this document's full-Rust-parser,
factory-first, and default-distributed implications: compose in Python,
reuse the Python parser, build Rust only after profiling, and use YT only
for useful CPU work projected above roughly five local minutes.

This document distinguishes three kinds of statement:

- **Observed:** measured in this repository or specified by the contest.
- **Proposed:** a design choice Codex currently recommends.
- **Open:** a question that should remain unsettled until an experiment or a
  second architecture review resolves it.

## Executive position

Littleman should be treated as a spatial, concurrent hardware target rather
than as an unusual assembly language. A room is a sequential processing
element, a pipe is a bounded FIFO with latency and backpressure, and the final
grid is physical layout. The complete flow should therefore resemble:

```text
problem oracle
  -> typed process graph
  -> component instances and stream protocols
  -> logical netlist
  -> component implementation variants
  -> floorplan and routed pipes
  -> exact .man
  -> parser/simulator/server-compatibility verification
```

The load-bearing interface is the **component contract**. Rust, YT, a
component factory, and a higher-level language are useful only if they all
consume and produce the same contract.

The recommended strategy has two lanes:

1. **Baseline synthesis:** deterministic, conservative, fast enough to produce
   a correct program from components.
2. **Optimization synthesis:** retain many equivalent component and layout
   variants, search a Pareto frontier, and validate selected candidates with
   the exact simulator.

A general soft-core interpreter remains useful as a third, deliberately
low-scoring fallback for problems that are otherwise too slow to implement.
It should share the component library and verification flow rather than become
a separate project.

## Evidence already present in the project

| Observation | Architecture consequence |
| --- | --- |
| Grade Book's finite-state-room compiler reduced an initially huge layout by about 96.8% before a later geometry-only change improved live score another 15.97%. | Component-body compilation and physical compaction are separate, both valuable optimization stages. |
| Recovered TCP variants separate a large protocol improvement from a later 43×38 to 38×38 geometry-only improvement. | Preserve architecture, component, and layout lineages separately; do not collapse them into one “best program.” |
| TCP uses in-band tags, durable values in B, phase debt, and shorter feedback paths. | The library needs protocol-level components and timing properties, not just reusable ASCII rooms. |
| Memory packing reduced the number of ring values by encoding several logical values per signed-64 word. | Representation selection must feed back from physical cost into the logical design. |
| Sudoku and Grade Book benefited from balancing the bounding square, even when rectangular area was not the direct target. | The placer must optimize `max(width,height)`, not ordinary area alone. |
| Plotter, Brackets, and TCP exposed wrong-pipe and route-crossing failures. | Port resolution and routing legality must be machine-checked properties of every component instance. |
| `q`, display ADDR/DATA/SWAP ordering, `R`/`U`, blocking sends, and pipe fill can make timing observable. | “Pipe length does not affect semantics” is a conditional property, never a global assumption. |
| The local parser differed from the platform on shared walls, backtick pairing, and final wall behavior. | A Rust implementation must be differential-tested against both the Python oracle and preserved server evidence. |
| Existing Python generators reproduce exact accepted artifacts and retain measured variants. | Migration must wrap and compare before replacing; the Python corpus is valuable executable specification. |

The detailed evidence lives in:

- `docs/littleman-cookbook.md`
- `docs/toolchain-plan.md`
- `docs/synthesis-stack.md`
- `reports/2026-07-25-tcp-recovery-lessons.md`
- `reports/2026-07-24-grade-book.md`
- `reports/2026-07-24-grade-book-optimization.md`
- `reports/2026-07-25-tcp-transfer-audits.md`

## Recommended architecture

### 1. Correctness kernel

One small, heavily tested layer owns the exact language:

- grid parsing and room/display/pipe discovery;
- signed-64 execution;
- blocking and pipe-shift order;
- nearest-pipe resolution and reading-order ties;
- round, output, display, and scoring semantics;
- compatibility checks for known server behavior.

Everything else calls this kernel. Search workers may use approximations for
speed, but no candidate becomes authoritative without the kernel.

### 2. Typed logical IR

The logical IR represents patient processes connected by typed token streams.
It has no absolute coordinates. It records transaction boundaries, stream
schemas, state ownership, reset/round behavior, and which timing effects are
semantically observable.

### 3. Component library

A logical component names an interface and behavior. It owns a family of
physical implementations. Each implementation records:

- room grid or a generator for it;
- exact and alternative physical ports;
- protocol and token order;
- timing and capacity characterization;
- legal orientations and transformations;
- proof and test evidence;
- measured geometry and tick properties.

### 4. Component factory

The factory generates equivalent implementations by changing instruction
sequences, state allocation, control-flow layout, spills, port placement,
packing, and local geometry. It keeps a multi-objective Pareto archive rather
than one winner.

### 5. Netlist synthesizer

The synthesizer chooses component variants, places them, routes legal pipes,
checks selection margins and capacity, predicts timing, and evaluates complete
machines. The exact simulator is used selectively: at every correctness gate
and on promising candidates, not necessarily for every cheap search move.

### 6. Distributed experiment plane

YT evaluates independent candidate shards, fuzz corpora, placement seeds,
component parameter grids, and large benchmark matrices. It is not the source
of truth. Every remote row is content-addressed and reproducible locally.

## Principles

1. **Contract first.** Freeze the data model before optimizing its producers.
2. **Logical and physical identities are distinct.** One component behavior
   may have many implementations; one network may have many layouts.
3. **Latency independence must be declared and verified.** Components using
   only deterministic blocking `r`/`s` may often be safely retimed; `q`,
   `R`/`U`, display timing, capacity assumptions, and multi-stream races need
   explicit constraints.
4. **Ports are geometric resources.** A port contract includes wall, offset
   or offset candidates, direction, instruction sites, and a pipe-selection
   safety margin.
5. **Capacity and latency are separate properties of the same pipe.** A route
   can be long enough for storage and still be too slow, or fast enough while
   too short for a burst.
6. **Keep the full Pareto frontier.** Width, height, maximum dimension,
   latency, initiation interval, capacity, bytes, and robustness can trade
   against each other across different networks.
7. **Use exact evidence at promotion boundaries.** Approximate cost models may
   rank candidates; exact parse, simulation, hashes, and test results promote
   them.
8. **Make search deterministic and replayable.** Seeds, tool versions,
   component hashes, workloads, and configuration are part of every result.
9. **Build vertical slices.** A narrow end-to-end flow that reproduces a known
   machine is more valuable than isolated ambitious subsystems.
10. **Do not erase hand knowledge.** Verified idioms become library elements,
    assertions, and transformations rather than prose that a new optimizer
    must rediscover.

## What this proposal deliberately avoids

- Replacing the Python simulator before differential parity exists.
- Treating arbitrary `.man` text as safely decomposable without annotations.
- Assuming all networks are latency-insensitive.
- Starting with a general HLL before the component/netlist contract works.
- Using GPU compute merely because it is available.
- Reducing every objective to one public-case score too early.
- Keeping only the latest candidate and losing optimization lineage.

## First architectural wager

The first vertical slice should reconstruct recovered `tcp_02` from declared
components and nets, then use the new physical optimizer to rediscover at
least the known 43×38 to 38×38 geometry improvement while holding every room
program constant. This benchmark has:

- an exact structural generator;
- several measured variants;
- meaningful capacity and phase constraints;
- public and adversarial tests;
- a clear separation between protocol and geometry changes.

Grade Book should be the second slice because it exercises generated FSM
rooms, many repeated component instances, broadcast/acknowledgement topology,
and square balancing at larger scale.
