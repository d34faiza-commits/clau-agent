"""Registry agent (agents/registry.json): sumber intent → agent → pilar → approval minimum (core router)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "agents" / "registry.json"


@lru_cache(maxsize=1)
def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def agent_for_intent(intent: str) -> dict | None:
    return next((a for a in load_registry()["agents"] if intent in a["intents"]), None)
