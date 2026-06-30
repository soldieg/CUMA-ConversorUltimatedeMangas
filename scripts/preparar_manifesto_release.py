#!/usr/bin/env python3
r"""
Prepara o manifesto de atualização do CUMA para GitHub Releases.

Uso Windows:
  python scripts/preparar_manifesto_release.py soldieg CUMA 1.100.30 C:\caminho\CUMA_windows.zip Stable NOTAS.txt windows

Uso Linux:
  python scripts/preparar_manifesto_release.py soldieg CUMA 1.100.30 /tmp/CUMA_linux.tar.gz Stable NOTAS.txt linux

Uso macOS:
  python scripts/preparar_manifesto_release.py soldieg CUMA 1.100.30 /tmp/CUMA_macos.zip Stable NOTAS.txt macos

O script mantém compatibilidade com o formato antigo, mas agora também escreve:
  stable.json -> platforms.windows / platforms.linux / platforms.macos
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def release_notes_from_file(path: Path | None) -> list[str]:
    if not path or not path.exists():
        return ["Atualização do CUMA publicada via GitHub Releases."]
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    notes: list[str] = []
    for line in raw.splitlines():
        item = line.strip()
        if not item:
            continue
        item = re.sub(r"^#{1,6}\s*", "", item).strip()
        item = re.sub(r"^[-*•]\s*", "", item).strip()
        if item:
            notes.append(item)
        if len(notes) >= 12:
            break
    return notes or ["Atualização do CUMA publicada via GitHub Releases."]


def infer_platform(path: Path | None, explicit: str | None = None) -> str:
    value = (explicit or "").strip().lower()
    aliases = {"win": "windows", "windows": "windows", "linux": "linux", "mac": "macos", "macos": "macos", "darwin": "macos"}
    if value in aliases:
        return aliases[value]
    name = (path.name if path else "").lower()
    if "linux" in name or name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "linux"
    if "macos" in name or "mac_" in name or "darwin" in name:
        return "macos"
    return "windows"


def asset_defaults(platform: str) -> tuple[str, str, str]:
    if platform == "linux":
        return "CUMA_linux.tar.gz", "tar.gz", "cuma"
    if platform == "macos":
        return "CUMA_macos.zip", "zip", "cuma"
    return "CUMA_windows.zip", "zip", "cuma.exe"


def main() -> int:
    if len(sys.argv) < 4:
        print("Uso: python scripts/preparar_manifesto_release.py soldieg CUMA 1.100.30 [pacote] [Stable] [NOTAS.md] [windows|linux|macos]")
        return 2

    owner = sys.argv[1].strip()
    repo = sys.argv[2].strip()
    version = sys.argv[3].strip().lstrip("v")

    package_path: Path | None = None
    release_tag = "Stable"
    notes_path: Path | None = None
    platform_arg = ""

    if len(sys.argv) >= 5 and sys.argv[4].strip():
        candidate = Path(sys.argv[4]).expanduser()
        if candidate.exists() or str(candidate).lower().endswith((".zip", ".tar.gz", ".tgz")):
            package_path = candidate.resolve()
        else:
            release_tag = sys.argv[4].strip()

    if len(sys.argv) >= 6 and sys.argv[5].strip():
        if package_path is not None:
            release_tag = sys.argv[5].strip()
        else:
            notes_path = Path(sys.argv[5]).resolve()

    if len(sys.argv) >= 7 and sys.argv[6].strip():
        notes_path = Path(sys.argv[6]).resolve()

    if len(sys.argv) >= 8 and sys.argv[7].strip():
        platform_arg = sys.argv[7].strip()

    platform = infer_platform(package_path, platform_arg)
    asset_name, archive_type, main_exe_name = asset_defaults(platform)
    if package_path:
        asset_name = package_path.name
        if asset_name.lower().endswith((".tar.gz", ".tgz")):
            archive_type = "tar.gz"

    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/updates/stable.json"
    download_url = f"https://github.com/{owner}/{repo}/releases/download/{release_tag}/{asset_name}"

    readme_path = ROOT / "README.md"
    if readme_path.exists():
        txt = readme_path.read_text(encoding="utf-8", errors="replace")
        txt = txt.replace("https://github.com/soldiego/CUMA", f"https://github.com/{owner}/{repo}")
        txt = txt.replace("https://raw.githubusercontent.com/soldiego/CUMA/main/updates/stable.json", raw_url)
        txt = txt.replace("https://github.com/soldieg/CUMA", f"https://github.com/{owner}/{repo}")
        txt = txt.replace("https://raw.githubusercontent.com/soldieg/CUMA/main/updates/stable.json", raw_url)
        txt = txt.replace("SEU_USUARIO/CUMA", f"{owner}/{repo}")
        readme_path.write_text(txt, encoding="utf-8")

    notes = release_notes_from_file(notes_path)

    template_path = ROOT / "cuma_settings_template.json"
    if template_path.exists():
        data = json.loads(template_path.read_text(encoding="utf-8"))
        cfg = data.setdefault("config", {})
        cfg["update_manifest_url"] = raw_url
        cfg["update_channel"] = "stable"
        updates = data.setdefault("updates", {})
        updates["manifest_url"] = raw_url
        updates["channel"] = "stable"
        updates["release_tag"] = release_tag
        updates.setdefault("platforms", {})
        updates["platforms"][platform] = {
            "asset_name": asset_name,
            "download_url": download_url,
            "archive_type": archive_type,
            "main_exe_name": main_exe_name,
        }
        if platform == "windows":
            updates["download_url"] = download_url
        data.setdefault("versioning", {})["current_version"] = version
        template_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stable_path = ROOT / "updates" / "stable.json"
    stable_path.parent.mkdir(parents=True, exist_ok=True)
    stable = json.loads(stable_path.read_text(encoding="utf-8")) if stable_path.exists() else {}

    sha = "COLOQUE_O_SHA256_DO_PACOTE_AQUI"
    size = 0
    if package_path and package_path.exists():
        sha = sha256_file(package_path)
        size = package_path.stat().st_size

    stable.update({
        "app_id": "cuma",
        "channel": "stable",
        "version": version,
        "minimum_supported_version": stable.get("minimum_supported_version", "1.080.0"),
        "mandatory": bool(stable.get("mandatory", False)),
        "published_at": date.today().isoformat(),
        "release_notes": notes,
    })
    platforms = stable.setdefault("platforms", {})
    platforms[platform] = {
        "asset_name": asset_name,
        "download_url": download_url,
        "sha256": sha,
        "size_bytes": size,
        "archive_type": archive_type,
        "main_exe_name": main_exe_name,
    }

    # Compatibilidade com versões antigas do updater: campos globais apontam para Windows.
    win_asset, win_archive, win_main = asset_defaults("windows")
    win = platforms.get("windows", {})
    stable["download_url"] = win.get("download_url") or f"https://github.com/{owner}/{repo}/releases/download/{release_tag}/{win_asset}"
    stable["sha256"] = win.get("sha256", "COLOQUE_O_SHA256_DO_ZIP_AQUI")
    stable["size_bytes"] = win.get("size_bytes", 0)
    stable["archive_type"] = win.get("archive_type", win_archive)
    stable["main_exe_name"] = win.get("main_exe_name", win_main)
    stable["build_manifest_note"] = (
        "Manifesto multiplataforma. Publique CUMA_windows.zip, CUMA_linux.tar.gz e CUMA_macos.zip na Release Stable. "
        "Cada pacote deve ser gerado na própria plataforma ou pelo GitHub Actions."
    )

    stable_path.write_text(json.dumps(stable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("Manifesto atualizado:")
    print(f"- {stable_path}")
    print(f"Plataforma: {platform}")
    print(f"Asset: {asset_name}")
    print(f"URL: {download_url}")
    print(f"SHA256: {sha}")
    print(f"Tamanho: {size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
