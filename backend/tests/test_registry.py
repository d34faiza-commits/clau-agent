import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = json.loads((ROOT / "agents" / "registry.json").read_text(encoding="utf-8"))
ROUTER = ROOT / "core" / "orchestrator" / "router.md"


def test_intents_unique():
    intents = [i for a in REGISTRY["agents"] for i in a["intents"]]
    assert len(intents) == len(set(intents))


def test_active_agents_have_artifact():
    for agent in REGISTRY["agents"]:
        if agent["status"] == "active":
            assert agent["skill"] or agent["prompt"] or agent["template"], agent["id"]
            assert agent["skill_repo"], agent["id"]


@pytest.mark.skipif(not ROUTER.is_file(), reason="core/ submodule not initialised")
def test_registry_matches_core_router():
    router_intents = set(re.findall(r"^\| `([a-z-]+)` \|", ROUTER.read_text(encoding="utf-8"), re.MULTILINE))
    registry_intents = {i for a in REGISTRY["agents"] for i in a["intents"]}
    assert registry_intents == router_intents
