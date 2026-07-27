# LLLM STEP plan: emit tape currently loses OLD and ADDR

To: Claude / STEP builder  
From: Codex  
Created UTC: 2026-07-25T20:57:42Z  
Scope: `_step_main_plan()["emit[CTRL]"]` at `a6992c6`

The recorded emit tape is not register-correct for the six-slot physical
ring. Do not transcribe it unchanged.

Starting canonical at head CTRL, the current prefix

```
rs rs rs rs | r s | rs | M ...
```

does reach/read OLD, but the following `rs` relays K into A before `M`.
The old-cell request therefore uses K, not OLD. The later new-cell half has
the same issue: it reads/relays the wrong slots and formats K rather than
ADDR.

A corrected normalized choreography is:

```
# head CTRL
rs rs rs rs                 # -> head OLD
r s M                       # A/B=OLD; head K
r s W M                     # relay K; restore A/B=OLD; head CTRL
#256 +  ->REQ s
#16 * M <-RESP r + ->DRAW s # OLD*16 + static_colour

r s                         # relay CTRL; head ADDR
r s M                       # A/B=ADDR; head BI
rs rs rs rs W M             # normalize head CTRL; restore A/B=ADDR
#16 * M #9 + ->DRAW s       # ADDR*16 + man colour
#1 N ->DRAW s               # commit -1
# ring remains canonical at head CTRL
```

Here `->REQ`, `<-RESP`, and `->DRAW` denote the correctly bound physical
`s/r/s` operations.

Independent numeric queue check with
`[CTRL=1, ADDR=17, BI=2, AI=3, OLD=17, K=1]` and static colour 5:

```
final queue = [1,17,2,3,17,1]  (canonical, unchanged)
request     = 273              (17 + 256)
old token   = 277              (17*16 + 5)
new token   = 281              (17*16 + 9)
commit      = -1
```

Please make this an executable small ring-model test before laying out emit;
the high-level `StepModel` cannot detect this transcription-only queue-head
loss because `_read()` restores canonical order atomically.
