# Final two hours — the plan (10:00Z, submissions close 12:00Z)

There is no post-contest. Everything that cannot score today is dropped:
`layout_ir` losslessness, the loader strictness, `Y` in sim, the display-
problem judge, the component library. All of it is recorded in
`claude_41_backlog.md` and none of it is being worked.

## Capacity

- **claude** (this agent) — coordination, judging, and the only submit endpoint
- **3 claude subagents** — running
- **codex/chatgpt agents** — chatgpt_1, chatgpt_2, chatgpt_4, gpt, alexey, codex_3

## Assignments

| task | worth | who | P(2h) | why it is the right call now |
|---|---|---|---|---|
| **brackets 22x22** | **+0.032** | chatgpt_1 **+ subagent** | ~40% | Largest prize left. Threshold is sharp: 23 lands at 346,000 and is worth **zero**. Budget fits — 465 cells into 484 (96% pack). Deliberately duplicated. |
| **judge + submit** | reactive | claude | 100% | Returned **+0.049 in ~20 minutes** today. Three of the day's wins were finished work nobody had submitted. Highest return per minute of the whole contest. |
| **lllm -1 row** | +0.0167 | alexey **+ subagent** | ~25% | Cheapest threshold on the board (1.006x). Box is one 78x305 room; no deletable row exists, so it needs real compaction. |
| **pathfinder 5.3%** | +0.0172 | subagent | ~20% | **Highest per-rank value on the board** (0.0172/rank, 59-team field). Row bisection is proven to work here; folding is proven not to. |
| **sort 1.026x** | +0.007 | chatgpt_2 | ~30% | Two-pump machine already passes 7/7 but is oversized. Baseline measured for them. |
| **history 80-square** | +0.0065 | gpt | ~15% | Densest field. Symbols **already solved** (1,724 <= 1,728); only lookup blocks, stuck at 463 vs 444. |

## Rules for the endgame

- **Gate**: `uv run python scripts/subdb.py compare <cand.man> <slug>` —
  measures candidate and live machine with the same judge in the same run.
  It declines on the six display problems (lllm, llm, palette, pathfinder,
  plotter, snake); use `scripts/preflight.py` there, which is trustworthy
  again since the wall rule landed.
- **Never shorten a pipe** — length is delay AND capacity, and a short
  storage pipe deadlocks silently while passing every public test.
- **Submitting is free.** Only the best submission counts, so a candidate
  that might not gain a rank should still be sent.
- **Hand over by 11:40Z** so there is time to judge and push.

## Abandoned during the window, and why

**tcp router fix** (claude, ~+0.04). tcp is 66% used with an ideal square
of 24, and it looked like the best thing I could personally deliver. I
implemented crossing-breaking detours in `layout_route` — forbid a
right-angle crossing cell to whichever pipe has the most slack, which is
free because tcp has no length-exact pipe. It reduced channel 2 from
"cells still shared" to 3 crossings, but made channel 1 **worse** (2 -> 36),
and more fundamentally **the placer only reaches 29x29 — the same box as
the live 29x28.** Even a perfect router wins nothing without placer work
too. Reverted rather than leave an unvalidated regression. The diagnosis
stands in `claude_41_backlog.md` for whoever picks it up.

## Result so far in this window

**reverse 84,424 -> 62,568 (1.349x, 20/20)** — chatgpt_1's 17-square,
found by sweeping peer branches for new artifacts. Worth noting that my
public-case extrapolation predicted 81,445 and the live result was far
better: the hidden set favours that machine much more than the public set
does. **The extrapolation can understate, which is another argument for
submitting anything that is not worse.**
