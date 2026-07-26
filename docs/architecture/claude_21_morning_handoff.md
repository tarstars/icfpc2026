# Morning handoff — 2026-07-26T06:00Z

What changed overnight, what to trust, and what to do next.

## Headline: LLLM is solved

`submissions/lllm/lllm_03.man` passes **21/21** on the server, score
**22,187,469,586** (submission `efce1ac1-ece0-4557-a08e-4d34edd9dd4d`).
It scored **zero for the entire contest** until 04:40Z; it first passed
21/21 at 139,039,110,268 as `lllm_02.man`, then a geometry press cut the
score 6.27x at 05:20Z.

The same artifact submitted to **LLM** passes **2/28**
(`e57fd7d2-352d-4929-a474-2009a6af4fd0`), because LLLM is a strict subset
of LLM. LLM's remaining cases need pipes and multiple men, which this
machine does not implement.

**The live artifact is `lllm_03.man`.** `lllm_00.man` is the file
`scripts/build_lllm.py` overwrites on every run — do not submit it
assuming it is the pressed one.

## Board

| problem | cases | was | now | factor |
|---|---|---|---|---|
| **LLLM** | **21/21** | — (zero) | **22,187,469,586** | new |
| **LLM** | **2/28** | — (zero) | partial | new |
| snake | 17/17 | 8,838,759,329 | 1,576,985,655 | 5.6x |
| plotter | 20/20 | 9,367,793,668 | 3,076,834,345 | 3.04x |
| matmul | 20/20 | 33,286,994,352 | 20,898,177,200 | 1.59x |
| sudoku | 20/20 | 25,480,732,026 | 16,126,208,644 | 1.58x |
| gradebook | 20/20 | 81,914,188,255 | 74,257,771,460 | 1.10x |

Untouched: subset-sum, tcp, brackets, sort, reverse-a-list, memory,
triangle, history — all still at 100% of cases.

**CORRECTION (06:20Z): pathfinder is NOT at zero** — it passes 18/18,
rank 20/24. Codex solved it. Every graded problem now passes 100% of its
cases except LLM at 2/28.

## What to do next, in value order

1. **Pathfinder** — up to 2 points, `privateTestCount: 0`, so one passing
   case of seven makes us eligible. As LLLM proved, submit partial early
   and often.
2. **LLM's pipe/multi-man support.** 26 cases are unclaimed there and the
   interpreter core already works. It needs: up to 3 rooms, up to 2 pipes
   (<= 20 pipe cells), several men, and the `s`/`r` ops. This is the
   single largest block of unclaimed points left.
3. Subset Sum — see the caveat below.

The LLLM press LANDED at 05:20Z: 141x775 -> 307x312, footprint
600,625 -> 97,344, score **139,039,110,268 -> 22,187,469,586 (6.27x)**,
still 21/21 (`efce1ac1-ece0-4557-a08e-4d34edd9dd4d`). Occupancy was 49.6%
by room box but only **9.62% of cells non-blank** — almost all air. All
four clusters moved rigidly into three column bands instead of four row
bands; only the 3 inter-cluster spine pipes were re-routed, so all 13
rooms stayed byte-identical with 0 pipe-role diffs and STEP's margins
unchanged at s=2/r=3. One constraint worth remembering: STEP's DRAW-out
(row 54) and LOAD-in (row 55) are on adjacent west-wall rows, so the
outgoing pipe cannot cross the incoming one locally.

## Things that will cost you time if you do not know them

- **Check `status` in the `problems` listing before starting anything.**
  `atoi`, `hello-world`, `max-element` and `palette` are ungraded practice
  and return `403 … does not accept submissions`. I lost an agent-hour and
  two agents to this. Nothing local tells you; the slug does not hint.
- **`data/small/problems` is a REDUCED copy.** 10 LLLM cases locally vs 21
  on the server, 14 LLM vs 28, 6-7 public vs 20 on most others. Local pass
  counts understate results — LLLM read 5/10 locally while scoring 10/21.
- **Redirect stderr separately when submitting.** Three records had
  `submission status:` lines ahead of their JSON, so every tool reading
  them skipped the record; snake_01's 5.6x was invisible in our own board
  table for hours. Fixed, but the habit matters.
- **Scoring is 2 points per graded problem**: `cases_passed/cases_total`
  plus a rank fraction. Absolute score only moves the rank half. Full
  working in `claude_20`.
- **Subset Sum is a trap in both directions.** Its 91.8 trillion looks
  alarming but is worth one rank point like everything else, and we
  already pass 20/20. Its docstring admits to being "a correctness-first
  generated layout" so the slack is probably large — but **one local judge
  run takes 15m25s**. Budget wall-clock, not difficulty.

## How the LLLM machine actually got finished

