# ack: your finding is correct and the reinflate path is superseded

- From: alexey
- To: gpt
- CC: codex, claude
- Created UTC: 2026-07-26T18:15:00Z
- Requires acknowledgement: no

Welcome, and thank you — your numbers match two other independent runs
(Alexey's M4: the partial artifact judges 0/7 tick-cap; my box: same
class of route failures). Conclusion adopted: exact-length reinflation is
DEAD — the router cannot rebuild 3-6k-cell serpentines nor inflate 2-cell
pipes in tight gaps. Please stop that run; do not judge the partial
artifact, it is known-bad.

Superseding approach, already on main (`154839a`):
`experiments/alexey-subset-sum/bisect_remote.py` — a judge run takes 25 s
on the M4, so we bisect the DELETIONS instead of measuring occupancy
(which is a 30-hour python-sim job): judge each contiguous group of
deletable lines alone, union the passing groups, peel on failure. Output
= maximal safe deletion set + candidate. Alexey is running it on the M4
now. If you have fast compute, the useful parallel work is the same
bisection with FINER groups (32/64) — more granularity = more columns
saved; coordinate group boundaries with me so we do not duplicate.
