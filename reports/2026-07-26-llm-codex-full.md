# Codex physical LLM full-public candidate

Date: 2026-07-26

## Candidate

- Artifact: `submissions/llm/llm_codex_01.man`
- Generator: `scripts/build_codex_llm.py`
- Preserved commit: `0e48cf3`
- SHA-256:
  `568d0b87937e9a41370d0b3434583d7109eb51ea9944b788e825e45c53e40ff6`
- Bytes: 9,137,982
- Occupied dimensions: 749 x 25,797
- Footprint: 665,485,209
- Parsed structure: 145 rooms, 231 pipes, 143 men

The candidate retains the exact setup, execution, and delta-render pipeline
from `llm_codex_00`. It adds a physical pre-tick stop detector so that any
live man on a wall freezes the global state, while all-halted states also
stop. Halted men standing on walls are ignored.

One physical protocol detail is important: the initial state entering the
runtime contains 64 packed world words, but every later full-tick response
contains only runtime state. The detector skips the world prefix exactly
once and then scans successive runtime streams directly.

## Public cases

The candidate passed all 14 public cases at the official 50,000,000-tick cap
through Claude's independently differential-tested C executor:

| Case | Ticks |
| --- | ---: |
| first steps | 5,877,438 |
| countdown relay | 20,047,788 |
| hello neighbor | 8,045,884 |
| bucket brigade | 10,178,879 |
| ping pong | 15,312,080 |
| switchboard | 12,205,273 |
| traffic jam | 10,794,079 |
| coin toss | 7,622,854 |
| pileup | 6,968,623 |
| long haul | 16,441,209 |
| cliffhanger | 11,362,261 |
| bounce house | 13,076,595 |
| grand tour | 27,216,732 |
| below zero | 8,419,831 |

This repairs all five former step-cap cases and all three former wrong-frame
cases without regressing the six cases passed by `llm_codex_00`.

## Adversarial and structural gates

- `tests/test_llm_roundstatus.py tests/test_llm_roundcontrol.py`:
  22 passed in 32.22 seconds.
- Complete `tests/test_llm*.py` suite: 2,012 passed in 858.86 seconds.
- Physical runtime test: all four `first steps` rounds passed.
- Multi-room fuzz: 50/50 deterministic cases at seed `20260726`, each with
  2-3 rooms and 1-2 pipes. The longest passed case used 40,748,909 ticks.
- Whole-machine pipe audit: 13,299 instructions fingerprinted as
  `491f6e5f195c396bcc99c653c9433e1bba1cd02659a121624c14bb00f980cccf`;
  13,041 lowercase instructions had more than one candidate pipe, the
  smallest binding margin was three cells, and there were no ties.
- Parser, `server_compat.validate_layout`, and `alexey_pipecheck`: passed.
- Every pipe has at least two cells; the shortest lengths are two.
- Canonical `scripts/preflight.py` under the slow Python judge passed all
  14 cases and printed `READY TO SUBMIT`. Average ticks were
  12,397,823.286 and local score was 8,250,568,020,438,638.
- The organizer WASM loaded the complete 9.1 MB machine and reported all 143
  initial runners. Its stock `stepN(5000)` harness later returned JavaScript
  `undefined`, so no execution result is inferred from that attempted check.

## Freshness and live state

Immediately before preservation, `git pull --ff-only` reported the branch
current and the authenticated API read still showed
`f077726c-a3b9-4ad3-b106-83091add453d` terminal at 14/28. No contest mutation
was performed while constructing or preserving this candidate.

Claude independently reviewed the frozen stop decisions, prefix transition,
and binding certificate, then explicitly approved submission in
`20260726T095730Z-APPROVE-submit-0e48cf3.md`.

## Live result

After a final Git pull, contest-clock read, authenticated read of the 14/28
predecessor, and artifact hash check, Codex submitted the candidate exactly
once:

- submission: `be96c6eb-e2bd-40a7-b5d2-a3aadbaf2b9b`;
- status: `done`;
- cases: **28/28**;
- dimensions: 749 x 25,797;
- area2: 665,485,209;
- average ticks: 13,185,917.785714285;
- score: 8,775,033,253,482,888;
- error and load error: null.

The terminal response and polling status are preserved as
`submissions/llm/llm_codex_01-submit.json` and
`submissions/llm/llm_codex_01-submit.err`.
