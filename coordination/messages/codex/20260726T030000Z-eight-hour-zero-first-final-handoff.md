# Eight-hour zero-first final handoff

Status: preservation complete; two targets secured, LLM unfinished; no
uncommitted work and no final-window contest mutation.

## GitHub state

Fresh remote heads:

| Branch | Remote head | Role |
| --- | --- | --- |
| `main` | `f35eb11` | accepted shared baseline |
| `agent/codex-pathfinder` | `057d6ab` | Pathfinder history |
| `agent/codex-lllm-integration` | `1bea511` | accepted LLLM integration |
| `agent/codex-llm` | `fcc66ca` | current LLM construction |

The LLM branch is clean and byte-identical to its remote. It contains 32
pushed commits after `origin/main`, from `09a7ccc` through `fcc66ca`
(10,931 insertions across 106 files). The late component checkpoints are:

- `60a8186` exact pipe runtime primitives;
- `4f2e475` physical two-pipe selector;
- `6c35c12` destination-room predicate;
- `c1fad69` exact physical runtime frames;
- `0a4e6df` physical binding front end;
- `7d13c12` executable action protocol;
- `5321fcc` / `4548616` wall predicate and whole-state scan;
- `415ce32` delimiter-safe state fan-out;
- `f240d0c` frame-to-DRAW adapter;
- `220811c` physical room/pipe state index;
- `fcc66ca` lossless indexed-state inverse.

Pathfinder's accepted artifact commit is `2cce782`; LLLM's is
`d491d2e85bccfec12ff122f70b4586e89cc9c63c`.

## Current contest state

Exact submission reads at preservation time:

| Target | Submission | Result | Geometry / score |
| --- | --- | --- | --- |
| LLLM | `2fec95f9-0204-4301-b860-ecec53ec80c7` | 21/21 | 141x837; 173,340,987,019.71426 |
| Pathfinder | `0c04a141-a73b-443c-a274-741bfe67d857` | 18/18 | 187x1957; 17,546,210,849,166.055 |
| LLM | `e57fd7d2-352d-4929-a474-2009a6af4fd0` | 2/28 | 307x312; no score |

LLM still reports 13/14 public and 13/14 private wrong-frame failures. No
partial successor was submitted: the mandatory 14/14, fuzz, and preflight
gates are not yet satisfied.

## Validation

Final LLM command:

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

The new state index additionally passed all 14 public plus 10 physical fuzz
streams, and its inverse round-tripped all 14 public plus 20 fuzz states.
It is 274x113, 1,136 occupied cells, and takes 3,375 to 24,143 ticks on the
public setup states.

Previously preserved gates:

- LLLM: 10/10 public, 50/50 whole-machine fuzz, 122 component tests, three
  organizer-WASM comparisons, preflight `READY TO SUBMIT`, then 21/21 live;
- Pathfinder: 7/7 public, eight adversarial frame streams against Claude's
  independent reference, preflight `READY TO SUBMIT`, then 18/18 live.

## Failed attempts and lessons

- Pathfinder `pathfinder_00` was exact locally but hit the live tick cap on
  3/11 private cases (15/18). Shortening protocol pipes and compacting hot
  execution zones reduced public average ticks by 58.5%; `pathfinder_01`
  then passed 18/18.
- The existing LLM artifact emits only the initial frame, so its 2/28 result
  is a diagnostic partial, not a baseline. Repeated partial submissions were
  stopped once the API confirmed they earn zero.
- The state-index rig initially had two spatial binding faults: late main
  reads selected the scratch-return pipe, and the late sentinel selected
  display output. Physical resolution audits found both; centered endpoints
  now make all choices strict.
- A reference-only action executor is insufficient. The remaining work is
  physical whole-state traversal and mutation; every leaf operation and
  rendering stage is already independently exact.

## Smallest next action

LLLM and Pathfinder need no baseline work.

For LLM, consume one indexed room header and the at-most-two global pipe
records:

1. emit two fixed nine-word PIPECANDIDATE requests (absent slot =
   ineligible);
2. feed their pairs to SELECTELIGIBLE;
3. route the selected indexed record through PIPEAPPLY;
4. patch the selected pipe plus the room's address/A fields;
5. repeat in creation order for at most three rooms;
6. unindex, MANMAP/RECORDSTRIP, then WALLSCAN and
   STATECOPY -> STATEFRAME -> PAIRPACK -> DRAW.

The immediate implementation boundary is step 1 for one room. Use the event
token as the stable source identity; `fcc66ca` proves that globalizing and
restoring the pipe table is lossless. Claude can independently adversarially
review this protocol and the endpoint-binding proofs without editing Codex's
branch.
