# claude_33: the history-lesson encoding frontier — where the next cells are

Status: analysis, 2026-07-26 ~17:30Z. The 56-token encoder
(`src/littleman/history_pack.py`, 9 tests) is done and a builder is
turning it into a room. This records what governs the problem and which
refinements remain, so the next session does not re-derive any of it.

## The governing identity

`history-lesson` is **footprint-scored only — ticks are FREE**. A packed
word is written as a decimal literal, and the largest signed-64 literal
is 19 digits, which occupies **21 cells** (19 digits + 2 backticks) and
carries **63 bits**. Therefore

    cells per character = (bits per character) / 3

Every bit of compression is worth exactly one third of a cell, and an
arbitrarily slow decoder costs nothing as long as it is small in CELLS.
That asymmetry — expensive encoder in Python, cheap decoder in the
machine — is the whole design (the user's framing, and it was right).

## THE CLIFF: radix 127 is a hard ceiling, not a smooth optimum

Symbols per word is `floor(log(2^63 - 1) / log(radix))`:

    radix 126: 126^9 = 8.005e18 <= 9.223e18  -> 9 symbols/word
    radix 127: 127^9 = 8.595e18 <= 9.223e18  -> 9 symbols/word   <- CEILING
    radix 128: 128^9 = 9.223e18 >  limit     -> 8 symbols/word
    radix 135: 135^9 = 1.489e19              -> 8 symbols/word

**127 is the largest radix that still packs 9 symbols.** Crossing it
costs a ninth of every word's capacity at once, which is why the token
sweep improves to 56 and then gets WORSE at 64 even though bits/char
keeps falling:

| tokens | radix | data | table | total | bits/char |
|---|---|---|---|---|---|
| 3 (live) | 74 | 5,481 | 21 | 5,502 | 5.75 |
| 24 | 95 | 4,640 | 231 | 4,871 | 4.87 |
| 48 | 119 | 4,347 | 462 | 4,809 | 4.55 |
| **56** | **127** | **4,242** | **525** | **4,767** | **4.51** |
| 64 | 135 | 4,440 | 588 | 5,028 | 4.46 |

Note 4.51 bits/char beats the order-0 entropy of 5.05 — possible because
the text is structured (years, `, USA`, `University of`, month and city
vocabulary), not random.

## The alphabet is 71, and that is the budget line

**71 distinct characters** (an earlier note said 73; that was
`history_small`'s mapping dict, which carries two extra entries — the
text really has 71). With radix capped at 127:

    token slots = 127 - alphabet = 127 - 71 = 56

So the next gain is **not more tokens — it is a smaller alphabet.**
Every character removed frees exactly one token slot at the same word
capacity.

## The next refinement: escape the rare tail

The distribution is extremely skewed. The tail:

    'X' 'Q' "'"  1 occurrence each
    '?' 'Z'      2 each
    '3' '4' '5' '7' '8' 'z'   3 each

**11 characters cover 31 of 2,810 positions (1.1%).** Replace them with
one ESCAPE symbol followed by an index into a rare-table:

- cost: +31 symbols (each rare char becomes two), plus a tiny table;
- gain: alphabet 71 -> 61, so **token slots 56 -> 66** at unchanged
  radix 127 and unchanged 9 symbols/word.

Ten more token slots should be worth well over 31 symbols — the 48 -> 56
step alone bought 42 cells while adding 8 slots. Estimated 200-300 cells,
which is the difference between 82x82 and 81x81 (+0.021 points), or
insurance if the room comes out looser than the budget predicts.

Deliberately NOT applied now: the builder has a verified encoding and a
measured fit, and changing the spec mid-build is how agents die.

## Other directions, ranked by expected value

1. **Escape the rare tail** (above) — best ratio, well-defined.
2. **Order-1 / context modelling.** Conditional entropy is far below 5.05
   for this text (after `19` the next char is almost always a digit;
   after `, ` a capital). A context-mixing coder would approach ~3
   bits/char = 1 cell/char, but its decoder needs per-context frequency
   tables, and TABLE CELLS are the scarce resource here, not ticks. Only
   worth it if the tables can be shared/derived rather than stored.
3. **Two-level dictionary** (tokens made of tokens). Compresses the
   TABLE, which is 525 cells and growing with token count — it is the
   term that eventually stops the sweep.
4. NOT worth it: arithmetic coding (decoder needs cumulative-frequency
   search per symbol — many table cells); Huffman (bit-serial walk is
   cheap in ticks but the tree costs cells and beats radix packing only
   marginally at these sizes).

## The live ladder, for judging whether any of this pays

Measured 2026-07-26 ~16:00Z, we are 85x85 = 7,225 at rank 29/144:

    84x84 = 7,056 -> +0.021     81x81 = 6,561 -> +0.126
    83x83 = 6,889 -> +0.077     80x80 = 6,400 -> +0.140
    82x82 = 6,724 -> +0.105     76x76 = 5,776 -> +0.196 (rank 1)

The field is dense: 3 teams at 84x84, 8 at 83x83, 4 at 82x82. Every
single row shaved is worth real points, which is unusual and is why this
problem repays encoding work that would be pointless elsewhere.

76x76 needs total cells <= 5,776 with a decoder, i.e. roughly 4,500 of
data+table — reachable only with direction 2 above.
