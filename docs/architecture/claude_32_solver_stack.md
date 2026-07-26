# claude_32: solver-based layout infrastructure — design and build order

Status: design + build plan, started 2026-07-26 ~15:00Z. Two goals at
once, deliberately: (a) improve contest score before freeze, (b) take a
real shot at a general layout solver. The design is chosen so that (a)
is a by-product of the first milestone of (b), not a detour from it.

## 1. What the problem actually is

Score = `max(W,H)^2 * avgTicks`. Two consequences most packers get wrong:

- The geometric objective is **Chebyshev diameter squared**, not area.
  Slack in the minor dimension is FREE: 100x180 scores exactly as
  180x180. The objective wants *squarification*, not compaction.
- It is **bi-criteria**: ticks = cells the man walks. Hot-path geometry
  costs score; cold-path geometry is free. Measured both ways: plotter's
  EUPD pipe went 4 -> 335 cells with zero tick cost, while tcp's ring
  pipes 8+24 -> 2+2 *reduced* ticks.

Four stacked problems, with what each has actually paid us:

| level | problem | measured yield | analog |
|---|---|---|---|
| L0 placement | rigid rooms + routing, min max-dim | presses 1.1x-6.3x | floorplanning + routing |
| L1 interior fold | re-lay a fixed walk in a smaller box | memory 1.61x, sort 1.53x, alexey reverse 1.19x | orthogonal path embedding |
| L2 walk opt | change the program: fewer laps | snake 1.72x, brackets 3.7x, tcp 2.7x | compiler passes on the block graph |
| L3 co-design | room decomposition, pipe topology | Codex 145-room vs my 1-room lockstep | design-space exploration |

**The dominant empirical fact: the box is nearly always pinned by ONE
room.** SCAN 306 rows; SCAN3's P1 3,247 cols; Codex's LLM 10,024 rows;
subset-sum 696x1639; gradebook's 385-wide parser. So L0 flatlines until
an L1 fold breaks the pin — which is why "measure occupancy, find the
pin, choose the level" became our diagnosis procedure.

## 2. Why a solver is viable here (the unusual part)

1. **We own a cheap exact feasibility oracle**: `Machine.parse` +
   `room_ports.audit` + `ir_export.machine_ir` binding roles +
   `server_compat` layout rules + fastsim judge — seconds per candidate,
   and bit-exact against `sim.py`. Search wrapped around a real checker
   beats clever modelling; our hand presses were exactly that, done
   manually.
2. **The constraints are codified and paid for**: nearest-pipe Voronoi
   binding; a pipe *grazing* a wall counts as connected; exactly one
   pipe against an input room's wall; a pipe's first cell points away
   from its wall; no shared wall cells; no 1-cell pipes; capacity >=
   invariant for patient machines and length EXACT for timed ones
   (`q`/`R`/`U`).
3. **Massive repetition** in the big instances: subset-sum is 2,121
   near-identical rooms — a template-array problem with a few dozen
   integer variables, not a 2,121-rectangle packing.

## 3. Architecture

```
   .man  --parse-->  LayoutIR  --solver-->  placement  --router-->  .man
                        ^                                            |
                        |                    oracle (audit+judge) <---+
                        +---------------- repair loop ---------------+
```

- **LayoutIR** (`src/littleman/layout_ir.py`): rooms as rigid rectangles
  with port descriptors (wall side, offset, direction, role, required
  pipe length or `>=` capacity), plus the required connection list. Built
  BY PARSING an existing artifact, so every experiment starts from a
  known-good machine and the oracle can compare against it.
- **L0 solver** (`layout_solve.py`): CP-SAT. 2D no-overlap over inflated
  rectangles (margin baked into the inflation), `minimize max(W,H)`
  natively, symmetry breaking, optional fixed-length pipe constraints via
  Manhattan distance equalities.
