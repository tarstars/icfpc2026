# Blocker: reinflated Subset Sum candidate changes 73 logical pipe bindings

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T18:19:00Z`
- Task: `20260726-gpt-subset-sum-verify`
- Branch: `agent/gpt-subset-verify`
- Requires acknowledgement: yes

## Verdict now

**Do not submit the current squeeze-plus-reinflation artifact.** Independent
construction completed, but it does not satisfy either the capacity premise or
the binding-equivalence gate.

## Reinflation result

```text
shortened pipes found: 118
exact reroutes accepted by runner: 55
reroutes failed and kept short: 63
```

The resulting structural gate reports:

```json
{
  "rooms": 2121,
  "pipes": 2164,
  "men": 2119,
  "min_pipe": 2,
  "shared_walls": false,
  "length_multiset_restored": false,
  "shorter_pipes": 116,
  "longer_pipes": 0,
  "box": [1006, 2374],
  "fp": 5635876
}
```

Large failed storage/control routes include:

```text
(1 -> 8)     3233 -> 996
(1 -> 2107)  2738 -> 1889
(1 -> 2114)  5911 -> 2884
(49 -> 2107) 2345 -> 469
(51 -> 2107) 1173 -> 794
```

## Logical binding audit

I compared all `s/S/r/R/U/q` sites by room and operation index, resolving each
to its logical `(source room, destination room)` pipe. There are no duplicate
source/destination room pairs, so this identity is unambiguous.

Results:

```text
pipe operations before: 9413
pipe operations after:  9413
logical binding changes: 73
per-pipe length changes: 93
endpoint-role changes:   117
```

Examples in controller room 2107:

```text
r op 10: 2111 -> 2107  became 51 -> 2107
r op 14: 2112 -> 2107  became 51 -> 2107
r op 20:   49 -> 2107  became 2112 -> 2107
r op 24:   51 -> 2107  became 2112 -> 2107
```

Thus this is not merely a different route geometry. The squeeze changes room
and port positions enough to alter nearest-pipe selection in the large
multi-input controller.

## Running judge

The full public judge remains active only to obtain an exact observed failure
mode and tick evidence. Its result cannot rescue this artifact because the
static logical-binding contract is already broken.

## Required redesign

A viable compact candidate must preserve, for every pipe instruction:

1. the exact logical pipe selected;
2. source and destination attachment roles, or an independently verified new
   binding map;
3. required storage capacity and phase/transit constraints;
4. all public execution traces.

A whole-program squeeze followed by opportunistic rerouting is not sufficient
for this machine. The promising next route is component/block placement with
ports constrained as solver variables, rather than deleting dimensions under
the giant controller.

No Alexey-owned file was modified and no contest mutation occurred.
