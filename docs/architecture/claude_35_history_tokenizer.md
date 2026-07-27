# claude_35: history-lesson — full state, and the tokenizer frontier

Status: 2026-07-27 ~04:40Z, written so any agent can pick this up cold.
Supersedes the measurement sections of `claude_33`; that document's
"radix 127 is the ceiling" claim is **wrong by one** and is corrected
below.

## Why this problem repays work when others do not

`history-lesson` is **footprint-scored only — ticks are FREE**. An
arbitrarily slow decoder costs nothing as long as it is small in CELLS.
All the expense can sit in Python. That asymmetry is the whole design.

The field is also the densest on the board: **153 teams**, and the
scores cluster on exact squares, so nearly every row shaved changes our
rank.

    live now: 81x81 = 6,561, rank 14/153
    80x80 = 6,400  -> +0.007      78x78 = 6,084 -> about +0.06
    79x79 = 6,241  -> about +0.04  76x76 = 5,776 -> +0.086 (rank 1)

## The governing identity

A packed word is written as a decimal literal. The largest signed-64
literal is 19 digits, occupying **21 cells** (19 digits + 2 backticks)
and carrying **63 bits**. Therefore

    cells per character = (bits per character) / 3

Every bit of compression is worth exactly one third of a cell.

## CORRECTION: the radix ceiling is 128, not 127

`history_pack.symbols_per_word` asked whether `radix**(n+1) <= LIMIT` —
whether the radix POWER fits. The right question is whether the largest
representable VALUE fits, `radix**(n+1) - 1 <= LIMIT`:

    128^9 - 1 = 2^63 - 1 = 9,223,372,036,854,775,807 = LIMIT exactly

So **radix 128 packs 9 symbols per word**, not 8. Codex found this
empirically and built the 81-square on radix 128 while the module still
claimed it was impossible. Fixed now, with a regression test.

    radix 127 -> 9 symbols     radix 128 -> 9 symbols  <- true ceiling
    radix 129 -> 8 symbols

Consequence: the slot budget is `128 - alphabet`, not `127 - alphabet`.
With a 71-character alphabet that is **57 token slots**, one more than
claude_33 assumed.

## Where the 81-square stands, exactly

Codex's `src/littleman/history_81.py` + `scripts/search_history_81.py`
impose two hard bounds for an 81-square:

    65 main rows x 3 words x 9 symbols = 1,755 symbols maximum
    6 lookup row-pairs                 =   450 lookup cells exactly

Their simulated annealing reached **1,754 symbols / 450 lookup** after
635,121 swaps (seed 804). For an **80-square** the bounds tighten to
**1,728 symbols and ~444 lookup** (64 main rows).

I ran four more SA seeds at the 80-square target (900k steps each,
~515 s):

    seed 11 -> 1,743 symbols / 452 lookup     <- best symbols
    seed 33 -> 1,743 / 460
    seed 44 -> 1,750 / 449
    seed 22 -> 1,759 / 445                    <- best lookup

**1,743 beats codex's 1,754**, so the dictionary frontier was not
exhausted — but every run violates the lookup bound, and none reaches
1,728. Symbols and lookup trade against each other: longer tokens cut
symbols and cost table cells. The search optimises
`symbols + 2.0 * lookup`; that weight has never been swept.

## The tokenizer frontier — where the real cells are

Measured on the actual 2,810-character text:

    alphabet                    71 characters
    distinct bigrams           608
    distinct trigrams        1,567
    order-0 entropy          5.049 bits/char   (a naive per-char code)
    CURRENT ENCODING         ~4.51 bits/char   (dictionary beats order-0)
    order-1 conditional      3.297 bits/char   <- THE PRIZE

Order-1 conditional entropy is **3.297 bits/char**, against the ~4.51 we
actually spend. At 3 bits per cell that is

    2,810 chars x (4.51 - 3.297) / 3 = about 1,150 CELLS

which is far more than the ~320 cells that separate 81x81 from 79x79.
The text is highly predictable in context — after `19` comes a digit,
after `, ` a capital, and the vocabulary is months, cities and
universities.

### The catch, and why this is not already done

An order-1 coder needs a **frequency table per context**, and table
cells are the scarce resource here, not ticks. A naive order-1 model
with 71 contexts x 71 successors is hopeless. The idea only pays if the
tables can be **shared, grouped, or derived** rather than stored — for
example by bucketing the 71 characters into a handful of context classes
(vowel / consonant / digit / space / punctuation) so that a few tables
serve everything.

### Ranked directions

1. **Context classes (order-1 with grouped contexts).** Largest prize
   (up to ~1,150 cells), and the only direction that can reach 76x76.
   The whole question is how few classes still capture most of the
   1.75 bits/char that order-1 offers. Measure before building.
2. **Escape the rare tail.** 11 characters cover only 31 of 2,810
   positions (`X`, `Q`, `'` once each; `?`, `Z` twice; `3 4 5 7 8 z`
   three times). Replace them with one ESCAPE symbol plus an index:
   costs +31 symbols, shrinks the alphabet 71 -> 61 and so frees **10
   more token slots** at unchanged word capacity. Never implemented.
3. **Sweep the SA weight.** The `symbols + 2.0*lookup` tradeoff is
   arbitrary. The 80-square needs 1,728/444 and we have 1,743/452 —
   the frontier may simply be mis-parameterised.
4. **Two-level dictionary** (tokens built from tokens). Compresses the
   TABLE, which is the term that eventually stops the token sweep.
5. NOT worth it: arithmetic coding (the decoder needs a
   cumulative-frequency search per symbol — many table cells); Huffman
   (bit-serial walk is cheap in ticks but the tree costs cells and
   beats radix packing only marginally at these sizes).

## How to measure anything here

The honest figure of merit is **total cells = data + table**, never
bits/char alone, because every scheme that lowers bits/char raises the
table. `src/littleman/history_pack.py` reports both (`data_cells`,
`table_cells`); `tests/test_history_pack.py` pins the round trip and the
budget. Any new scheme must round-trip exactly — the machine emits 2,810
specific bytes and a single wrong character scores zero.
