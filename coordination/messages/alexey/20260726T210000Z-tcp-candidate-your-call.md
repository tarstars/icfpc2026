# question: tcp candidate (+0.77%), margin-1 on the ring -- your lane, your call

- From: alexey
- To: claude
- CC: codex, gpt
- Created UTC: 2026-07-26T21:00:00Z
- Requires acknowledgement: yes (it is your artifact)

Ported today's probes onto tcp_08 (read-only sweep, per the endgame):

* **squeeze finds 2 rows on tcp_08** — your "tcp squeeze found nothing" was
  true of tcp_04/06; the rule "re-run after every layout change" pays again.
* Candidate: `experiments/alexey-tcp/tcp_09_candidate.man` — rows-only
  squeeze, 31x29 (fp unchanged, width binds), pipes [.,7,15]->[.,6,14].
* Verification: 6/6 public, local 958,117 -> 950,749 (+0.77%, ~13k live).
* **Risk you must judge**: the 15->14 ring now has margin 1 — peak occupancy
  measured 13 across ALL 6 public cases. The 6-cell (was 7) is peak-1
  transport, safe. If the ring's 13 is protocol-bounded (window size?), the
  candidate is safe; if it can reach 14+ on private cases, it deadlocks. You
  know the protocol invariant; I do not.
* sort_07 swept too: everything at Manhattan minimum, ring at capacity
  16/17, squeeze empty — its floor is real. memory skipped (0.09 pts left).

Submit it or bin it — no action from me either way. If you want the same
sweep on anything else of yours, name it; it takes minutes per program.
