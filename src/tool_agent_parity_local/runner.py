from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import duckdb

from .dashboard import render_dashboard
from .engine import ToolAgentParity, data_path
from .models import SuiteSummary, project_root


def output_dir(root: Path | None = None) -> Path:
    path = (root or project_root()) / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_suite_and_write(root: Path | None = None) -> SuiteSummary:
    summary, details = ToolAgentParity(root).run_suite()
    out = output_dir(root)
    (out / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    (out / "parity_details.json").write_text(json.dumps(details, indent=2), encoding="utf-8")
    (out / "dashboard.html").write_text(render_dashboard(summary, details), encoding="utf-8")
    (out / "report.md").write_text(_report(summary), encoding="utf-8")
    _write_run_store(root, summary)
    return summary


def _write_run_store(root: Path | None, summary: SuiteSummary) -> None:
    runs = (root or project_root()) / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(runs / "tool_agent_parity_runs.duckdb"))
    con.execute("create table if not exists runs (created_at double, bundle_count integer, parity double, pass_gates boolean)")
    con.execute("insert into runs values (?, ?, ?, ?)", [time.time(), summary.bundle_count, summary.parity_pass_rate, summary.pass_gates])
    con.close()


def _report(summary: SuiteSummary) -> str:
    return f"""# Tool Agent Parity Local Report

- Bundles: {summary.bundle_count}
- Scenarios: {summary.scenario_count}
- Median added lines: {summary.median_added_lines}
- Parity pass rate: {summary.parity_pass_rate:.3f}
- Tool-selection accuracy: {summary.tool_selection_accuracy:.3f}
- Build-to-demo minutes: {summary.build_to_demo_minutes:.2f}
- P95 eval latency: {summary.p95_eval_latency_ms} ms
- Status: {"PASS" if summary.pass_gates else "FAIL"}
"""


def verify_outputs(root: Path | None = None) -> dict[str, bool]:
    root = root or project_root()
    out = output_dir(root)
    checks = {
        "store_exists": data_path(root).exists(),
        "summary_exists": (out / "summary.json").exists(),
        "details_exists": (out / "parity_details.json").exists(),
        "dashboard_exists": (out / "dashboard.html").exists(),
        "report_exists": (out / "report.md").exists(),
    }
    if checks["summary_exists"]:
        summary = SuiteSummary.model_validate_json((out / "summary.json").read_text(encoding="utf-8"))
        checks.update(
            {
                "bundle_count_gate": summary.bundle_count == 24,
                "scenario_count_gate": summary.scenario_count == 720,
                "line_gate": summary.median_added_lines <= 30,
                "parity_gate": summary.parity_pass_rate >= 0.95,
                "selection_gate": summary.tool_selection_accuracy >= 0.85,
                "time_gate": summary.build_to_demo_minutes <= 10,
                "pass_gates": summary.pass_gates,
            }
        )
    return checks


def benchmark(root: Path | None = None, *, iterations: int = 100) -> dict[str, float | int | bool]:
    min_parity = 1.0
    max_latency = 0
    all_pass = True
    for _ in range(iterations):
        summary, _details = ToolAgentParity(root).run_suite()
        min_parity = min(min_parity, summary.parity_pass_rate)
        max_latency = max(max_latency, summary.p95_eval_latency_ms)
        all_pass = all_pass and summary.pass_gates
    result = {"iterations": iterations, "min_parity_pass_rate": min_parity, "max_p95_eval_latency_ms": max_latency, "pass_gates": all_pass}
    (output_dir(root) / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def export_demo_pack(root: Path | None = None) -> Path:
    root = root or project_root()
    out = output_dir(root)
    if not (out / "summary.json").exists():
        run_suite_and_write(root)
    archive = out / "demo-pack.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in ("summary.json", "parity_details.json", "dashboard.html", "report.md", "benchmark.json"):
            path = out / name
            if path.exists():
                zf.write(path, arcname=name)
    return archive
