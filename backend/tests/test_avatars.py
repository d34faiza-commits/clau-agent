"""Every agent (and every concept role with an image) ships a valid 3D avatar."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CROPS = ROOT / "frontend" / "public" / "agents"
MASTERS = ROOT / "agents" / "avatars"
MAX_BYTES = 150_000  # keep the repo and page weight lean


def _is_webp(path: Path) -> bool:
    head = path.read_bytes()[:12]
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def _check(name: str) -> None:
    for folder in (CROPS, MASTERS):
        path = folder / f"{name}.webp"
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"
        assert _is_webp(path), f"not a WebP: {path.relative_to(ROOT)}"
        assert path.stat().st_size <= MAX_BYTES, f"too large: {path.relative_to(ROOT)}"


def test_every_registry_agent_has_avatar():
    registry = json.loads((ROOT / "agents" / "registry.json").read_text(encoding="utf-8"))
    for agent in registry["agents"]:
        _check(agent["id"])


def test_concept_images_exist():
    team = (ROOT / "frontend" / "lib" / "team.ts").read_text(encoding="utf-8")
    names = re.findall(r'image: "/agents/(concept-[a-z]+)\.webp"', team)
    assert names, "no concept images referenced in frontend/lib/team.ts"
    for name in names:
        _check(name)


def test_no_orphan_avatar_files():
    registry = json.loads((ROOT / "agents" / "registry.json").read_text(encoding="utf-8"))
    team = (ROOT / "frontend" / "lib" / "team.ts").read_text(encoding="utf-8")
    expected = {a["id"] for a in registry["agents"]} | set(re.findall(r'/agents/(concept-[a-z]+)\.webp', team))
    for folder in (CROPS, MASTERS):
        found = {p.stem for p in folder.glob("*.webp")}
        assert found == expected, (folder.relative_to(ROOT), sorted(found ^ expected))
