# Authoritative eight-hour zero-first handoff

This message supersedes earlier handoff tables where later Claude/API
synchronization changed LLLM state. It is the single current handoff for the
goal in `coordination/goals/20260725-eight-hour-zero-first.md`.

Status: Pathfinder and LLLM secured; LLM unfinished; goal remains active.
No final-window solution edit or contest mutation occurred.

## Pushed branches and commits

| Branch | Remote head before this message | Preserved result |
| --- | --- | --- |
| `agent/codex-llm` | `d389aeb` | LLM construction and final evidence |
| `agent/codex-y-memory` | `cb945c5` | Y-worker design and goal file |
| `agent/codex-pathfinder` | `057d6ab` | accepted Pathfinder history |
| `agent/claude` | `1d62342` | Claude's pressed LLLM history |
| `main` | `f35eb11` | current shared remote baseline |

The LLM implementation is the 32-commit range `09a7ccc..fcc66ca` after
`origin/main`. Its final implementation checkpoints are:

- `60a8186`: exact pipe runtime primitives;
- `4f2e475`: physical selector;
- `6c35c12`: destination-room predicate;
- `c1fad69`: exact runtime frames;
- `0a4e6df`: physical binding front end;
- `7d13c12`: executable action protocol;
- `5321fcc`, `4548616`: wall predicate and state scan;
- `415ce32`: delimiter-safe state fan-out;
- `f240d0c`: frame-to-DRAW adapter;
- `220811c`, `fcc66ca`: physical state index and lossless inverse.

Pathfinder's accepted artifact commit is `2cce782`. Claude's accepted pressed
LLLM commit is `143beb7`; it has been independently reviewed but is not yet
integrated into `main`.

## Exact current API state

Final exact submission reads:

| Target | Submission | Result | Geometry / score |
| --- | --- | --- | --- |
| LLLM | `efce1ac1-ece0-4557-a08e-4d34edd9dd4d` | 21/21 | 307x312; 22,187,469,586.285713 |
| Pathfinder | `0c04a141-a73b-443c-a274-741bfe67d857` | 18/18 | 187x1957; 17,546,210,849,166.055 |
| LLM | `e57fd7d2-352d-4929-a474-2009a6af4fd0` | 2/28 | 307x312; no score |

LLM reports 13/14 public and 13/14 private wrong-frame failures because the
submitted artifact is the single-room LLLM machine. No incomplete physical
successor was submitted.

## Validation evidence

Final consolidated LLM command:

```text
uv run pytest -q \
  tests/test_llm_actionprotocol.py tests/test_llm_bindscore.py \
  tests/test_llm_bordercheck.py tests/test_llm_pipecandidate.py \
  tests/test_llm_pipeselect.py tests/test_llm_selecteligible.py \
  tests/test_llm_pipeaction.py tests/test_llm_pipeapply.py \
  tests/test_llm_pipeframe.py tests/test_llm_stateframe.py \
  tests/test_llm_wallhit.py tests/test_llm_wallscan.py \
  tests/test_llm_statecopy.py tests/test_llm_pairpack.py \
  tests/test_llm_stateindex.py
```

Result: `375 passed in 89.16s`.

Additional LLM evidence:

- STATEINDEX is physical/reference exact for all 14 public plus 10 fuzz
  states; its inverse round-trips all 14 public plus 20 fuzz states;
- STATEINDEX is 274x113, 1,136 occupied cells, 3,375–24,143 public ticks;
- all 47 STATEINDEX pipe operations have strict intended bindings; minimum
  competing-port margin is 19 cells;
- event-token room identities selected exactly the same pipe as numeric room
  indices for 1,596 executed actions, including four two-eligible cases and
  two exact Manhattan-distance ties.

LLLM pressed-artifact review in a clean worktree:

```text
uv run pytest -q tests/test_lllm_press.py
2 passed in 0.14s

uv run python scripts/preflight.py \
  submissions/lllm/lllm_03.man little-little-little-man
VERDICT: READY TO SUBMIT
cases: 10/10
sha256: 2e2b99e00d03904731247e280c87c6f3b9c7a014126f03d1177fa2f0a88543e6
```

The preserved LLLM and LLM `llm_03` artifacts are byte-identical and their
JSON records match exact API reads.

Previously preserved Pathfinder gates:

- 7/7 public;
- eight deterministic adversarial frame streams against Claude's independent
  reference;
- preflight `READY TO SUBMIT`;
- 18/18 live.

## Uncommitted ownership

Every Codex agent worktree is clean.

The shared local `main` worktree has four pre-existing untracked files not
modified or claimed by this run:

- `coordination/goals/20260725-eight-hour-zero-first.md`;
- `docs/PERFORMANCE_OPTIMIZATION_AGENT_GOAL.md`;
- `src/littleman/memory_packed_codex.py`;
- `submissions/triangle/triangle_00.man`.

The goal file itself is safely pushed on both `agent/codex-llm` and
`agent/codex-y-memory`; the shared-main copy was left untouched.

## Failed attempts and measured reasons

1. Pathfinder `pathfinder_00` passed all public but hit the live tick cap on
   3/11 private cases (15/18). Geometry-only pipe/hot-zone compaction reduced
   public average ticks by 58.5%; `pathfinder_01` then passed 18/18.
2. LLM's current live 2/28 artifact is diagnostic only and earns no score.
   Partial resubmissions were stopped; the next submission remains gated on
   a complete physical runtime.
3. STATEINDEX initially misbound late main reads to scratch and its sentinel
   to display output. Physical tests exposed both; centered endpoints now
   give a measured 19-cell minimum margin.
4. Claude's pressed LLLM could not be mechanically integrated into `main`:
   - press-only cherry-pick preflighted 10/10 but its source tests lacked
     `lllm_02` and generated a bad pipe at `(55,218)`;
   - the full four-commit chain preflighted 10/10 but conflicted with main's
     independent STEP source/tests, failed test collection on removed layout
     constants, and had 20 Ruff findings.
   Both temporary integrations were discarded; no `main` push occurred.

## Smallest next actions

Pathfinder and LLLM require no baseline work.

For LLM:

1. consume one indexed room header and the at-most-two global pipe records;
2. extract send target from the first body cell and receive target from the
   last body cell before `PIPE_DEST_STATE`—never use the packed start token;
3. issue two fixed PIPECANDIDATE requests, marking an absent slot ineligible;
4. SELECTELIGIBLE, route the selected record through PIPEAPPLY, and patch the
   mutable pipe table plus room address/A on success;
5. repeat in creation order for at most three rooms;
6. unindex, MANMAP/RECORDSTRIP, then WALLSCAN and
   STATECOPY -> STATEFRAME -> PAIRPACK -> DRAW.

The immediate coding boundary is steps 1–3 for one room. The leaf services,
stream formats, selection identity, tie handling, frame rendering, freeze
predicate, fan-out, and DRAW packing are already independently exact.

For repository integration, reconcile Claude's final LLLM STEP source and
main's black-box tests on a dedicated branch before bringing the pressed
artifact to `main`; do not mechanically cherry-pick or merge wholesale.
