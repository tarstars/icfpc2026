# Result: tarstars TCP 10 repack is release-ready

- From: codex TCP fusion lane
- To: integrator
- Created UTC: 2026-07-27T00:46:54Z
- Requires acknowledgement: no
- Branch: `agent/codex-tcp-fusion`
- Artifact: `submissions/tcp/tarstars_tcp_10.man`
- Submission authority: integrator only

The original P+C fusion was correct but noncompetitive: unchanged room
dimensions force a maximum dimension of at least 31 and its core did not
improve simple-case ticks. I stopped that lane and found a monotonic successor
by repacking the unchanged `tcp_09` rooms.

`tarstars_tcp_10.man` is 30x30, passes all six public cases, and has local
score 874,950 versus 928,646.333 for `tcp_09`, a 5.782216% improvement.
Public ticks are `[432, 1326, 1212, 391, 32, 2440]`.

Release evidence:

- SHA-256
  `6cf6a21d6b38d12214c628aa614570a2dc4ec136b27e12ecff359b9bdb244765`;
- six byte-identical rooms, seven pipes, four men;
- all 35 normalized send/receive bindings match `tcp_09`;
- server-compatible validation and pipe check pass;
- six boundary streams and 768 deterministic differential streams pass;
- 44 focused TCP tests pass;
- strict preflight reports `READY TO SUBMIT`;
- fresh `tcp_09` API state remains 20/20 at score 1,575,127.05.

The measured local ratio projects a live score near 1,484,049.81, improving
the incumbent by about 91,077. It is not projected to cross rank 28. No
submission or merge was performed in this lane.
