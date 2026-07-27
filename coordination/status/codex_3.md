# codex_3 Status

- Updated UTC: 2026-07-27T10:20:00Z
- State: ACTIVE
- Role: Grade Book score improver
- Authoritative assignment: `coordination/ASSIGNMENTS.md`
- Current task: `20260727-gradebook-extra-fold-search`
- Branch: `agent/codex_3-gradebook-v2`
- Base main: `b240cc2d67a125a31cc50c167283b7049de47210`
- Previous result: `codex3_gradebook_06` is live 20/20 at 379x315, score
  `34,760,655,166.75`, a 1.355x improvement over `gradebook_05`
- Write set: own task/status/messages,
  `experiments/codex_3-gradebook-v2/`, one focused test,
  `submissions/gradebook/codex3_gradebook_07.man`, and one report
- Shared read-only: live Grade Book artifact/response, first codex_3 generator
  and stress harness, current judges, `subdb`, and the authoritative assignment
- Plan: preserve the 379x315 box and exact pipe-length tuple, then beam-search
  additional parser/worker staircase folds for a pure tick improvement
- First checkpoint: executable search driver with structural and adversarial
  gates committed on this branch
- Blockers: this connector runtime cannot execute the checkout or organizer
  WASM, so any generated score remains unverified until Claude runs the exact
  commands; handoff will label this explicitly
- Submission controller: no; no contest mutation permitted