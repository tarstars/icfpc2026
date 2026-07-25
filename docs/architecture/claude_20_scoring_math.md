# Claude: what the scoring rules actually reward

Status: measured finding, 2026-07-26T00:20Z. This changes priorities, so
it is written down rather than acted on silently.

## The rule (docs/grading.md, verbatim arithmetic)

Each **graded** problem is worth at most **2 points**:

    test-case points = passing test cases / total test cases      (max 1)
    ranking points   = (eligible teams we beat or tie) / (other eligible teams)   (max 1)

Eligibility requires passing **at least one private test case** — but on a
problem with **no private tests, passing any test case makes you eligible**.
Total = the sum of our best score on every problem. The raw score number
(`footprint x avgTicks`) enters ONLY through the ranking half.

## Consequence 1: our absolute scores are not the scoreboard

| problem | live score |
|---|---|
| subset-sum | 91,769,596,778,390 |
| gradebook | 81,914,188,255 |
| everything else combined | < 60,000,000,000 |

Subset Sum is a thousand times the rest of the board and it is tempting to
attack. It is worth **at most one point**, the same as every other problem,
and we already pass 20/20 there. Its 3646x3029 layout is only a ranking
concern.

## Consequence 2: test-case points are already maxed where we compete

All twelve problems we have ever submitted pass **100% of test cases**
(20/20, 26/26, 24/24, ...). So on those twelve, the entire test-case half
is banked and **only rank fractions remain** — which is exactly what a
geometry press buys.

## Consequence 3: the unscored problems are the big prize

Never scored: **pathfinder** (Codex's), **LLM**, **LLLM** — up to 2 points
each, ~6 points unclaimed, versus fractions everywhere else.

All three have **`privateTestCount: 0`**, so eligibility costs exactly one
passing public case. Partial credit is per **test case**, not per round: a
case counts only if every one of its rounds is right, so a machine must
carry a whole case end to end. The cheapest targets are the small ones:

| problem | cases | smallest case |
|---|---|---|
| LLM | 14 | `first steps` — 4 rounds, 18 ints (a 4x4 grid) |
| LLLM | 10 | `first steps` — 4 rounds, 18 ints; `revolving door` — 6 rounds, 27 ints |
| pathfinder | 7 | all 258 ints (a full 16x16 board) |

This is the arithmetic that justifies the overnight queue's rule that a
machine interpreting a correct SUBSET and halting cleanly on the rest is
worth submitting: 1 of LLM's 14 cases is 0.071 points that we do not have.

## Consequence 4: do not spend anything on the practice set

**atoi, hello-world, max-element and palette** are
`Practice Problems (Ungraded)`. The server refuses them outright:

    403 forbidden: This is an ungraded practice problem; it does not accept submissions

They can never contribute. A correct 13x13 hello-world (68 ticks, 1/1) was
built here before the 403 revealed this, and two agents were building atoi
and palette before being stopped; the artifact is kept only as a worked
example of the delta-chain constant trick. **Check `status` in the
`problems` listing before starting any new problem** — `graded` vs
`practice` is the only field that matters, and the slug gives no hint.

## Honest caveat on ranking estimates

`icfpc-api standings <slug>` returns **0 rows for every problem**, so no
rank here is measured. The last recorded positions (Sudoku 42/46, Plotter
37/43, from `docs/current-state.md`) predate tonight's work. Every
"this press should gain us N places" claim is therefore a guess about the
field, not a measurement — the score improvements themselves are real and
server-confirmed, the rank consequences are not.
