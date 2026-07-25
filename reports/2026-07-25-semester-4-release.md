# Semester 4 problem release

Date: 2026-07-25

The public contest API released four new graded problems. Their complete API
objects—including statements, I/O contracts, display frames, and public test
data—are attached under `data/small/problems/`. The refreshed index now
contains 20 released problems: 16 graded and 4 practice.

| Order | Problem | ID | Public cases | Tick cap | Archived SHA-256 |
| ---: | --- | --- | ---: | ---: | --- |
| 0 | `snake` | `15982f19-7465-4902-b7ef-c592e2b0150b` | 5 | 15,000,000 | `68324e0bdbf5623160a88c39fcf7c1bc164bfd8090149270a1a0c60668a6c37d` |
| 1 | `pathfinder` | `c778ba35-4918-415b-83d0-37dc8f6f68c9` | 7 | 15,000,000 | `5744a044c6436b8ba5a6bf8ca93b2bd24428fbb2f6dd1f3b1ae51042e900958d` |
| 2 | `little-little-little-man` (LLLM) | `d91edb43-4e94-4541-b8f7-9c79ba8c8331` | 10 | 15,000,000 | `072c621e5f2c595cde2906b7893b6ca34e6ac7aeae201ba76a90ae956a4a6982` |
| 3 | `little-little-man` (LLM) | `383158cc-1891-46b2-9a9f-d9ed2661c85d` | 14 | 50,000,000 | `f90e0768bcd4e2edb6f410d880570611584d54bd6d5de43884e03e88b5f17fc8` |

All four use footprint-tick scoring and a 16×16 display.

## Contracts at a glance

- **Snake:** maintain a growing snake for at most 100 rounds, apply fruit and
  direction events, detect wall/self collision, and render snake/fruit state.
- **Pathfinder:** ingest a 256-cell maze, then render every move of the
  tie-broken shortest path to each successive flag; paths are at most 64
  moves.
- **LLLM:** interpret one single-room subset program for at most 200 ticks,
  including arithmetic, conditional turns, halting, and wall-stop semantics.
- **LLM:** interpret up to three communicating rooms and two pipes, including
  blocking sends/receives, exact FIFO animation, nearest-pipe resolution, and
  whole-program wall-stop semantics.

## Reproduction and validation

```bash
uv run python scripts/sync_problem_specs.py \
  snake pathfinder little-little-little-man little-little-man

python3 -m json.tool data/small/problems/index.json >/dev/null
```

The attachment command fetched all response objects before changing any
file, verified every returned slug, wrote the four compact JSON fixtures, and
regenerated the complete released-problem index. Each attached file and the
index parsed successfully with `python3 -m json.tool`.
