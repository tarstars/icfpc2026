# 20260727-gpt-solvers-floorplan: solver-assisted TCP layout vertical slice

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `tcp` / physical-synthesis tooling
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T04:22:00Z`
- Last updated UTC: `2026-07-27T04:22:00Z`

## Outcome

Build an exact, reproducible macro-floorplanning slice for a known-good TCP
architecture, then determine whether the best proven square placement can pass
a detailed routing and repository-oracle gate.

## Exclusive write set

- `coordination/tasks/20260727-gpt-solvers-floorplan.md`
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
- `src/littleman/alexey_tcp_recovered.py`
- `src/littleman/ir_export.py`
- `src/littleman/room_ports.py`
- `submissions/tcp/`
- `tests/test_tcp_recovered.py`

## Do not touch

- `main`
- existing `.man` files, catalogs, or submission responses
- shared simulator, parser, API, package, or lock files
- Alexey, Claude, or Codex status and message namespaces
- contest state

## Deliverables

- exact small-instance floorplanner and JSON CLI;
- checked-in TCP macro instance and deterministic optimal solution;
- focused regression tests, including the preserved 38-square layout;
- report distinguishing proved model facts from routing and score projections;
- next-stage route witness or concise routing counterexample.

## Acceptance checks

- From `experiments/gpt-solvers-usage`, `python3 -m py_compile floorplan_milp.py test_floorplan_milp.py` succeeds.
- From the same directory, `python3 floorplan_milp.py tcp_room_instance.json --output /tmp/tcp_room_solution.json --time-limit 120` returns side 35 and MIP gap 0.0.
- From the same directory, `python3 -m unittest -v test_floorplan_milp.py` passes all focused tests.
- The preserved TCP 38-square placement satisfies the same model.
- No score, `.man` validity, or routability claim is made before repository
  parser, binding, compatibility, and judge gates pass.

## Contest authority

Read-only API access: not needed for this tooling checkpoint.

Contest submission: forbidden unless the user separately authorizes the exact
candidate and the submission controller accepts the handoff.

## Handoff

Push a reproducible checkpoint with the exact solver result and limitations.
After the routing gate, hand off either a rendered candidate plus exact oracle
commands, or a counterexample and the next enumerated placement target, to
Codex for review and integration.
