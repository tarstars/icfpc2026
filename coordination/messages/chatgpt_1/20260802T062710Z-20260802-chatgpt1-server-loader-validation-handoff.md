# Handoff: server-compatible loader validation

- Task: `20260802-chatgpt1-server-loader-validation`
- Sender: chatgpt_1
- Timestamp UTC: 2026-08-02T06:27:10Z
- Branch: `agent/chatgpt-1-server-loader-validation`
- Handoff commit: `2ac7101627d236c1a0e6c1e7013c336801418b8b`
- Base: `main` at `5e5b60d812f12d95023432699f187f2f9cf0fe8e`

## Diff scope

- `src/littleman/server_compat.py`
  - adds `MIN_PIPE_CELLS`, `validate_pipe_lengths`, and `parse_server_compatible`;
  - parses once and applies the minimum-length, input-wall-adjacency, and shared-wall rules;
  - keeps the existing public APIs and makes `validate_layout` delegate to the consolidated gate.
- `src/littleman/alexey_pipecheck.py`
  - documentation-only synchronization; its tolerant legacy behavior remains unchanged.
- `tests/test_server_compat.py`
  - rejects all four preserved server-invalid layouts through both strict entry points;
  - accepts `reverse_01`, `sort_06`, and `triangle_04`.
- `tests/test_server_compat_pipe_lengths.py`
  - pins the exact one-cell-pipe counts and fixed successors.
- `reports/2026-08-02-chatgpt1-server-loader-validation.md`
  - design, evidence, commands, limitations, and observed geometry.

## Validation

Exact branch blob contents were compiled with `python3 -m py_compile`.

A focused harness using the current `sim.py` room/pipe discovery routines and the preserved artifact texts ran:

```text
PYTHONPATH=/tmp/lmcheck pytest -q \
    tests/test_server_compat.py -k 'not final_wall' \
    tests/test_server_compat_pipe_lengths.py

13 passed, 1 deselected in 0.04s
```

Observed rejections:

- `reverse_02`: 3 one-cell pipes;
- `reverse_03`: 2 pipes against the input-room wall;
- `sort_05`: 1 one-cell pipe;
- `triangle_03`: 3 shared wall cells.

Observed accepted successor pipe lengths:

- `reverse_01`: `[2, 2, 2, 17]`;
- `sort_06`: `[2, 3, 7, 17]`;
- `triangle_04`: `[2, 2]`.

## Unverified / reviewer checks

This runtime could not clone the repository because `github.com` DNS resolution is unavailable. No GitHub Actions run exists for the branch. Before integration, run:

```text
uv run pytest -p no:xdist tests/test_server_compat.py \
    tests/test_server_compat_io_pipes.py \
    tests/test_server_compat_pipe_lengths.py
uv run pytest
```

The existing final-wall-step test was not executed in the focused harness; its judge path is unchanged after the new layout gate.

## Integration order

The branch is current with its base and is not behind `main` at handoff. Review the compatibility module and focused tests, run the commands above, then integrate the branch through the normal maintainer workflow. No contest-side action is required.

## External mutations and caveats

No contest API or submission mutation occurred.

During branch setup, chatgpt_1 accidentally created a placeholder task file on `main` in commit `a76ad66df1ec6c938731867f424fe94ff8604c66`, then immediately deleted it in `5e5b60d812f12d95023432699f187f2f9cf0fe8e`. The `main` tree is unchanged, but the two net-zero commits remain in history; no force rewrite was attempted.

The task write set is released after this handoff.
