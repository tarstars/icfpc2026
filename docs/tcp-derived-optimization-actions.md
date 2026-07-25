# TCP-Derived Optimization Actions

Updated: 2026-07-25

This is the execution ledger derived from
`reports/2026-07-25-tcp-recovery-lessons.md`. An action is complete only when
its stated evidence exists; a promising idea is not a completed action.

| Priority | Action | Acceptance evidence | Status |
|---:|---|---|---|
| 1 | Preserve the recovered TCP lineage | Immutable sources, hashes, public metrics, 45-case regression, compatibility check, and variant catalogue | Complete |
| 2 | Restore reproducibility for the winning TCP source | A generator reproduces `tcp_02.man` byte-for-byte without embedding an opaque downloaded file as its implementation | Complete |
| 3 | Replace Sort's `q`/settling protocol with an in-band remaining-count token | New numbered generated variant; ≥5% local score reduction; all public, worst-shape, and 300 seeded random tests pass | Complete |
| 4 | Test three-value packing for Memory | Reference model plus a component-level encode/decode test; proceed to a machine only if projected ring capacity and score improve materially | Complete; proceed to guarded machine prototype |
| 5 | Audit Grade Book and Matrix collectors for tagged single-route output | Count current result/ack pipes and serialized relay work; retain a redesign only if it removes a route or full traversal | Complete |
| 6 | Audit Plotter, Brackets, and Reverse for phase-debt and final-wall savings | Exact candidate or a recorded negative result with the binding dimension and tick tradeoff | Complete |
| 7 | Audit Sudoku and Subset Sum for square balancing and packing | Identify the binding component/axis and one bounded layout or packing experiment per problem | Complete |
| 8 | Integrate validated improvements safely | Focused report, variants metadata, current-state update, full tests, mandatory pull and live score query before solution commit, then push | Complete |

## Execution order

1. Complete TCP preservation and tests before changing another ring machine.
2. Use Sort as the first transfer experiment because its `q` race and delay
   corridor are exactly the mechanism TCP's in-band control removed.
3. Run the remaining items as cheap discriminating experiments in priority
   order. Do not start a full redesign when the measured binding cost lies
   elsewhere.
4. Do not submit any candidate without explicit user authorization.

## Completed evidence

- Priorities 1–2: `littleman.alexey_tcp_recovered` reconstructs
  `submissions/tcp/tcp_02.man` byte-for-byte. `tests/test_tcp_recovered.py`
  locks the four recovered hashes, duplicate identification, six public cases,
  server-compatible layouts, and 45 deterministic boundary cases. Results and
  provenance are in `reports/2026-07-25-tcp-recovery-lessons.md` and
  `submissions/tcp/alexey-variants.json`.
- Priority 3: `sort_05` replaces `q` and the settling corridor with a
  remaining-count token, then folds the return pipe into the shelf below the
  pump. It passes seven public cases, eight worst-shape workloads, and 300
  seeded randomized workloads. The local score improves 16.20%, from
  928,440.43 to 778,062.86. See
  `reports/2026-07-25-sort-count-token.md`.
- Priority 4: the delegated `littleman.memory_packing_model` proves that three
  signed Memory values fit safely in one signed-64 word, reducing 100
  circulating values to 34 words. Its 26 focused tests pass. After correcting
  the projection to charge decode overhead for all assumed operations, the
  conservative estimate is still a 17.19% score reduction. See
  `reports/2026-07-25-memory-packing-feasibility.md`.
- Priorities 5–7: `reports/2026-07-25-tcp-transfer-audits.md` records exact
  pipe counts, binding dimensions, final-wall comparisons, the retained
  15×15 `reverse_02` candidate, a 306-square Sudoku packing bound, and the
  executable Subset Sum relocation probe plus its precise route collision.
