# Claude: factory, composer, and the YT experiment plane

Status: Proposed. Implements Tiers 2-3 of `claude_00_position.md`; consumes
the IR and engine of `claude_02`; agrees with codex_01's contract layers and
speaks its vocabulary.

## 1. Characterizer: the simulator IS the testbench

A component implementation is characterized without any harness rooms: the
engine can inject values into a pipe's cells and observe them directly, so
a "testbench" is just an IR containing the single room plus stub pipes,
driven by the engine API.

Per implementation x workload, produce (all exact, per `claude_01` §2):

```
II per transaction variant     latency (first/last output)
prologue_ticks                 park state {register: meaning} at idle
burst/occupancy on each port   B-liveness through the hot loop
```

plus the **resolution certificate**: for every `s`/`r`/`q` site, the set of
external attachment positions under which the engine's own resolver picks
the declared port (computed by sweeping candidate attachment cells and
re-running the resolver — minutes, once, cached with the implementation
hash). This turns codex_01's `nearest_margin` from a promise into a
computed region.

First extraction batch (all have measured live lineage): I/O feeders, the
2x4 ring relay, memory P1/HEAD/P2/station, the tcp pump family, sort's
compare cell, plotter's stream rooms, and the three Semester 4 patterns
(draw-once display driver, interpreter ring, bitboard row kit) — each must
reproduce its source room byte-for-byte before generalization (codex_01's
extraction rule, adopted verbatim).

## 2. Factory: three rungs, priced honestly

1. **v0 — characterize + pin.** No search; every library entry gets its
   datasheet and regression tests. (Hours; must exist before any search,
   or the search has no fitness function.)
2. **v1 — parametric sweep.** Our components are already emitted by
   generators with parameters (field widths, ring sizes, loop shapes, port
   offsets). Sweep = map {params} -> build -> preflight -> eval on YT.
   This is embarrassingly parallel and needs zero new theory. Expected
   yield: the same class of wins the hand sweeps found (squeeze report:
   sudoku 4.13x, plotter 4.48x) applied uniformly and overnight.
3. **v2 — free-form room superoptimization.** SA/beam over interior glyph
   grids <= ~8x8 against a behavior model + directed tests, fitness =
   testbench pass then (footprint, II) lexicographic. Plausible for the
   small stations (relay, compare, tag codecs); *not* attempted for parser
   rooms in this window. Label: worth one YT night, capped, results are a
   bonus not a plan.

## 3. Composer: floorplan + route over the IR

Formulation (rooms rigid, from the library or an existing machine's IR):

```
vars:        room origins; route polylines per net
hard checks: rooms disjoint + no shared wall cells (gap >= 1)
             routes >= 2 cells, vertex-disjoint, legal bends/terminals
             route capacity >= net capacity_min      (ring: 34-word rule)
             resolution map == declared bindings      (engine-checked)
             display attach sides; I/O room rules
objective:   lexicographic( max(W,H), sum_i traversals_i * len(route_i) )
```

Traversal weights come from characterization (a request-path cell costs a
tick per operation; a parked ring cell costs ~nothing — `claude_01` §2).

Search: greedy constructive placement (largest room first, ports facing
their nets) + simulated annealing with moves {translate room, swap rooms,
reroute net via BFS with congestion penalty, flip port candidate}, feasible
moves only. Every accepted candidate re-derives the resolution map in
Python (cheap) and the final Pareto set replays public + adversarial
workloads in the exact engine before anything is called an improvement.

Two proof slices, in order:

1. **memory_04 re-lay parity** (cheap, fully specified constraints, owner:
   Claude): the composer must reproduce <= 37x37 from the IR with all
   checks green. Any invalid emission = a missing checker, found in
   minutes, not on the server.
2. **tcp_02 reconstruction** (codex_00's wager, richer: capacity + phase
   constraints, known 43x38 -> 38x38 geometry delta to rediscover).

## 4. YT experiment plane

Shape: vanilla operations, static musl `lm-exec` + driver binary, JSONL
rows in, JSONL rows out, everything content-addressed and re-runnable
locally (codex_00's "YT is not the source of truth" — adopted).

| Job family | Row = | Fan-out | Reduce |
|---|---|---|---|
| Parametric sweep (factory v1) | {generator, params} | 1e4-1e6 | top-K + Pareto per component |
| Placement search (composer) | {netlist, seed} | 1e3-1e5 anneal seeds | best-of + lineage |
| Differential fuzz (engine CI) | {random IR, seed inputs} | 1e5/night | mismatches only |
| Adversarial attack (pre-submission) | {live-candidate IR, stream-gen seed} | 1e4 per candidate | worst ticks, any failure |
| Superopt (factory v2, capped) | {spec, SA seed} | one night | survivors to review |

The adversarial family deserves emphasis: Semester 4 problems have tick
caps (15M/50M) and all-or-nothing pass scoring, so "find the input that
maximizes our ticks / breaks a frame" is directly submission-de-risking —
the same harness that verified memory_04 (430 cases, 0 failures) scaled by
four orders of magnitude.

Ops notes: rows are KB-scale, evals are ms-scale => batch >= 1e3 evals per
process to amortize startup; seeds and tool hashes ride in every row
(codex_00 principle 8); GPU pool unused (rationale in `claude_02`
non-goals) unless someone proposes a concrete kernel that beats 1e10
CPU evals/night on value-per-watt.

## 5. What "done" means for the platform inside this contest

1. Engine: golden corpus + adversarial corpus bit-exact; >= 5e7 ticks/s/core.
2. Composer: memory_04 parity, then >= 1 live-submitted improvement found
   by search on any existing problem.
3. Library: >= 8 components with datasheets and byte-exact extraction.
4. YT: >= one sweep and one attack campaign actually executed, results in
   the repo with seeds.
5. Every claim in these four documents either upgraded to Observed with an
   artifact, or explicitly retracted in a follow-up note — the docs are
   falsifiable, and that is deliberate.
