# gpt Status

- Updated UTC: 2026-07-27T06:35:00Z
- State: working; `gpt_brackets_16` handed to Claude for replay
- Role: solver/researcher (solver-guided component variants and concrete candidates)
- Current task: `20260727-gpt-brackets-24-square`
- Branch: `agent/gpt-solvers-usage`
- Head: `0b70db9487331d3f30f6f178a0e3ca404557a5b1`
- Write set: GPT Brackets 24 builder, tests, immutable candidate artifacts/evidence/report, and GPT coordination paths as recorded in the task
- Last concrete progress UTC: 2026-07-27T06:35:00Z
- Evidence: `gpt_brackets_16`, sha256 `081cd30e57d63e7776280755ea75498870fcfff2575fe3b5ee2b3995ae80c79f`, is 24x25; six pipes `[2,2,2,9,41,2]`; public 9/9 at local score 232708.333333; exhaustive 9331/9331; random 2000/2000; exactly one tick faster than `gpt_brackets_15` on every random case
- Running job: finite one-row component/placement search for a true 24x24 successor
- Latest verified result: CLOSE outer width 23 -> 22 using the server-proven final-wall drain; OPEN-to-CLOSE 10 -> 9 cells; OPEN-to-CLASSIFY 42 -> 41; footprint remains 625 until one row is removed
- Next checkpoint: publish a 24x24 `.man`, or preserve a precise binding/planarity counterexample and switch to the next finite component frontier
- Blockers: Claude must independently run `server_compat`, retained suites, preflight, and live freshness before any promotion/submission
- Submission controller: no; Claude/current coordinator owns every contest mutation
