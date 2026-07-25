# Claude: critical review of the brief (introduction.md)

Status: requested by the user ("critically review my input"). Same evidence
labels as the rest of the set. This reviews the six bullets of
`introduction.md` against two days of measured project reality.

## What the brief gets right — and provably so

1. **The component framing matches the physics of the target.** Blocking
   `r`/`s` gives latency-insensitive composition; footprint is squared, so
   global geometry dominates local cleverness. Two independent analyses
   (`docs/synthesis-stack.md`, `codex_00`) converged on the same
   hardware-synthesis shape before this brief existed. Convergence of three
   independent derivations is evidence the framing is natural, not
   fashionable.
2. **The language bullet names the deepest platform quirk unprompted.** "At
   which places should input and output pipes be connected to work" is
   exactly the nearest-pipe binding problem — the one place where *placement
   changes semantics*, the cause of two brackets rebuilds, and the reason
   the memory station carries a 15-cell empirical audit. The user's instinct
   found the load-bearing difficulty without having debugged it personally.
3. **YT is the right tool for this search.** Candidate evaluation is
   ms-scale, stateless, KB-sized — embarrassingly parallel. The arithmetic
   (`claude_01` §6) supports ~1e10 exact evaluations per night on a modest
   pool. No part of the platform vision requires more compute than that.

## Where the brief should be pushed back on

### 1. The binding constraint is the clock, and the brief does not mention it

~46 hours remain. The six bullets describe a multi-week platform. Without a
ruthless cutline the platform consumes the contest and returns nothing
submitted. `claude_00`'s tiers are a proposed answer; the real decision is
the user's: **is this contest-first (platform must pay by Sunday noon) or
foundation-first (contest is the testbed for a longer program)?** The two
readings order work differently — contest-first funds the composer and
verification; foundation-first funds the contract schema and LM-Spec
design quality. Claude proceeds contest-first until told otherwise, and
flags that this is an assumption, not a given.

### 2. "High performance tooling wrought on Rust" aims the speed at the wrong place if taken literally

Measured: evaluation is the hot loop (2e5 ticks/s in Python); parsing is
once-per-candidate and cold. Every server divergence we have ever hit lives
in the *load* path — and those divergences already cost two
dead-on-arrival submissions (`sort_05`, `reverse_02`) and one live artifact
our parser rejects (`history_00`). A full Rust toolchain (parser included)
maximizes exactly that risk to speed up exactly the wrong stage. The
performance need is real but narrow: an IR executor (`claude_02`).
Corollary honestly stated: we have not yet measured that end-to-end search
is eval-bound; if the composer turns out move-generation-bound in Python,
even the executor's priority drops. Measure one annealing loop before
writing the second thousand lines of Rust.

### 3. "A components factory which optimizes components" is the weakest expected-ROI bullet of the six

> **Correction (2026-07-25T14:2xZ):** the user clarified the intended
> meaning — not room superoptimization but *contract-first decomposition
> to attack infeasible problems, with composition and implementation as
> parallel streams*. That reading is endorsed and applied to the LLM
> problem in `claude_07_llm_attack.md`; the demotion below stands only
> for the superoptimizer reading.

The record of this contest: the big wins were *representation and
architecture changes* — 3-per-word packing (3.78x local, 3.15x live), the
single-station ring rebuild, protocol redesigns in TCP (3.35x lineage). The
mechanical-polish wins on already-tight machines were 1.04-1.27x, and the
squeeze sweep measured "already spent" on several problems. A superoptimizer
polishing room interiors cannot find "pack three values into one word" —
that insight lives in the *encoding/behavior* layer of the contract, not in
the glyph grid. So: fund the composer (global geometry, squared payoff) and
the encoding levers above free-form room search. The factory's payable
rungs this window are characterize-and-pin and parametric sweeps of the
generators we already have; free-form superopt is a capped lottery ticket
(`claude_03` §2).

