# WORK ORDER: LLLM final assembly

All five component rooms exist or are in flight. This composes them into
one machine and submits it. It is WIRING, not integration risk: the built
components have already validated against each other (STEP's hooks armed
themselves against FETCH; DRAW was checked on real StepModel streams).

## Topology (no output room anywhere — frames are the output)

```
I -> SCAN -> CLASSIFY -> STEP <-> FETCH <-> RELAY
                          |
                          +-> DIST -> ADDRDRV/DATADRV/SWAPDRV -> LM-75
```

Pipes: I->SCAN, SCAN->CLASSIFY, CLASSIFY->STEP, STEP->FETCH(req),
FETCH->STEP(resp), FETCH<->RELAY (the ring, >=70 cells), STEP->DIST,
DIST->drivers, drivers->display sides.

## Sources (lift the room blocks; do not re-derive)

`lllm_scan.py`, `lllm_classify.py`, `lllm_step.py`, `lllm_fetch.py`,
`lllm_draw.py` — each exposes a rig; take the room grids out of the rigs
and place them with `canvas.Canvas`. Keep every room's INTERNAL geometry
byte-identical; only placement and pipe routing change.

## Mandatory checks before submission

1. `uv run python -m littleman submissions/lllm/lllm_00.man little-little-little-man`
   -> 10/10.
2. `uv run python scripts/preflight.py submissions/lllm/lllm_00.man little-little-little-man`
   -> READY TO SUBMIT.
3. Binding audit: `littleman.ir_export.machine_ir` — every `s`/`r` in
   STEP and FETCH resolves to its intended pipe (both have 2-in/2-out).
   Use `littleman.room_ports.audit` for margins; margin < 2 is a red flag.
4. Fuzz: >= 50 `llm_fuzz.corpus` cases judged against the `littleman.llm`
   oracle's frames. Zero failures required.
5. Second opinion: run 3 public cases through `claude/official-sim`
   (the organizers' own engine) and compare frames.

## Submission

`uv run icfpc-api --env-file /home/tarstars/prj/icfpc2026/.env submit
d91edb43-4e94-4541-b8f7-9c79ba8c8331 submissions/lllm/lllm_00.man
--confirm --wait > submissions/lllm/lllm_00-submit.json`

Standing authorization covers it once every gate above passes. Preserve
the response; message Codex after any contest mutation.
