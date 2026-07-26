
## step0

Baseline: reverse_06 exactly as submitted (live 98,676.2).

```
+--+>---v
|@v|^+-------+
|v<| |  v-rM<|
|Rs| |  b   2|
|>^| |v Xrs@^|
+--+ |>sU   s|
 ^^  |^md   W|
 ||  |  >Mrs^|
 ||  +-------+
 |^-<  v   v
 ^  |  |   v
+-+ |  |  +-+
|I| |  |  |O|
+-+ ^--<  +-+
```

## step1

Output flush against the pump: the pipe bends into O's right wall instead of dropping into its roof, so O climbs from rows 11-13 to rows 9-11.

```
+--+>---v
|@v|^+-------+
|v<| |  v-rM<|
|Rs| |  b   2|
|>^| |v Xrs@^|
+--+ |>sU   s|
 ^^  |^md   W|
 ||  |  >Mrs^|
 ||  +-------+
 |^-<  v+-+v
 ^  |  ||O|<
+-+ |  |+-+
|I| |  |
+-+ ^--<
```

## step2

Relay down two rows (rows 2-7). Ring-in now starts above the relay corner and is 7 cells instead of 5 -- the capacity the ring-out will lose later is bought back here.

```
   >----v
   ^ +-------+
+--+ |  v-rM<|
|@v| |  b   2|
|v<| |v Xrs@^|
|Rs| |>sU   s|
|>^| |^md   W|
+--+ |  >Mrs^|
 ^^  +-------+
 |^-<  v+-+v
 ^  |  ||O|<
+-+ |  |+-+
|I| |  |
+-+ ^--<
```

## step3

Input up one row (rows 10-12); ring-out re-terminates via row 9 into the relay floor at (8,3). Row 13 now carries nothing but the ring-out west leg.

```
   >----v
   ^ +-------+
+--+ |  v-rM<|
|@v| |  b   2|
|v<| |v Xrs@^|
|Rs| |>sU   s|
|>^| |^md   W|
+--+ |  >Mrs^|
 ^ ^ +-------+
 ^ ^<  v+-+v
+-+ |  ||O|<
|I| |  |+-+
+-+ |  |
    ^--<
```

## step4

Ring-out pulled out of row 13: 14x13. Ring is now 12+7=19 cells, still buffers n=16 (stress green).

```
   >----v
   ^ +-------+
+--+ |  v-rM<|
|@v| |  b   2|
|v<| |v Xrs@^|
|Rs| |>sU   s|
|>^| |^md   W|
+--+ |  >Mrs^|
 ^ ^ +-------+
 ^ ^<  v+-+v
+-+ |  ||O|<
|I| |  |+-+
+-+ ^--<
```

## step5

Pump one column left (cols 4-12): the relay is now FLUSH against it, no gap column. 13x13, fp 169, score 53,911. The gap column was only ever needed because the ring-in used to leave the relay right wall; after step 2 it leaves through the roof.

```
   >---v
   ^+-------+
+--+|  v-rM<|
|@v||  b   2|
|v<||v Xrs@^|
|Rs||>sU   s|
|>^||^md   W|
+--+|  >Mrs^|
 ^ ^+-------+
 ^ ^< v+-+v
+-+ | ||O|<
|I| | |+-+
+-+ ^-<
```

## step6

Ring-out serpentines through the free block (13 cells instead of 11): capacity 19 against a measured peak of 16, AND 0.6% faster. 13x13, fp 169, score 53,594.

```
   >---v
   ^+-------+
+--+|  v-rM<|
|@v||  b   2|
|v<||v Xrs@^|
|Rs||>sU   s|
|>^||^md   W|
+--+|  >Mrs^|
 ^ ^+-------+
 ^ ^-<v+-+v
+-+ >^||O|<
|I| | |+-+
+-+ ^-<
```
