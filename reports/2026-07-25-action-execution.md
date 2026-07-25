# Action Execution — 2026-07-25

Started: 2026-07-25 09:09 Europe/Moscow

## Objective

Turn the overnight-work review into concrete, reproducible project work.

## Actions and acceptance criteria

1. **Recover the provenance of the live Packet Reassembly score.**
   Record the exact source and submission ID behind the team's current
   5,981,625.6 score, or document the exhausted evidence and the remaining
   manual recovery step.
2. **Finish the reproducible `tcp_01` experiment.**
   Preserve its source, generator, validation, live result, and comparison
   against `tcp_00`.
3. **Refresh shared project state.**
   Make the concise current-state documents agree that all twelve graded
   problems are solved, distinguish current live scores from historical
   snapshots, and retire completed handoffs.
4. **Add a server-compatibility gate.**
   Detect layouts whose rooms share wall cells and execute final-wall-step
   cases with server-compatible semantics before submission.
5. **Attempt the highest-return practical weak-rank optimization.**
   Preserve the accepted baseline, change geometry rather than protocol where
   possible, and accept a candidate only after exact regeneration and oracle
   validation.
6. **Integrate safely.**
   Run focused and full validation, perform the mandatory pull and live score
   check before a solution commit, then commit and push only the intended
   files.

## Execution record

| Action | Status | Evidence |
|---|---|---|
| Packet provenance | Exhausted locally | The authenticated API has no submission-list endpoint (`GET /api/v1/submissions` returns 404). Repository history, branches, local session logs, `/tmp`, and shell history contain no source or submission ID matching 5,981,625.6. Manual recovery is required. |
| `tcp_01` | Complete upstream | Integrated through `main` at `b2f8b58`; 20/20 live, 62×62, score 52,747,175. This proves the offset-window architecture but is worse than `tcp_00` and does not explain the current 5,981,625.6 score. |
| State refresh | Complete | Updated `docs/current-state.md`, `codex/state.md`, and `claude/STATE.md`; marked the completed Memory handoff historical. |
| Compatibility gate | Complete | Added `littleman.server_compat` and regressions for both confirmed server differences. The all-artifact audit accepted 27 layouts and rejected only the known shared-wall Triangle; the historical rejected History source retained its independent parser error. |
| Weak-rank optimization | Complete locally | `plotter_01` compacts 394×535 to 388×441, passes 6/6 public and the 20-segment oracle, and lowers measured local score 32.98%. It is preserved but not submitted. |
| Integration | Validation complete | `git pull --ff-only origin main` confirmed `b2f8b58` current. The final Plotter standings query returned empty rows at `2026-07-25T06:22:56.768Z`; a direct API read confirmed the preserved baseline at 20/20 and score 75,794,498,065. The full suite passes: 142 tests in 64.56 seconds. |

## Packet provenance conclusion

The locally recoverable evidence is insufficient to reconstruct the artifact
behind the live 5,981,625.6 Packet Reassembly score. The live standings prove
that the result exists, but the contest API exposes individual submission
lookups only when the UUID is already known. The next recovery step is manual:
open the team's Packet Reassembly submission history in the contest web UI,
copy the winning submission UUID and source, then preserve both under
`submissions/tcp/` before making further TCP submissions.
