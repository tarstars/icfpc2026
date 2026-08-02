# Task 20260802-chatgpt1-io-pipe-counts

- Status: complete; handoff ready
- Owner: chatgpt_1
- Reviewer/integrator: repository maintainer
- Branch: `agent/chatgpt-1-io-pipe-counts`
- Stacked base: `agent/chatgpt-1-server-loader-validation` at `ecb7c1eb6a57cd4e57d0c714ca3415f1d2aaae57`
- Completed UTC: 2026-08-02T11:44:00Z

## Outcome

Fix the known false positives in `server_compat.validate_io_pipe_counts`:

- `submissions/matmul/matmul_05.man` and `matmul_06.man` are organizer-accepted and pass all public cases, but the old adjacency heuristic rejected them;
- `submissions/reverse-a-list/reverse_03.man` remains rejected for the preserved organizer error: the input room has more than one outgoing pipe.

The corrected check counts outward-pointing arrowheads immediately outside an input-room border. It does not count unrelated pipe body cells that merely run alongside the wall.

## Exclusive write set

- `src/littleman/server_compat.py`
- `tests/test_server_compat.py` (expected error wording only)
- `tests/test_server_compat_io_pipes.py`
- `reports/2026-08-02-chatgpt1-io-pipe-counts.md`
- `coordination/status/chatgpt_1.md`
- `coordination/messages/chatgpt_1/20260802T*-20260802-chatgpt1-io-pipe-counts-*.md`
- this task record

## Acceptance results

1. PASS — `validate_io_pipe_counts` accepts `matmul_05.man` and `matmul_06.man`.
2. PASS — it rejects `reverse_03.man` and reports two outward starts at `(7, 1)` and `(7, 2)`.
3. COVERED — the existing accepted-artifact corpus regression remains and will populate from preserved submission responses in a full checkout.
4. PASS — `parse_server_compatible` and `validate_layout` call the corrected check.
5. PASS — the consolidated loader regression expects the corrected diagnostic.
6. PASS — no contest-side mutation and no integration into `main` by chatgpt_1.

Validation in this runtime: exact changed files compiled and matched their Git blob hashes; the focused geometry/test harness reported `4 passed, 1 skipped`. The skip was the dynamic accepted-submission corpus absent from the temporary focused tree. Full repository pytest remains a reviewer check because direct GitHub checkout is unavailable in this runtime.
