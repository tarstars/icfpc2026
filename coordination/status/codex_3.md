# codex_3 Status

- Updated UTC: 2026-07-27T10:12:00Z
- State: ACTIVE
- Role: Grade Book scoring solver
- Current task: `20260727-gradebook-submit-ready`
- Branch: `agent/codex_3-gradebook-submit-ready`
- Head: `b41f17330609d083857e507cf0343015b717b951`
- Base main: `7e658b4d8a9e5fda14fbabe422cc023609455c8f`
- Write set: own task/status/messages,
  `experiments/codex_3-gradebook-submit/`,
  `tests/test_codex3_gradebook_submit_ready.py`,
  `submissions/gradebook/codex3_gradebook_06.man`, and
  `reports/2026-07-27-codex3-gradebook-submit-ready.md`
- Shared read-only: draft PR #3, existing Grade Book artifacts and sources,
  simulators, preflight, subdb, and organizer-WASM wrapper
- Coordinator target: live `gradebook_05` 382x307, score 47,115,780,603.6;
  rank 60 threshold 46,112,231,167, requiring 1.022x
- Starting point: experimental reverse-worker-order/result-confirmation design
  at PR #3; none of its numerical assertions are accepted until reproduced
- Plan: port the experiment onto current main, remove unverified assumptions,
  obtain an exact generated artifact, and hand it to Claude for same-judge and
  organizer-WASM execution; repair only within the declared write set
- Next checkpoint: inspectable current-main generator or exact blocker
- Blockers: this connector runtime cannot execute the repository; validation
  must be performed by Claude's local worktree, so handoff evidence will clearly
  separate static construction from measured results
- Submission controller: no; no contest mutation permitted