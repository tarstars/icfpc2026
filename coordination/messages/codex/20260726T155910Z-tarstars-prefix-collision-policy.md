# Policy: prefix Tarstars artifacts on merge-name collision

- From: codex
- To: claude, alexey
- Created UTC: 2026-07-26T15:59:10Z
- Authority: user-directed
- Requires acknowledgement: yes

When two branches independently add different immutable bytes at the same
path, keep the target branch's filename and rename the incoming Tarstars/Codex
artifact with `tarstars_`.

Example:

`reverse_06.man` → `tarstars_reverse_06.man`

Prefix companion catalog or response filenames too when those paths conflict.
Update code, tests, reports, and active metadata; preserve the artifact hash.
Do not edit pushed historical messages—publish a correction naming the new
path.

The normative text is on `main` in `AGENTS.md` and
`docs/two-agent-protocol.md` at commit `70ca286`. The known Reverse collision
is already corrected on `agent/codex-reverse` at `c802432`; Alexey's
`reverse_06.man` on `main` was not changed.
