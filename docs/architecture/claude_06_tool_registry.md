# Claude: the tool registry — status by evidence, not by effort

Status: Proposed in response to the user's registry idea, with a seeded
registry below. Intended home after integration: a single top-level
`docs/TOOLS.md` owned by the integrator, updated only with evidence links.

## The user's idea, and one correction

Proposal as given: track tools; when a lot of effort went into one (like
the `.man` -> IR converter), mark it **gold** and everyone must use it.

Adopted — with the criterion changed. **Effort is not what makes a tool
gold; evidence is.** The cookbook is the counterexample that settles this:
it absorbed more effort than any tool in the repository and carried a wrong
register rule for two days, plus a missing load rule that killed two
submissions. An expensive tool can be wrong; a cheap generated table can be
right. So the ladder runs on verification state, and effort is only a
reason to *finish* verifying something, never a reason to trust it.

The second half of the idea — *everyone must use it* — is adopted exactly,
as a property called **mandatory-on**: a gold tool names the workflows
where hand-rolling an alternative is a protocol violation (e.g. no
submission bypasses `preflight`; no one computes pipe bindings by hand
instead of `ir_export`).

## Status ladder

| Status | Meaning | Requirements |
|---|---|---|
| `draft` | exists; owner may use | none |
| `verified` | others may rely on it | pinned tests; at least one real use with a recorded result |
| `gold` | **mandatory on its declared paths** | tests + a gate against ground truth (golden corpus, server evidence, or oracle) + documented one-line usage + named owner + a `displaces` list |
| `errata` | still in use, known-wrong parts listed | each erratum linked to its correction |
| `retired` | do not use | pointer to the replacement |

Demotion is a first-class transition: a gold tool contradicted by server
evidence goes to `errata` the same day, with the incident linked. Statuses
change only with an evidence link; the history is append-only.

## Where it lives

**This repository, one file.** Not a separate repo: tools must version with
the code and the golden corpus they are gated on, or the registry desyncs
into a second cookbook. Not a directory of records: one table is greppable
and cheap to keep honest. The file is integrator-owned shared state
(single-writer rule); either agent proposes changes by message with
evidence, Codex applies them.

Tasks stay where they are: `coordination/tasks/` already has owners, write
sets and acceptance checks. The only glue needed: a task record's
acceptance checks name the gold tools it must run (submission tasks already
de-facto require `preflight`). Agents' onboarding prompts point at the
registry instead of hand-listing tools — this session's subagent prompts
hand-listed gates, which is exactly the duplication a registry removes.

## Seed registry (statuses as of 2026-07-25T14:0xZ, honest)

| Tool | Path | Status | Mandatory-on | Gate / evidence | Displaces |
|---|---|---|---|---|---|
| Exact simulator + parser | `littleman/sim.py` | **gold** | all execution/parsing | golden corpus; server-corroborated (B-survival via brackets_00 experiment) | any ad-hoc interpreter |
| Round-controller judge | `littleman/judge.py` | **gold** | all timing/scoring | bare `run()` proven meaningless on server machines (twice) | timing via `Machine.run` |
| Server-compat gates | `littleman/server_compat.py` | **gold** | pre-submission | shared-wall + final-wall divergences, confirmed live | trusting the plain parser |
| Two-cell pipe check | `littleman/alexey_pipecheck.py` | **gold** | pre-submission | killed artifacts sort_05, reverse_02 | eyeballing pipe lengths |
| Preflight gate | `scripts/preflight.py` | **gold** | every submission | chains all of the above; verified on live memory_04 | any partial checklist |
| Submission CLI | `src/icfpc_api/` | **gold** | every contest mutation | sole sanctioned submit path; responses preserved | curl / manual UI submits |
| .man -> IR exporter | `littleman/ir_export.py` | verified -> gold candidate | binding/geometry queries | 94 tests; 45-artifact corpus round-trip; engine-true resolution map | hand Manhattan math |
| Opcode effects table | `scripts/gen_effects.py` + `claude_effects.json` | verified | register-model questions | 400 probes/op; 16 pinned facts; server-corroborated | prose op tables |
| LLM/LLLM reference | `littleman/llm.py` | verified | oracle for both interpreter problems | 24/24 public frame sequences exact; inherited-semantics tests | judging those machines by eye |
| LLM/LLLM fuzz | `littleman/llm_fuzz.py` | verified | pre-submission for LLM/LLLM | contract-compliance + oracle-exactness tests | public-cases-only validation |
| Snake reference | `littleman/snake.py` (agent WIP) | verified (reference part) | oracle for snake | 5/5 public, 129 frames | — |
| Pathfinder reference | `claude/pathfinder-reference.py` | verified | oracle for pathfinder (Codex-owned build) | 7/7 public | — |
| Canvas assembler | `littleman/canvas.py` | verified | — | used by every shipped generator | — |
| Squeeze/trim tools | `littleman/alexey_squeeze.py`, `alexey_trimrooms.py` | draft (Codex's to grade) | — | sweep results recorded on main | — |
| Cookbook | `docs/littleman-cookbook.md` | **errata** | still the idiom reference | §1 register list wrong (fix pending); 2-cell rule absent from §4 | — |

Two entries deserve emphasis because they encode the registry's own logic:
the cookbook sits at `errata` precisely because effort never conferred
trust, and `ir_export` waits at `verified` until the composer actually
consumes it in anger — promotion needs a consumer, not a birthday.

## Enforcement, cheap where it matters

- Submission path: already hard-gated (`preflight` refuses; protocol
  requires it). Keep the only hard enforcement here — it is where a miss
  costs a dead submission.
- Corpus gates as CI: `test_ir_export` already forces every checked-in
  artifact through the IR round-trip; `test_effects_table` pins the
  register model. A new gold tool ships with exactly such a pin.
- Everything else is review-time: the registry makes "you hand-rolled what
  X already does" a one-line objection with a link.

## Requested decisions

1. Codex: adopt as `docs/TOOLS.md` (integrator-owned), seeded from the
   table above, statuses adjustable by evidence.
2. Both agents: onboarding/subagent prompts reference the registry instead
   of hand-listing tools.
3. User: confirm the criterion change (evidence over effort) matches the
   intent.
