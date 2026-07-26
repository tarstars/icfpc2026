# Handoff: Subset Sum squeeze/reinflation candidate rejected

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T18:25:00Z`
- Task: `20260726-gpt-subset-sum-verify`
- Branch: `agent/gpt-subset-verify`
- Payload commit: `5ef6c8e02e444e23eaf5f00dfb44609b2e9828c6`
- Requires acknowledgement: yes

## Final verdict

**Do not submit the current full-squeeze-plus-reinflation candidate.** The
independent C-fast-simulator run is 0/7, with every public case reaching the
tick cap. Static audits independently prove the artifact is not equivalent.

## Exact result

```text
backend: c-ext
full squeeze: 8.3 s
shortened pipes found: 118
reroutes accepted: 55
reroutes failed and kept short: 63
reinflation total at gate: 1,254.6 s

rooms / pipes / men: 2121 / 2164 / 2119
minimum pipe length: 2
shared walls: false
box: 1006x2374
footprint: 5,635,876
length multiset restored: false

logical pipe operations: 9,413
logical binding changes: 73
logical per-pipe length changes: 93
endpoint-role changes: 117

public cases: 0/7
failure: tick-cap on all seven
judge wall time: 61.1 s
total wall time: 1,326.5 s
```

Invalid local artifact:

```text
SHA-256 3244efda2f47164987603acfb3358fbd9df783c7ce303429478e640f9453373a
```

It is reproducible from the committed runner and was intentionally not added as
a 1.7 MiB invalid Git artifact.

## Root causes

1. The generic router fails to restore 63 of 118 shortened pipes, including
   the largest storage/control routes.
2. The squeeze changes room-relative port positions in controllers 1, 2107 and
   2114.
3. Nearest-pipe selection changes at 73 executable pipe instructions.
4. Even among logical pipes, 63 end shorter and 30 end longer than the
   original; a sorted length-multiset comparison hides the correspondence.

Representative binding changes:

```text
room 2107 r#10: 2111->2107 became 51->2107
room 2107 r#14: 2112->2107 became 51->2107
room 2107 r#20: 49->2107 became 2112->2107
```

## Evidence paths

```text
experiments/gpt-subset-sum-verify/run_remote.py
experiments/gpt-subset-sum-verify/logical_audit.py
experiments/gpt-subset-sum-verify/reinflation_failures.json
experiments/gpt-subset-sum-verify/logical_binding_audit_summary.json
experiments/gpt-subset-sum-verify/remote_result.json
reports/2026-07-26-gpt-subset-sum-verify.md
```

## Recommended next line

Treat rooms 1, 2107 and 2114 as rigid macros with fixed dimensions and port
roles. Compact repeated 1-in/1-out sorter banks around them, route storage nets
to explicit capacity requirements, and make exact logical-binding equality a
cheap pre-judge gate. Do not apply another whole-program squeeze to these
controllers.

## External effects

No Alexey-owned path was modified. No contest API mutation or submission
occurred. GPT's implementation write set is released.
