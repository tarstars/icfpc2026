# Claude: LOADER is not simple — the misjudgement and what it teaches

Status: post-mortem + contingent design, 2026-07-25T21:1xZ. Written after
the user challenged the premise: "size of it tells me it is not simple."
Correct. This records the analysis, the error, and the evidence-driven
decision rule now in force.

## The claim I made, and why it was wrong

`claude_08`/`claude_09` treated LOADER as the easy component ("read
tokens, classify, store"). Codex's correct implementation came back at
**723 x 8134** — footprint ~66M against a whole-machine best of 49,729.
I attributed ~100% of that to compiler naivety (one corridor per FSM
state, no row sharing). On reflection ~90% is naivety and **~10% is
irreducible content**: a 13-way classifier is a genuinely large branch
structure however it is laid out. Size was a signal about the PROBLEM
and I read it purely as a signal about the TOOL.

## Why LOADER is the hardest component in the machine

Every other component streams with a fixed shape. LOADER is the only one
that converts 1-D input into 2-D structure *while* classifying it, and it
carries four jobs per token simultaneously:

1. 13-way character classification (glyph -> class, value, colour);
2. a positional predicate — "is this cell on the program's perimeter?" —
   requiring live `x`, `y`, `W`, `H` and two comparisons per cell;
3. reindexing — W x H input into a 16 x 16 canvas, emitting padding at
   the end of each row and after the last row;
4. 4-records-into-1-token packing with a BP-counted accumulator.

That is four live quantities (`x`, `y`, `W`, `H`) before the character or
the accumulator is considered, against two readable registers. The real
cost is **state juggling**, not classification: every quantity must spill
to a scratch loop and be re-fetched.

Contrast with its neighbours, which is the tell I missed:

| component | live state | per-token work |
|---|---|---|
| FETCH | one index | re-emit unchanged, peel one record |
| STEP | 5-slot loop, one cell/tick | dispatch 9 classes |
| DRAW | none (stateless transducer) | one arithmetic split |
| **LOADER** | **x, y, W, H + char + accumulator** | **classify + test + pad + pack** |

LOADER is the only place where all the hard categories meet.

## The decomposition I should have written (SCAN | CLASSIFY+PACK)

Mirrors the EXEC -> FETCH/STEP split that worked:

- **SCAN** — geometry only. Consumes `W H`, then per input token emits
  `(x, y, is_perimeter, is_padding, char)`. No classification, no
  packing. All coordinate state lives here, in one place.
- **CLASSIFY+PACK** — semantics only. Consumes SCAN's tuples, derives
  records (colour | class<<4 | value<<8 | wall<<12), accumulates four
  per token, emits the 64 tokens then `man_addr`. Never computes a
  coordinate.

Each half then holds ~2 live quantities instead of 4 — the difference
between "fits in A/B with one spill" and "spills constantly". The
external interface (`claude_09`) is unchanged: this is an internal
re-decomposition, exactly as `claude_11a/11b` was for EXEC.

## Decision rule now in force (do not split yet)

Cost check: splitting means a new work order plus two builds, with three
of four LLLM components already done and the deadline Sunday 12:00Z. So
the question is handed to evidence rather than to my judgement, which has
already been wrong once on this component:

**Gate 3 of `claude_12` (the room assembler) decides it.** That gate is
"compile this same LOADER op sequence, land <= 200 rows".

- assembler hits the gate  => LOADER stays monolithic; nothing spent.
- assembler lands far above (say > 1000 rows) => the size is content,
  not naivety; write SCAN / CLASSIFY+PACK immediately per the sketch
  above and rebuild.

The 200-row figure is my estimate, not a measurement, and may be
optimistic — treat a near-miss (200-600) as "monolithic but hand-shaped",
not as a failure of the assembler.

## Transferable lesson

Component difficulty is not proportional to how simple its DESCRIPTION
sounds. Two better predictors, both available before writing a line:

1. **count the live quantities** the component must hold simultaneously,
   against the two readable registers;
2. **count the distinct job categories** it performs per token
   (classification / geometry / reformatting / accumulation). More than
   two categories at once is a decomposition smell.

By both measures LOADER scored worst in the machine and I still called it
easy. `claude_08`'s five-layer contract captured *what* it must do and
said nothing about *how much state that costs* — a gap worth closing in
the contract schema: a `live_state` field alongside timing and capacity.
