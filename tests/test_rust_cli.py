"""Standalone pure-Rust batch CLI parity and determinism."""

from __future__ import annotations

import json
import pathlib
import subprocess

from littleman import judge, rustexec

REPO = pathlib.Path(__file__).resolve().parent.parent


def run_cli(request, ir_path=None):
    command = [
        "cargo",
        "run",
        "--quiet",
        "--release",
        "--no-default-features",
        "--features",
        "cli",
        "--manifest-path",
        str(REPO / "rust/Cargo.toml"),
        "--bin",
        "littleman-rust",
    ]
    if ir_path is not None:
        command.extend(["--", "--ir", str(ir_path)])
    process = subprocess.run(
        command,
        cwd=REPO,
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(process.stdout)


def test_cli_matches_python_binding_and_worker_counts(tmp_path):
    text = (REPO / "submissions/max-element/max_00.man").read_text()
    problem = json.loads((REPO / "data/small/problems/max-element.json").read_text())
    cases = [judge.normalize_case(case) for case in problem["publicTestData"]]
    compiled = rustexec.CompiledMachine(text)
    expected = rustexec.run_rounds_parallel(compiled, cases, workers=1)

    one_request = compiled.cli_request(cases, workers=1)
    two_request = compiled.cli_request(cases, workers=2, include_spec=False)
    encoded = compiled.encoded_ir()
    ir_path = tmp_path / "max-element.lmir.zst"
    ir_path.write_bytes(encoded)
    one = run_cli(one_request)
    two = run_cli(two_request, ir_path)

    assert encoded.startswith(b"LMIR\x01Z")
    assert len(encoded) < len(json.dumps(one_request["spec"]))
    assert one == two
    assert [result["status"] for result in one] == ["passed"] * len(cases)
    assert [result["judged_ticks"] for result in one] == [
        result.judged_ticks for result in expected
    ]
    assert [result["output"] for result in one] == [
        list(result.output) for result in expected
    ]
