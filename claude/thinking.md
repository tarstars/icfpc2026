# Thinking — scratchpad, newest first

Messy on purpose. Hunches, dead ends, "why not X". Promote anything that
solidifies into STATE.md or a shared doc.

---

## 2026-07-24 — pre-contest posture

- Resist the urge to pre-build a "framework" before the task drops. ICFPC
  tasks vary wildly (optimization, interpreters, games, protocols); generic
  scaffolding usually gets thrown away. The scaffold that DOES always pay
  off: fast eval loop (score a solution locally), a submitter, and a run
  manifest habit.
- Historically the highest-leverage first-day artifacts: (1) correct
  parser/validator, (2) local scorer matching the judge, (3) dumb baseline
  submitted early to confirm the pipeline end-to-end.
- Keep an eye on the 400 GiB free-space floor on `medium_data` — generous
  now (~426 GiB free), but Monte Carlo / corpus generation eats disk fast.
