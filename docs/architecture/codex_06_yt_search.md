# Codex decision: local-first search, YT as the overflow tier

Status: contest-window decision, aligned with the user-validated compute
policy in `claude_05_contest_plan.md`.

## Decision

Use the local 20-logical-core machine first. A CPU-heavy, independently
shardable experiment expected to exceed approximately **five minutes
locally** is a YT candidate. Below that threshold, packaging, scheduling, and
result-transfer overhead is unlikely to pay.

This supersedes the earlier one-hour threshold in this file for the contest
window. It also removes the assumption that the YT worker must be Rust:
package the smallest deterministic implementation already validated locally.
Rust is justified only by a measured executor bottleneck.

GPU work is explicitly out of scope before contest close. The current
simulation, routing, and discrete mutation workloads have irregular control
flow and small per-candidate state; no GPU kernel or training workload has
passed a local smoke gate.

## Workload decision

| Workload | Local first | Promote to YT when |
| --- | --- | --- |
| Unit, public-case, and preflight tests | always | never |
| One composer chain or interactive debugging | always | not independently shardable |
| Independent annealing seeds | multiprocess smoke | projected aggregate exceeds ~5 min |
| Parameter/component sweeps | small grid | useful grid exceeds ~5 min |
| Differential fuzz and attack corpora | deterministic sample | independent corpus exceeds ~5 min |
| Candidate × workload matrices | top candidates locally | full matrix exceeds ~5 min |
| GPU training/inference | deferred | post-contest proposal with a concrete kernel |

YT is not the source of truth and never performs contest submissions.
Finalists return to the local Python parser, exact judge, and preflight.

## Preconditions

Before any local bulk write, follow `docs/storage-and-compute.md` and run:

```text
python3 scripts/check_external_storage.py --required-free-gib <GiB>
```

Stop if the `medium_data` volume, project root, free-space floor, or required
symlink is unavailable. Do not silently create repository-local replacements.

Before the first YT operation, confirm access to the canonical root:

```text
//home/delivery_ml/research/tarstars/icfpc2026
```

No access, operation, throughput, or row-count claim is made until a command
records it.

## Reproducible work unit

One task row should contain:

```text
task_id
task_kind
tool_hash
schema_version
base_candidate_hash
contract_or_netlist_hash
workload_hash
config_hash
seed
shard
budget
```

One result row should contain:

```text
task_id
status
candidate_hash
parent_hash
transformation
static_metrics
exact_metrics_if_run
validation_level
failure_class
counterexample_hash
elapsed_cpu
peak_memory
worker_version
```

Use consolidated native tables with discriminator columns rather than a
Cypress object per run or candidate. Candidate bodies and traces are
content-addressed objects referenced by hash, not repeated in every row.

Suggested remote layout:

```text
//home/delivery_ml/research/tarstars/icfpc2026/
  tables/catalog/objects
  tables/catalog/workloads
  tables/search/tasks
  tables/search/results
  tables/search/frontiers
  tables/validation/failures
  runtime/worker/<tool-hash>
  runs/<run-id>/manifest
```

## Promotion protocol

For every new job family:

1. Estimate local wall time from a small deterministic sample.
2. If the full useful workload is at most ~5 minutes, finish locally.
3. Run the exact packaged worker on a tiny local batch.
4. Run the same batch as a small YT smoke operation.
5. Compare result hashes and metrics exactly.
6. Record operation ID, source/tool/config/input hashes, row counts, resource
   settings, and compact metrics locally.
7. Launch the larger operation only after parity.
8. Download or summarize unique counterexamples and Pareto finalists before
   deleting reconstructable remote output.
9. Revalidate every selected finalist locally.

Search chains must be deterministic per seed. YT coordinates independent
chains or batches, not individual mutations with interactive driver feedback.

## First useful experiment

Do not launch a ceremonial fixed-size run. First implement and profile the
Python `memory_04` composer parity workload locally:

1. generate deterministic independent floorplan/route seeds;
2. statically reject overlap, pipe, capacity, and resolution failures;
3. exact-judge only the Pareto survivors;
4. measure aggregate local wall time on the 20-core pool.

If the useful seed budget exceeds ~5 minutes, package that exact workload for
a small YT parity smoke, then scale it. If it does not, keep the entire
experiment local and revisit YT on the next larger target.

The first distributed run succeeds only if it either finds a revalidated
candidate/counterexample or demonstrates a reproducible throughput advantage.
Merely completing an operation is not architectural validation.

## Credentials and integrity

- Keep submitter and worker credentials separate.
- Never package `.env`, API keys, browser state, or Git credentials.
- Pass worker credentials only through the operation secure vault.
- Workers have no contest-mutation capability.
- Cache keys include candidate, workload, evaluator, policy, and
  configuration hashes.
- Treat remote results as untrusted until locally schema-checked and
  revalidated.
- Preserve compact run manifests locally; raw logs and reconstructable bulk
  output do not belong in Markdown or ordinary Git.

## Post-contest GPU gate

GPU work may be reconsidered only with:

- a large stable corpus and fixed tensor/batch representation;
- a concrete training or inference kernel;
- a deterministic split and CPU baseline;
- a small parity smoke;
- evidence that proposal/ranking gains save more CPU search than training and
  inference cost.

A learned model may rank or propose candidates. Exact CPU validation remains
authoritative.
