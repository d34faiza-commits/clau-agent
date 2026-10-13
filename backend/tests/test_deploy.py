"""Paket deploy VPS 1 (scripts/deploy/, docs/deploy/vps-1-setup.md § 8).

Script ini dijalankan root di server, jadi kesalahan kecil (sintaks, opsi systemd yang mematikan sudo,
file yang dipasang tapi tidak dicek) baru ketahuan saat owner menjalankannya. Test ini menjaganya di CI.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "scripts" / "deploy"
UNITS = DEPLOY / "systemd"


def unit(name: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in (UNITS / name).read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values.setdefault(key.strip(), []).append(value.strip())
    return values


@pytest.mark.parametrize("script", sorted((ROOT / "scripts").rglob("*.sh")), ids=lambda p: str(p.relative_to(ROOT)))
def test_shell_scripts_parse(script):
    subprocess.run(["bash", "-n", str(script)], check=True)


def test_frontend_runs_as_read_only_user_without_internet():
    u = unit("clau-frontend.service")
    assert u["User"] == ["clau-web"] and u["Group"] == ["clau-web"]
    assert u["ProtectSystem"] == ["strict"]
    assert "ReadWritePaths" not in u, "frontend tidak menulis apa pun (tanpa ISR/next/image)"
    assert u["IPAddressDeny"] == ["any"]
    assert u["NoNewPrivileges"] == ["true"]


def test_deploy_service_keeps_sudo_working():
    # sudo gagal di bawah NoNewPrivileges; opsi ini memasang seccomp/NNP secara tidak langsung.
    u = unit("clau-deploy.service")
    assert u["User"] == ["clau-deploy"]
    for option in ("NoNewPrivileges", "PrivateDevices", "ProtectKernelModules", "SystemCallFilter", "RestrictSUIDSGID"):
        assert option not in u, f"{option} membuat sudo restart frontend gagal"
    assert u["ExecStart"] == ["/srv/clau/clau-ai-agents/scripts/deploy/vps1-deploy.sh"]


def test_sudo_rule_matches_deploy_restart_and_check():
    harden = (DEPLOY / "vps1-harden.sh").read_text()
    check = (DEPLOY / "vps1-check.sh").read_text()
    deploy = (DEPLOY / "vps1-deploy.sh").read_text()
    rule = re.search(r"echo '(clau-deploy ALL=\(root\) NOPASSWD: (\S+ \S+ \S+))'", harden)
    assert rule, "aturan sudoers tidak ditemukan di vps1-harden.sh"
    assert f"'^{rule.group(1)}$'" in check, "clau-vps1-check harus mengecek aturan sudoers yang sama persis"
    assert f"sudo -n {rule.group(2)}" in deploy


def test_check_covers_every_installed_file():
    harden = (DEPLOY / "vps1-harden.sh").read_text()
    check = (DEPLOY / "vps1-check.sh").read_text()
    units = re.search(r"for u in ([^;]+); do\n  install -m 644", harden).group(1).split()
    for name in units:
        assert (UNITS / name).is_file()
        assert f"systemd/{name}:/etc/systemd/system/{name}" in check, f"{name} dipasang tapi tidak dicek"
    for src, dst in re.findall(r'install -m 755 -o root -g root "\$SRC/(\S+)" (\S+)', harden):
        assert f"{src}:{dst}" in check, f"{dst} dipasang tapi tidak dicek"
    assert "nginx/clau.conf:/etc/nginx/sites-available/clau" in check


def test_backup_never_includes_secrets():
    backup = (DEPLOY / "vps1-backup-config.sh").read_text()
    paths = re.search(r"paths=\(\n(.*?)\n\)", backup, re.S).group(1).split()
    for p in paths:
        assert not re.search(r"\.env|_deploy$|id_|\.key$|ssh_host", p), p


def test_vps1_only_deploys_ci_green_release_branch():
    # AI-BOUNDARY 1.3.0: VPS 1 menayangkan release/vps1, yang hanya dimajukan job CI setelah semua job hijau.
    assert "CLAU_BRANCH=release/vps1" in unit("clau-deploy.service")["Environment"]
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    job = ci.split("\n  release-vps1:\n", 1)[1]
    needs = set(re.search(r"needs: \[([^\]]+)\]", job).group(1).replace(" ", "").split(","))
    jobs = set(re.findall(r"^  ([a-z0-9-]+):\n", ci.split("\njobs:\n", 1)[1], re.M)) - {"release-vps1"}
    assert needs == jobs, "release-vps1 harus menunggu semua job CI"
    assert "github.ref == 'refs/heads/main'" in job
    deploy = (DEPLOY / "vps1-deploy.sh").read_text()
    assert 'fetch --quiet origin "$BRANCH"' in deploy and "FETCH_HEAD" in deploy and not re.search(r"git .*\bpull\b", deploy)
