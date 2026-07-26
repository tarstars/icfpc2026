# GPT Status

- Updated UTC: 2026-07-26T18:19:00Z
- State: working; candidate rejected, judge collecting exact failure evidence
- Role: independent architecture researcher and verifier
- Current task: `20260726-gpt-subset-sum-verify`
- Branch: `agent/gpt-subset-verify`
- Base: `origin/main@0410f654f71425990bf3e1c7d70a0bc2317d3e39`
- Write set: GPT task/status/messages; `experiments/gpt-subset-sum-verify/`; focused verification report
- Last concrete progress UTC: 2026-07-26T18:19:00Z
- Evidence: 118 shortened pipes found; only 55 reroutes accepted, 63 kept short; length multiset not restored; independent audit finds 73 logical `s/S/r/R/U/q` binding changes
- Running job: full 20-case public judge still active solely to capture exact observed failure/ticks in `/tmp/gpt_subset_verify.log`
- Latest verified result: candidate is statically non-equivalent and must not be submitted; blocker message `20260726T181900Z-...-blocker.md` published to Alexey/Codex/Claude
- Next checkpoint: preserve judge result, scripts, audits and final negative report; release task
- Blockers: candidate architecture, not verifier: capacity and nearest-pipe contracts are broken
- Submission controller: no; Alexey retains candidate/submission authority and no contest mutation is permitted
