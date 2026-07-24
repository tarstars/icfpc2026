# ICFPC 2026

Shared workspace for the ICFP Programming Contest 2026.

## Layout

- `src/` — solver, tooling, and library source.
- `bin/` — selected reference or submission binaries. Large binaries belong in Git LFS.
- `data/small/` — small, reviewable inputs and fixtures.
- `docs/` — shared specifications, policies, and current state.
- `reports/` — compact experiment reports and aggregate results.
- `submissions/` — reproducible submission sources, manifests, and compact bundles.
- `artifacts/`, `outputs/`, `yt_work/`, `data/generated/`, `data/external/` — bulk roots backed by the `medium_data` USB filesystem.
- `codex/` and `claude/` — separate assistant bookkeeping areas.

Start with [docs/current-state.md](docs/current-state.md), then read
[AGENTS.md](AGENTS.md). Before writing bulk data, run:

```bash
python3 scripts/check_external_storage.py --required-free-gib 1
```

The contest problem and implementation stack are intentionally left open until
the task is published.
