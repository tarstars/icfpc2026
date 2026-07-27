# Handoff: experimental Grade Book reverse-ack candidate

- From: codex_3
- To: claude
- CC: chatgpt_1, chatgpt_2, gpt, alexey, codex
- Created UTC: 2026-07-27T10:09:00Z
- Task: `20260727-gradebook-rank-step`
- Branch: `agent/codex_3`
- Payload commit: `a6cc565f80cd3b7e74a6cbbaea18b6d3e8452cb8`
- Base used for implementation: `ad0324bb6ef915c195a1cde9a3115689131c99a2`
- Current main inspected: `80da1326b72b55e794afd7c10d453735fb8066f4`
- Requires acknowledgement: yes

## Diff scope

The payload adds only owner-specific coordination records, an isolated
Grade Book experiment, one focused test, and one report. It does not modify
shared solver, simulator, catalog, live-result, or submission files.

## Candidate idea

The generator reverses the physical subject-worker order while preserving the
logical acknowledgement order, brings the final acknowledgement return next to
the parser, and adds an explicit result-collector confirmation pipe. The
confirmation is intended to prevent one output-producing operation from
overtaking another after the routing reduction.

## Validation status

This is an **experimental handoff, not a submission-ready artifact**. The
connector runtime could write the branch but could not execute the repository,
organizer WASM, or contest API. Numerical constants in the focused test are
unverified targets and must not be reported as measurements until reproduced.

Required reviewer commands are recorded in
`reports/2026-07-27-codex3-gradebook-rank-step.md`; the decisive command is:

```sh
uv run python scripts/subdb.py compare \
  submissions/gradebook/codex3_gradebook_06.man gradebook
```

If generation or any assertion fails, preserve the branch as a negative
experiment and do not submit. If it passes, preserve the exact generated
`.man`, SHA-256, same-judge comparison, and organizer-WASM result before any
contest mutation.

## Freshness and integration

The branch is 212 commits behind current `main`, but its changed paths are all
new and non-overlapping. The Grade Book source dependency is still unchanged on
current main: `src/littleman/gradebook.py` blob
`699608b38cc4516fde774e60450f995eda2ae6fe`. Prefer cherry-picking the payload
commit or merging the draft PR after review rather than force-moving either
branch.

No external mutation occurred.