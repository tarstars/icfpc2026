# Independent verification of the Subset Sum squeeze/reinflation candidate

Date: 2026-07-26

Task: `20260726-gpt-subset-sum-verify`

Branch: `agent/gpt-subset-verify`

Candidate owner: Alexey. Reviewer/integrator: Codex. GPT performed only an
independent local verification; no contest mutation occurred.

## Verdict

**Reject the current full-squeeze-plus-opportunistic-reinflation artifact. Do
not submit it.**

The candidate keeps the same parser-visible counts, minimum legal pipe length
and absence of shared walls, but it fails the two properties it was intended to
restore:

1. 63 of 118 shortened pipes could not be reinflated and were deliberately
   left short;
2. 73 `s/S/r/R/U/q` instruction sites resolve to different logical pipes.

The C-fast-simulator public judge confirms the static failure: all seven public
cases reach the tick cap.

## Exact experiment

Starting point:

```text
origin/main@0410f654f71425990bf3e1c7d70a0bc2317d3e39
```

The verifier independently ran:

```bash
cd <repo>
PYTHONPATH=src python3 scripts/build_fastsim_ext.py
PYTHONPATH=src python3 \
  experiments/gpt-subset-sum-verify/run_remote.py
```

The generated invalid artifact was:

```text
SHA-256: 3244efda2f47164987603acfb3358fbd9df783c7ce303429478e640f9453373a
size: approximately 1.7 MiB
```

It is not committed because it is a large, invalid, reproducible intermediate.
`run_remote.py` regenerates it deterministically from `build_subset_sum()`.

Relevant evidence committed on this branch:

```text
experiments/gpt-subset-sum-verify/run_remote.py
experiments/gpt-subset-sum-verify/logical_audit.py
experiments/gpt-subset-sum-verify/reinflation_failures.json
experiments/gpt-subset-sum-verify/logical_binding_audit_summary.json
experiments/gpt-subset-sum-verify/remote_result.json
```

## Build and reinflation result

The full squeeze completed in 8.3 seconds and found 118 pipes shorter than in
the generated baseline.

```text
exact-length reroutes accepted by Router: 55
reroutes rejected and kept short:       63
reinflation wall time:                  1,254.6 seconds
```

The accepted/rejected count is not enough to establish final lengths. Parsing
the actual result and comparing logical pipes gives 93 per-pipe length changes:

```text
logical pipes shorter than original: 63
logical pipes longer than original:  30
logical pipes with changed length:   93
```

The runner's sorted-length gate reports 116 shorter multiset positions and no
longer positions. That is a statement about the two sorted multisets, not a
logical pipe-by-pipe correspondence. The logical audit is the appropriate gate
for protocol reasoning.

The largest unresolved contractions include:

| Logical pipe | Original cells | Candidate cells |
|---|---:|---:|
| `1 -> 2114` | 5,911 | 2,884 |
| `1 -> 8` | 3,233 | 996 |
| `2113 -> 2114` | 2,021 | 122 |
| `49 -> 2107` | 2,345 | 469 |
| `2114 -> 2119` | 966 | 63 |
| `2119 -> 2114` | 955 | 60 |
| `1 -> 2107` | 2,738 | 1,889 |
| `51 -> 2107` | 1,173 | 794 |

The complete 63-entry route failure list is in
`reinflation_failures.json`.

## Structural gates

The actual generated candidate parses as:

```json
{
  "rooms": 2121,
  "pipes": 2164,
  "men": 2119,
  "min_pipe": 2,
  "shared_walls": false,
  "length_multiset_restored": false,
  "box": [1006, 2374],
  "footprint": 5635876
}
```

Thus the footprint hypothesis is real: the box would be 2.36 times smaller
than the current 13,293,316 footprint. The machine semantics are not preserved.

## Logical nearest-pipe audit

`logical_audit.py` identifies each parsed pipe by:

```text
(source room index, destination room index, parallel-pipe ordinal)
```

There are no duplicate source/destination room pairs in either machine, so the
logical identity is unambiguous without relying on coordinates.

For every executable `s`, `S`, `r`, `R`, `U` and `q`, the audit resolves the
pipe exactly as the simulator does and compares the result at the same room and
operation index.

```text
pipe operations before:       9,413
pipe operations after:        9,413
logical binding changes:         73
endpoint-role changes:           117
```

Examples from controller room 2107:

```text
r op 10: 2111 -> 2107  became 51 -> 2107
r op 14: 2112 -> 2107  became 51 -> 2107
r op 20:   49 -> 2107  became 2112 -> 2107
r op 24:   51 -> 2107  became 2112 -> 2107
r op 26:   51 -> 2107  became 2112 -> 2107
```

Room 2114 also has dozens of reads redirected from worker inputs 2116–2119 to
2113. These are genuine logical-pipe changes, not merely translated endpoint
coordinates.

## Public judge result

Backend: C fastsim extension.

```text
cases passed: 0 / 7
failure for every case: tick-cap
judge wall time: 61.1 seconds
total build + reinflation + judge time: 1,326.5 seconds
score: undefined
```

The exact strict-JSON result is in `remote_result.json`.

## Why the preservation argument fails

The proposed argument was:

> same source/destination ports plus the same cell count preserves capacity and
> transit time.

That argument would be useful only after its premises were established. The
current transformation violates them in three separate ways:

1. **Most target lengths are not restored.** Failed routes are kept short.
2. **Room-relative attachment positions change.** A global squeeze changes the
   large controllers' dimensions and moves their attachment cells.
3. **Nearest-pipe selection changes.** The language resolves `r` and `s` from
   Manhattan distance to the attachment cell; preserving room identities and
   pipe count does not preserve that ranking.

Even a future router that restores every numerical length must still audit all
9,413 pipe operations. Equal length preserves nominal per-pipe capacity and
single-value transit time, but it does not preserve which pipe an instruction
selects.

## Recommended next architecture

Do not retry whole-program squeeze followed by generic reinflation. Treat the
three high-fan-in/high-fan-out controllers as rigid macros:

```text
room 1     parser / dispatch controller
room 2107  first merge/controller
room 2114  second merge/controller
```

A safer compaction line is:

1. freeze each macro's room dimensions and room-relative port locations;
2. compact only repeated 1-in/1-out sorter-stage banks first;
3. place rigid macros and banks with explicit port constraints;
4. route storage nets to declared minimum capacities, not merely shortest
   paths;
5. require exact logical binding equality before launching the expensive
   judge;
6. measure peak occupancy and phase margins on any pipe whose length changes.

This is naturally a constrained block-placement/router task. It may still
recover much of the 2.36x geometric opportunity, but the parser and merge
controllers cannot be blindly squeezed.

## Reproduction of the audits

After `run_remote.py` writes its local candidate:

```bash
PYTHONPATH=src python3 \
  experiments/gpt-subset-sum-verify/logical_audit.py \
  experiments/gpt-subset-sum-verify/ss_reinflated.man
```

The audit exits nonzero when any logical binding changes and writes the full
machine-readable report. A compact result summary is committed as
`logical_binding_audit_summary.json`.

## External effects

No contest submission, API mutation, shared catalogue change or Alexey-owned
file modification occurred.
