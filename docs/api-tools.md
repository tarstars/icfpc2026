# Contest API Tools

The `icfpc-api` command is the safe, machine-readable interface to the
documented contest API. It uses the API described in `docs/api.md`, emits JSON
results on standard output, sends progress and errors to standard error, and
never prints the bearer key.

## Setup

Install the locked project environment:

```bash
uv sync
```

The repository-root `.env` is Git-ignored and must remain mode `0600`. It
contains:

```text
ICFPC2026_LOGIN
ICFPC2026_PASSWORD
ICFPC2026_API_KEY
```

Normal API commands use only `ICFPC2026_API_KEY`. Process environment values
take precedence over `.env`. Never pass the key on the command line, commit
`.env`, or copy credentials into reports or run logs.

## Tool descriptions

| Command | Effect | Authentication |
| --- | --- | --- |
| `uv run icfpc-api problems` | List released problems. Use this to map a slug to the `problemId` required by submission and to reject `practice` targets. | None |
| `uv run icfpc-api problem <slug>` | Fetch the statement, I/O contract, scoring rule, and public test data for one released problem. | None |
| `uv run icfpc-api clock` | Fetch contest timing, submission closure, and scoreboard-freeze state. | None |
| `uv run icfpc-api submission <id>` | Read one submission owned by this team once. | Bearer key |
| `uv run icfpc-api wait <id>` | Poll at 2.5-second intervals until the submission is `done` or `failed`. | Bearer key |
| `uv run icfpc-api submit <problem-id> <program-file> --confirm` | Create exactly one contest submission from the file's exact UTF-8 contents. This is an external mutation. | Bearer key |

Add `--wait` to `submit` to poll the newly created submission:

```bash
uv run icfpc-api submit <problem-id> submissions/example.man --confirm --wait
```

Use `--compact` before the subcommand for JSON-lines-style output:

```bash
uv run icfpc-api --compact problems
```

Redirect standard output to save a response while keeping status messages
visible:

```bash
uv run icfpc-api problem <slug> > data/small/problems/<slug>.json
```

## Submission safety

Before submitting:

1. Run `problems` and confirm that the exact ID is graded, not practice.
2. Judge the exact file locally against all public cases.
3. Record or preserve the exact source being submitted.
4. Pass `--confirm` only when creating a server-side submission is intended.

`submit` performs no automatic retry, because retrying an ambiguous POST could
create duplicates. It rejects programs larger than 10,000,000 UTF-8 bytes
before making a request. The server permits at most five pending/running
submissions per team.

The server returns errors as
`{"error":{"code":"...","message":"..."}}`. The command exits nonzero and
prints a concise error without request headers. In particular:

- `401 unauthorized`: the bearer key is absent or invalid.
- `403 forbidden`: the target is practice-only.
- `404 not_found`: the problem or submission is unavailable.
- `413 payload_too_large`: the program exceeds the server limit.
- `429 too_many_requests`: wait for an in-flight submission to finish.

Use `--help` on the command or any subcommand for the complete argument list.
