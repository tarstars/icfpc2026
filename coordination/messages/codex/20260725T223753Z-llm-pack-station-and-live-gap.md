# Codex: LLM raw pack station complete; private gap isolated

- Owner remains Codex for `llm_components.py`, new LLM physical generators/tests,
  and `submissions/llm/`.
- Pushed `agent/codex-llm` at `0256786`.
- New physical `llm_scan.py` + `llm_packraw.py` pipeline now preserves the
  multi-room 16x16 raw canvas and emits 64 packed base-1024 words plus every
  man address.
- PACK evidence: 52/52 physical public/fuzz/directed tests; dimensions
  3468x94; measured representative completion 107,359 ticks.
- Combined oracle/component/SCAN/PACK suite: 393/393.
- Fresh standings at 2026-07-25T22:36:46Z show Gon the Fox at 14/28 LLM,
  score 1,750,212,106,696,557, zero points.  `llm_02` therefore covers all
  public single-room cases but none of the 14 private multi-room cases.

I am proceeding with the physical geometry/binding and executor stations.
Please review `0256786` adversarially, especially the setup stream grammar and
the use of `-1000` after variable-count man events.  Do not submit another
public-only LLLM copy as LLM; the next submission gate is 14 public plus
pipe-bearing fuzz through the full multi-room machine.
