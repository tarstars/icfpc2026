# LLM physical nearest-pipe selector

Status: pushed component checkpoint; no contest mutation.

The endpoint binding arithmetic is now physical and exact:

- `llm_bindscore.py` maps `(man_addr, endpoint_addr)` to
  `Manhattan distance * 256 + endpoint_addr`. Comparing this integer is
  exactly LLM's distance then reading-order rule.
- `llm_pipeselect.py` selects slot 0/1 from one or two already eligible
  endpoints. Equal endpoint scores retain the first slot.
- Both rooms are streaming and reusable; the selector contains the score
  service and its private recirculation ring.

Evidence:

- 1,280 systematic grid-edge/self pairs plus 1,000 seeded random score
  pairs were physical/reference exact.
- 2,000 seeded one/two-candidate selection requests were
  physical/reference exact.
- Directed equal-distance/read-order and exact-tie cases pass.
- Both generated rigs pass deterministic generation, server layout, and
  pipe-audit gates.
- `6 passed in 10.85s`; Ruff clean.
- Score room `64 x 78`, 467 occupied cells. Selector room `37 x 78`,
  321 occupied cells; complete selector rig `64 x 192`, 922 occupied cells.

Remaining integration must filter eligible endpoints for the current room,
feed one/two targets to this selector, and use the returned slot to route the
record through `llm_pipeapply`.
