#!/usr/bin/env python3
"""Print the corrected fixed-component Brackets frontier certificate.

The original implementation of this file was retired on 2026-07-27 because it
applied a source-arrow constraint to destination endpoints as well.  A source
endpoint must have a free cell in the direction away from its room; a
destination endpoint points into its wall and may be approached sideways.

The corrected search first enumerated exact nearest-pipe port assignments with
that distinction, then solved all surviving placements with a joint binary
six-commodity grid-flow MILP.  The immutable result and the correction are in
``exact_frontier.json``.  This small entry point deliberately prints the checked
certificate rather than silently rerunning the superseded model.
"""
from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main() -> int:
    payload = json.loads((HERE / "exact_frontier.json").read_text())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
