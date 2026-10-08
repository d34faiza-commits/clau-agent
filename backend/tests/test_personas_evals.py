"""Every agent has a persona card and eval cases whose checks are meaningful."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("run_evals", ROOT / "agents" / "evals" / "run_evals.py")
run_evals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_evals)


def test_personas_and_evals_are_valid():
    assert run_evals.check_all() == []


def test_shared_principles_present():
    text = (ROOT / "agents" / "personas" / "README.md").read_text(encoding="utf-8")
    assert "bukan mengaku manusia" in text.lower()


def test_ai_self_reference_is_always_caught():
    registry = json.loads((ROOT / "agents" / "registry.json").read_text(encoding="utf-8"))
    for agent in registry["agents"]:
        cases = json.loads((ROOT / agent["evals"]).read_text(encoding="utf-8"))["cases"]
        for case in cases:
            assert run_evals.run_checks("Sebagai AI, saya sarankan ini.", case["checks"]), (agent["id"], case["id"])


def test_escalation_marker_detected():
    assert run_evals.run_checks("ESKALASI L3 ke owner.", {"escalate": True}) == []
    assert run_evals.run_checks("Tentu, saya bantu.", {"escalate": True})


def test_escalation_marker_must_lead_the_output():
    # Kartu persona: tulis ESKALASI di AWAL output. Menyebut kata itu di tengah kalimat tidak dihitung.
    assert run_evals.run_checks("Terima kasih atas reviewnya. Kasus ini tidak perlu eskalasi.", {"escalate": True})
    assert run_evals.run_checks("  eskalasi: hubungi owner.", {"escalate": True}) == []
