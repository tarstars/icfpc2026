# release: old TCP routing continuation is not score-positive

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T04:48:00Z`
- Task: `20260727-gpt-solvers-floorplan`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: no

After synchronizing with current `main`, I am releasing the TCP-specific routing
continuation. The 38->35 exact macro result remains a useful solver regression,
but the live TCP lineage is already 30x30, so routing the older 35-square
placement cannot improve score.

No TCP source, artifact, catalog, API state, or contest submission was touched.
The shared GPT experiment/report paths are reclaimed by the separately recorded
port-assignment task below.
