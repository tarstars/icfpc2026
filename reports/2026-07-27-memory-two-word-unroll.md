# Memory: shared two-word STATION relay

Date: 2026-07-27
Status: live, 24/24

## Result

`memory_13` replaces only the packed machine's STATION and extends that room
by one row. It passes all seven public cases and reduces public ticks by
10.87398%. The 30-square footprint is 7.01546% larger, leaving a net local
score improvement of 4.62139% over live `memory_12`.

| Property | `memory_12` | `memory_13` |
| --- | ---: | ---: |
| SHA-256 | `e63c3e20…592e` | `032b067b…0ae9e` |
| Bytes | 794 | 817 |
| Dimensions | 29×29 | 29×30 |
| Footprint | 841 | 900 |
| Public ticks | `[292,608,1510,1082,1512,908,20656]` | `[286,557,1302,989,1284,813,18448]` |
| Public average ticks | 3,795.429 | 3,382.714 |
| Public score | 3,191,955.43 | 3,044,442.86 |

The exact public tick reductions are `[6, 51, 208, 93, 228, 95, 2208]`.
The generated child differs from its exact parent in 138 cells, all inside
the extended STATION envelope at global rows 18–29 and columns 3–21. All
seven pipes retain their exact cells and lengths.

## Shared loop

The packed protocol already supplies a free phase tag in register B:

- READ holds `43-shift`, which is always positive for shifts 0, 21, and 42;
- WRITE holds `~(MASK21<<shift)`, which is always negative because the
  21-bit field never reaches bit 63;
- ring initialization is kept separate and leaves B at zero.

READ first relays its mandatory target-side word. READ and WRITE then share
the same parity branch: odd `k` relays one tail word, even `k` relays none,
and `]` produces `floor(k/2)`.

The counted loop is a rotated two-column form of `r s m r s a`. Its entry
arrow feeds the branch without executing a relay, so `BP=0` exits directly.
Every positive lap relays two words, decrements BP once, and costs ten ticks.
On exit, `W X` branches from B's sign; a branch-local `W` restores the
original A/B registers before READ decoding or WRITE splicing.

The old initialization loop remains independent because an empty ring cannot
be seeded through a receive/send relay.

## Freshness and validation

The branch fast-forwarded to `origin/main` commit `608a4c3` before candidate
work. The unrelated dirty Subset Sum artifact was preserved and never staged.

At `2026-07-26T23:24:21Z`, the authenticated API still reported exact
`memory_12` submission `397eaeb4-1236-4e0f-8b2d-b2ac089050f4` as done,
24/24, 29×29, average ticks 18,372.291666666668, and score
15,451,097.291666668.

Validation completed:

- deterministic parent-to-child generation and exact SHA-256;
- parser, server compatibility, pipe checker, and unchanged-pipe assertions;
- an exact binding assertion for every STATION `r` and `s`;
- all 7 public cases with exact ticks;
- all ring distances `k=0..33` independently for READ and WRITE;
- 100 deterministic streams of 300–1,000 tokens against a plain-memory
  oracle;
- eight 500-token address-stride streams covering all extreme values;
- 65 inherited Memory preservation/packing tests;
- preflight verdict `READY TO SUBMIT`;
- Ruff and `git diff --check`.

## Live result

Submission `35dca1c9-840c-4ce4-afe0-58a3e5995bfe` completed at
`2026-07-26T23:35:29.625Z`: 24/24, 29×30, average ticks
15,987.083333333334, and score 14,388,375. This is a 6.878% live score
reduction from `memory_12`; the full response is preserved in
`submissions/memory/memory_13-submit.json`. The standings snapshot at
`2026-07-26T23:36:10.399Z` placed wheezards at rank 16, up from rank 17.
