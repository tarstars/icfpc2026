# Claim: fine-grained Subset Sum deletion bisection

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T18:27:29Z`
- Task: `20260726-gpt-subset-sum-fine-bisect`
- Branch: `agent/gpt-subset-bisect-fine`
- Base: `origin/main@5ba6c3376b76103484d5ded289f2fa2dce3df6a3`
- Requires acknowledgement: no

## Coordination boundary

I am taking the finer search you requested, with exact non-overlapping group
counts:

```text
rows:    32 contiguous groups
columns: 64 contiguous groups
```

Your active M4 script remains the 8-row/16-column coarse search. I will not edit
or write under `experiments/alexey-subset-sum/` or any submission path.

The 96 independent group tests will run four at a time with the C fastsim
extension. The passing-group union and interaction peeling are serialized and
fully re-judged. Any result will be returned as hashes, deletion lists and
metrics; you retain candidate ownership and submission authority.

No contest mutation is authorized.
