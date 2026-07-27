# 20260727-gpt-brackets-26-square: immutable 26x26 Brackets candidates

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T05:15:01Z`
- Last updated UTC: `2026-07-27T05:25:00Z`

## Outcome

Produce immutable 26x26 `.man` successors to accepted `brackets_11`, with
exact generators, structural gates, public/directed/fuzz evidence, and a handoff
that lets Codex or another submission controller decide whether to use a
candidate on the platform.

## Exclusive write set

- `src/littleman/gpt_brackets_26.py`
- `tests/test_gpt_brackets_26.py`
- `submissions/brackets/gpt_brackets_12.man`
- `submissions/brackets/gpt_brackets_13.man`
- `experiments/gpt-solvers-usage/gpt_brackets_12.man`
- `experiments/gpt-solvers-usage/gpt_brackets_12-evidence.json`
- `experiments/gpt-solvers-usage/gpt_brackets_13.man`
- `experiments/gpt-solvers-usage/gpt_brackets_13-evidence.json`
- `experiments/gpt-solvers-usage/README.md`
- `reports/2026-07-27-gpt-brackets-26-square.md`
- `reports/2026-07-27-gpt-solvers-usage.md`
- `coordination/tasks/20260727-gpt-brackets-26-square.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`

## Shared read-only paths

- `submissions/brackets/brackets_11.man`
- `submissions/brackets/variants.json`
- `src/littleman/brackets_fast.py`
- `src/littleman/sim.py`
- `src/littleman/server_compat.py`
- `src/littleman/alexey_pipecheck.py`
- `src/littleman/alexey_resolveaudit.py`
- `data/small/problems/brackets.json`
- all peer coordination namespaces

## Do not touch

- `main`
- existing numbered or accepted `.man` artifacts
- existing variant catalogs or submission responses
- shared parser, simulator, package, lock, API, or policy files
- contest state

## Deliverables

- immutable `gpt_brackets_12.man` and its strictly better successor
  `gpt_brackets_13.man`;
- deterministic builder reproducing both byte-for-byte;
- focused repository tests and exact public tick vectors;
- directed and seeded fuzz evidence;
- structural/topology comparison against `brackets_11`;
- endpoint optimality note for the moved long transport pipe;
- submission-neutral handoff to Codex.

## Acceptance checks

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_26.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_13.man brackets
```

Expected `gpt_brackets_13` properties:

- strict dimensions `26x26`, footprint `676`;
- exactly five rooms, six pipes, three men;
- pipe lengths `[2, 2, 2, 44, 13, 2]` in parser order;
- generator/artifact SHA-256
  `c4f5449b830f72f5529e82aa7034d580956aa83baffd162e4a36ebb6219e4eed`;
- all nine repository cases at ticks
  `[248, 60, 108, 72, 147, 381, 137, 137, 2083]`;
- local score `253349.77777777778` versus `276615.0` for `brackets_11`;
- no platform submission from this task.

## Contest authority

Read-only API access: allowed if available to the integrator.

Contest submission: forbidden for GPT. Codex or the current submission
controller may decide after independently replaying all gates and refreshing
the exact live Brackets state.

## Handoff

Push exact files and evidence. The handoff must distinguish the locally
reconstructed simulator evidence from checks independently rerun in a repository
checkout. No server score may be projected as measured.
