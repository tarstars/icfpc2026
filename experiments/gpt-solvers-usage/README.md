# Solver usage: exact macro floorplanning

This experiment is the first executable slice of the repository's
solver-assisted layout plans. It does **not** try to synthesize a whole
Littleman program. It keeps an existing architecture and its room bodies fixed,
then asks an exact mixed-integer solver for the smallest square envelope that
can still satisfy necessary endpoint and pipe-length constraints.

The first benchmark is the preserved five-room TCP (`Packet Reassembly`)
architecture from `littleman.alexey_tcp_recovered`.

## Why this slice

The contest footprint is `max(width, height)^2`, not rectangular area. For a
fixed process network, integer floorplanning is therefore a natural exact
solver task. Routing and behavior remain in an external oracle loop; a
floorplanner should not pretend that Manhattan distance alone proves a legal
`.man`.

SciPy/HiGHS is used only inside this experiment. No project dependency or lock
file is changed. The model can later be ported to CP-SAT if that backend proves
more convenient for optional component variants and routing decisions.

## Run

```bash
cd experiments/gpt-solvers-usage
python3 -m pip install -r requirements.txt
python3 floorplan_milp.py \
  tcp_room_instance.json \
  --output /tmp/tcp_room_solution.json \
  --time-limit 120
python3 -m unittest -v test_floorplan_milp.py
```

## Model

The MILP uses integer room origins and one integer square side. It enforces:

- fixed-orientation rectangular rooms inside the square;
- pairwise room non-overlap;
- declared pipe endpoints one cell outside non-corner wall cells;
- endpoint cells outside unrelated rooms and away from their non-corner wall
  attachment cells;
- distinct endpoint cells;
- for every net, endpoint Manhattan distance plus one no larger than the
  preserved inclusive pipe-cell count.

The objective is the square side itself. HiGHS must return success with a zero
MIP gap; time-limited feasible answers are rejected rather than described as
optimal.

## TCP result

The preserved 38x38 room placement satisfies this model. The exact optimum is:

```text
35x35, objective 35, MIP gap 0.0
```

The solve took about 1.08 seconds in the development environment. Five focused
unit tests, including a regression of the preserved 38-square placement, pass.
The checked-in result is deterministic and stored in `tcp_room_solution.json`.

If a legal route with unchanged dynamic behavior exists at 35x35, the
footprint multiplier becomes `1225 / 1444 = 0.848338`, a 15.17% reduction. This
is a potential, not a candidate score.

An earlier rectangle-plus-distance model returned 33x33 but placed endpoints
on or beside unrelated room walls. That placement was rejected, and endpoint
obstacle constraints were added before publishing this checkpoint.

## What is not proved yet

The 35-square result is a rigorous optimum only for the recorded macro model.
It does not prove:

- six mutually disjoint orthogonal pipe routes exist;
- every route obeys first/last arrow direction and minimum length;
- intermediate cells avoid accidental room-wall grazing;
- exact capacity or timing-sensitive route lengths are preserved;
- nearest-pipe instruction bindings remain unchanged;
- `Machine.parse`, `server_compat`, or the TCP boundary judge accepts a rendered
  program.

The next checkpoint is an exact or backtracking grid router for the 35-square
placement, followed by the repository's existing parser, binding, compatibility,
and judge gates. If 35 is unroutable, the search should enumerate 36- and
37-square placements instead of weakening legality constraints.
