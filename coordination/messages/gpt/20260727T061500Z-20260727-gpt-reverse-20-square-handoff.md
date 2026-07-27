# handoff: Reverse single-Y farm reaches 20x18 and score 73,550

- From: gpt
- To: claude
- CC: alexey, codex, gpt solver line
- Created UTC: 2026-07-27T06:15:00Z
- Task: `20260727-gpt-reverse-fresh-farm`
- Branch: `agent/gpt-reverse-fresh`
- Payload head: `4ff24cf4ca30d986919d4021fab8cb47e64a6074`
- Supersedes: `20260727T053000Z-20260727-gpt-reverse-21-square-handoff.md`
- Requires acknowledgement: YES

## Exact candidate

```text
artifact: experiments/gpt-reverse-fresh/reverse_fresh_20.man
sha256:  a94a74bc0d422648579f718a6221aff10e0d22dc0eb397751f721457f59ae28d
size:    20x18, 348 bytes
public:  8/8 organizer WASM
```

Exact public ticks to final correct output emission:

```text
[148, 85, 134, 211, 120, 127, 253, 393]
average = 183.875
score   = max(20,18)^2 * 183.875
        = 73,550
```

Current live Reverse is 84,423.95. The measured reduction is **12.880172036%**
(1.147844324x). This supersedes my 21x18 candidate at 77,781.375.

## Architecture change

The solver replaced the alternating two-Y worker factory with one six-tick
recurrence:

```text
Y -> m -> d -> ^ -> blank -> > -> Y
```

One worker is born every six ticks; the countdown chain costs seven ticks per
BP unit, so later workers emit one tick earlier. BP-zero exits the loop and the
controller returns to the next-round input U. There are no unused workers,
sentinels, parity returns, or reset protocol.

## Validation

```text
1,277 / 1,277 deterministic organizer-WASM stress cases
maximum stress runtime 4,705 ticks
```

Coverage:

- every length 1..16;
- ascending/descending and alternating lifecycle streams;
- 32 full-size rounds and 64 singleton rounds;
- all 256 ordered length pairs;
- 1,000 random one-to-five-round streams;
- signed extreme values.

Static gates pass: byte-identical generator, SHA, parser 3/2/1, input-room
single pipe, `server_compat`, and pipe lengths `[2,3]`.

Reproduce:

```text
PYTHONPATH=src python3 \
  experiments/gpt-reverse-fresh/verify_single_y_candidate.py
```

## Requested action

Please acknowledge, fetch the branch, run current Git/API freshness and the
focused verifier, then submit the exact SHA if the live best has not already
been superseded. GPT performed no contest mutation.
