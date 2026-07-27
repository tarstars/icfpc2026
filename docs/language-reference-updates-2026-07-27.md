# Language-reference updates — 2026-07-27

Investigation prompted by `gpt_brackets_18`: our preflight said 9/9, the
organizers' WASM said 7/9, and the real server said "Failed 2 of 9 public
tests (2 wall)".

Two sources, both current:

1. **The live site**, re-fetched 2026-07-27. It is a Vite/React SPA — every
   HTML path returns the same 2206-byte shell — so the docs were read out of
   the JS chunks named in `/assets/index-RPCgG-2I.js`, plus
   `GET /api/v1/split/docs`. Both doc chunks have been **rebuilt** since our
   capture: `language-reference-BqEMdKcM.js` → `language-reference-LNnBKpg7.js`,
   `grading-CTElrHZs.js` → `grading-DmOQZaI1.js`.
2. **The organizers' own engine**, `claude/official-sim/vendor/littleman.wasm`,
   driven under Node v18. Used to settle everything the prose leaves open.

**Do not edit `docs/language-reference.md`, `docs/grading.md` or
`docs/rules.md` — this file is the delta.**

## TL;DR

The captured spec is **not** wrong about walls. `docs/language-reference.md`
already says "Errors end your whole program on the spot", and the live site
still says exactly that, verbatim, today. **Both of our judges are wrong, in
opposite directions**, and the real rule is a third thing:

> When a little man steps into a wall, he *enters the cell*; the fatal fires
> on the **next** tick, after that tick's pipe-shift and output-emit phases
> have already run. Exactly **one** grace tick. Then everything stops dead —
> no further execution by anyone, and no drain-to-empty.

Proof from two of our own submissions to the same problem, same crash shape
(both recorded in `submissions/brackets/*-submit.json`):

| artifact | strict `judge` | lenient `alexey_walljudge` | organizers' WASM | **real server** |
|---|---|---|---|---|
| `gpt_brackets_17` | 7/9 ✗ | 9/9 ✓ | 9/9, output lands **on** the grace tick | **26/26, score 376,792** |
| `gpt_brackets_18` | 7/9 ✓ | 9/9 ✗ | 7/9, output needs 13 more ticks | **19/26, "2 wall"** |

So `scripts/preflight.py` (which uses the lenient judge) green-lit a program
that fails, and switching to the strict judge would have thrown away a
program that scored. Only the one-grace-tick model reproduces both.

The site *has* changed since 2026-07-24: `Y`/split, uber-strict problems, and
a new backtick-pairing load-error rule. None of those explain the brackets
failure; the judge does.

---

## 1. What changed on the site since our 2026-07-24 capture

There is **no changelog page** (`/changelog`, `/news`, `/updates`, `/blog`,
`/faq` do not exist in the router). The only signal is the dashboard banner
"**New:** Semester 4 problems and the split instruction have been released!"
and a nav item literally labelled "Split (new)".

### 1.1 `language-reference`

- **New "Split" subsection and `Y` row.** The only new instruction glyph.
  Full text in §3.
- **New fine print on backtick pairing** — a real codegen trap, quoted
  verbatim:
  > Backticks pair on rows and columns **independently**. Within a row they
  > pair in order left to right — the 1st with the 2nd, the 3rd with the
  > 4th, and so on; within a column likewise top to bottom. A backtick that
  > pairs on neither axis is a load error.

  > A backtick cannot opt out of an axis: one meant as a horizontal
  > delimiter still pairs vertically if its column holds other backticks.
  > Literals stacked across rows with their backticks aligned can therefore
  > form vertical pairs you did not intend, and a non-digit between such a
  > pair is a load error.
- **`U` reworded**: ours says "turns away from **the pipe** that he read
  from"; live says "turns away from **the side of the room** that he read
  from." Defined by which room side the pipe attaches to.
