# Claim: correct input-room pipe counting

- Task: `20260802-chatgpt1-io-pipe-counts`
- Sender: chatgpt_1
- Timestamp UTC: 2026-08-02T06:42:00Z
- Branch: `agent/chatgpt-1-io-pipe-counts`
- Stacked base: `agent/chatgpt-1-server-loader-validation` at `ecb7c1eb6a57cd4e57d0c714ca3415f1d2aaae57`

I am taking the focused C5 correctness task. The change will narrow the input-room check from all adjacent pipe cells to actual outward-pointing pipe starts immediately outside the border, preserving the observed `reverse_03` rejection while accepting organizer-approved matmul layouts.

No contest mutation or `main` integration is in scope.
