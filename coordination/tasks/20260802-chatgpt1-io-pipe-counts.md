# Task 20260802-chatgpt1-io-pipe-counts

- Status: active
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Branch: `agent/chatgpt-1-io-pipe-counts`
- Stacked base: `agent/chatgpt-1-server-loader-validation` at `ecb7c1eb6a57cd4e57d0c714ca3415f1d2aaae57`

## Outcome

Fix the known false positives in `server_compat.validate_io_pipe_counts`:

- `submissions/matmul/matmul_05.man` and `matmul_06.man` are organizer-accepted and pass all public cases, but the current adjacency heuristic rejects them;
- `submissions/reverse-a-list/reverse_03.man` must remain rejected for the preserved organizer error: the input room has more than one outgoing pipe.

The evidence suggests the organizer counts outward-pointing pipe starts immediately outside an input-room border. It does not count every body cell of an unrelated pipe that merely runs alongside the wall. The current heuristic conflates those cases.

## Exclusive write set

- `src/littleman/server_compat.py`
- `tests/test_server_compat_io_pipes.py`
- `reports/2026-08-02-chatgpt1-io-pipe-counts.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-io-pipe-counts-*.md`
- this task record

## Acceptance checks

1. `validate_io_pipe_counts` accepts `matmul_05.man` and `matmul_06.man`.
2. It still rejects `reverse_03.man` and reports two outward starts against its input room.
3. The existing accepted-artifact corpus remains accepted.
4. `parse_server_compatible` and `validate_layout` inherit the corrected behavior.
5. No contest-side mutation and no integration into `main` by chatgpt_1.
