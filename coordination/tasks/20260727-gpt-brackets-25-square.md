# 20260727-gpt-brackets-25-square: fold terminal paths into a 25x25 candidate

- Status: active
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Problem: `brackets`
- Base main commit: `e6ed1423a7fb0cda17d1f3db79e82e8831b08244`
- Branch: `agent/gpt-solvers-usage`
- Progress lease: 15 minutes without concrete evidence
- Created UTC: `2026-07-27T05:34:01Z`
- Last updated UTC: `2026-07-27T05:34:01Z`

## Outcome

Build and preserve a 25x25 Brackets `.man` by selecting two further finite room
variants, validate it at least as strongly as the 26-square lineage, and hand it
to Codex without performing platform submission.

## Exclusive write set

- `src/littleman/gpt_brackets_25.py`
- `tests/test_gpt_brackets_25.py`
- `submissions/brackets/gpt_brackets_14.man`
- `experiments/gpt-solvers-usage/gpt_brackets_14.man`
- `experiments/gpt-solvers-usage/gpt_brackets_14-evidence.json`
- `reports/2026-07-27-gpt-brackets-25-square.md`
- `reports/2026-07-27-gpt-solvers-usage.md`
- `coordination/tasks/20260727-gpt-brackets-25-square.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`

## Shared read-only paths

- all `brackets_11`, `gpt_brackets_12`, and `gpt_brackets_13` artifacts,
  builders, tests, and evidence;
- existing Brackets catalogs and submission responses;
- parser, simulator, compatibility, API, package, lock, and policy files;
- all peer coordination namespaces.

## Do not touch

- `main`;
- existing immutable `.man` files;
- existing variant catalogs or submission responses;
- contest state.

## Candidate design

- CLOSE: route the empty-stack output sequence vertically at relative column 21
  and share the existing row-5 halt, reducing its outer width 24 -> 23.
- OPEN: move startup into row 5 and join the existing row-7 return, reducing its
  outer height 10 -> 9.
- route OPEN-to-CLASSIFY through newly freed global column 24, reducing the long
  transport pipe 44 -> 42 cells.

## Acceptance checks

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_25.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_14.man brackets
```

Expected local properties:

```text
25x25, footprint 625
SHA-256 9aa12829131b7bd9c4771b4bbfd49eec9fe83374a01fee91227d58ca142b0875
pipes [2, 2, 2, 42, 13, 2]
public 9/9
public ticks [249, 61, 109, 73, 146, 380, 136, 136, 2083]
local score 234236.1111111111
```

## Contest authority

GPT may create and push branch candidates but may not submit. Codex or the
current submission controller decides after freshness and independent gates.
