from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tool_agent_parity_local.engine import ToolAgentParity, init_store, jsonl_loop
from tool_agent_parity_local.runner import benchmark, export_demo_pack, run_suite_and_write, verify_outputs


def test_lift_metadata(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    metadata = ToolAgentParity(tmp_path).lift("bundle-0001")
    assert metadata.estimated_added_lines <= 30
    assert metadata.tools[0].input_schema["type"] == "object"


def test_eval_bundle(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    summary, results = ToolAgentParity(tmp_path).eval_bundle("bundle-0001")
    assert summary["parity_pass_rate"] == 1
    assert len(results) == 30


def test_suite_outputs(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    summary = run_suite_and_write(tmp_path)
    assert summary.pass_gates
    assert all(verify_outputs(tmp_path).values())
    assert benchmark(tmp_path, iterations=3)["pass_gates"] is True
    assert export_demo_pack(tmp_path).exists()


def test_jsonl_loop(tmp_path: Path) -> None:
    init_store(tmp_path, force=True)
    request = {"tool": "lift", "arguments": {"bundle_id": "bundle-0001"}}
    [line] = jsonl_loop([json.dumps(request)], tmp_path)
    assert json.loads(line)["bundle_id"] == "bundle-0001"


def test_cli_smoke() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "tool_agent_parity_local.cli", "lift", "bundle-0001"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "bundle-0001" in result.stdout
