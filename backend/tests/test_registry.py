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


CORE_README = ROOT / "core" / "README.md"
CORE_STATUS = {"Aktif": "active", "Planned": "planned"}


def test_pillars_cover_every_agent():
    pillar_ids = [p["id"] for p in REGISTRY["pillars"]]
    assert pillar_ids == [1, 2, 3, 4, 5]
    for agent in REGISTRY["agents"]:
        assert agent["pillar"] in pillar_ids, agent["id"]
    for pillar in REGISTRY["pillars"]:
        assert pillar["name"]["en"] and pillar["name"]["id"], pillar["id"]
        assert (pillar["repo"] is not None) == (pillar["status"] == "active"), pillar["id"]


def test_planned_pillar_agents_without_artifact_are_planned():
    # An agent may serve a planned pillar early only with a Pillar 1 artifact (e.g. `report`), never on its own.
    planned = {p["id"] for p in REGISTRY["pillars"] if p["status"] == "planned"}
    for agent in REGISTRY["agents"]:
        if agent["pillar"] in planned and agent["status"] == "active":
            assert agent["skill_repo"] == "clau-ai-marketing", agent["id"]


@pytest.mark.skipif(not CORE_README.is_file(), reason="core/ submodule not initialised")
def test_pillars_match_core_readme():
    section = CORE_README.read_text(encoding="utf-8").split("## 5 Pilar CLAU AI", 1)[1]
    rows = re.findall(r"^\| (\d) \| \**([^|*]+?)\** \| [^|]+ \| ([^|]+) \| \**([^|*]+?)\** \|$", section, re.MULTILINE)
    core = {int(n): (name.strip(), repo.strip(), CORE_STATUS[status.strip()]) for n, name, repo, status in rows}
    registry = {p["id"]: (p["name"]["en"], p["repo"] or "—", p["status"]) for p in REGISTRY["pillars"]}
    assert registry == core


AUTONOMY_LEVELS = {"A", "B", "C"}


def test_autonomy_max_valid_and_default_b():
    # AI-CONSTITUTION §4a: default Level B; Level A needs an explicit owner decision in core/orchestrator/router.md.
    for agent in REGISTRY["agents"]:
        assert agent["autonomy_max"] in AUTONOMY_LEVELS, agent["id"]
        if agent["status"] == "planned":
            assert agent["autonomy_max"] != "A", agent["id"]


@pytest.mark.skipif(not ROUTER.is_file(), reason="core/ submodule not initialised")
def test_autonomy_matches_core_router():
    text = ROUTER.read_text(encoding="utf-8")
    router = dict(re.findall(r"^\| `([a-z-]+)` \|.*\| ([ABC]) \|$", text, re.MULTILINE))
    assert router, "router.md has no Otonomi column"
    for agent in REGISTRY["agents"]:
        for intent in agent["intents"]:
            assert router.get(intent) == agent["autonomy_max"], intent
