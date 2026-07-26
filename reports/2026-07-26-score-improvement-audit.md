# Accepted score-improvement audit

Date: 2026-07-26

This audit checks Stream C of
`coordination/goals/20260726-llm-rust-and-score.md`: at least three
already-solved problems must obtain lower accepted server scores.

The evidence is the immutable `*-submit.json` collection on
`origin/agent/claude`. Every current result below has `status=done`, no error
or load error, and full live case coverage.

| Problem | Previous accepted score | Current accepted score | Reduction | Current submission |
| --- | ---: | ---: | ---: | --- |
| Reverse a List | 193,481.40 | 117,213.75 | 39.419% | `20a3f425-2ab2-4b41-aae8-503706a2810a` |
| Brackets | 943,438.46 | 836,345.19 | 11.351% | `3b77acf3-21cd-4ba9-80fb-5fcebf24ed44` |
| Packet Reassembly | 5,655,749.70 | 1,640,475.05 | 70.995% | `c5b2472f-8f70-4b9c-a263-d026c385def9` |
| Sort | 1,367,453.56 | 896,305.24 | 34.454% | `930fb828-32ed-42b6-8481-37e542270bb7` |
| Snake | 1,576,985,654.59 | 915,991,438.35 | 41.915% | `370c272b-75c5-4539-99b2-8794cf7591a9` |

## Evidence paths

- Reverse:
  `submissions/reverse-a-list/reverse_04-submit.json` ->
  `submissions/reverse-a-list/reverse_05-submit.json`
- Brackets:
  `submissions/brackets/brackets_03-submit.json` ->
  `submissions/brackets/brackets_04-submit.json`
- Packet Reassembly:
  `submissions/tcp/alexey-tcp_06-submit.json` ->
  `submissions/tcp/tcp_08-submit.json`
- Sort:
  `submissions/sort/alexey-sort_06-submit.json` ->
  `submissions/sort/sort_07-submit.json`
- Snake:
  `submissions/snake/snake_01-submit.json` ->
  `submissions/snake/snake_02-submit.json`

The current live coverage totals are respectively 20/20, 26/26, 20/20,
25/25, and 17/17. Thus five independent improvements satisfy the requested
minimum of three. The exact peer artifacts and responses are preserved in
`agent/codex-main-integration@a899e03`; the final repository suite passed
3,822 tests with no failure. Claude independently approved the integration;
promotion of the reviewed candidate to `main` is the remaining Git step.

The TCP result was independently refreshed through the authenticated API on
2026-07-26: terminal `done`, 20/20, 31×31, average 1,707.05 ticks, no error or
load error. Its exact artifact SHA-256 is
`70f3b2e7cfe297976d712d11197d0b835f8e325dc8c798b3d10654b239da13a2`.
