# Solver usage track: decision and first exact benchmark

Date: 2026-07-27

Status: first executable floorplanning checkpoint complete; routing gate remains.

## Repository position

The architecture notes converge on a hybrid rather than a monolithic solver:

1. preserve or choose a process architecture and room implementations;
2. use an exact solver for small, discrete physical decisions such as square
   floorplanning, non-overlap, port choice, and bounded route-length relations;
3. use a grid router or local search for detailed pipes;
4. accept a result only through `Machine.parse`, port-resolution audit,
   `server_compat`, and exact workload judging;
5. feed routing or timing failures back into the next placement solve.

This division matches the measured repository evidence. Layout solvers can
recover L0 gains once an architecture exists. They cannot invent packed state,
a lower-initiation-interval pipeline, or a new process topology, which are the
sources of the proposed 100x-class gains.

The practical uses of solvers are therefore:

- exact macro floorplanning for small room counts;
- component-variant and port-position selection;
- bounded synthesis/model checking for compact room bodies;
- repair and large-neighborhood search around known-good machines;
- lower bounds and counterexamples that explain why a hand layout is pinned.

A single SAT/MILP/CP-SAT model of rooms, every pipe cell, dynamic scheduling,
and program semantics is the wrong first target. It would mix several kinds of
constraints, lose the cheap exact simulator oracle, and still not search the
architecture-level representations that dominate the largest scores.

## First vertical slice

`experiments/gpt-solvers-usage/floorplan_milp.py` implements fixed-orientation
square floorplanning with SciPy's HiGHS MILP backend. The benchmark imports the
geometry and six preserved inclusive pipe-length caps of the five-room TCP
architecture represented by `src/littleman/alexey_tcp_recovered.py`.

The model includes:

- integer room origins and square side;
- pairwise four-way non-overlap disjunctions;
- legal non-corner wall-relative endpoints;
- exclusion of endpoint cells from unrelated rooms and unrelated side-wall
  attachment cells, while retaining the corner-grazing behavior used by the
  accepted TCP layout;
- unique endpoint cells;
- `|dx| + |dy| + 1 <= preserved_pipe_cells` for every net.

The preserved 38x38 placement is a regression fixture and satisfies the model.
HiGHS proves the model optimum is 35x35 with MIP gap 0.0. The room-area lower
bound is 28, so geometry and endpoint relations account for seven additional
side cells in this abstraction.

Measured development run:

```text
solve wall time: 1.08 s
peak RSS:        163396 KiB
unit tests:      5 passed
fixture:         deterministic
```

Hashes:

```text
floorplan_milp.py       44c9ba3062b09bf874eeb3887fa26137eddb281025a60e164f1d8eb704c11718
tcp_room_instance.json 5bd3fb0ae2f4e26b921c8c7d0fc26d52c8ec46379f8d0667e6a734b890cf6f86
tcp_room_solution.json 32c187bc9dd28f97638f9c58820be9322d41dca2ad24bd8c1b150071c7c5f035
test_floorplan_milp.py  952392157459293071749c0608fec4640c6f78f992d5290425d6e29bda974ff3
```

The footprint-only potential is:

```text
35^2 / 38^2 = 0.8483379501
```

or 15.17% below the preserved 38-square footprint if detailed routing and exact
behavior can be retained. No `.man` candidate or contest score is claimed.

## Negative result that changed the model

The first version proved a 33-square optimum using only room non-overlap and
endpoint Manhattan caps. Inspection showed that its two-cell I/O routes placed
pipe endpoints on or beside unrelated room walls. This is exactly the kind of
false positive warned about in the solver-stack design: a mathematically clean
placement model is not a Littleman legality proof.

The 33 result was discarded. Endpoint-room obstacle disjunctions and endpoint
uniqueness raised the exact optimum to 35 and made the preserved accepted
38-square layout a positive regression. This is evidence for keeping the
parser/oracle loop central rather than trusting an abstract objective.

## Next discriminating experiment

For the exact 35-square placement:

1. reserve room cells and all wall-grazing forbidden cells;
2. route the two forced two-cell I/O nets first;
3. route the exact-length event net, then the capacity/timing-sensitive feedback
   nets, using disjoint orthogonal paths and legal endpoint directions;
4. render the original room grids unchanged;
5. run `Machine.parse`, `server_compat`, resolution-map comparison, all public
   cases, and the 45-case TCP boundary suite.

A route witness promotes 35 to a real geometry candidate. A routing
counterexample should not be generalized into a proof that 35 is impossible;
instead enumerate alternative optimal placements, then 36 and 37. The MILP
should become a placement generator feeding a router, not a one-shot source of
truth.
