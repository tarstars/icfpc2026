# question: subset-sum candidate needs an independent judge run (Rust executor?)

- From: alexey
- To: codex
- CC: claude
- Created UTC: 2026-07-26T17:50:00Z
- Task: 20260726-subset-sum-footprint
- Branch: main
- Requires acknowledgement: yes

## Summary

I have a subset-sum candidate at **fp 5,635,876 vs live 13,293,316 (2.36x)**
and my box is too slow to iterate on it comfortably (one 20-case judge run
is ~30+ min on the C fastsim; the bare-squeeze variant burned 32 min to
fail). Requesting an independent verification, ideally on the **Rust
executor**, which I believe is faster than anything I have here.

State:

* `experiments/alexey-subset-sum/ss_fullsqueeze.man` — full squeeze of the
  regenerated artifact. Structure identical (2121/2164/2119), gates green,
  **but it deadlocks: 20-case judge fails on tick-cap**, because squeeze
  deletes blank-or-`|` rows and thereby shortens 118 pipes (39,755 ->
  20,305 cells), some of which are storage. This confirms claude's snake
  counterexample on a second machine. Do NOT submit this one; it is kept as
  the measured failure.
* `ss_reinflated.man` (being built; lands with my next push) — same squeeze,
  then every shortened pipe re-inflated to its ORIGINAL cell count with
  `alexey_piperoute` (ports untouched -> resolution untouched; lengths
  restored -> capacity untouched by construction).
* `experiments/alexey-subset-sum/run_remote.py` — a one-file check: builds
  the candidate if absent, runs all gates + the 20-case judge, writes
  `remote_result.json`. Alexey may also run this on his M4 laptop.

## Requested action

1. codex: when `ss_reinflated.man` appears, judge it with the Rust executor
   (or fastest available) and reply with cases/ticks/score. If 20/20, I
   submit under my standing authorization.
2. Either of you: sanity-check the re-inflation idea itself — same ports,
   same per-pipe cell count, only the geometry between ports changes. I
   claim that preserves both resolution and capacity exactly; if you can
   think of a timing dependency it does NOT preserve (e.g. a machine that
   depends on a pipe's TRANSIT TIME being short, not just its capacity),
   say so before I burn a submission.
