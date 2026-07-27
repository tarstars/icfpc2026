# handoff: exact port-assignment layer and Brackets replay

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T04:57:00Z`
- Task: `20260727-gpt-solvers-port-assignment`
- Branch: `agent/gpt-solvers-usage`
- Commit: `2c432bcbe8d5c339b082e7e023815f6ed2212ccf`
- Requires acknowledgement: yes

## Diff scope

Only GPT-owned coordination files, `experiments/gpt-solvers-usage/`, and
`reports/2026-07-27-gpt-solvers-usage.md` changed. Existing source, solution
artifacts, catalogs, shared infrastructure, `main`, and contest state are
untouched.

## Commands and measured evidence

```bash
cd experiments/gpt-solvers-usage
python3 -m py_compile port_assignment_milp.py test_port_assignment_milp.py
python3 port_assignment_milp.py brackets_10_port_instance.json \
  --output /tmp/brackets_10_port_solution.json --time-limit 30
python3 port_assignment_milp.py brackets_11_port_instance.json \
  --output /tmp/brackets_11_port_solution.json --time-limit 30
python3 -m unittest -v test_port_assignment_milp.py
```

Result: Brackets 10 transport objective `10 -> 4`, Brackets 11 exact objective
`4` with incumbents retained, HiGHS MIP gap `0.0`, five focused tests passing.
Measured replay wall/RSS was 1.31 seconds / 149948 KiB.

## Review focus

1. Exact `(distance,row,column)` incompatibility constraints for `s`/`r`/`q`.
2. The `machine_ir` adapter's same-wall candidate generation and deliberate
   omission of positional constraints for set-valued `S`/`R`/`U`.
3. Distinction between endpoint Manhattan lower bounds and a legal routed
   `.man`; no route or behavior is claimed.
4. The strategy correction: old TCP 35-square routing is no longer
   score-positive against live 30x30, while Brackets component variants are.

## Unverified assumptions and known limits

The branch has no rendered candidate and has not run repository parser,
compatibility, resolution-map, or judge gates against a changed `.man`. The
Brackets replay is a solver/model regression against a known accepted manual
lineage, not a new contest candidate.

## Suggested integration order

Integrate the complete branch checkpoint after review; the experiment-local
SciPy requirement does not alter project dependencies. Then assign a new task
for a finite Brackets middle-room implementation frontier and one-hot component
selection. No external mutation occurred.
