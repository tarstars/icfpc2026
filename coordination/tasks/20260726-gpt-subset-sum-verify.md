# 20260726-gpt-subset-sum-verify: independently verify reinflated candidate

- Status: complete; candidate rejected; write set released except GPT status/messages
- Record owner: gpt
- Work owner: gpt
- Reviewer: codex
- Integrator: codex
- Candidate owner: alexey
- Problem: `subset-sum`
- Base main commit: `0410f654f71425990bf3e1c7d70a0bc2317d3e39`
- Branch: `agent/gpt-subset-verify`
- Progress lease: complete
- Created UTC: `2026-07-26T17:53:53Z`
- Last updated UTC: `2026-07-26T18:25:00Z`

## Outcome

Independently build and judge Alexey's full-squeeze-plus-reinflation Subset Sum
candidate, preserving Alexey's ownership. Produce structural gates, backend,
case results, ticks, score and a review of whether same ports plus restored pipe
lengths preserve the relevant semantics.

## Delivered paths

- `experiments/gpt-subset-sum-verify/run_remote.py`
- `experiments/gpt-subset-sum-verify/logical_audit.py`
- `experiments/gpt-subset-sum-verify/reinflation_failures.json`
- `experiments/gpt-subset-sum-verify/logical_binding_audit_summary.json`
- `experiments/gpt-subset-sum-verify/remote_result.json`
- `reports/2026-07-26-gpt-subset-sum-verify.md`
- GPT-owned claim, progress, blocker and handoff messages

The invalid generated `.man` is not committed because it is a 1.7 MiB
reproducible intermediate. Its SHA-256 is
`3244efda2f47164987603acfb3358fbd9df783c7ce303429478e640f9453373a`.

## Exact result

```text
backend: C fastsim extension
shortened pipes found: 118
reroutes accepted: 55
reroutes failed/kept short: 63
structure: 2121 rooms / 2164 pipes / 2119 men
minimum pipe length: 2
shared walls: false
box: 1006x2374
footprint: 5,635,876
length multiset restored: false
logical per-pipe length changes: 93
logical binding changes: 73
public cases: 0/7
all failures: tick-cap
judge wall time: 61.1 seconds
total build + route + judge wall time: 1,326.5 seconds
```

## Acceptance-check disposition

- Candidate builds from the generator and squeeze: **pass**.
- Failed exact reroutes listed explicitly: **pass, 63 failures recorded**.
- Parsed structure remains `2121/2164/2119`: **pass**.
- Minimum two-cell pipes and no shared walls: **pass**.
- Original logical bindings retained: **fail, 73 sites changed**.
- Original lengths/capacity restored: **fail, 93 logical lengths changed**.
- Public correctness: **fail, 0/7 tick-cap**.

## Verdict

The candidate must not be submitted. Whole-program squeeze changes the large
controllers' port positions and nearest-pipe selections, while the generic
router cannot restore many storage routes. A future line should freeze rooms
1, 2107 and 2114 as rigid macros and compact only components whose port
contracts can be preserved explicitly.

## Contest authority

No contest mutation occurred. Alexey retains candidate and submission control.

## Handoff

The focused report and immutable handoff give Alexey and Codex the exact
negative evidence and a constrained next architecture. The GPT implementation
write set is released.
