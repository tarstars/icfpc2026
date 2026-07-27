# Solver usage track: hybrid decision, floorplanning, and port assignment

Date: 2026-07-27

Status: two exact solver layers implemented; Brackets replay measured; next
missing variable is component/landing-pad selection.

## Synchronization findings

The current repository state changes the interpretation of the first TCP
benchmark. The recovered `tcp_02` 38-square architecture remains a useful
known-answer floorplanning case, but the live lineage is now `tarstars_tcp_10`
at 30x30. A 35-square route for the old architecture would therefore not improve
score and detailed routing is deferred.

Two peer messages determine the useful continuation:

- Codex explicitly identified the fixed-port limitation of the proposed placer
  and said component relocation/folding has higher leverage when a room pins the
  machine.
- Alexey supplied a concrete customer for variable port assignment: Brackets'
  width-pinning middle room and its landing-pad dependencies. Alexey also
  established the acceptance rule for pipe shortening: transport pipes should
  be shortest; storage pipes require occupancy and adversarial capacity proofs.

The solver stack should therefore be layered:

1. room implementation/shape frontier;
2. exact macro placement and square objective;
3. exact port assignment under nearest-pipe semantics;
4. detailed routing with transport/storage annotations;
5. parser, compatibility, resolution, and judge oracle.

## Layer 1 already present: macro floorplanning

`experiments/gpt-solvers-usage/floorplan_milp.py` uses integer room origins and
four-way non-overlap disjunctions. On the recovered TCP benchmark:

```text
preserved placement: 38x38, feasible
exact abstract optimum: 35x35
HiGHS MIP gap: 0.0
```

The model rejects endpoints inside or beside unrelated non-corner walls. A
weaker first formulation produced a false 33-square optimum and was discarded.
This result remains a regression for placement constraints, not a live
candidate.

## New layer: exact joint port assignment

`port_assignment_milp.py` treats logical pipe endpoints as one-hot candidate
variables. For each `s`, `r`, or `q` instruction, incompatible candidate pairs
are excluded using the simulator's exact key:

```text
(distance to endpoint, endpoint row, endpoint column)
```

For each net, source/sink pair variables enforce inclusive Manhattan pipe-cell
bounds and supply the weighted objective. HiGHS must prove a zero-gap optimum.
A second exact solve chooses a stable optimum with the fewest moved endpoints,
then least displacement.

The tool can read explicit problem JSON or derive the problem from
`littleman.ir_export.machine_ir`. The adapter keeps movable endpoints on their
current wall and obtains operation-to-pipe roles from the IR resolution map.
It does not duplicate parser semantics.

## Brackets measured replay

The peer handoff described two five-cell room0<->room2 pipes whose endpoint
freedom ranges overlap. The checked-in `brackets_10` instance contains:

- 12 logical endpoints for six pipes;
- 30 exact nearest-pipe binding constraints;
- same-wall candidate ranges for the four movable endpoints;
- the remaining endpoints fixed;
- current length caps and a transport objective on the two gap pipes.

Measured result:

```text
brackets_10 objective: 10 weighted pipe cells
exact optimum:          4 weighted pipe cells
selected gap lengths:   2 and 2
HiGHS MIP gap:          0.0
focused tests:          5 passed
solve wall time:        1.31 s
peak RSS:               149948 KiB
```

This automatically recovers the six-cell endpoint/latency reduction that led to
live `brackets_11` (26/26, score 484,532.65). The solver's deterministic optimum
moves fewer endpoints than the historical hand variant, which is a model-level
alternative only; no new `.man` claim is made without routing and judge gates.

The corresponding `brackets_11` instance returns objective four with its
incumbent ports unchanged. Since every server pipe needs at least two cells,
four is an absolute lower bound for two distinct pipes. The endpoint-only search
for this gap is therefore exhausted.

Hashes:

```text
port_assignment_milp.py        7e16d141e0cfb40cecee16374fb187bec0b7de77e83735d45430027e406785f0
brackets_10_port_instance.json a161cf303690391c22822d65a6f4fdcb5b71ede5a0abb7e07f1f29d21d7239f0
brackets_10_port_solution.json 16ab7cb0767e538f7858bb049917f01a61b31690369fed92773c96d7949ad15b
brackets_11_port_instance.json f6f78ef62bdabc56fd44c7799bd4364886d667e6dbb5f28b024787794c9e325d
brackets_11_port_solution.json 31cc5936fe19a26603eef68f51d403dafc060340c7634dd2d82c28be28bc90e1
test_port_assignment_milp.py   8420c7b10624795e3616a92def77e87c3f5532b25838cf7ddfa2c02ba122783e
```

## What this changes strategically

The most profitable immediate solver milestone is no longer routing the old TCP
35-square placement. It is **component-frontier selection for the Brackets
middle room**, with landing-pad positions and room width represented as discrete
implementation choices.

Why Brackets is the right next discriminating target:

- a peer has identified the exact manual bottleneck;
- the current machine is small, deterministic, and cheap to judge;
- fixed-room port assignment is now proved exhausted, so the next variable is
  unambiguous;
- reducing 27x27 to 26x26 at unchanged ticks is a 7.2702% score reduction:
  `484,532.65 -> approximately 449,306`;
- the resulting component-choice machinery transfers directly to Plotter,
  Grade Book, Sudoku, and the sparse Subset Sum selector room.

The next implementation should not ask the MILP to invent arbitrary room code.
Instead:

1. extract the middle room's block graph and the three landing-pad dependency;
2. generate a finite, tested frontier of equivalent room bodies with named port
   offsets and exact walk costs;
3. add one-hot implementation selection to the floorplanner;
4. use the port solver to choose compatible endpoint cells;
5. route and promote only through the repository oracle.

## Negative and deferred directions

- Old TCP 35-square routing: useful tool test, no longer score-positive against
  live 30x30.
- Endpoint-only Brackets gap work: exact lower bound reached.
- Raw squeeze without occupancy annotation: unsafe; Snake and Subset Sum already
  provide counterexamples.
- One monolithic SAT/MILP over room code, every pipe cell, and runtime semantics:
  too broad and ignores the cheap exact simulator oracle.
