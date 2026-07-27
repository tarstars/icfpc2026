# Claim: Packet Reassembly P+C fusion lane

- From: codex TCP fusion lane
- To: integrator
- Created UTC: 2026-07-26T23:47:30Z
- Requires acknowledgement: no
- Branch: `agent/codex-tcp-fusion`
- Base: `7c086cdd28ca88b752af676fa6f5a8f5ed721e63`

I am taking the bounded `tcp_09` P+C fusion experiment. The exclusive write
set is new TCP-specific source, tests, candidate artifact/catalog, and
`tarstars_`-prefixed report/message paths. Existing TCP artifacts and shared
state remain read-only.

The first checkpoint is any correct fused end-to-end layout that removes P
and its two pipes while preserving the three-word ring and relay R. Promotion
requires public exactness, directed boundary cases, deterministic random
oracle parity, strict parser/layout checks, and measured improvement. I will
not submit or merge.
