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

## Addendum: the STEP3 post-mortem (user's diagnosis, confirmed)

Three-plus agent lifetimes died on "finish the interpreter room"; zero
tasks of that shape completed in one life, while narrow-lever and
rig-per-room tasks shipped at ~90%. The proximate cause was always the
64k output ceiling, but the task shape set the exposure: one large
coupled room makes whole-grid inspection the natural move, and that move
is the killer. The deeper error was conflating the MACHINE's
architecture (one compact room -- correct for score) with the WORK's
architecture (one task -- wrong for building). SCAN3 finished because it
was four rigs; Codex's 145-room machine won the case race because every
piece was trivially testable. claude_14's rule ("two failures -> change
the task, not the prompt") was violated here: the third dispatch changed
only the warnings.

Binding decision: if the LLM score lane resumes, STEP3 is FIVE
rig-scoped tasks (emit, round-in, tick-pass, phase-B integration,
phase-C integration), each with its own oracle slice and agent. Never
again "finish the room". Post-contest: the block-graph compiler + (nop n)
direction removes this task class entirely.

## Addendum 2 (11:40Z): sort k-rings KILLED by arithmetic; dispatch policy changed

Two more agents died at the 64k ceiling (tcp pass-2, sort k-ring), both
during the ANALYSIS phase, both leaving zero files. Total ceiling deaths:
six. The pattern is now unambiguous: the modelling phase is where agents
die, because modelling generates long output.

**Policy change, effective now: the supervisor does the analysis; agents
get build-only briefs whose first action is a WRITE.** A brief that says
"measure X, then decide" is a brief that kills its agent.

### The sort k-ring idea is dead -- arithmetic, done here in 2 minutes

Model: `ticks(n,k) = A*ceil(n/k)*(ceil(n/k)+1)/2 + B*n` with the measured
A=10.60, B=29.64, over the 19 real public lists (n from 1 to 16, **mean
6.3**):

| k | tick factor | box | fp factor | NET |
|---|---|---|---|---|
| 2 | 1.90 | 22x22 | 1.34 | **1.42x** |
| 2 | 1.90 | 24x24 | 1.60 | 1.19x |
| 2 | 1.90 | 26x26 | 1.87 | 1.01x |
| 3 | 2.24 | 26x26 | 1.87 | 1.20x |

Top-5 needs 2.8x. Best case is 1.42x, and only if a second pump, a
second man and a merger fit in 22x22 (they will not comfortably).

The previous builder's "2.5-3x realistic" estimate was anchored on the
**n=16** case, where the quadratic term dominates. Averaged over the real
distribution (mean n=6.3) the quadratic term is minor, so parallel rings
buy far less than they appear to. **Check the estimate against the actual
input distribution before believing any asymptotic argument.**

Sort stays at 896,305; the slot went to a tcp geometry repack instead
(C room is 18x14 at 40.1% interior fill, and its 14 rows set the box's
bottom edge; 35 -> 31 is 1.27x, a contained press-shaped task).
