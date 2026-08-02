# Handoff: correct input-room pipe counting

- Task: `20260802-chatgpt1-io-pipe-counts`
- Sender: chatgpt_1
- Timestamp UTC: 2026-08-02T11:45:00Z
- Branch: `agent/chatgpt-1-io-pipe-counts`
- Handoff checkpoint: `488d9e520c6dad6d482cff497a8235c3c76eaed3`
- Stacked base: `agent/chatgpt-1-server-loader-validation` at `ecb7c1eb6a57cd4e57d0c714ca3415f1d2aaae57`

## Diff scope relative to the stacked base

- `src/littleman/server_compat.py`
  - replaces broad adjacent-pipe-cell counting with `_outward_pipe_starts`;
  - scans the raw grid one cell outside each input-room side;
  - counts only arrowheads pointing away from the corresponding border;
  - remains independent of parsed pipe ownership, which can hide a start through the parser's global `used` set.
- `tests/test_server_compat_io_pipes.py`
  - explicitly accepts organizer-approved `matmul_05.man` and `matmul_06.man`;
  - requires `reverse_03.man` to report two starts at `(7, 1)` and `(7, 2)`;
  - retains the accepted-submission corpus guard and `validate_layout` coverage.
- `tests/test_server_compat.py`
  - updates the consolidated `reverse_03` diagnostic expectation.
- `reports/2026-08-02-chatgpt1-io-pipe-counts.md`
  - records the evidence, root cause, implementation, validation, and integration dependency.

## Measured facts

- `reverse_03` input room: zero-based rows `8..10`, columns `0..2`; outward starts are exactly `(7, 1)` and `(7, 2)`.
- `matmul_05` and `matmul_06` have one true outward input start and several unrelated pipe body cells beside the input-room wall.
- The matmul variants catalog records organizer acceptance at 20/20 for both artifacts; the old adjacency heuristic was therefore a demonstrated false positive.

## Validation

The exact published Python files compiled and their local `git hash-object` values matched the GitHub branch blob hashes:

```text
src/littleman/server_compat.py       8348e23d85da062640a6b1f8bf932619250dad78
tests/test_server_compat_io_pipes.py 8f4415da2e66151bc0b03c98e02719fba42c4c5b
tests/test_server_compat.py          3e6d6209864e99ac6a84d2a96dd7daf6e7112f81
```

Focused geometry and pytest execution:

```text
reverse_03 rejected at starts (7,1),(7,2); matmul neighborhood accepted
4 passed, 1 skipped in 0.05s
```

The skip is the dynamic successful-submission corpus, absent from the temporary focused tree.

## Reviewer checks

A full checkout is unavailable in this runtime because direct `github.com` access cannot resolve. Before integration run:

```text
uv run pytest -p no:xdist tests/test_server_compat_io_pipes.py \
    tests/test_server_compat.py tests/test_server_compat_pipe_lengths.py
uv run pytest
```

## Integration order

This is a stacked handoff. Integrate or otherwise incorporate `agent/chatgpt-1-server-loader-validation` first, then review the C5-only diff from that branch to `agent/chatgpt-1-io-pipe-counts`. Alternatively review and integrate the combined stacked branch as one unit.

No contest API call or submission occurred. chatgpt_1 did not update `main`. The task write set is released.
