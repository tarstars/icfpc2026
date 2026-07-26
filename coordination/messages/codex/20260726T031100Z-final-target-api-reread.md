# Final target API reread

Read-only freshness check during the zero-first goal's final window. Commands
used the canonical CLI and shared ignored environment file:

```text
uv run icfpc-api --env-file /home/tarstars/prj/icfpc2026/.env \
  --compact submission <submission-id>
```

All commands exited 0. No submission was created.

| Target | Submission | Terminal result | Geometry / score |
| --- | --- | --- | --- |
| LLLM | `efce1ac1-ece0-4557-a08e-4d34edd9dd4d` | 21/21 | 307x312; 22,187,469,586.285713 |
| Pathfinder | `0c04a141-a73b-443c-a274-741bfe67d857` | 18/18 | 187x1957; 17,546,210,849,166.055 |
| LLM | `e57fd7d2-352d-4929-a474-2009a6af4fd0` | 2/28 | 307x312; no score |

LLM still reports 13/14 public and 13/14 private failures, all
`wrong-frames`. This is the unchanged shared LLLM artifact, not the
unfinished physical LLM successor.

Conclusion: the target state in the authoritative handoff remains exact.
Pathfinder and LLLM are secured; LLM is incomplete, so the goal remains
active and must not be marked complete.
