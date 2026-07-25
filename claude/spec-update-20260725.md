# Contest spec update detected 2026-07-25 ~15:00Z

The language-reference page was re-published: bundle
`language-reference-BqEMdKcM.js` (captured 2026-07-24 into
`docs/language-reference.md`) is now `language-reference-CMQAiAcd.js`.
Full-text sentence diff of the extracted content against our capture
yields exactly two semantic changes; everything else (opcodes, pipes,
displays, tick order, judging) is unchanged. The grading page shows no
semantic delta.

## Change 1 — backtick pairing formalized (the load-bearing one)

The Constants row now says "Anything but a digit or a space between a
**matched pair** is a load error. See the fine print for **how backticks
pair**", and the fine print gains two normative bullets, verbatim:

> Backticks pair on rows and columns. Within a row they pair in order
> left to right — the 1st with the 2nd, the 3rd with the 4th, and so on;
> within a column likewise top to bottom. A backtick that pairs on
> neither axis is a load error.
>
> A backtick cannot opt out of an axis: one meant as a horizontal
> delimiter still pairs vertically if its column holds other backticks.
> Literals stacked across rows with their backticks aligned can
> therefore form vertical pairs you did not intend, and a non-digit
> between such a pair is a load error.

**Our simulator already implements exactly this** (`sim.py`
`_build_literals`: in-order pairing per row and per column via
`range(0, len-1, 2)`, error on non-digit between a pair, error on a
backtick unpaired on both axes, no opt-out). The update codifies our
behavior.

Consequences:

- The "divergences run both ways" caveat around `history_00` (live on the
  server, rejected locally with `invalid vertical literal`) is now
  probably **historical**: the server appears to have been brought to the
  strict rule the page now documents. `history_00`'s accepted score
  stands, but a resubmission of a like artifact would likely be rejected.
  Unverifiable without a probe submission; do not spend one on it.
- The risk direction "local parse passes, server rejects on literals" has
  shrunk to near zero: anything our parser accepts complies with the
  published rule. No action needed for in-flight builders — their
  artifacts pass through our parser anyway.
- The cookbook §7 guidance (offset stacked literal columns) was the
  correct practice all along and is now spec-backed rather than
  empirical.

## Change 2 — `U` wording

Old: "turns away from the pipe that he read from." New: "turns away from
the **side of the room** that he read from." `sim.py._turn_away` already
derives the direction from which room wall the pipe's destination segment
sits on — i.e., the side — so no code change. `U` remains quarantined in
our designs regardless.

## Actions

- `docs/language-reference.md` is integrator-owned: recapture requested
  from Codex (message 20260725T150500Z), including the new bundle name in
  the header.
- Registry (`claude_06` seed): sim's literal handling upgrades from
  "divergent vs server" to "spec-exact"; the capture row gets flagged
  stale until Codex recaptures.
- `claude_01` DRC row 5 (literals) annotated: divergence probably
  resolved server-side by this update.
- Process note: the spec can move mid-contest. A cheap daily check —
  compare asset hashes of language-reference/grading/textbook against
  the recorded ones — belongs in the registry as a `draft` tool.
