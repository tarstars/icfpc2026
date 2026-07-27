# Final state, 2026-07-27 11:45Z (submissions close 12:00Z)

## Live artifact per problem — verified, not assumed

| problem | artifact | score | cases | box |
|---|---|---|---|---|
| brackets | gpt_brackets_17 | 376,793 | 26/26 | 24 |
| gradebook | codex3_gradebook_07 | 33,985,503,692 | 20/20 | 379 |
| history-lesson | history_06 | 6,561 | 1/1 | 81 |
| lllm | lllm_05 | 17,618,466,246 | 21/21 | 303 |
| llm | llm_codex_01 | 8,775,033,253,482,888 | 28/28 | 25,797 |
| matmul | gpt_matmul_08 | 5,931,034,966 | 20/20 | 99 |
| memory | tarstars_memory_14 | 14,009,062 | 24/24 | 30 |
| pathfinder | pathfinder_04 | 4,366,568,960,000 | 18/18 | 960 |
| plotter | plotter_10 | 958,166,470 | 20/20 | 123 |
| reverse-a-list | chatgpt1_reverse_09 | 62,568 | 20/20 | 17 |
| snake | snake_05 | 808,967,647 | 17/17 | 150 |
| sort-numbers | chatgpt2_sort_01 | 792,452 | 25/25 | 18 |
| subset-sum | alexey-subset_sum_01 | 37,401,859,010,507 | 20/20 | 2,374 |
| sudoku-validity | sudoku_06 | 6,736,645,738 | 20/20 | 117 |
| tcp | tarstars_tcp_11 | 1,357,416 | 20/20 | 29 |
| **triangle** | **triangle_04** (see below) | **832** | 19/19 | 8 |

## KNOWN GAP: triangle has no submission record

We are **rank 1 of 267** on triangle at **832**, and the repo contains no
`-submit.json` for the artifact that produced it. The submissions database
therefore reports `alexey-triangle_02` (891) as our best, which is wrong.

**Identified by measurement under the organizers' WASM:**

    triangle_04              8x8  6/6  avgTicks 13  score   832   <- THE LIVE ONE
    alexey-triangle_02       9x9  6/6  avgTicks 11  score   891
    alexey-triangle_8x8_960  8x8  6/6  avgTicks 15  score   960
    triangle_03              8x8  0/6                             (broken)

**`submissions/triangle/triangle_04.man` is our rank-1 machine.** Recorded
here because without it nobody could tell which artifact holds our best
result.

## Fourteen live improvements today

    matmul       8,436,652,022  ->  5,931,034,966         1.42x
    sudoku      11,307,342,643  ->  9,290,407,668         1.22x
                                ->  6,736,645,738         1.379x
    snake          848,516,029  ->  808,967,647           1.05x
    tcp              1,490,670  ->  1,357,416             1.10x
    brackets           484,533  ->  376,793               1.286x
    reverse             84,424  ->  62,568                1.349x
    gradebook   47,115,780,604  ->  34,760,655,167        1.355x
                                ->  33,985,503,692        1.023x
    lllm        21,174,308,704  ->  17,618,466,246        1.202x
    plotter      1,007,182,812  ->  958,166,470           1.055x
    pathfinder  16,071,390,291,618 -> 5,356,161,884,516   3.0x
                                ->  4,366,568,960,000     1.227x   (3.68x total)
    sort               802,302  ->  792,452               1.012x

**Ten of the fourteen were other agents' finished work** that only needed
someone able to judge and submit it.

## Verified negatives — recorded so they are not re-attempted

- **llm line-merge deadlocks.** Only 73 of 25,797 rows carry no pipe cell;
  two mega-pipes blanket the height, so 153 of 231 pipes shortened and the
  machine is `timing_sensitive`. See BACKLOG A4.
- **gradebook shape search**: no verified sparse-column shave exists.
- **pathfinder room fold**: 462 of 497 I/O cells belong to a pipe whose
  cells straddle any cut line — the binding contract is unsatisfiable
  under a multi-band fold.
- **tcp**: the placer reaches 29x29, equal to live. The ROUTER is the
  limit, not the placer.

## Where the work continues

`docs/BACKLOG.md` — every task with its evidence, acceptance test and
estimate. `docs/MANIFEST.md` — the component-library direction.
`docs/architecture/claude_42_delay_loops.md` — buy delay with a loop, not
distance. The deepest finding: **the backpack has no read port**, and that
one missing op is what makes both delay-loops and room-splitting
conditional.
