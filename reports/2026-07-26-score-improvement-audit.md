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
| Packet Reassembly | 5,655,749.70 | 2,146,016.25 | 62.056% | `3267eca6-494d-4c9d-aa1d-dfe308aee7a1` |
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
  `submissions/tcp/tcp_07-submit.json`
- Sort:
  `submissions/sort/alexey-sort_06-submit.json` ->
  `submissions/sort/sort_07-submit.json`
- Snake:
  `submissions/snake/snake_01-submit.json` ->
  `submissions/snake/snake_02-submit.json`

The current live coverage totals are respectively 20/20, 26/26, 20/20,
25/25, and 17/17. Thus five independent improvements satisfy the requested
minimum of three. Integration still needs to preserve the peer artifacts and
responses on the final shared branch; this report does not substitute for
that Git reconciliation.
