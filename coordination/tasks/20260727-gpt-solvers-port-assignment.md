# 20260727-gpt-solvers-port-assignment: exact port variables and Brackets replay

- Status: handoff-ready
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets` / reusable physical-synthesis tooling
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T04:48:00Z`
- Last updated UTC: `2026-07-27T04:57:00Z`

## Outcome

Remove the solver stack's fixed-port limitation with an exact joint endpoint
model, automatically replay one known live optimization, and identify the next
score-positive variable rather than continuing an obsolete benchmark.

## Exclusive write set

- `coordination/tasks/20260727-gpt-solvers-port-assignment.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`
- `experiments/gpt-solvers-usage/`
- `reports/2026-07-27-gpt-solvers-usage.md`

## Shared read-only paths

- `docs/architecture/claude_32_solver_stack.md`
- `docs/architecture/codex_05_program_synthesis.md`
- `docs/architecture/codex_07_roadmap_and_questions.md`
- `docs/synthesis-stack.md`
- `docs/REVOLUTIONARY_OPTIMIZATION_ROADMAP.md`
- `docs/alexey-footprint-playbook.md`
- `src/littleman/ir_export.py`
- `src/littleman/room_ports.py`
- `src/littleman/alexey_resolveaudit.py`
- `submissions/brackets/brackets_10.man`
- `submissions/brackets/brackets_11.man`
- all existing solution artifacts and catalogs

## Do not touch

- `main`
- existing `.man` files, catalogs, or submission responses
- shared simulator, parser, API, package, or lock files
- Alexey, Claude, or Codex status and message namespaces
- contest state

## Deliverables

- exact joint port-assignment MILP and JSON CLI;
- adapter from versioned `machine_ir` resolution maps;
- deterministic Brackets 10 replay fixture and solution;
- Brackets 11 endpoint-only lower-bound certificate;
- focused tests for reading-order ties, IR conversion, replay, and validation;
- report naming the next score-positive solver variable.

## Acceptance checks

From `experiments/gpt-solvers-usage`:

```bash
python3 -m py_compile port_assignment_milp.py test_port_assignment_milp.py
python3 port_assignment_milp.py brackets_10_port_instance.json \
  --output /tmp/brackets_10_port_solution.json --time-limit 30
python3 port_assignment_milp.py brackets_11_port_instance.json \
  --output /tmp/brackets_11_port_solution.json --time-limit 30
python3 -m unittest -v test_port_assignment_milp.py
```

Verified properties:

- Brackets 10 weighted endpoint length is exactly `4`, down from `10`;
- both selected gap nets have two cells;
- Brackets 11 also has exact objective `4` with its incumbent ports unchanged;
- HiGHS reports MIP gap `0.0`;
- five focused tests pass;
- no `.man`, route, server-score, or behavior claim is made from endpoint
  optimization alone.

## Contest authority

Read-only API access: not needed for this tooling checkpoint.

Contest submission: forbidden unless the user separately authorizes the exact
candidate and the submission controller accepts the handoff.

## Handoff

Implementation commit `2c432bcbe8d5c339b082e7e023815f6ed2212ccf` is pushed
on `agent/gpt-solvers-usage`. Codex should review the IR adapter, exact
nearest-pipe incompatibility constraints, and the Brackets replay fixtures.
The next score-positive task is a finite Brackets middle-room landing-pad/body
frontier with one-hot implementation selection; it requires a fresh claim and
write set before shared source or solution paths are touched.
