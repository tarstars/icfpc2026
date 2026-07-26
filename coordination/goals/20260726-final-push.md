# GOAL: raise our table position until 2026-07-27T09:00Z, sharing with the team

- Set: 2026-07-26T20:45Z by the user
- Deadline: **2026-07-27T09:00Z** (standings freeze 10:00Z)
- Team: claude (me), codex, alexey, gpt — four writing lines
- Standing rule: share findings; interact rather than duplicate

## Where we are

Board ~24.9/32. Today's team movement is large and mostly NOT mine:
subset-sum 91.77T -> 37.40T (alexey), history 85x85 -> 84x84 live
(codex, on my encoder), matmul 33.3B -> 8.44B (me then codex), brackets
3.49M -> 484k (me then alexey), tcp 5.66M -> 1.64M (me), snake 1.58B ->
855M (me then codex), reverse 472k -> 84.9k (me then alexey).

## What I do in the remaining hours

1. **Verification service.** I hold the fastest local judge (C fastsim:
   subset-sum in 44s where alexey reports 30+ min) and the strictest
   gate. Running peers' candidates is higher value per minute than
   building my own — alexey has an unverified 2.36x subset-sum candidate
   right now.
2. **Bank k-ring** (+0.15 at 22x22). MERGER is built; assembly remains.
3. **Endgame sweep at ~07:30Z.** Mandatory. Recompute the next-place
   ladder and spend the last window wherever one small factor buys back
   places lost to field drift.
4. **Clear the ack backlog** and keep it clear — 8 unacked when this goal
   was set, across three peers.

## What I do NOT do

Start any architecture rewrite (matmul packed lanes, gradebook record
ring, sudoku nine-word state). Measured: they need 100x to pay, and
none is a 13-hour job. They are the post-contest plan in claude_34.

## Rules that stay in force

Verify in my tree before submitting — own pytest, own judge, own
preflight. Submit only via `icfpc-api ... submit <UUID> --confirm --wait`
with stdout and stderr separated. `.man` files immutable; on a name
collision the incoming Tarstars/Codex artifact takes a `tarstars_`
prefix (codex policy, user-directed, 2026-07-26T15:59Z). Sweep the peer
inbox every 30 minutes and around every submission.
