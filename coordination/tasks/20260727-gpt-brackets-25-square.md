# 20260727-gpt-brackets-25-square: fold terminal paths into 25x25 candidates

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
- Last updated UTC: `2026-07-27T05:48:00Z`

## Outcome

Build and preserve 25x25 Brackets `.man` candidates by selecting finite room
and endpoint variants, validate them at least as strongly as the 26-square
lineage, and hand the best result to Codex without performing platform
submission.

## Exclusive write set

- `src/littleman/gpt_brackets_25.py`
- `tests/test_gpt_brackets_25.py`
- `submissions/brackets/gpt_brackets_14.man`
- `submissions/brackets/gpt_brackets_15.man`
- `experiments/gpt-solvers-usage/gpt_brackets_14.man`
- `experiments/gpt-solvers-usage/gpt_brackets_14-evidence.json`
- `experiments/gpt-solvers-usage/gpt_brackets_15.man`
- `experiments/gpt-solvers-usage/gpt_brackets_15-evidence.json`
- `reports/2026-07-27-gpt-brackets-25-square.md`
- `reports/2026-07-27-gpt-solvers-usage.md`
- `coordination/tasks/20260727-gpt-brackets-25-square.md`
- `coordination/status/gpt.md`
- `coordination/messages/gpt/`

## Shared read-only paths

- all `brackets_11` and GPT 26-square artifacts, builders, tests, and evidence;
- existing Brackets catalogs and submission responses;
- parser, simulator, compatibility, API, package, lock, and policy files;
- all peer coordination namespaces.

## Do not touch

- `main`;
- existing immutable `.man` files;
- existing variant catalogs or submission responses;
- contest state.

## Candidate design

`gpt_brackets_14`:

- CLOSE shares a terminal halt to reduce outer width 24 -> 23;
- OPEN embeds startup into an existing row to reduce outer height 10 -> 9;
- long transport corridor moves column 25 -> 24, length 44 -> 42.

`gpt_brackets_15`:

- preserve every body and placement from 14;
- move the OPEN-to-CLOSE state source from global `(20,3)` to the highest legal
  left-wall cell `(17,3)`;
- route directly to `(11,0)`, reducing 13 -> 10 cells, the Manhattan minimum
  for the selected endpoints.

## Acceptance checks

```bash
PYTHONPATH=src uv run pytest -q -n 0 tests/test_gpt_brackets_25.py
PYTHONPATH=src uv run python scripts/preflight.py \
  submissions/brackets/gpt_brackets_15.man brackets
```

Expected best-candidate properties:

```text
25x25, footprint 625
SHA-256 826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605
pipes [2, 2, 2, 10, 42, 2]
public 9/9
public ticks [246, 58, 106, 70, 146, 380, 136, 136, 2082]
local score 233333.3333333333
```

## Contest authority

GPT may create and push branch candidates but may not submit. Codex or the
current submission controller decides after freshness and independent gates.
