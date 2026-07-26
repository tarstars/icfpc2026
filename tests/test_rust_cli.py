"""Standalone pure-Rust batch CLI parity and determinism."""

from __future__ import annotations

import json
import pathlib
import subprocess

from littleman import judge, rustexec

REPO = pathlib.Path(__file__).resolve().parent.parent


def cli_command(ir_path=None):
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
    return command


def run_cli(request, ir_path=None):
    process = subprocess.run(
        cli_command(ir_path),
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


def test_cli_llm_frame_case_matches_python_binding(tmp_path):
    text = (REPO / "submissions/llm/llm_codex_01.man").read_text()
    problem = json.loads(
        (REPO / "data/small/problems/little-little-man.json").read_text()
    )
    cases = [judge.normalize_case(problem["publicTestData"][0])]
    compiled = rustexec.CompiledMachine(text)
    expected = compiled.run_rounds(0, cases[0], problem["tickCap"])
    ir_path = tmp_path / "llm.lmir.zst"
    ir_path.write_bytes(compiled.encoded_ir())
    request = compiled.cli_request(
        cases,
        max_ticks=problem["tickCap"],
        workers=1,
        include_spec=False,
    )
    actual = run_cli(request, ir_path)[0]
    assert actual["status"] == expected.status == "passed"
    assert actual["judged_ticks"] == expected.judged_ticks
    assert actual["output"] == list(expected.output)
    assert actual["output_ticks"] == list(expected.output_ticks)
    assert actual["frame_ticks"] == list(expected.frame_ticks)


def test_cli_round_controller_edge_shapes_match_python_binding(tmp_path):
    text = (REPO / "submissions/max-element/max_00.man").read_text()
    problem = json.loads((REPO / "data/small/problems/max-element.json").read_text())
    first = judge.normalize_case(problem["publicTestData"][0])
    second = judge.normalize_case(problem["publicTestData"][1])
    wrong = [{**first[0], "out": [int(first[0]["out"][0]) + 1]}]
    edge_cases = [
        [],
        wrong,
        [{"in": [], "out": [0]}],
        [{"in": first[0]["in"], "frames": [["0" * 16] * 16]}],
        first + second,
    ]
    compiled = rustexec.CompiledMachine(text)
    expected = [
        compiled.run_rounds(index, rounds, 100_000)
        for index, rounds in enumerate(edge_cases)
    ]
    ir_path = tmp_path / "max-element.lmir.zst"
    ir_path.write_bytes(compiled.encoded_ir())
    request = compiled.cli_request(
        edge_cases,
        max_ticks=100_000,
        workers=4,
        include_spec=False,
    )
    actual = run_cli(request, ir_path)
    assert [result["status"] for result in actual] == [
        result.status for result in expected
    ]
    assert [result["ticks"] for result in actual] == [
        result.ticks for result in expected
    ]
    assert [result["judged_ticks"] for result in actual] == [
        result.judged_ticks for result in expected
    ]
    assert [result["output"] for result in actual] == [
        list(result.output) for result in expected
    ]
    assert [result["status"] for result in actual] == [
        "passed",
        "failed",
        "tick-cap",
        "failed",
        "halted",
    ]


def test_cli_rejects_corrupt_compressed_ir(tmp_path):
    text = (REPO / "submissions/max-element/max_00.man").read_text()
    compiled = rustexec.CompiledMachine(text)
    ir_path = tmp_path / "corrupt.lmir.zst"
    ir_path.write_bytes(b"LMIR\x01Znot-zstd")
    request = compiled.cli_request([], include_spec=False)
    process = subprocess.run(
        cli_command(ir_path),
        cwd=REPO,
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 2
    assert "invalid cached IR" in process.stderr
