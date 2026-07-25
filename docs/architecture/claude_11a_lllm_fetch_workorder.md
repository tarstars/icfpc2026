# WORK ORDER: LLLM FETCH station (world owner)

Half of EXEC per the approved split. Knows NOTHING about interpretation.
Independently implementable and rig-testable.

## Frozen interfaces

In from STEP (one pipe), phase-split by count:
- SETUP: first 64 tokens received are the packed world (claude_09
  format), pushed into the ring in order. Thereafter, every token is a
  REQUEST:
- `0..255`  : op fetch. addr=t. Respond `class<<4 | value` (one token).
- `256..511`: color fetch. addr=t-256. Respond `color` (0..15).
- `-1`      : full stream. Respond 256 tokens: the COLOR of every cell,
  canvas order, raw 0..15. (STEP formats addresses; FETCH only peels.)

Out to STEP: responses as above. Plus the private ring: FETCH <-> 2x4
RELAY room, combined pipe capacity >= 64+slack.

## Internals (memory_04 pattern, reuse aggressively)

Request addr -> word=addr/4, field=addr%4 (one `/` by 4). BP-counted
relay of `word` ring tokens; peel target via `/` 8192 ladder + field
X-ladder; re-emit token UNCHANGED (world is read-only); counted relay of
the rest. Record fields per claude_09: color=rec&15, class=(rec>>4)&15,
value=(rec>>8)&15 — peels are divides by 16. Full stream: one rotation
peeling all 4 records per token, sending 4 colors each.

## Deliverables / write set
`src/littleman/lllm_fetch.py` (pure-Python `fetch_reference(world,
requests)` + `build_fetch_rig()`: 3x3 I -> FETCH+RELAY -> 3x3 O; rigs
may use O rooms) and `tests/test_lllm_fetch.py`. Nothing else.

## Acceptance
1. Rig equality vs `fetch_reference` for: the world of every public
   LLLM case (via `lllm_loader.reference_stream` if landed, else a
   20-line local packer per claude_09) x request scripts covering: every
   addr 0..255 op-fetched; every addr color-fetched; -1 full stream;
   interleaved mixes; 30 fuzz worlds.
2. Directed: addr 0, 255; field 0..3 of one word; requests straddling
   word boundaries; two -1 streams back-to-back (ring order restored —
   count appends).
3. Binding audit (2in/2out) via ir_export map; layout gates; determinism;
   ticks per request + per full stream reported.
Model-first: `fetch_reference` green before ASCII.
