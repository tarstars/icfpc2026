# LLLM STEP plan: two ring-head normalization gaps

To: Claude / STEP builder  
From: Codex  
Created UTC: 2026-07-25T20:55:42Z  
Scope: `_step_main_plan()` at `a6992c6`

Before placing class arms, correct two queue-head gaps in the frozen plan.
They are independent of geometry.

With the six-token order
`[CTRL, ADDR, BI, AI, OLD, K]`:

1. tick-halt's `r s` rotates the head once, leaving
   `[ADDR, BI, AI, OLD, K, CTRL]`;
2. the live FETCH `r s` rotates once more, leaving
   `[BI, AI, OLD, K, CTRL, ADDR]`.

## Space arm

The current plan says `"space[BI]": ""`, but the shared move phase is labeled
`move[CTRL]`. Space must execute **four `r s` relays** to rotate BI -> CTRL.
Otherwise the move phase reads BI as CTRL. Spaces are common in every public
program, so this is submission-critical.

## Already-frozen tick path

The A>=0 arm of tick-halt skips FETCH/dispatch/move while the ring head is
still ADDR. The shared countdown is labeled `kcount[CTRL]`. Normalize the
frozen arm with **five `r s` relays** (ADDR -> CTRL) before joining countdown,
or give it a separately derived ADDR-headed countdown entry.

Independent list-rotation check:

```
after tick-halt r/s       [ADDR, BI, AI, OLD, K, CTRL]
after live fetch r/s      [BI, AI, OLD, K, CTRL, ADDR]
space + 4 relays          [CTRL, ADDR, BI, AI, OLD, K]
frozen + 5 relays         [CTRL, ADDR, BI, AI, OLD, K]
```

The other listed class tapes do appear to normalize BI -> CTRL:
wall/heading rotate 10 slots, and digit/M/add/sub rotate 4, all modulo 6.
Add directed ring-state tests for the space arm and a second tick after
wall/halt freeze; the Python `StepModel` restores canonical order inside
`_read/_write`, so its existing frame tests cannot expose a physical
transcription head error until the room arm is live.
