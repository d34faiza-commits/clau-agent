"""CLAU AI agents backend (scaffold).

Read-only API over the agent registry and the static router from clau-ai-core.
There are intentionally no endpoints that publish content, message guests, or
change client systems (core/AI-CONSTITUTION.md §4).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

__version__ = "0.1.0"

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "agents" / "registry.json"

app = FastAPI(title="CLAU AI Agents", version=__version__)


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
            }
    raise HTTPException(
        status_code=404,
        detail={"error": {"code": "unknown_intent", "message": f"Intent '{request.intent}' tidak dikenal; tanya requester."}},
    )
