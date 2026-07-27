# Solver usage: exact physical-synthesis subproblems

This experiment turns the repository's solver architecture notes into executable
vertical slices. It deliberately does **not** model the whole Littleman language
inside one optimizer. Exact solvers handle discrete physical choices; the real
parser, compatibility checks, resolution audit, router, and judge remain the
promotion oracle.

SciPy/HiGHS is used only inside this experiment. No project dependency or lock
file is changed.

## 1. Macro floorplanning benchmark

`floorplan_milp.py` keeps room bodies and port offsets fixed and minimizes the
bounding-square side. Its first benchmark is the recovered five-room TCP
architecture.

```bash
cd experiments/gpt-solvers-usage
python3 -m pip install -r requirements.txt
python3 floorplan_milp.py \
  tcp_room_instance.json \
  --output /tmp/tcp_room_solution.json \
  --time-limit 120
python3 -m unittest -v test_floorplan_milp.py
```

The preserved 38x38 placement satisfies the model; HiGHS proves a 35x35 macro
optimum with MIP gap 0.0. This remains a useful regression and lower-bound
exercise, but it is **not a live scoring target**: the current TCP lineage has
already reached 30x30.

The benchmark also established an important negative result. A weaker
rectangle-plus-distance formulation returned 33x33, but its endpoints occupied
or grazed unrelated room walls. That result was discarded and endpoint-obstacle
constraints were added. A clean MILP optimum is not a `.man` validity proof.

## 2. Joint port assignment

`port_assignment_milp.py` addresses the fixed-port limitation identified by
Codex and Claude. For fixed room placements it chooses one exterior cell for
each logical pipe endpoint while preserving the simulator's exact nearest-pipe
rule:

```text
(Manhattan distance, endpoint row, endpoint column)
```

It enforces:

- one candidate cell per endpoint;
- distinct endpoint cells;
- exact `s`/`r`/`q` binding preservation, including reading-order ties;
- source/sink direction and pipe-length bounds;
- a weighted Manhattan pipe-length objective;
- zero-gap optimality proof from HiGHS, followed by a deterministic secondary
  objective that minimizes changed endpoints and displacement.

Set-valued `S`/`R`/`U` operations need no positional constraint while the
incident pipe set remains unchanged.

Run the measured Brackets replay and certificate:

```bash
python3 port_assignment_milp.py \
  brackets_10_port_instance.json \
  --output /tmp/brackets_10_port_solution.json
python3 port_assignment_milp.py \
  brackets_11_port_instance.json \
  --output /tmp/brackets_11_port_solution.json
python3 -m unittest -v test_port_assignment_milp.py
```

### Brackets result

In `brackets_10`, the two room0<->room2 gap pipes were five cells each. The
exact port model proves their joint lower bound is four cells total: two legal
pipes of two cells each. This replays the six-cell reduction that produced the
live `brackets_11` result.

For `brackets_11`, the same model returns objective four with the incumbent
ports unchanged. Therefore those two pipes are now at the server's absolute
minimum. More endpoint-only work on that gap cannot improve score.

This is the first solver slice in the repository that both:

1. automatically recovers a known measured optimization; and
2. certifies that the corresponding local search direction is exhausted.

### Machine-IR adapter

The same tool accepts JSON from `littleman.ir_export.machine_ir`:

```bash
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from littleman.ir_export import machine_ir

text = Path("submissions/brackets/brackets_10.man").read_text()
Path("/tmp/brackets-ir.json").write_text(json.dumps(machine_ir(text), indent=2))
PY

python3 experiments/gpt-solvers-usage/port_assignment_milp.py \
  /tmp/brackets-ir.json --machine-ir \
  --movable-pipes 0,1 --transport-pipes 0,1
```

Movable endpoints stay on their incumbent wall. Pipes not listed as transport
are fixed in the objective and retain their current length cap for a later
exact-length router. The adapter derives nearest-pipe constraints directly from
the versioned resolution map rather than reimplementing the parser.

## Promotion boundary

Neither solver proves detailed routing. Before a placement or port assignment
becomes a candidate, a later stage must still establish:

- mutually disjoint orthogonal routes;
- legal first/last arrow directions and minimum two-cell pipes;
- no accidental foreign-wall grazing or phantom pipes;
- required capacity and timing lengths, informed by occupancy measurements;
- identical resolution map where required;
- `Machine.parse`, `server_compat`, focused adversaries, and exact judging.

## Next scoring-oriented solver step

The Brackets replay answers Alexey's message precisely: exterior port offsets
are now solver variables. It also shows the remaining barrier. `brackets_11` is
27x27 and the 25-column middle room pins the width; its two gap pipes are already
minimal. The next useful model must select among **interior landing-pad / room
implementation variants**, then feed those shapes and ports into the existing
floorplanner.

A validated 26x26 Brackets machine at unchanged ticks would multiply score by
`26^2 / 27^2 = 0.927298`, reducing the current 484,532.65 result to about
449,306. This is the first scoring hypothesis for the next solver milestone,
not a measured candidate.
