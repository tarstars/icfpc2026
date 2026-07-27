# Codex: LLM physical geometry composed; review/help boundary

Branch `agent/codex-llm`, head `2541100`.

The physical setup path now reaches exact source-to-destination pipe cells:

`PACK stream -> ROOMFIND -> PERIMETER -> PIPESTARTS -> PIPETRACE`

Evidence:

- 178/178 combined component tests before composition.
- 48/48 focused post-hardening tests.
- four representative whole-chain programs pass byte-for-byte through the
  composed physical pipeline, including switchboard and pileup.
- composed geometry machine is 2,087 rows by 319 columns, server-compatible,
  and within the 50M tick cap on all four.
- fresh LLM standings remain 14/28 and zero points.

The position-first implementation now covers:

- every room rectangle from its unique man;
- ordered exterior candidate generation, including explicit off-canvas
  rejection rather than address wrapping;
- source arrow filtering in parser order;
- bends and source-to-destination pipe-cell tracing.

Bounded help request if Claude resumes: adversarially review `fabb871` and
`2541100`, focusing on terminal-arrow/body ambiguity and whether candidate
ordering exactly matches `Machine._find_pipes`. A separate useful build task
is INIT-FRAME from this rich stream; do not edit Codex's current modules
without an ownership transfer. The remaining critical path on my side is
metadata normalization plus the multi-man/pipe executor.
