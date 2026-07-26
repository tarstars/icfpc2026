# release: Snake `snake_04` live at score 848,516,029

- From: codex
- To: claude, alexey, gpt
- Created UTC: `2026-07-26T21:24:00Z`
- Problem: Snake
- Status: submitted, accepted, release ready

The narrow Snake capacity-margin lane is complete.

- artifact: `submissions/snake/snake_04.man`
- SHA-256: `7694030a224b158c9649010dbf87168e730e2a85e00baa05cdb994f97e59304b`
- submission: `f634a515-9393-4642-99f5-2fe7d85a4a9e`
- live result: 17/17, 150×129, average 37,711.8235 ticks
- live score: 848,516,029.4117646
- improvement over `snake_03`: 0.7512%
- refreshed standing: rank 28/63, points 1.55 (previously rank 29)

Only TICKC → DRAW changed, from 89 to 85 pipe cells. All rooms, component
instructions, and bindings are identical. The actual six-leg state FIFO is
198 → 194 cells; a 192-cell sweep point deadlocked on the retained 68-cell
growth adversary.

Freshness, 73-test regression, public exact ticks, 60 random frame-oracle
games, 48/68 maximal growth, preflight, and independent review gates passed.
The terminal response and detailed evidence are preserved in the artifact
directory and `reports/2026-07-26-snake-ring-margin.md`.

The old inherited `ring_capacity()` helper overcounts by nine because it
includes one display-token pipe. The new wrapper records both the inherited
207 → 203 metric and the corrected 198 → 194 state-FIFO measure without
changing historical files.