Worth recording, because four attempts at "finish STEP" had failed and
the fix was not technical.

The task was **shrunk to one 4x4 program** — `first steps`, three ticks,
needing only a heading and a halt — and then each remaining phase was
handed to a **fresh clock carrying the previous agent's own notes**. The
last four handoffs landed in 26, 9, 2.5 and 9 minutes of agent time
against a task that had consumed a full day. Two supporting moves:

- An **assembly harness built in parallel** with the unfinished component,
  whose only job was to report *where* execution stalled. It located the
  stall as "halts on its own class-staircase stub at room-relative
  (44,42), tick ~123,400" — which turned a vague blocker into a one-line
  target.
- A **fast inner loop**. The agent was iterating through full-machine
  rebuilds at minutes per cycle; switching it to `StepModel`/`sim` on the
  STEP room alone, with the full assembly used only to confirm, is what
  made the last three rounds minutes instead of hours.

Technical findings that generalise:

- **Long corridors must be left BLANK.** A man keeps his heading across
  empty floor, so a blank column crosses every existing walkway without
  diverting either man. Columns 61/67/71 and rows 147/148 are corridors
  nothing else touches.
- **Arms can own alternating rows.** The `X` arm works because each arm
  owns an odd row, leaving even rows spare for the two sign arms.
- **Dead paths hide behind unimplemented features.** The frozen-tick path
  had never executed, because until wall-freeze existed no case reached a
  second tick after halting. It ran east into empty floor. Expect a
  feature to reveal a second bug in the code that was waiting for it.
- **Read the shape of a failure, not just the verdict.** Three cases
  failing exactly 3 deltas short — two pixels and a commit, one whole
  round — with ticks far below the cap says "a man stopped", not "a class
  computed a wrong value". That pointed at routing rather than arithmetic
  and saved the night.

## Press methodology, now measured

**Measure occupancy first** (room cells vs bounding box). It predicted
every outcome tonight:

| target | occupancy | result |
|---|---|---|
| matmul | 43.9% (6.1% glyphs) | -37.2% |
| gradebook | 90.4% | -8.8%, near its floor |

**The tick lever is a dud.** Cutting gradebook's command/ack loop and
relay laps by 25-40% moved avgTicks by 0.5%: ticks are intra-room walking
and interiors are off limits to a press. Footprint is the lever.

Every press must clear a **binding audit with 0 pipe-role diffs**
(`ir_export.machine_ir` re-keyed by room and cell offset) and keep
`room_ports.audit` margins >= 2. A silent re-binding is the characteristic
failure of this whole class of change and it does not show up in the
public cases.

**Capacity is correctness, and it must be measured rather than argued.**
The plotter press settled its ring question with a +20-cell probe (+620
ticks ⇒ traversed once per pixel, so its 233 cells were kept exact). The
snake press earlier found the public cases never stress the ring at all,
and needed a purpose-built 48-cell maximal-growth game to justify a
change.

## CORRECTION 06:20Z — standings ARE readable, by UUID

`icfpc-api standings <slug>` silently returns `{"rows": []}`. Given a
problem **UUID** it returns the full table. Every "rank is unmeasured"
caveat below is therefore wrong, and the measured position is in
`coordination/goals/20260726-llm-and-rank.md`: team **wheezards**,
**22.86 of 32 points**, and the gap to the best team is 1,000x-227,421x
on the mid-size problems — a gap no geometry press can close.

## Closing board, 2026-07-26T05:30Z

| problem | cases | box | live score |
|---|---|---|---|
| subset-sum | 20/20 | 3646x3029 | 91,769,596,778,390 |
| gradebook | 20/20 | 390x404 | 74,257,771,460 |
| **lllm** | **21/21** | 307x312 | 22,187,469,586 |
| matmul | 20/20 | 128x145 | 20,898,177,200 |
| sudoku-validity | 20/20 | 198x194 | 16,126,208,644 |
| plotter | 20/20 | 155x185 | 3,076,834,345 |
| snake | 17/17 | 153x154 | 1,576,985,655 |
| memory | 24/24 | 34x32 | 23,344,360 |
| tcp | 20/20 | 37x37 | 5,655,750 |
| brackets | 26/26 | 37x41 | 3,494,864 |
| sort | 25/25 | 19x18 | 1,367,454 |
| reverse-a-list | 20/20 | 16x16 | 472,346 |
| triangle | 19/19 | 9x9 | 891 |
| **llm** | **2/28** | 307x312 | partial |

**13.07 of 14** test-case points across the problems we have touched;
**pathfinder** is the only graded problem never attempted.

Six submissions went live overnight, every one verified here before
submitting (own pytest run, own judge run, own preflight) rather than on
the agent's report: sudoku, plotter, gradebook, matmul, LLLM x3, LLM x3.
