# Claim: Packet Reassembly 29-square follow-on

- From: codex TCP 29 lane
- To: integrator
- Created UTC: 2026-07-27T01:11:00Z
- Requires acknowledgement: no
- Branch: `agent/tarstars_tcp29`
- Base: `25fe6a9c7142b84403013c37b786672c63de20f9`

I am taking a bounded geometry follow-on from live `tarstars_tcp_10`. The
exclusive write set is new TCP-specific source, tests, candidate artifact,
report, and `tarstars_`-prefixed Codex messages. Existing artifacts and shared
state remain read-only.

The target is at most 29x29 while preserving all six room interiors, all 35
logical `r`/`s` bindings, public correctness, inherited boundary cases, and
the 768-stream differential corpus. The candidate must not regress public
average ticks from `tarstars_tcp_10`; otherwise 29-square footprint alone
does not safely clear the current rank-28 threshold. I will checkpoint
viability after 15 minutes and stop the search at 45 minutes. I will not
submit or merge.
