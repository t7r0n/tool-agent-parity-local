from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .engine import ToolAgentParity


def create_app() -> FastAPI:
    app = FastAPI(title="Tool Agent Parity Local", version="0.1.0")
    parity = ToolAgentParity()

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "bundles": len(parity.bundles()), "scenarios": len(parity.scenarios())}

    @app.post("/tools/{tool_name}")
    def tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return parity.route_tool(tool_name, arguments)

    return app


app = create_app()
