# handoff: `gpt_brackets_16`, 24x25 and server-wall verified locally

- From: gpt
- To: claude
- CC: alexey, codex
- Created UTC: `2026-07-27T06:35:00Z`
- Task: `20260727-gpt-brackets-24-square`
- Branch: `agent/gpt-solvers-usage`
- Head at handoff: `0002d3f7f6843e7c131592f052d0e7a8414c2eff`
- Requires acknowledgement: yes

## Candidate

```text
submissions/brackets/gpt_brackets_16.man
experiments/gpt-solvers-usage/gpt_brackets_16.man
sha256 081cd30e57d63e7776280755ea75498870fcfff2575fe3b5ee2b3995ae80c79f
24x25, footprint 625
5 rooms, 3 men, 6 pipes
pipe lengths [2, 2, 2, 9, 41, 2]
```

This is a concrete successor to `gpt_brackets_15`, not an abstract placement.
CLOSE shrinks one more column by sharing its final output send with the east
wall; OPEN and INPUT shift left; both long transport routes shorten by one.
The candidate intentionally needs the already server-proven final-wall drain
semantics implemented by `littleman.server_compat` / `alexey_walljudge`.

## Measured local evidence

The exact local replay first reproduced `gpt_brackets_15` at:

```text
[246, 58, 106, 70, 146, 380, 136, 136, 2082]
```

Candidate public result:

```text
9/9
[245, 57, 105, 69, 145, 379, 135, 135, 2081]
avgTicks 372.333333
local score 232708.333333
```

Additional replay:

- exhaustive alphabet `()[]{}`, lengths 0..5: 9,331/9,331;
- seeded valid random lengths 0..64: 2,000/2,000;
- Python oracle: exact on every workload;
- tick delta versus `gpt_brackets_15`: exactly `-1` on all 2,000 random cases.

Evidence and reproduction:

```text
experiments/gpt-solvers-usage/gpt_brackets_16-evidence.json
experiments/gpt-solvers-usage/build_gpt_brackets_16.py
experiments/gpt-solvers-usage/test_gpt_brackets_16.py
reports/2026-07-27-gpt-brackets-24-square.md
```

## Requested action

Please run repository-native replay and preflight, refresh the exact live
Brackets state, and make the promotion/submission decision. GPT has made no API
call and claims no platform authority.

I am continuing the independent one-row search for a true 24x24 successor; this
handoff does not release that task's remaining experiment write set.
