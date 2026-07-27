# Release: compact TCP relay experiment paused

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-26T17:41:57Z`
- Task: `20260726-gpt-tcp-relay-component`
- Branch: `agent/gpt`
- Requires acknowledgement: no

## Summary

The user explicitly reprioritized GPT to commit two existing locally validated
`.man` candidates. I am pausing and releasing the TCP relay write set before
switching tasks.

No file under `experiments/gpt-tcp-relay/` or `reports/2026-07-26-gpt-tcp-relay-component.md`
was created. No shared TCP source, test, submission artifact, or catalogue was
modified. The only work performed was source inspection and publication of the
claim.

## Useful retained observation

`tcp_fast.build_r()` is already a six-cell relay cycle for the packed
three-word ring. Alexey's `> s U d m ^` loop primarily saves a dedicated head
send/approach when a new value is already in `A`; whether it improves the
unrolled packed controller remains open and unmeasured.

The task may be resumed only through a fresh assignment or explicit
reactivation after the candidate-preservation handoff.
