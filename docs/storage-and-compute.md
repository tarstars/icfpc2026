# Storage and Compute Policy

Updated: 2026-07-24

This policy adapts the established `troll_farm` and `math_through_eml`
workflows for ICFPC 2026.

## Placement

Keep these in Git:

- contest statements and compact reference documents;
- source, tests, selected release/submission binaries;
- small fixtures and hand-built cases;
- configs, manifests, checksums, aggregate metrics, figures, and reports.

Keep these on `medium_data`:

- raw or generated bulk datasets;
- search frontiers, simulation matrices, traces, and replay corpora;
- checkpoints, model weights, profiler captures, and raw predictions;
- YT payloads, runtime archives, and downloaded output bundles.

Use these stable repository paths:

| Logical path | Purpose |
| --- | --- |
| `artifacts` | Large durable experiment artifacts and checkpoints |
| `outputs` | Large run outputs and extracted bundles |
| `yt_work` | YT payload staging and downloads |
| `data/generated` | Regenerable generated data |
| `data/external` | Downloaded or externally supplied bulk data |

They resolve below the physical root
`<medium_data mount>/database/icfpc2026`. The filesystem label is authoritative;
the current mount path is only observed state.

## Mandatory USB preflight

Before any write through a bulk root:

```bash
python3 scripts/check_external_storage.py --required-free-gib <GiB>
```

The check verifies the unique mount by label, physical project root, symlink
targets, target filesystem label, and requested free-space floor. A failure
blocks the write. Do not create a local fallback directory under a broken
symlink name.

For migration, copy before delete. Compare regular-file counts and apparent
bytes, require an itemized `rsync --dry-run --delete` with zero differences,
then replace the source path. Use checksums for irreplaceable inputs.

## Git LFS

Git LFS is for large, version-worthy objects, not for arbitrary run output.
The attributes file covers common archive, array, table, and model formats.
For a large extensionless binary, add an explicit path rule:

```bash
git lfs install
git lfs track "bin/<name>"
git add .gitattributes "bin/<name>"
git lfs status
```

Do not add matching objects while `git lfs version` fails. Prefer a compact
manifest plus an external artifact when the object is reproducible or changes
frequently.

## YT

Use:

```text
//home/delivery_ml/research/tarstars/icfpc2026
```

Suggested remote layout:

```text
tables/catalog/records
tables/catalog/datasets
runtime/<runtime-name>
runs/<run-name>/config
runs/<run-name>/inputs
runs/<run-name>/outputs
```

Prefer native YT tables for large record sets. Consolidate logical datasets
and distinguish them with columns such as `dataset_version`, `origin`, `split`,
or `experiment`. Reference canonical datasets and runtimes from runs instead
of copying them.

Use map/sort/reduce for large independent CPU batches. Use vanilla GPU
operations for training-scale neural work after smoke validation. An expected
local wall time above roughly five minutes is the preferred point to evaluate
YT. This is a scheduling preference, not a hard cutoff: keep interactive work
or jobs dominated by YT packaging/startup overhead local.

The local launcher credential and remote worker credential are separate roles.
Use a least-privilege worker token delivered through YT secure vault. Never
forward a personal token by default, print token values, or store them in
payloads.

Each remote run should leave a compact local record containing its operation
ID, exact command/config, source revision or hash, canonical input paths,
runtime identity, row/task counts, and final status. Preserve useful outputs
or summaries before removing reconstructable remote nodes.
