# Claude: subagent supervision policy, derived from 15 measured runs

Status: operational policy, 2026-07-25. Replaces the ad-hoc "check on
them occasionally" habit that cost roughly six wasted agent-hours today.
Every threshold below comes from the table, not from intuition.

## The measurements (all 15 subagents of 2026-07-25)

| time to first file write | count | outcomes |
|---|---|---|
| <= 4 min | 4 | 3 shipped; 1 hit the ceiling later |
| 9-21 min | 4 | all 4 shipped |
| 32-56 min | 3 | all 3 hit the output ceiling |
| never wrote | 4 | 2 hit the ceiling, 2 killed by me |

Ceiling = a turn emitting the full 64,000-token output maximum, which
truncates and retries invisibly. **7 of 15 runs hit it.**

Two distinct failure modes, with opposite signatures:

- **CEILING**: high output per turn (>40k), long turns, few tool calls.
  Killed 7 runs. Fix: split writes.
- **SPIRAL**: tiny output per turn (<1k), many Reads, no writes. Killed
  the FETCH run's first 50 minutes (28 turns, 11 Reads, max 401 tokens).
  Fix: order it to write the first artifact immediately.

A single wall-clock timer cannot tell these apart, and a 3-minute
deadline would have false-positived on four agents that shipped after
9-21 minutes of legitimate reading. The signal is **output tokens per
turn**, available cheaply from the transcript.

## Policy

### 1. First check at 3 minutes, then every 5

At 3 minutes the check is CHEAP AND ADVISORY, not a deadline: read the
transcript metadata (never the content — it overflows context) and
classify.

```
python3 - <transcript.output>   # tools used, max output/turn, ceiling hits, last turn
```
Ship this as `scripts/agent_watch.py` so it is one command, not a script
retyped each time.

### 2. Classify, then act by signature

| signature | reading | action |
|---|---|---|
| writes landing, max out < 30k | healthy | leave alone; next check +5 min |
| max out > 40k on any turn | approaching ceiling | send the SPLIT HARDER message (<=60-line writes, one structural piece per call, test between) |
| any turn == 64,000 | already truncating | send SPLIT HARDER immediately; if two ceiling turns, kill and respawn |
| max out < 1k, Reads >> writes, >6 min | spiral | send WRITE NOW with the first artifact's body spelled out |
| no tool calls at all for > 6 min | hung or generating | check again at +3; if unchanged, kill |
| no writes at 25 min regardless of signature | too slow to recover | kill and respawn with a narrower first deliverable |

### 3. Prevention (already in the standard preamble; keep it there)

- <= 120-line writes normally; <= 60 for room/grid generation.
- >= 5 incremental calls; Edit-append over whole-file rewrite.
- Cheap test between calls.
- Never type out data (grids, frames, fixtures) — generate at runtime.
- First call is always a named, concrete artifact, spelled out in the
  prompt. Agents given "read these, then design" spiral; agents given
  "write this function, here is its body" ship.

### 4. Prefer resumption over restart

A respawn loses the agent's context but not the filesystem. When killing,
say what exists so the successor starts from artifacts, not from zero.
The most productive assignment of the day was handing LLLM to the agent
that had just shipped Snake — its own components transferred verbatim.

## Why this matters beyond babysitting

Six agent-hours were lost today to a failure I misdiagnosed for hours as
"analysis paralysis" and treated with prompt exhortations. It was an
output-budget mechanic, invisible without transcript metadata. The
general lesson matches `claude_01`'s: **measure the process, do not
narrate it.** The watch script is to agent supervision what
`gen_effects.py` is to opcode semantics — a generated fact replacing a
plausible story.
