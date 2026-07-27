#!/usr/bin/env python
"""Build the current Codex LLM artifact without printing its grid."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from littleman.llm_machine import build_llm_machine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("submissions/llm/llm_codex_01.man"),
    )
    args = parser.parse_args()
    text = build_llm_machine()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    rows = text.splitlines()
    print(f"path={args.output.resolve()}")
    print(f"sha256={hashlib.sha256(text.encode()).hexdigest()}")
    print(f"bytes={len(text.encode())} rows={len(rows)} cols={max(map(len, rows))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
