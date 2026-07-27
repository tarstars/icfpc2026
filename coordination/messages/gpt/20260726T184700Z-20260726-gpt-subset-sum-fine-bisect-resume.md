# Progress: fine Subset Sum search resumed safely after OOM

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T18:47:00Z`
- Task: `20260726-gpt-subset-sum-fine-bisect`
- Branch: `agent/gpt-subset-bisect-fine`
- Requires acknowledgement: no

## Infrastructure finding

The initial four-worker pool reached the container's 4 GiB cgroup limit. The
kernel killed one worker at about 876 MiB RSS; eight completed group results
were already atomically checkpointed.

The search resumed with three workers, cached baseline, and columns-first order.
This is stable within the measured memory limit.

## Current evidence

```text
completed fine groups: 11 / 96
passed independently: 11
failed: 0
```

Green groups so far:

```text
row-000 through row-007
col-000 through col-002
```

The first resumed column wave took about 134–135 seconds per candidate and
passed 7/7. The remaining tests continue from the same checkpoint. No solution
or Alexey-owned path is modified.
