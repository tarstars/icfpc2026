# 20260727-gpt-brackets-26-square: immutable 26x26 Brackets candidate

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
- Last updated UTC: `2026-07-27T05:15:01Z`

## Outcome

Produce a new immutable 26x26 `.man` derived from accepted `brackets_11`, with
an exact generator, structural gates, public/directed/fuzz evidence, and a
handoff that lets Codex or another submission controller decide whether to
probe the platform.

## Exclusive write set

- `src/littleman/gpt_brackets_26.py`
- `tests/test_gpt_brackets_26.py`
- `submissions/brackets/gpt_brackets_12.man`
- `experiments/gpt-solvers-usage/gpt_brackets_12.man`
- `experiments/gpt-solvers-usage/gpt_brackets_12-evidence.json`
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

- immutable `submissions/brackets/gpt_brackets_12.man`;
- deterministic builder reproducing it byte-for-byte;
- focused repository tests and exact public tick vector;
- directed and seeded fuzz evidence;
- structural comparison against `brackets_11`;
- submission-neutral handoff to Codex.

## Acceptance checks

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_26.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_12.man brackets
```

Expected properties:

- strict dimensions `26x26`, footprint `676`;
- exactly five rooms, six pipes, three men;
- pipe lengths `[2, 2, 2, 13, 47, 2]` in parser order;
- generator/artifact SHA-256
  `8cc306772304f39e21f6b140586844419b55103cec575834228dc9350bc2c4a5`;
- all nine repository cases at ticks
  `[248, 60, 108, 72, 150, 384, 140, 140, 2086]`;
- local score `254476.44444444444` versus `276615.0` for `brackets_11`;
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
