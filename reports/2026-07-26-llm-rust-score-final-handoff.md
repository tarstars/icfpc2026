# LLM, Rust executor, and score-stream handoff

Date: 2026-07-26

## Release candidate

The complete candidate is pushed as:

- branch: `agent/codex-main-integration`
- validated implementation commit: `a899e03`
- base: `origin/main@f35eb11`
- merged Rust lineage: `agent/codex-rust@37bbb4d`
- merged Claude lineage: through `agent/claude@a9760e1`

It contains the complete accepted LLM machine, exact Rust executor, all five
score-improvement streams including the latest 31×31 TCP successor, both
agents' compact-LLM/LLLM evidence, and current `origin/main`. The user's dirty
local `main` worktree was not modified.

Claude subsequently pushed the explicitly incomplete compact-LLM checkpoint
`103cb8d` (no rig test and unfinished wiring). It is preserved remotely on
`agent/claude` but deliberately excluded from this release candidate; no
verified or submitted artifact depends on it.

## Requirement audit

| Goal requirement | Status | Authoritative evidence |
| --- | --- | --- |
| Correct LLM preserved and terminal | **proved** | `llm_codex_01.man`, SHA below; API submission `be96c6eb-...` refreshed terminal at 28/28 |
| Exact Rust executor | **proved for tested scope** | whole-state corpus, randomized/mutated programs, frames, pipes, registers, official Split/annihilation, cache and CLI tests |
| Frozen LLM workload below 60 s | **proved** | 1,623 assertions in 17.53 s versus 621.31 s |
| Expanded LLM workload below 60 s | **proved** | 2,012 assertions in 53.08 s versus 858.86 s |
| Deterministic multicore | **proved** | full 14-case batch equal at one/eight workers; 18.56 s versus 4.93 s |
| Standalone CLI and caching | **proved** | pure-Rust Rayon CLI, compressed versioned IR, one/N worker and full-frame LLM tests |
| At least three live score improvements | **proved, five** | refreshed terminal API results listed below |
| All valuable goal work pushed | **proved** | LLM, Rust, LLLM integration, Claude, and final integration commits are reachable on `origin`; local-only files are classified below |
| Independent final review | **proved** | Claude approved integration and Rust, then Codex closed the sole fallback finding in `a899e03` |
| Promotion to `main` | **pending final fast-forward** | reviewed integration branch is ready; local dirty `main` remains untouched |

## Accepted LLM

- artifact: `submissions/llm/llm_codex_01.man`
- SHA-256:
  `568d0b87937e9a41370d0b3434583d7109eb51ea9944b788e825e45c53e40ff6`
- bytes: 9,137,982
- dimensions: 749 × 25,797
- submission: `be96c6eb-e2bd-40a7-b5d2-a3aadbaf2b9b`
- result: 28/28, average 13,185,917.7857 ticks, score
  8,775,033,253,482,888

The authenticated API refresh on 2026-07-26 returned `done`, 28/28, with no
error or load error and the same dimensions and score as the checked-in
response.

## Rust executor

The Python parser remains authoritative. `littleman.fastsim` lowers it to a
versioned dense IR; `littleman.rustexec` crosses the PyO3 boundary; the native
engine executes the tick loop. Python batches use cached IR plus forked
processes because round callbacks hold the GIL. The standalone
`littleman-rust` binary uses a shared `Arc<Spec>` and deterministic indexed
Rayon collection, with no Python runtime.

Key measurements on an i7-13700H, Python 3.11.15, Rust 1.75.0:

| Measurement | Result |
| --- | ---: |
| Frozen 46-module LLM suite | 1,623 passed in 17.53 s; 35.44× baseline |
| Expanded 69-module LLM suite | 2,012 passed in 53.08 s; 16.18× baseline |
| Full 14-case LLM batch | 173,569,526 judged ticks |
| One worker | 18.56 s |
| Eight workers | 4.93 s; 3.76×; results identical |
| Compressed LLM IR | 33,149,652 bytes; 0.63 s encode |

The final integrated repository run was:

```text
uv run pytest -q -p littleman.rustexec -n 8 --durations=25
```

