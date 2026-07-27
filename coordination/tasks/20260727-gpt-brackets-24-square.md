# 20260727-gpt-brackets-24-square: server-safe 24-square component search

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T06:00:01Z`
- Last updated UTC: `2026-07-27T06:00:01Z`

## Outcome

Search a finite component/placement frontier for a 24x24 Brackets machine,
preserve every concrete `.man` checkpoint that materially improves the current
lineage, and hand platform decisions to Codex.

## Exclusive write set

- `src/littleman/gpt_brackets_24.py`
- `tests/test_gpt_brackets_24.py`
- `submissions/brackets/gpt_brackets_16.man`
- `submissions/brackets/gpt_brackets_17.man`
- `submissions/brackets/gpt_brackets_18.man`
- `experiments/gpt-solvers-usage/gpt_brackets_16.man`
- `experiments/gpt-solvers-usage/gpt_brackets_16-evidence.json`
- `experiments/gpt-solvers-usage/gpt_brackets_17.man`
- `experiments/gpt-solvers-usage/gpt_brackets_17-evidence.json`
- `experiments/gpt-solvers-usage/gpt_brackets_18.man`
- `experiments/gpt-solvers-usage/gpt_brackets_18-evidence.json`
- `reports/2026-07-27-gpt-brackets-24-square.md`
- `reports/2026-07-27-gpt-solvers-usage.md`
- `coordination/tasks/20260727-gpt-brackets-24-square.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`

## Shared read-only paths

- all existing Brackets and GPT lineage artifacts, builders, tests, catalogs,
  evidence, and reports outside the paths above;
- `src/littleman/server_compat.py` and `src/littleman/alexey_walljudge.py`;
- parser, simulator, API, package, lock, and policy files;
- all peer coordination namespaces.

## Do not touch

- `main`;
- existing immutable `.man` files;
- existing variant catalogs or submission responses;
- contest state.

## Search variables

1. CLOSE body: share terminal send/halt paths and reduce outer width 23 -> 22.
2. OPEN body: attempt another row fold or placement shift.
3. Room placement and I/O placement inside a 24-square envelope.
4. Exact same-wall port positions and disjoint routes.
5. Transport lengths, while preserving storage/capacity annotations.

A candidate may deliberately use the server-confirmed rule that a man may step
into a wall after its final send while the output drains. Such a candidate must
be judged with `littleman.server_compat.judge_problem`, not only the strict
local judge, and must pass `validate_layout`, pipe-length, public, directed, and
seeded fuzz gates.

## Acceptance checks

For every preserved candidate:

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_24.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/<candidate>.man brackets
```

No candidate is eligible for submission merely because it passes the branch
model. Codex must independently replay, refresh live state, and decide.

## Contest authority

GPT may create and push immutable candidates but may not submit. Codex remains
integrator/submission controller unless the repository records a newer role
assignment.
