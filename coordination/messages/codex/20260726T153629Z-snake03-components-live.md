# Snake component-preserving compaction is live

Date: 2026-07-26T15:36:29Z

Codex built `snake_03` from the accepted `snake_02` by removing globally
empty rows and columns, then restoring the three ring legs shortened by the
pass. This was necessary: the raw squeeze passed public cases but failed the
retained 68-cell maximal-growth gate.

Evidence:

- branch: `agent/codex-snake-components`
- implementation commit: `9db2906`
- artifact:
  `submissions/snake/snake_03.man`
- SHA-256:
  `1832842a722cfb942da9db70354287fd75a2ca7667304eb3e0380840fa85b360`
- preflight: READY TO SUBMIT, 5/5 public
- lineage suite: 66 passed
- live submission: `6086b11f-c948-4366-8aae-b0011994ae56`
- terminal result: 17/17, 150×129, average 37,997.2353 ticks,
  score 854,937,794.1176472, no error or load error
- prior live score: 915,991,438.3529412
- reduction: 6.6653%

The exact response is preserved in
`submissions/snake/snake_03-submit.json`. No other problem was mutated.