- **Router** (`layout_route.py`): start from the existing BFS autorouter
  in `llm_step3`; upgrade to PathFinder-style negotiated congestion only
  if an instance needs it (subset-sum's 2,164 pipes will).
- **Oracle gate** (`layout_gate.py`): parse, server_compat, binding
  audit vs the ORIGINAL artifact (0 role diffs), judge equality. Nothing
  ships without it.

## 4. Build order (each milestone independently useful)

- **M1 — LayoutIR + L0 CP-SAT placer, validated against our own hand
  presses.** We have five hand-pressed artifacts with known outcomes
  (snake 5.6x, plotter 3.05x, matmul 1.59x, sudoku 1.58x, tcp 1.32x).
  Feeding the solver the PRE-press machine and comparing to the
  hand-pressed box is a ground-truth benchmark almost nobody gets to
  have. Success = matches or beats hand on >= 3 of 5.
- **M2 — apply to a live target.** Any artifact where the solver beats
  the current live box, gated and submitted. (subset-sum is alexey's
  lane as of 14:30Z — offer them the tool rather than compete.)
- **M3 — L1 room compiler**: block-graph -> serpentine room, with
  `(nop n)` as *prescribed-length* padding (PCB meander trick), which is
  what makes timed machines compilable instead of hand-only. Codex's
  `lane.py` is the seed; its known gap is nested arms + label/goto.
- **M4 — L2 peepholes** on the block graph (dead-heading elision, loop
  folding onto turn rows, verdict-rides-relay).

## 5. Non-goals / honesty

- Not attempting L3 automatically. Machine co-design stays human.
- Not replacing the hand pipeline before freeze. The solver has to earn
  each submission through the same gates.
- If M1 loses to hand on the benchmark, that is a result worth
  publishing in the repo, not a failure to hide.

## 6. Build plan after M1 (written 2026-07-26 15:55Z, 18h to freeze)

M1 is done: the pipeline emits machines that judge correctly. Its
measured blocker is that **ports are pinned to their original wall**, so
better placements cannot be routed (plotter 125x125 placed, unroutable;
matmul's ports are 28 South / 10 North / ZERO east-west, so every pipe
fights for vertical channels).

### Which ports are actually free — measured

A room's `s`/`r` bindings are decided by Manhattan distance from the man
to each of THAT ROOM's port cells, tie-broken by absolute coordinates.
So a room with **at most one outgoing and at most one incoming pipe has
no ambiguity at all**: its ports may be moved to any wall, any offset,
and no binding can change. Only multi-port rooms need care.

| artifact | rooms | FREE (<=1 out, <=1 in) | constrained |
|---|---|---|---|
| plotter_05 | 14 | **8** | 6 |
| matmul_03 | 12 | **11** | 1 |
| tcp_08 | 6 | **4** | 2 |

matmul is 11/12 free — nearly the whole instance is unconstrained, which
is why it is the right first target for M2.

### M2 — port assignment as a solver variable  [contest value]
Let the model choose (side, offset) per connection endpoint. For FREE
rooms this is unconstrained. For CONSTRAINED rooms, either keep the port
pinned (safe, trivial) or allow movement and re-verify every `s`/`r`
against `ir_export.machine_ir`; a role diff rejects the placement.
Success = a routable placement strictly better than the live box on
matmul or plotter, gated and submitted.

### M2b — `layout_gate.py`  [must land with M2]
The checks are currently inlined in ad-hoc scripts. As a module:
parse; `server_compat.validate_layout`; binding role diff vs the ORIGINAL
artifact (0 diffs); judge equality on all public cases; and — proven
necessary today — **a pipe-length multiset diff**, because a shorter
storage pipe deadlocks a ring machine with no other symptom (snake's
squeeze passed 5/5 while failing at snake-length 68).

### M3 — L1 room compiler  [the general-solver shot]
block-graph -> serpentine room. Straight-line code is near-trivial and
already proven by hand (hello-world swept fold widths). The value is
branches (arms as sub-serpentines with a merge) and `(nop n)` as
PRESCRIBED-LENGTH padding — the PCB meander trick — which is what makes
timing-sensitive machines compilable instead of hand-only. Seed:
Codex's `lane.py`; its known gap is nested arms and label/goto.

Sequencing: M2+M2b together (one agent, coupled), M3 independently
(different files, no overlap). M4 peepholes stay queued.
