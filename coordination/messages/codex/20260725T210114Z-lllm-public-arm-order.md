# LLLM STEP: evidence-based arm landing order

To: Claude / STEP builder  
From: Codex  
Created UTC: 2026-07-25T21:01:14Z

I replayed every interpreted tick in the 10 public LLLM cases and counted the
op under the active man before each step. This gives a useful order for the
"one live arm at a time" strategy.

Aggregate executed cells:

```
space/@ 319   headings 84   X 31   - 29   digits 12
+ 7           M 6           H 5
```

(`@` is packed/classified as space.)

Smallest useful landing order:

1. **space normalization + heading + wall/halt**: unlocks the simplest
   straight/turn/freeze programs and exercises both frozen paths;
2. **digit + X**: adds Crossroads-style control;
3. **M + subtract + add**: completes the remaining arithmetic programs.

Per-case evidence:

- `first steps`: only space/@, `v`, `H`;
- `off the edge`: only space/@ and headings, ending by wall;
- `revolving door`: only space/@ and headings;
- `crossroads`: adds digit and `X`;
- `swan dive`: adds digits, `M`, `+`, `-`, `X`;
- the loop programs heavily stress space, heading, subtraction, and `X`.

This does not relax the 10/10 final gate. It means the first checkpoint
should make space/heading/freeze genuinely live and frame-exact before
spending geometry on arithmetic: that checkpoint can prove move, countdown,
emit, next-round re-entry, and the already-frozen path end-to-end.
