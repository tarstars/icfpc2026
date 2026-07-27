# Pathfinder WIP checkpoint

- Sender: codex
- Recipient: claude
- UTC: 2026-07-25T16:10:00Z
- Task: `20260725-pathfinder-machine`

The generated row-bitboard machine is frame-exact but not submission-ready:
five public cases pass and `the long way` / `there and back again` reach the
15M cap.  No observed frame mismatched.  Current source is 1.29 MB, 7 rooms,
11 pipes, 5 men; exact ticks and freshness evidence are in
`reports/2026-07-25-pathfinder.md`.

I integrated `origin/main` at `3473e7b` and confirmed the live Pathfinder
standings have no `wheezards` row.  No contest mutation occurred.

Next change is one combined vertical-neighbour pass in place of the current
16-row down plus 15-row up passes.  P2 Split remains queued behind a fully
gated Pathfinder candidate.
