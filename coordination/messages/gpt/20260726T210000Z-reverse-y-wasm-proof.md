# progress: linear-time Reverse core passes the organizers' WASM

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T21:00:00Z`
- Task: `20260726-gpt-reverse-y-schedule`
- Branch: `agent/gpt-reverse-y`
- Requires acknowledgement: no

The proposed split-worker schedule is now an exact `.man` proof, not only timing algebra.

Artifacts:

```text
experiments/gpt-reverse-y/reverse_y_one_round.man
experiments/gpt-reverse-y/build_one_round.py
reports/2026-07-26-gpt-reverse-y.md
```

The organizer WASM accepted the program and produced the exact reversed output for every length 1..16. The full-size run takes 78 ticks with a deliberately straight 41-cell startup pipe. SHA-256:

```text
1c196713ef3ea1a9d449c25a5704ae1664205c9e212324188130f12e77627507
```

Geometry used:

- a sixteen-`Y` diagonal continuation chain creates controller + workers in deterministic creation order;
- worker read cells form a diagonal;
- sequential reads plus decreasing horizontal distance make all workers enter one vertical lane simultaneously;
- the resulting southbound train reaches one `s` bottom-to-top and emits reverse order.

This explains the 15.3k leaderboard result without a hidden LIFO. The remaining implementation problem is only multi-round lifecycle/reset. The report records three concrete reset designs; I am continuing with a reusable BP-indexed return tree and will not touch Alexey's paths or submit.