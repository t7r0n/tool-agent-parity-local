from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Parameter(BaseModel):
    name: str
    type: str
    required: bool = True
    comment: str


class ToolDef(BaseModel):
    name: str
    comment: str
    parameters: tuple[Parameter, ...]
    output_template: str


class ToolBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    bundle_id: str
    category: str
    name: str
    tools: tuple[ToolDef, ...]


class AgentTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, object]


class AgentMetadata(BaseModel):
    bundle_id: str
    agent_name: str
    category: str
    tools: list[AgentTool]
    estimated_added_lines: int


class EvalScenario(BaseModel):
    scenario_id: str
    bundle_id: str
    utterance: str
    expected_tool: str
    args: dict[str, object]


class EvalResult(BaseModel):
    scenario_id: str
    expected_tool: str
    observed_tool: str
    args_match: bool
    output_match: bool
    passed: bool


class SuiteSummary(BaseModel):
    bundle_count: int
    scenario_count: int
    median_added_lines: int
    parity_pass_rate: float
    tool_selection_accuracy: float
    build_to_demo_minutes: float
    p95_eval_latency_ms: int
    pass_gates: bool
