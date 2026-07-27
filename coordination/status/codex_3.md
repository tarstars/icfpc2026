# codex_3 Status

- Updated UTC: 2026-07-27T10:36:13Z
- State: HANDOFF_READY
- Role: Grade Book score improver
- Authoritative assignment: `coordination/ASSIGNMENTS.md`
- Current task: `20260727-gradebook-extra-fold-search`
- Branch: `agent/codex_3-gradebook-v2`
- Base/current main: `b240cc2d67a125a31cc50c167283b7049de47210`
- Saved payload commit: `33e0d87c16f0ff64fa6048103d388cd0340647c7`
- Handoff message commit: `c38ccf584b406b716d59b54f8d9c829f6fd811f9`
- Previous result: `codex3_gradebook_06` is live 20/20 at 379x315, score
  `34,760,655,166.75`, a 1.355x improvement over `gradebook_05`
- Write set: own task/status/messages,
  `experiments/codex_3-gradebook-v2/`, one focused test,
  `submissions/gradebook/codex3_gradebook_07.man`, and one report
- Shared read-only: live Grade Book artifact/response, first codex_3 generator
  and stress harness, current judges, `subdb`, and the authoritative assignment
- Saved search 1: `search_extra_folds.py` beam-searches additional parser/worker
  staircase folds while requiring exact 379x315 geometry and the exact ordered
  31-pipe length tuple
- Saved search 2: `search_shape.py` tries sparse-column shaves using same-run
  instruction slides, `room_shrink.verify`, no pipe shortening, public 7/7,
  randomized stress, and all 256 ordered output-transition pairs
- Saved report: `reports/2026-07-27-codex3-gradebook-v2.md`
- Immutable handoff:
  `coordination/messages/codex_3/20260727T103613Z-20260727-gradebook-extra-fold-search-handoff.md`
- Last verified repository state: branch was synchronized with current `main`,
  ahead only and zero commits behind before the handoff commits
- Numerical status: no `codex3_gradebook_07.man` and no additional score are
  claimed; this runtime cannot execute the checkout or organizers' WASM
- Next checkpoint: Claude runs the deterministic commands and acknowledges with
  either an exact candidate plus measurements or the negative frontier
- Blockers: execution and contest submission are unavailable in this runtime
- Submission controller: no; no contest mutation performed
