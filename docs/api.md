# Contest API

Source: https://icfpcontest2026.com/api-help, captured 2026-07-24 from the SPA
bundle. Base URL: `https://icfpcontest2026.com/api/v1`. Responses are JSON.

Note: plain `urllib` gets HTTP 403 — send a browser-like `User-Agent` header
(curl with `-A "Mozilla/5.0"` works).

## Your API key

Send it as a bearer token on every submission request. It identifies your
team.

## List problems

    curl https://icfpcontest2026.com/api/v1/public/problems

Every released problem, as `id`, `slug`, `name`, `problemSetName`, and
`status`. Submitting takes the `id`; everything else here takes the `slug`.
A `practice` problem is ungraded and rejects submissions. No key needed.

## Fetch one problem

    curl https://icfpcontest2026.com/api/v1/public/problems/<slug>

Adds `description`, `io`, `scoring`, and `publicTestData` — the same public
cases the editor runs. Private cases are not served. No key needed.

## Fetch problem standings

    curl https://icfpcontest2026.com/api/v1/standings/problems/<problem-id>

Returns the current public snapshot for one graded problem, including update
time, freeze state, team rows, passed cases, scores, ranks, and points. No key
needed. The repository command is
`uv run icfpc-api standings <problem-id>`.

## Submit a program

    curl -X POST https://icfpcontest2026.com/api/v1/submissions \
      -H "Authorization: Bearer <your-api-key>" \
      -H "Content-Type: application/json" \
      -d '{"problemId":"<problem-id>","program":"<source>"}'

Returns `202` with `{"id":"…","status":"pending"}`. `program` is the grid
itself, newlines and all.

## Poll a result

    curl https://icfpcontest2026.com/api/v1/submissions/<submission-id> \
      -H "Authorization: Bearer <your-api-key>"

`status` goes `pending` → `running` → `done` or `failed`. On `done`,
`casesPassed`/`casesTotal` are the counts and `output` is the runner's
summary. If the program failed to load, `loadError` carries the load failure
instead — no test case was run. You may only read your own team's
submissions.

## Limits and errors

Every error is `{"error":{"code":"…","message":"…"}}` with a matching HTTP
status.

- `401 unauthorized` — missing or invalid key.
- `403 forbidden` — the problem is practice-only.
- `404 not_found` — no such problem, or it isn't released.
- `413 payload_too_large` — programs cap at 10 MB.
- `429 too_many_requests` — 5 of your submissions may be waiting to run at
  once. Wait for one to finish.

## Repository tooling

Use the `icfpc-api` commands rather than hand-built authenticated requests.
Their command descriptions, setup, and submission safeguards are documented
in [api-tools.md](api-tools.md).