Result: **3,822 passed, 2 skipped, 4 expected xfails, 0 failed in 527.02 s**.
The skips are intentionally unloadable historical artifacts exercised by two
differential collectors. The xfails are the four explicitly unfinished
multi-man compact-LLM transcription cases, not the accepted LLM machine.

During integration this run caught a real plugin bug: replacing the
wall-tolerant server judge's `Machine` bypassed its Python `_tick` patch. The
specialized judge is now protected from replacement and the server-confirmed
Triangle final-wall-drain behavior has a directed regression.

Claude independently reviewed the candidate in a detached worktree and
approved it, finding one release issue: an explicit Rust-executor import
raised when PyO3 had not yet been built. Commit `a899e03` adds a transparent
`fastsim` fallback. The forced no-extension suite now reports 108 passed and
11 native-only skips; the native executor/CLI suite reports 122 passed and
one intentional skip. Compressed-IR encoding and official Split execution
remain explicitly native-only.

## Accepted score improvements

Each API result was refreshed on 2026-07-26 and returned `done`, full case
coverage, and no error/load error.

| Problem | Before | Current | Reduction | Submission |
| --- | ---: | ---: | ---: | --- |
| Reverse a List | 193,481.40 | 117,213.75 | 39.42% | `20a3f425-2ab2-4b41-aae8-503706a2810a` |
| Brackets | 943,438.46 | 836,345.19 | 11.35% | `3b77acf3-21cd-4ba9-80fb-5fcebf24ed44` |
| Packet Reassembly | 5,655,749.70 | 1,640,475.05 | 70.99% | `c5b2472f-8f70-4b9c-a263-d026c385def9` |
| Sort | 1,367,453.56 | 896,305.24 | 34.45% | `930fb828-32ed-42b6-8481-37e542270bb7` |
| Snake | 1,576,985,654.59 | 915,991,438.35 | 41.92% | `370c272b-75c5-4539-99b2-8794cf7591a9` |

Exact sources, response JSON, generators, and tests are integrated. Their
focused score-builder suites include 18 passing `tcp_08` tests. The newest
TCP result was independently refreshed through the authenticated API:
terminal 20/20 at 31×31, with no error or load error.

## Integration decisions

- Claude's compact LLLM `lllm_step` and `lllm_assemble` lineages are the
  authoritative generators because they reproduce the pressed variants.
- Both branches had independently named `lllm_00`. Claude's expected parent
  retains that name; Codex's separate 21/21 artifact/response are preserved as
  `lllm_codex_00`.
- The dependency union retains Maturin, bounded pytest-xdist, default
  parallel pytest execution, and the PyO3 build configuration.
- Seven Claude LLM artifacts were converted to the repository's existing Git
  LFS rule; `git lfs status` was inspected before staging and the objects were
  pushed.

## Worktree preservation audit

All Codex goal branches are clean and pushed. The formerly ahead
`agent/codex-lllm-integration` tracking branch was pushed through `1f381e1`;
those commits were already ancestors of this integration candidate. `git lfs
fsck` reports `Git LFS fsck OK`.

The old user-owned `main` worktree remains 186 commits behind with four
pre-existing untracked files; it was not modified or used as release state.
Claude's worktree has:

- an inbox-watermark edit;
- a regenerated `llm3_00.man` corresponding to the pushed but explicitly
  incomplete `103cb8d` STEP3 checkpoint;
- an untracked `sort_kring.py` skeleton with an empty pump body, superseded by
  the recorded negative k-ring analysis.

None is a completed, accepted, or otherwise irreproducible goal result.
Claude's source checkpoint is pushed on `origin/agent/claude`; the stable
release candidate intentionally excludes it.

## Remaining actions

1. Re-fetch and fast-forward `origin/main` to this approved integration
   candidate without touching the user's dirty local worktree.
2. The user's separate manual Memory improvement (16,033,454.75) has no
   recoverable source in Git or bearer-authenticated API. If the user still
   has it, preserve it as `submissions/memory/memory_11.man`; this is external
   to the agent-created score stream but is the only known live result lacking
   its exact source.
3. Compact LLM remains a score-only research lane; its accepted 28/28 baseline
   is already secure and must not be replaced unless a fully gated candidate
   has a strictly lower server score.