### 4. GPU should be declined explicitly, not left as an option

Branch-heavy, tiny-state, divergent integer simulation is a poor GPU
workload; a warp would mostly idle. The CPU fleet already saturates every
search design on the table. The only honest GPU use — learned proposal
models — cannot land in this window. Keeping the bullet alive invites
setup-time burn for zero contest value. (Post-contest, revisit with a
concrete kernel proposal or drop.)

### 5. The language bullet is right about content, early about form

"Come up with a language" invites the classic trap: syntax before two
consumers exist. Both sides independently landed on: freeze the *data
model* (contracts as schema + JSON), zero or thin syntax until the schema
survives two vertical slices. The user's required-content list (data in/out,
timing, pipe placement) is correct and is the minimal core — but it misses
two fields the measured record says are mandatory:

- **Capacity.** The memory ring deadlocks below 34 pipe cells across its
  two nets; sort and reverse have equivalent minimums. Capacity is a net
  property co-equal with timing (codex_01 agrees).
- **Evidence.** Prose decays: the cookbook's register-destruction list was
  wrong for two days (`claude_01` §1); the LLLM perimeter-wall rule is
  public-data-scoped, not spec-guaranteed. Every contract field needs its
  provenance (proved / measured / assumed-on-evidence), or the library will
  accumulate confident falsehoods exactly the way the cookbook did.

## What the brief is missing entirely

1. **Verification as a co-equal pillar.** Nothing in the six bullets
   mentions testing, yet the platform's most profitable subsystem so far IS
   the verification stack: preflight gates (which would have saved two
   submissions), reference oracles (24/24 and 7/7 frame-exact before any
   machine was built), adversarial fuzz (430 cases, 0 failures, projection
   corroborated within 0.5%). Under all-or-nothing pass scoring, one hidden
   -case bug = zero points, so verification is not hygiene — it is score.
   Proposed seventh bullet: *high-performance adversarial verification, same
   engine, same YT plane* (`claude_03` §4's attack family).
2. **The knowledge pipeline.** The library bullet assumes knowledge capture
   but does not say how facts stay true. The B-register episode is the
   cautionary tale and `claude_effects.json` the fix: datasheets are
   *generated* from characterization runs; prose only narrates. Make this a
   stated principle or the component library becomes a second cookbook.
3. **Multi-agent operations.** The platform multiplies writers (two models,
   subagents, YT jobs). This session alone produced one justified takeover,
   one filename collision (`memory_02.man` twice), and duplicate spec
   caching. Conventions now exist (prefixes, disjoint write sets, 15-minute
   pushed-progress leases) but they are folklore; the brief should own an
   explicit artifact-ownership and numbering scheme, because a composer
   emitting candidates at machine rate will hit every one of these
   collisions at machine rate.
4. **Score-model realism.** Local public-case scores rank; only submissions
   measure. The +12.5% projection miss on memory_04 (local:server tick
   ratio is machine-dependent) means any "create large optimal projects"
   tool must optimize scale-invariant quantities and treat projected scores
   as ±15% (`claude_01` §3).

## One process observation, in the brief's favor

The two-model split the user designed is already paying in both
directions: Codex's independent review caught two real gaps in Claude's
reference interpreter (wrap64, collisions) within the hour; Claude's
handoff caught the frontier-order bug in Codex's Pathfinder walk before it
became a wrong machine. Keep the structure — but promote agreements into
neutral decision records quickly (codex_index proposes the same), so the
debate converges instead of forking into two parallel platforms.

## Bottom line

The brief's shape is right and two of its six bullets (composition tooling,
the description language's *content*) point at exactly the hard, valuable
core. Re-weight the rest: narrow Rust to the executor, demote free-form
component optimization below the composer, decline GPU explicitly, add
verification and the knowledge pipeline as first-class pillars, and pin the
one decision only the user can make — contest-first or foundation-first —
because every prioritization above flips with that answer.
