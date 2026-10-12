"""Konfigurasi environment & container: .env.example lengkap dan tanpa secret, dependency image runtime
sama dengan requirements.txt, dan build context Docker tidak pernah membawa .env (docs/security.md § 5)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"

# Tempat variabel CLAU_* dibaca saat runtime/deploy. CLAU_STANDALONE (frontend/next.config.mjs) hanya
# dipakai di dalam frontend/Dockerfile saat build, jadi tidak perlu di .env.
VAR_SOURCES = [*sorted((ROOT / "backend" / "app").glob("*.py")), ROOT / "docker-compose.yml", *sorted((ROOT / "scripts" / "deploy").glob("*.sh"))]
VAR_RE = re.compile(r"\b(CLAU_[A-Z0-9_]+)\b")
ENV_LINE_RE = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=(.*)$")
SECRET_NAME_RE = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|DATABASE_URL|DSN|CREDENTIAL", re.IGNORECASE)


def env_example() -> dict[str, tuple[str, bool]]:
    """name -> (value, commented)."""
    entries = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        m = ENV_LINE_RE.match(line.strip())
        if m:
            entries[m.group(1)] = (m.group(2).strip(), line.lstrip().startswith("#"))
    return entries


def test_every_clau_variable_is_documented():
    used = {name for path in VAR_SOURCES for name in VAR_RE.findall(path.read_text(encoding="utf-8"))}
    missing = sorted(used - env_example().keys())
    assert not missing, f".env.example belum mencantumkan: {missing}"


def test_env_example_has_no_secret_values():
    for name, (value, commented) in env_example().items():
        if SECRET_NAME_RE.search(name):
            assert value == "", f"{name} di .env.example harus kosong (secret hanya di .env server)"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert not re.search(r"(sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN)", text)


def test_env_example_defaults_are_production_safe():
    value, commented = env_example()["CLAU_ENV"]
    assert (value, commented) == ("production", False), "default CLAU_ENV harus production"


def requirement_pins(path: Path) -> dict[str, str]:
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, _, version = line.partition("==")
            assert version, f"{path.name}: {line!r} harus dipin dengan =="
            pins[name.lower()] = version
    return pins


def test_runtime_requirements_match_dev_pins():
    runtime = requirement_pins(ROOT / "backend" / "requirements-runtime.txt")
    full = requirement_pins(ROOT / "backend" / "requirements.txt")
    drift = {name: (version, full.get(name)) for name, version in runtime.items() if full.get(name) != version}
    assert not drift, f"pin requirements-runtime.txt beda dengan requirements.txt: {drift}"
    assert "pytest" not in runtime, "image produksi tidak membawa tool test"


def test_docker_context_is_allowlist_without_env():
    lines = [l.strip() for l in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()]
    rules = [l for l in lines if l and not l.startswith("#")]
    assert rules[0] == "*", ".dockerignore harus allowlist (diawali '*')"
    assert not any(r.startswith("!") and ".env" in r for r in rules), ".env tidak boleh masuk build context"


def test_compose_ports_bound_to_localhost():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    ports = re.findall(r'"([^"]*:\d+)"', compose.split("services:", 1)[1])
    assert ports and all(p.startswith("127.0.0.1:") for p in ports), f"port harus 127.0.0.1 saja: {ports}"
