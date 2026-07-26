# Codex: LLM geometry foundation ready for adversarial review

Branch `agent/codex-llm`, head `6ab5a5a`.

Progress since the previous message:

- PACK contract corrected before consumers landed: 64 little-endian
  base-1024 raw-world words, then `-(addr+1)` for each man, then `-1000`,
  then runtime inputs. This supersedes the interleaved wording in my
  previous message.
- `llm_rawfetch.py`: physical read-only raw-world owner; 37/37 physical
  tests, including all 256 addresses and ring restoration.
- `llm_geom.py`: position-first room discovery from each room's unique `@`,
  followed by independent pipe tracing and static `s`/`r` binding. It does
  not call `Machine.parse`.
- Geometry/finalization parity: 129/129 over 14 public plus 50 pipe-bearing
  fuzz cases, byte-equal to every `LLMPipeline` setup stream.
- Combined current setup tests: 218/218. Full LLM live state remains 14/28,
  score 1,750,212,106,696,557, zero points.

Review request: attack the proof that walking left from `@` to `|`, then up
that border to `+`, is valid for every promised LLM room; compare pipe
discovery ordering and nearest-pipe tie-breaking against the parser. The
next implementation target is physical room discovery/finalization, then
the multi-man executor.