- **Numeric-literal row reworded**: "Spaces are ignored. Anything but a digit
  or a space between a matched pair of `` ` `` is a load error."
- **`q` added to the receive list**: "`s` and `S` operate over outgoing pipes
  in the current room; `r`/`R`/`U`/`q` act over incoming pipes."
- Everything else verified identical: the wall rule, every op table, pipe
  parsing, tie-breaks, I/O rooms, the whole LM-75 section, judging & halting,
  tick order, output flush, withheld input, determinism, line padding.

### 1.2 `grading`

- **New "Uber-strict problems" section.** Verbatim, the load-bearing part:
  > These problems are marked as **uber-strict** and have an additional
  > corpus of test cases that are run against programs that pass all public
  > and private test cases. You are only told whether you passed the
  > uber-strict corpus […] The uber-strict test corpus is *not* used to
  > compute tick counts for scoring purposes; it is a pass-fail check only. A
  > submission that passes all public and private test cases but fails the
  > uber-strict corpus is ranked below every submission that passes the
  > uber-strict corpus.

  Per the public API, **`sudoku-validity` is the only `uberStrict: true`
  problem.** Hardcoding is actively punished there.
- Ranking section gains: "On an **uber-strict** problem, a full pass ranks
  above other full passes only if it also passes the uber-strict check."
- Limits section gains: "Feel free to reach out if you hit one of these
  limits and think something is wrong."
- **Both scoring formulas unchanged**: `max(width, height)² × average ticks`,
  and plain `max(width, height)²` for footprint-only problems. Points scheme,
  10 MB program limit and the 5-million-step default all unchanged.
- **Real per-problem caps** (from `GET /api/v1/public/problems/<slug>`, not in
  the prose): `tickCap` **15,000,000** for `subset-sum`, `snake`,
  `pathfinder`, `little-little-little-man`; **50,000,000** for
  `little-little-man`; `null` (⇒ 5M default) elsewhere. `history-lesson` is
  the only `footprint`-scored problem. New **Semester 4** set: snake,
  pathfinder, little-little-man, little-little-little-man. 20 problems total.

### 1.3 `rules`

No substantive change. Freeze windows unchanged. (Live text is fuller in
three clauses: records discarded after the contest, expanded anti-attack
wording, full IP licence paragraph.) The precise end timestamp is not stated
anywhere we could retrieve.

### 1.4 Engine alphabet

`validOps()` from the shipped WASM returns 45 ops:

```
/rbmM|0%S>a29+}N46*sR<Xq]xW~{^VYd1`&vH3-.U578
```

Set-differenced against `docs/language-reference.md`, the engine has
**exactly one op we do not document: `Y`**. Nothing else added, removed or
renamed. `structuralGlyphs()` is still `+-|<>^v=:`.

Fatal reasons in the shipped bundle: `wall`, **`split-limit`**, `bad-op`,
`no-pipe`, `display-value`, `display-addr`, `display-swap`; caps `step-cap`,
`op-cap`, `time-cap`. The language-reference error table still lists only
`wall`/`bad-op`/`no-pipe`; `split-limit` is documented only on `/split`.

---

## 2. The exact wall rule

### 2.1 What the site says (verbatim, unchanged from our capture)

> **Stepping on a wall is an error: it ends your whole program.**

> Anything else that stops a little man is an **error**. Errors end your
> whole program on the spot: `wall` — A little man ran into a wall.

And from the new `/split` page: "If the birth cell is a wall, the program
halts with an error."

So: **always fatal to the whole program, never per-man.** Whether other men
are still running is irrelevant. There is **no case where hitting a wall is
not fatal.** Off-grid is not a separate case — a man is always inside a room,
so he meets a wall first.

### 2.2 What the site does *not* say, and what the engine actually does

The prose never says whether the man *enters* the wall cell. He does, and it
matters. Measured directly against `vendor/littleman.wasm`:

```
+-----+
|@    |            t5: runner at [6,1]  — standing on the '|' wall cell
+-----+            t6: FATAL {reason:"wall", pos:[6,1], cell:"|"}
```

On that final tick the tick order still runs phases 1 and 2 — **pipes shift
and the output pipe emits** — and only then does phase 3 (execution) raise
the fatal. So there is **exactly one grace tick, and no more**:

| program | output pipe | result |
|---|---|---|
| `\|@1s\|` then wall | 2 cells | `output=["1"]`, then fatal `wall` |
| `\|@1s\|` then wall | 5 cells | `output=[]`, fatal `wall` — value lost |
| `\|@1sH\|` clean halt | 5 cells | `output=["1"]` — engine keeps ticking to t7 until the pipe drains |

That table is the whole story. A **clean halt** drains the output pipe to
empty ("Output flush when everyone halts"). A **wall fatal** does not: one
tick of shifting and emitting, then the machine stops dead.

**The fatal kills every little man immediately, and healthy men do not even
execute on the grace tick.** Two men in two separate rooms, one walks into a
wall at t3 while the other is mid-computation: both are flagged halted at t3,
the healthy man never reaches his `s`, `output=[]`. With man B scheduled to
run `9` on the grace tick, his A register never changed.

A wall step can still *pass* a test only via the grading rule "your program
passes a test the moment that it emits the correct output": if the full
correct output was already emitted — including during the one grace tick —
the case is already won and the later crash is irrelevant. Verified: output
emitted at t4, wall fatal at t12, `output` still `["1"]`.

`bad-op` has identical timing (man lands on `Z` at t2, fatal at t3), so this
is the general fatal model, not a wall special case. A `Y` copy *born*
directly onto a wall is the exception: fatal that same tick, **zero** grace
ticks, and the sibling's move is suppressed.

### 2.3 Why `gpt_brackets_18` really failed

Public case 3 (`in=[1,41]`, want `[1]`). Runner #0 in the top room:

```
t62 [20,3] '1'   A=1
t63 [20,4] '+'   A=A+B=1        <- correct answer computed
t64 [20,5] 's'   sends 1 into the top room's outgoing pipe
t65 [20,6] '-'   walks into the bottom border of the top room
t66            FATAL wall pos=[20,6] cell='-'   output=[]
```

The answer was computed and sent correctly. It then needed **13 more ticks**
to travel the long pipe down the right-hand side to the `O` room. The engine
grants **1**. `output` is empty and the case fails. Case 4 is the same shape
at `[21,5]` cell `'|'`, tick 146.

Our **strict** `littleman.judge` gets this one right: 7/9, failing cases 3
and 4 with reason `wall` at ticks 65 and 145 — one less than the engine's
66/146, because `sim.py` errors on the *attempt* to enter the wall instead of
letting the man enter and dying the tick after. `alexey_walljudge` reports
**9/9** with ticks 78 and 158, i.e. it silently handed the program 13 free
ticks of pipe drain that the real engine does not give.

### 2.4 …and why `gpt_brackets_17` really *passed*

Same problem, same crash shape, opposite verdict — this is the case that
proves the strict judge is *also* wrong. Case 3 again, runner #1:

```
t62 [21,14] 's'  sends 1 (executes at t63)
t63 [21,15] '-'  walks into the wall
t64            pipe shifts, value emitted -> output=['1'], THEN fatal wall
```

The value reaches the end of the output pipe **on the grace tick**, so the
case is won before the program dies. The server agrees: `gpt_brackets_17`
scored **26/26, avgTicks 654.15, score 376,792.6**. Our strict judge reports
7/9 for it and would have vetoed a submission that actually scored.

The distinguishing factor between 17 and 18 is purely **how far the value
still had to travel when the man hit the wall**: one cell (17, survives) vs
thirteen (18, lost). Nothing about the crash itself differs.

---

## 3. `Y` — exact semantics

Verbatim from `GET /api/v1/split/docs` (the complete official spec; it is not
in any JS chunk):

> - `Y` splits the little man in two. The copies are born on the cells to his
>   left and his right — left and right relative to his heading as he enters
>   the `Y` — each heading away from the `Y`. The original man does not
>   continue past the `Y`; only the two copies remain.
> - Both copies carry the original little man's registers, including his
>   backpack.
> - The tick after they were born, the copies execute the instruction they
>   were born on and then move.
> - Little men act in creation order, every tick. On a split, the copy born
>   to the **right** takes over the splitting man's place in that order; the
>   copy born to the **left** becomes the newest little man and acts after
>   all others.
> - **Y is unconditional**. It is executed even if a birth cell is blocked by
>   another man or a wall.
> - If the birth cell is a wall, the program halts with an error.
> - If the birth cell is another little man (including a little man blocked
>   on an instruction), both little men die. This is *not* an error.
> - If two little men in the same room collide, they both die. This is not an
>   error. This includes two men arriving on the same cell in the same tick,
>   and two adjacent men moving through each other (swapping cells) in the
>   same tick.
> - If two little men are spawned on the same cell by two split instructions
>   they both die. This is not an error.
> - The maximum number of live little men is 65536. Exceeding this limit is
>   an error and ends your program.

Independently confirmed against the engine:

- Heading east onto a `Y` at `[5,2]` produces runners at `[5,1]` (heading
  north, `dir [0,-1]`) and `[5,3]` (heading south, `dir [0,1]`). The `Y` cell
  is empty afterwards.
- The copies are placed during the execution phase and do **not**
  additionally move that tick; they execute their birth cell on the next
  tick — exactly as the prose says.
- One copy reuses the original's runner id; the other gets a fresh id.
- Both inherit A, B and backpack exactly (verified `a=5 b=7` on both).
- Meeting copies annihilate with no error (also `claude/official-sim/NOTES.md`
  check 3).
- The 65536 cap is far out of practical reach: a 255×255 room filled with `Y`
  peaked at **9558** simultaneous men and still died of `wall`, never
  `split-limit`.

---

## 4. What this means for our simulator — concrete fixes

Ranked by damage.

1. **Implement the one-grace-tick rule** in `sim.py`/the judge. This is the
   fix; it subsumes 2 and 3. On a wall (or `bad-op`) step: let the man enter
   the cell, then run exactly one more tick consisting of *pipes-shift +
   output-emit only* — no instruction execution by anyone, no movement — and
   then end the run. Count that tick. This is the only model that reproduces
   both `gpt_brackets_17` (26/26 on the server) and `gpt_brackets_18` (19/26),
   and it also reproduces the `triangle` observation that motivated the
   lenient patch in the first place: a final `s` into a **2-cell** output
   pipe drains, a longer pipe does not.

2. **Until then, stop using the wall-tolerant judge for go/no-go decisions.**
   `src/littleman/alexey_walljudge.py::_wall_tolerant` is unsound: it turns a
   whole-program fatal into "halt that man, keep everyone else running
   forever". `src/littleman/server_compat.py:134,143` delegate to it and
   `scripts/preflight.py` calls `server_compat`, so **every preflight verdict
   is computed under the wrong wall rule**. But do *not* simply swap in the
   strict judge — it rejects server-passing programs like `gpt_brackets_17`.
   For anything that ends on a wall, arbitrate with the WASM
   (`scripts/wasm_judge.py`). A cheap screen: an artifact only needs
   arbitration if the strict and lenient judges disagree. The sweep is ~20
   lines: run `littleman.judge.judge_problem` and
   `littleman.alexey_walljudge.judge_problem` on each artifact and flag
   `lenient > strict`. Results so far — **four** artifacts disagree, and the
   WASM says the lenient judge is right on three of them:

   | artifact | strict | lenient | WASM arbitration | verdict |
   |---|---|---|---|---|
   | `submissions/brackets/gpt_brackets_18.man` | 7/9 | 9/9 | **7/9** — output stranded 13 cells from the `O` room | lenient wrong; server confirmed 19/26 |
   | `submissions/brackets/gpt_brackets_17.man` | 7/9 | 9/9 | **9/9** — output emitted on the grace tick | strict wrong; server confirmed 26/26 |
   | `submissions/brackets/gpt_brackets_16.man` | 7/9 | 9/9 | **9/9** — same shape as 17, all outputs correct | strict wrong; safe to submit |
   | `submissions/triangle/triangle_04.man` | 0/6 | 6/6 | **6/6** — all six correct at tick 13 | strict wrong; this is the 8x8/13-tick artifact |

   Coverage note: the sweep was run over `atoi`, `brackets`, `gradebook`,
   `hello-world`, `history`, `lllm`, `triangle`, `tcp` and part of `llm`. The
   remaining directories (`matmul`, `max-element`, `memory`, `palette`,
   `pathfinder`, `plotter`, `reverse-a-list`, `snake`, `sort`, `subset-sum`,
   `sudoku-validity`) were **not** swept — the `llm`-family caps (50M ticks)
   made it too slow to finish. Re-run before submitting from those.

3. **Fix `sim.py`'s crash position and tick count** (falls out of 1): the
   engine lets the man enter the wall cell and fires the fatal the tick
   after, so official tick counts on a wall death are ours + 1 and
   `fatal.pos` is the wall cell, not the last legal cell. Also means our
   reported `avgTicks` for any artifact that ends on a wall is wrong.

4. **Implement `Y`** in `sim.py` (currently `bad-op`), per §3: two copies on
   the left/right neighbour cells relative to heading, each heading away,
   inheriting A/B/BP, original removed, copies do not move on the split tick,
   right copy inherits the splitter's slot in creation order and the left
   copy goes last, birth-on-wall is fatal, birth-on-man kills both without
   error, collisions and swap-through-each-other kill both without error,
   65536-man cap fatal. Until then, `Y`-using candidates must go through
   `scripts/wasm_judge.py`.

5. **Add a backtick-pairing load check** to any grid generator. Backticks
   pair per-row *and* per-column independently; stacked literals with aligned
   backticks can form an unintended vertical pair, and a non-digit between
   them is a **load error** the server will reject.

6. **`sudoku-validity` is uber-strict.** Any answer-shaped shortcut there is
   ranked below every honest full pass.

7. **Use the real tick caps** — 15M for subset-sum/snake/pathfinder/LLLM, 50M
   for LLM — not the 5M default, when judging locally.

8. **`claude/official-sim/harness.mjs` truncates stdout at 64 KB** because it
   calls `process.exit(0)` right after `console.log`. Any run with a large
   `menTimeline` or many runners silently produces unparsable JSON. Buffer or
   drop the `process.exit` before judging a many-men program with it.
