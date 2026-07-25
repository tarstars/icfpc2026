# Agent Coordination

Read `docs/two-agent-protocol.md` before concurrent work. That document is
normative; this directory contains the synchronization artifacts.

## Layout

| Path | Purpose | Write owner |
| --- | --- | --- |
| `tasks/<task-id>.md` | Work package and exclusive path scope | Declared record owner |
| `status/<agent-id>.md` | Current agent snapshot | Named agent only |
| `messages/<sender>/*.md` | Immutable notifications | Sender only |
| `goals/*.md` | User-activated, time-boxed agent objectives | Integrator |
| `templates/` | Schemas for tasks, status, messages, and handoffs | Integrator |
| `peer-prompt.md` | Ready-to-paste onboarding prompt | Integrator |

The initialized agent IDs are `codex` and `claude`. Codex is the initial
integrator and submission controller; the user may change either role in a
task record.

## First-time worktree setup

After these protocol files are committed and available on `origin/main`,
inspect existing worktrees and branches:

```bash
git -C /home/tarstars/prj/icfpc2026 worktree list
git -C /home/tarstars/prj/icfpc2026 branch --all
```

If `agent/claude` does not exist, the integrator or user can create the
isolated peer worktree:

```bash
git -C /home/tarstars/prj/icfpc2026 fetch origin
git -C /home/tarstars/prj/icfpc2026 worktree add \
  /home/tarstars/prj/icfpc2026-claude \
  -b agent/claude origin/main
```

If the branch already exists, attach the worktree to that branch without
`-b`. Never reuse the integration worktree for a second writing agent.

## Fast check

From an agent worktree:

```bash
git fetch origin
git status --short --branch
find coordination/tasks -maxdepth 1 -type f ! -name README.md -print
sed -n '1,160p' coordination/status/codex.md
sed -n '1,160p' coordination/status/claude.md
find coordination/messages -type f -name '*.md' -print | sort
```

When inspecting a peer branch without checking it out:

```bash
git show origin/agent/claude:coordination/status/claude.md
git ls-tree -r --name-only origin/agent/claude \
  coordination/messages/claude
git log --oneline origin/main..origin/agent/claude
git diff --stat origin/main...origin/agent/claude
```

Replace `claude` with the relevant agent ID.

## Ownership invariant

Never edit the peer's status file or message namespace, even to acknowledge
their work. Send a new `ack` or `blocker` message from your own namespace.
