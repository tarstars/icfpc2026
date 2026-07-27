# codex_3 Status

- Updated UTC: 2026-07-27T10:32:00Z
- State: ACTIVE
- Role: Grade Book score improver
- Authoritative assignment: `coordination/ASSIGNMENTS.md`
- Current task: `20260727-gradebook-extra-fold-search`
- Branch: `agent/codex_3-gradebook-v2`
- Head: `d76368f16d648ccbac4ef421ff6791c343cc6432`
- Base main: `b240cc2d67a125a31cc50c167283b7049de47210`
- Previous result: `codex3_gradebook_06` is live 20/20 at 379x315, score
  `34,760,655,166.75`, a 1.355x improvement over `gradebook_05`
- Write set: own task/status/messages,
  `experiments/codex_3-gradebook-v2/`, one focused test,
  `submissions/gradebook/codex3_gradebook_07.man`, and one report
- Shared read-only: live Grade Book artifact/response, first codex_3 generator
  and stress harness, current judges, `subdb`, and the authoritative assignment
- Reproducible checkpoint 1: `search_extra_folds.py` beam-searches additional
  parser/worker staircase folds while requiring exact 379x315 geometry and the
  exact ordered 31-pipe length tuple
- Reproducible checkpoint 2: `search_shape.py` tries sparse-column shaves using
  same-run instruction slides, `room_shrink.verify`, ordered no-shortening,
  public 7/7, randomized stress, and all 256 output-transition pairs
- Next checkpoint: Claude executes the two deterministic commands and either
  returns a candidate SHA/score or a negative frontier; codex_3 will immediately
  package the result for handoff or retarget
- Blockers: this connector runtime cannot execute the checkout or organizer
  WASM, so no numerical improvement is claimed on this branch yet
- Submission controller: no; no contest mutation permitted