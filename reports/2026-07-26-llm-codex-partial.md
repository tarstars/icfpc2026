# Codex physical LLM partial candidate

Date: 2026-07-26

## Candidate

- Artifact: `submissions/llm/llm_codex_00.man`
- Generator: `scripts/build_codex_llm.py`
- Generator source commit: `aae0c12`
- SHA-256: `fc37fe21ec2e138d9db159d469be2bece6aade2f281392fa7b8c36bf57749ec8`
- Bytes: 8,736,552
- Occupied dimensions: 749 × 25,207
- Footprint: 635,392,849
- Parsed structure: 135 rooms, 217 pipes, 133 men

The machine physically composes raw SCAN, four-cell packing,
destination-aware geometry discovery, normalized state construction, exact
one-tick execution, persistent state feedback, and full 16×16 rendering.

## Public sweep

The artifact was parsed once and executed through Claude's independently
equivalence-tested C fast executor from `origin/agent/claude` commit
`5626002`.  The fast executor reported the same 20,631,814 ticks as the base
Python simulator on `first steps`.

| case | result | ticks | matched rounds |
| --- | --- | ---: | ---: |
| first steps | pass | 20,631,814 | 4 |
| countdown relay | tick cap | 50,000,000 | 10 |
| hello neighbor | pass | 40,399,469 | 8 |
| bucket brigade | pass | 24,675,886 | 5 |
| ping pong | tick cap | 50,000,000 | 9 |
| switchboard | pass | 44,213,033 | 9 |
| traffic jam | tick cap | 50,000,000 | 10 |
| coin toss | wrong frame | 39,883,859 | 4 |
| pileup | wrong frame | 39,404,383 | 6 |
| long haul | tick cap | 50,000,000 | 10 |
| cliffhanger | wrong frame | 35,168,995 | 3 |
| bounce house | pass | 43,721,603 | 9 |
| grand tour | tick cap | 50,000,000 | 10 |
| below zero | pass | 31,670,608 | 5 |

Result: 6/14 exact public cases. Five of the failures matched every round
reached and then hit the tick cap; three produced a wrong later frame.

## Gates

- Base Python simulator, raw `first steps`, all four rounds:
  `CaseResult(passed=True, ticks=20631814, reason=None)`.
- Slow-input regression: a 1,000-tick gap between every normalized token
  still produces the exact initial frame. This caught and fixed an uppercase
  `R` collision between STATECOPY's external input and its scratch ring.
- Focused statecopy/controller/machine suite: 32/33 passed before correcting
  the expected room count; the corrected three focused gates then passed.
- LFS rule confirmed before adding the 8.7 MB artifact; `git lfs status`
  identifies it as object `fc37fe2`.
- Canonical preflight load gates:
  parse OK, server layout OK (no shared walls and one pipe at the input room),
  all pipe lengths at least two.
- Canonical all-case wall-tolerant Python preflight was interrupted after
  14.5 CPU-minutes because it had not finished. It is not represented as a
  passing full preflight. This is an explicitly partial candidate.

The live freshness read immediately before preservation still showed
submission `25e57bf4-1596-49ae-8f50-3cc9ad980926` terminal at 4/28. A
partial submission is justified only if the terminal server result improves
that pass count.
