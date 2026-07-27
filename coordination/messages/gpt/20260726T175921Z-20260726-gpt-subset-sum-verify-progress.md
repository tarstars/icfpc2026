# Progress: independent Subset Sum reinflation is not restoring all pipes

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T17:59:21Z`
- Task: `20260726-gpt-subset-sum-verify`
- Branch: `agent/gpt-subset-verify`
- Requires acknowledgement: no

## Reproducible finding

The independent run is active with the C fastsim backend. Generation and full
squeeze completed in 8.3 seconds and identified 118 shortened pipes.

After the first 10 attempted exact-length reroutes:

```text
attempted: 10
restored:   2
failed:     8
```

Failures already include large routes such as:

```text
(source room, destination room)  original -> squeezed
(1, 8)                            3233 -> 996
(1, 2107)                         2738 -> 1889
(1, 2114)                         5911 -> 2884
```

Therefore the current one-shot runner does **not** yet establish its claimed
length-multiset restoration. It keeps failed pipes short and continues, so the
resulting candidate must not be described as capacity-preserving unless the
final failure count is zero.

The bounded job continues to enumerate all 118 routes and will then run the
structural gates and public judge on the actual partially restored artifact.
No Alexey-owned file has been touched and no contest mutation has occurred.
