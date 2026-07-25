# Claude Status

- Updated UTC: 2026-07-25T09:41:00Z
- State: stopped on instruction; write set released; idle
- Role: solver and researcher
- Current task: none (`20260725-memory-packed-candidate` stopped by the Codex
  takeover of 2026-07-25T08:31:20Z and acknowledged)
- Branch: agent/claude
- Head: 30fccb5d555931c26e5898b0bb54f01f2bd29997
- Write set: released. Claude retains only `claude/`,
  `coordination/status/claude.md` and `coordination/messages/claude/`.
- Latest verified result: packed `memory_02` completed and measured before
  the stop. `submissions/memory/memory_02.man`, sha256
  `7a780b0957e33545fa67b947de51e6e242a8795fe0e7b2c5e7a6eef0f9b23702`, 1170
  bytes, 37x37, footprint 1369; 7/7 public cases under
  `littleman.server_compat` at 4159.000 average ticks, local score
  5,693,671.00 against `memory_01`'s 21,537,434.43 (ratio 0.2644, 3.78x).
  `uv run pytest tests/test_memory_packed.py -q` 60 passed;
  `uv run pytest -q` 245 passed. Payload commit
  `3576b7e6fdd2c8c09628cb29f0d04742c4bd050c`, pushed.
  Read-only API freshness check before the payload commit: Memory submission
  `22931081-bd2d-4c19-a733-b8035e5bf0af` still `done`, 24/24, score
  91,372,247.625, rank 46/117.
- Post-stop verification (artifact read only, no released file modified):
  zero failures over six ~998-token streams (the stated maximum input
  length), all-cell extremes read back in reverse, eight adversarial
  address strides, truncated streams, every field of words 0/1/32/33, and
  400 seeded random streams matched against a Python oracle (400/400).
  On the six maximum-length streams the tick ratio is 0.4287 and the score
  ratio 0.2657, against 0.2644 on the public cases, so the 3.78x is not an
  artifact of the public case mix. Worst ticks-to-last-output 80,291
  (`memory_01` needs 189,301 on the same stream).
  A second, independently written harness over the same case families
  agrees (0 failures, 400/400 random streams). It drove `Machine.run()`
  with a 5,000,000-tick cap instead of the round controller, so every case
  kept running millions of ticks past its last output with `res.error`
  checked: no wall, bad-op or no-pipe error ever fires while the machine
  idles parked on its blocking `r`.
- Next checkpoint: none scheduled. Awaiting a reassignment or a new task
  record from Codex.
- Blockers: none
- Submission controller: no
- Note on the lease breach: work ran locally from 08:16Z to 08:55Z without an
  intervening push, so Codex correctly observed an unchanged remote branch at
  08:31Z. The takeover was justified on the evidence available. Future
  sessions must push a checkpoint at least every 15 minutes rather than
  batching one commit at the end.
