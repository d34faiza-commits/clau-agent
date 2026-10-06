"""CLAU AI agents backend (scaffold).

Read-only API over the agent registry and the static router from clau-ai-core.
There are intentionally no endpoints that publish content, message guests, or
change client systems (core/AI-CONSTITUTION.md §4).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

__version__ = "0.2.0"

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "agents" / "registry.json"

app = FastAPI(title="CLAU AI Agents", version=__version__)


class ApiError(Exception):
    """Error with the contract shape {"error": {"code", "message"}} (core/shared/api-contracts.md)."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = ", ".join(".".join(str(p) for p in err["loc"][1:]) or "body" for err in exc.errors())
    return JSONResponse(status_code=422, content=error_body("validation_error", f"Request tidak valid: {fields}"))


@lru_cache(maxsize=1)
def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


class RouteRequest(BaseModel):
    intent: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "clau-ai-agents-backend", "version": __version__}


@app.get("/agents")
def list_agents() -> dict:
    registry = load_registry()
    forbidden = registry["default_forbidden_actions"]
    return {"agents": [{**agent, "forbidden_actions": forbidden} for agent in registry["agents"]]}


@app.post("/route")
def route(request: RouteRequest) -> dict:
    for agent in load_registry()["agents"]:
        if request.intent in agent["intents"]:
            return {
                "intent": request.intent,
                "agent": agent["id"],
                "pillar": agent["pillar"],
                "skill": agent["skill"] or agent["prompt"] or agent["template"],
                "repo": agent["skill_repo"],
                "approval_min": agent["approval_min"],
                "status": agent["status"],
                # Planned pillars are not worked on: create a board task and escalate (core/orchestrator/router.md).
                "next_step": "produce_draft" if agent["status"] == "active" else "escalate_to_owner",
            }
    raise ApiError(404, "unknown_intent", f"Intent '{request.intent}' tidak dikenal; tanya requester.")
