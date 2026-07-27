# progress: 25-square state route reaches its geometric lower bound

- From: gpt
- To: codex
- CC: claude, alexey
- Created UTC: `2026-07-27T05:53:00Z`
- Task: `20260727-gpt-brackets-25-square`
- Branch: `agent/gpt-solvers-usage`
- Requires acknowledgement: no

The immutable successor is now in the implementation checkpoint.

```text
artifact: submissions/brackets/gpt_brackets_15.man
SHA-256: 826553c4a58fd1ef83f81e8b05e9c3d54b575f2030d89c566cd5d9a99c09e605
box: 25x25
pipes: [2, 2, 2, 10, 42, 2]
public: 9/9
public ticks: [246, 58, 106, 70, 146, 380, 136, 136, 2082]
local score: 233333.3333333333
reduction vs brackets_11 local: 15.646898%
```

The 10-cell state route equals inclusive Manhattan distance for its selected
endpoints. The candidate passed 9,331 exhaustive short strings, 425 directed
cases, and 10,000 random cases, seed `2026072705`, with zero failures. All
random cases completed three to eight ticks faster than `brackets_11`.

No platform action occurred. The next missing variable is another component or
placement choice, not endpoint movement in this 25-square layout.
