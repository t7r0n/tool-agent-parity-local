from __future__ import annotations

from .models import EvalScenario, Parameter, ToolBundle, ToolDef

CATEGORIES = ("content", "calendar", "crm", "finance", "ops")
TYPE_MAP = ("string", "number", "boolean", "date")


def bundles() -> list[ToolBundle]:
    rows: list[ToolBundle] = []
    for idx in range(1, 25):
        category = CATEGORIES[(idx - 1) % len(CATEGORIES)]
        tools: list[ToolDef] = []
        for t_idx in range(1, 4):
            tool_name = f"{category}_tool_{t_idx}"
            params = (
                Parameter(name="record_id", type="string", comment="Stable source record identifier."),
                Parameter(name="limit", type="number", required=False, comment="Maximum number of rows to return."),
                Parameter(name="include_history", type="boolean", required=False, comment="Whether historical context is needed."),
                Parameter(name="effective_date", type="date", required=False, comment="Date used for time-aware lookups."),
            )
            tools.append(
                ToolDef(
                    name=tool_name,
                    comment=f"Use {tool_name} for {category} workflows when the user asks for deterministic source data.",
                    parameters=params,
                    output_template=f"{category}:{tool_name}:{{record_id}}",
                )
            )
        rows.append(
            ToolBundle(
                bundle_id=f"bundle-{idx:04d}",
                category=category,
                name=f"{category.title()} Bundle {idx}",
                tools=tuple(tools),
            )
        )
    return rows


def eval_scenarios() -> list[EvalScenario]:
    scenarios: list[EvalScenario] = []
    for bundle in bundles():
        for idx in range(30):
            tool = bundle.tools[idx % len(bundle.tools)]
            scenarios.append(
                EvalScenario(
                    scenario_id=f"{bundle.bundle_id}-scenario-{idx + 1:02d}",
                    bundle_id=bundle.bundle_id,
                    utterance=f"Use {bundle.category} source data for record rec-{idx:03d} with {tool.name}.",
                    expected_tool=tool.name,
                    args={
                        "record_id": f"rec-{idx:03d}",
                        "limit": 10,
                        "include_history": idx % 2 == 0,
                        "effective_date": "2026-05-18",
                    },
                )
            )
    return scenarios
