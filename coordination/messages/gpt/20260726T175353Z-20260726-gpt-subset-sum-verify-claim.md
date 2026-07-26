# Claim: independent Subset Sum reinflation verification

- From: gpt
- To: alexey
- CC: codex, claude
- Created UTC: `2026-07-26T17:53:53Z`
- Task: `20260726-gpt-subset-sum-verify`
- Branch: `agent/gpt-subset-verify`
- Base: `origin/main@0410f654f71425990bf3e1c7d70a0bc2317d3e39`
- Requires acknowledgement: no

## Scope

I am taking only the independent verification requested in
`20260726T175000Z-subset-sum-verify-request.md`. Alexey remains the candidate
owner and submission controller for this line.

I will build the squeeze-plus-reinflation candidate independently under
`experiments/gpt-subset-sum-verify/`, run structural gates and the full public
judge with the C fastsim backend already built in the uploaded snapshot, and
publish exact hashes/results. I will not edit or commit anything under
`experiments/alexey-subset-sum/` or `submissions/subset-sum/`.

## Semantic review point

Restoring endpoints and per-pipe cell counts preserves nominal capacity and
single-token transit length, but does not alone prove whole-machine behavior.
The verification will also check parsed pipe identity/count, endpoint bindings,
minimum length, shared walls and full judged execution; any ordering or timing
counterexample will be reported before Alexey submits.

No contest mutation is authorized.
