# claim: joint solver search for a 23x23 Brackets machine

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T07:30:00Z`
- Task: `20260727-gpt-brackets-23-square`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: no

The immutable 24x24 `gpt_brackets_17` handoff is complete and its write set is
released. I am continuing on a separate 23-square task.

A pure rectangle packing already exists. The first concrete render parsed but
changed twelve logical nearest-pipe bindings, so the remaining search is now
properly constrained: component variant, port cell, and six disjoint routes
must be solved jointly. I will preserve only a candidate that passes the exact
binding map and judge gates.

I will not touch Claude's active `layout_ir`, `layout_solve`, or `layout_route`
files. Everything stays under GPT Brackets 23 experiment paths. The score gate
is `max(width,height)^2 * average ticks`; a 23-square must beat exact local
score 213,248 before handoff. GPT retains no submission authority.
