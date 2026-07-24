# History Lesson Program Variants

Each generated candidate is preserved as `history_NN.man` and described in
`variants.json`. Older candidates are not overwritten when their encoding or
geometry changes.

`history_00.man` records the first radix-packed layout. The contest server
rejected it because vertically aligned backticks paired across dot padding.

`history_01.man` uses fixed-width slots whose vertical backtick pairs are
adjacent and therefore unambiguously legal. It passed the live judge.
