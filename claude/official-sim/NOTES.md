# Official littleman oracle (organizers' engine, headless)

The site's "TypeScript simulator" is actually a Go->WASM engine. The JS
bundle (`vendor/embed.js`, pretty at `vendor/embed.pretty.js`) contains no
interpreter — only UI + a runner that drives `globalThis.littlemanWasm`
from `/wasm_exec.js` + `/littleman.wasm` (both vendored here). We run that
exact WASM under Node v18: the truest local oracle, `Y` included.

## WASM API (session-based; every call returns a JSON string, `type:"error"` on failure)
- `newSession() -> handle`, `closeSession(h)`, `reset(h)`
- `load(h, rows: string[], input, expected, framesJSON) -> state`
  - input/expected: ints joined by spaces, rounds joined by ` / `
  - expected gates round release; `outputSettled` flips when all matched
- `step(h)`, `stepN(h, n, stopOnFrame) -> state`, `back(h)`
- `analyze(rows)`, `flow(rows)`, `route(...)`, `validOps()` (includes `Y`),
  `structuralGlyphs()` = `+-|<>^v=:`
- state: `{entities:{runners[{id,pos:[x,y],dir:[dx,dy],halted,a,b,backpack
  (int64 as strings)}],pipes,rooms,displays}, step, halted, reason
  ("done"|caps|fatal-kind), fatal:{reason,pos,cell,value}, output,
  inputReleased, inputRead, outputSettled, frameCommitted, frameJudge}`
- fatal reasons seen in bundle: wall, split-limit, bad-op, no-pipe,
  display-value, display-addr, display-swap; caps: step-cap/op-cap/time-cap

## Files
- `engine.mjs` boots the WASM (~80ms); `harness.mjs` is the CLI:
  `echo '{"program":"...","input":[[1,2]],"expected":[[3]],"maxTicks":1000,
  "trace":true,"stopOnSettle":true}' | node harness.mjs`
- `run_checks.py` — acceptance suite (all 5 pass, 2026-07-25)
- `smoke.mjs` — minimal raw-API example

## Gotchas
- Runner pos is [x=col, y=row]; sim.py Man is (r, c). dir [dx,dy] == sim
  (dc, dr). Registers arrive as strings (int64-safe).
- Official wall crash: the man visibly enters the wall cell, fatal fires
  the tick after; sim.py errors on the attempt. Reasons agree; positions
  around a crash do not.
- Public test cases are independent runs; the editor chains them as ` / `
  rounds in one machine (state persists — outputs then differ from the
  per-case `out` lists for stateful programs like memory).
- Y semantics verified here: split demo halts 1->2->both-on-H; meeting
  copies annihilate (men count -2, no error), matching /split.
