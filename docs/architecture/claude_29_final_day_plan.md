# Final-day plan, post-LLM (2026-07-26 ~10:30Z; freeze 2026-07-27T10:00Z)

Codex's physical LLM machine went 28/28 live at 10:02Z (be96c6eb, score
8.78e15). The compact SCAN3/STEP3/LLM3 lane stopped per the
first-full-pass rule; checkpoints preserved (claude_24/25, harness with
round-1-end-to-end proof). Team total at the stop: 24.54/32.

## Where the remaining 7.46 points actually live

Measured 10:15Z, per problem: available = 2.00 - points, with the factor
needed to reach top-5 among full-passers.

| problem | avail | x to top-5 | verdict |
|---|---|---|---|
| sudoku | 0.86 | 6,632x | algorithmic chasm -- skip |
| pathfinder | 0.81 | 1,581x | Codex's; chasm -- skip |
| gradebook | 0.76 | 742x | chasm -- skip |
| **little-little-man** | **0.73** | 907x (their artifact) | **only credible instrument: the compact machine (~30x better as-is); needs Codex/user blessing to resume as a SCORE lane** |
| matmul | 0.72 | 823x | chasm -- skip |
| plotter | 0.70 | 268x | chasm -- skip |
| subset-sum | 0.66 | 125,982x | skip forever |
| brackets | 0.40 | 11.9x | state-ring redesign killed 2 agents -- hold |
| snake | 0.35 | 9.8x | needs from-scratch controller (proven) -- hold |
| **tcp** | 0.32 | 6.1x | **pass 2 dispatched: named levers, ~1.3-1.6x** |
| **reverse** | 0.30 | 6.1x | pass 3 candidate: pipe-length reorder untried |
| **sort** | 0.28 | **2.8x** | **k-ring redesign dispatched: the only sub-3x top-5 gap; builder-estimated ceiling 2.5-3x** |
| history | 0.28 | 1.3x | encoder done, machine unbuilt; 85x85 plan gains only the 7744 band (+~0.05) |
| lllm | 0.18 | 1.8x | second press possible (+0.05-0.1) |
| memory | 0.10 | 1.8x | skip |
| triangle | 0.00 | 1.0x | done (rank 1) |

Field drift is real (sudoku 58->63, plotter 46->50 in half a day with no
action of ours): late banking beats early perfection.

## The queue

1. sort k-rings (running) -- best ratio on the board.
2. tcp pass 2 (running) -- cheap named levers.
3. LLM compact as a SCORE lane -- proposal open with Codex; resume on
   blessing. Largest pool, highest variance.
4. reverse pass 3 (pipe-length reorder, O(n) candidate).
5. lllm second press; history machine build -- small, if slots free.
6. MANDATORY: T-minus-2h standings sweep (~08:00Z) -- spend the last
   window wherever one factor buys back drifted places.

## Standing rules

Verify in-tree before submitting; server_compat for anything
wall-trick-adjacent (the triangle lesson); sweep the Codex inbox around
every submission and every 30 minutes -- and never pipe the sweep
through tail (that hid a stop order for 7 minutes today).
