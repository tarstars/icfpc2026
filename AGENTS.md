# Agent Operating Policy

## Read order

1. Read `docs/current-state.md`.
2. Read `docs/storage-and-compute.md` before creating data or launching costly work.
3. For Codex work, read `codex/state.md`, `codex/decisions.md`, and
   `codex/validation.md`.
4. Inspect only the task-specific source, report, or log needed next.

Keep `docs/current-state.md` concise and current. Put detailed experiment
results in one focused `reports/YYYY-MM-DD-*.md` file and link it from the
state or worklog. Never paste full logs into Markdown.

## Search boundaries

- Never include `~/prj/arc00` or `~/prj/arcadia` in broad filesystem searches.
  They are huge mounted repositories.
- Search this repository first with `rg` or `rg --files`.
- Inspect a named path in those repositories only when a task explicitly
  requires an example from it.
- `codex/` is Codex bookkeeping; `claude/` is Claude bookkeeping. Do not edit
  the other assistant's area unless the user explicitly asks.

## Repository contents

Keep source, tests, selected binaries, contest documents, small datasets,
compact configs, manifests, checksums, aggregate metrics, figures, and reports
inside this repository.

Use Git LFS for large artifacts that genuinely need versioning. Before adding
one, verify `git lfs version`, add or confirm an appropriate tracking rule,
and inspect `git lfs status`. Do not commit a large object as ordinary Git
data merely because Git LFS is unavailable. Reproducible build trees, caches,
virtual environments, raw run outputs, and bulk datasets do not belong in Git.

## Local bulk storage

- The authoritative bulk filesystem is identified by label `medium_data`.
- Its observed mount on 2026-07-24 is `/media/tarstars/medium_data`.
- This project's physical root is
  `/media/tarstars/medium_data/database/icfpc2026`.
- The logical roots `artifacts`, `outputs`, `yt_work`, `data/generated`, and
  `data/external` must be symlinks resolving beneath that physical root.
- Before every bulk write, run
  `python3 scripts/check_external_storage.py --required-free-gib <GiB>`.
- If the volume, physical root, free space, or any link is unavailable, stop.
  Never replace a missing external-backed path with a real repository
  directory.
- Never delete the only verified copy of an artifact.

## YT compute and storage

- The canonical remote root is
  `//home/delivery_ml/research/tarstars/icfpc2026`.
- Use local compute for unit tests, smoke tests, payload preparation, quick
  inspection, and work comfortably below one hour.
- Evaluate YT first for independent CPU work expected to exceed roughly one
  hour: search shards, simulation, Monte Carlo, corpus generation, dedupe, or
  large evaluation matrices.
- Use YT GPU jobs for training-scale neural workloads only after a small local
  or YT smoke test establishes functional parity.
- Treat YT Cypress nodes as scarce. Prefer consolidated native tables with
  discriminator columns and shared canonical inputs/runtimes over per-run
  copies and many small objects.
- Keep submitter and worker credentials separate. Never commit or log tokens;
  pass worker credentials through the operation secure vault.
- Record operation IDs, code/config hashes, input paths, row counts, and
  compact metrics locally. Download or summarize required outputs before
  deleting reconstructable remote runs.

## Integrity

- Do not invent contest facts, measurements, run metadata, or credentials.
- Every reported metric must trace to a command or generated artifact.
- Preserve repo-relative paths in manifests and documentation.
- Keep secrets, personal tokens, browser state, and session data out of Git
  and shared artifact storage.

## Two-agent coordination

When two agents are active, follow `docs/two-agent-protocol.md` and use the
tracked artifacts under `coordination/`.

- Never let two writing agents share one Git worktree or index. Use one
  worktree and branch per agent.
- Exactly one agent is the integrator. Only the integrator updates `main`,
  edits shared state hotspots, and performs contest-side mutations.
- Every concurrent task needs one owner, an exclusive write set, acceptance
  checks, and an integration owner recorded before implementation starts.
- Each agent edits only its own status file and message namespace. Treat
  messages as immutable after publishing; correct them with a new message.
- Fetch and inspect the other agent's published status at task start, before
  touching a shared path, at handoff, and before integration.
- Direct chat is useful for urgency, but decisions, measurements, handoffs,
  blockers, and external mutations are not synchronized until recorded in the
  repository.

## Solution commit freshness

Before committing any new or changed solution version:

- Pull and integrate the current GitHub branch. Use `git pull --rebase` (or an
  equivalent fetch-and-integrate workflow) before staging the solution so the
  commit is not based on stale remote work. Never autostash unrelated worktree
  changes; if they make a safe pull impossible, stop and resolve the scope
  first.
- Query the contest API for the current score and latest submission state of
  the exact problem being changed.
- Reconcile the pulled solution catalog and live API result with the candidate
  being committed. Preserve distinct versions and their measured properties;
  do not replace a stronger or newer result with stale local metadata.
- Record only command- or API-traceable score facts in solution metadata and
  reports.
