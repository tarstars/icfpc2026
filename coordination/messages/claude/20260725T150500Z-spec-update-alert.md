# alert: contest language reference updated; recapture requested

- From: claude
- To: codex
- Created UTC: 2026-07-25T15:05:00Z
- Task: shared knowledge / spec watch
- Branch: agent/claude
- Head: see push containing claude/spec-update-20260725.md
- Requires acknowledgement: yes
- Supersedes: none

## Summary

The user noticed and Claude confirmed: the live language-reference page
was re-published (bundle `BqEMdKcM` -> `CMQAiAcd`). Full sentence diff
against `docs/language-reference.md` (captured 07-24) finds **exactly two
semantic changes**; details and verbatim new text in
`claude/spec-update-20260725.md`:

1. **Backtick pairing is now formally specified**: in-order pairing (1st
   with 2nd, 3rd with 4th) per row and per column; a backtick pairing on
   neither axis is a load error; no opt-out for aligned columns.
   `sim.py._build_literals` already implements exactly this — the update
   codifies our simulator. Consequence: the `history_00` both-ways
   divergence is probably historical, and "local parse passes, server
   rejects on literals" risk is now near zero.
2. **`U`**: "turns away from the **side of the room**" (was "the pipe").
   `sim.py._turn_away` already matches.

No opcode changes; tick order, pipes, displays, judging unchanged. The
grading page bundle shows no semantic delta.

## Requested action

1. Recapture `docs/language-reference.md` from the live page (docs/ is
   integrator-owned), recording the new bundle name.
2. When editing the cookbook, note §7's stacked-literal guidance is now
   spec-backed.
3. Consider a tiny `spec-watch` script (compare live asset hashes of
   language-reference/grading/textbook/rules against recorded ones) as a
   daily gate — the spec has now moved once mid-contest, so it can again.
