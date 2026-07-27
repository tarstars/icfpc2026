# checkpoint: solver floorplanner pushed for peer review

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T04:28:30Z`
- Task: `20260727-gpt-solvers-floorplan`
- Branch: `agent/gpt-solvers-usage`
- Commit: `1a9b92c7c130ba3f17b2070ac65129947257cb6f`
- Requires acknowledgement: no

The first solver-usage checkpoint is pushed. Compared with base main
`e6ed1423a7fb0cda17d1f3db79e82e8831b08244`, it changes only the declared GPT
coordination paths, the new experiment, and its report.

Reproduction from `experiments/gpt-solvers-usage`:

```bash
python3 -m py_compile floorplan_milp.py test_floorplan_milp.py
python3 floorplan_milp.py tcp_room_instance.json \
  --output /tmp/tcp_room_solution.json --time-limit 120
python3 -m unittest -v test_floorplan_milp.py
```

Expected result: exact side 35, MIP gap 0.0, five tests passing. The preserved
38-square TCP placement is a positive model regression. The implementation
checkpoint is ready for inspection; the task remains active for detailed route
feasibility. No merge or contest action is requested yet.
