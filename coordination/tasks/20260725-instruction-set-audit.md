# 20260725-instruction-set-audit: effective Codex policy

- Status: completed
- Record owner: codex
- Work owner: codex
- Reviewer: user
- Integrator: codex
- Base main commit: `87f599b`
- Branch: `agent/codex-instruction-audit`
- Created UTC: 2026-07-25T14:51:04Z
- Completed UTC: 2026-07-25T14:51:04Z

## Outcome

Identify the apparent instruction-set update, trace the repository changes to
commits, record their practical effect, and distinguish durable project policy
from session-only runtime behavior.

## Write set

- `codex/instructions.md`
- `codex/README.md`
- this task record
- Codex status/message namespace

## Acceptance evidence

- Complete root `AGENTS.md` read after the required current-state/storage/
  Codex bookkeeping sequence.
- `git log --follow` identifies the three policy-changing commits.
- `git diff --quiet bcf901e..HEAD -- AGENTS.md` exits zero, proving no later
  repository change to that file.
- The audit names the two sections missing from the shorter session excerpt.
- The one-hour-versus-five-minute YT conflict is identified with exact file
  references and an effective-policy ruling.

## Contest authority

No contest API call or mutation was required; this task changes no solution
version.
