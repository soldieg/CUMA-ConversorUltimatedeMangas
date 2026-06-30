#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atualizador externo do CUMA.

Este executável é iniciado por uma cópia temporária para conseguir substituir
cuma.exe, cuma_updater.exe e a pasta _internal enquanto o aplicativo principal
está fechado.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
import tarfile
from datetime import datetime
from pathlib import Path


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
DETACHED_PROCESS = 0x00000008 if os.name == "nt" else 0
CREATE_NEW_PROCESS_GROUP = 0x00000200 if os.name == "nt" else 0
STILL_ACTIVE = 259


def _message_box(title: str, text: str, error: bool = False) -> None:
    """Mostra uma mensagem nativa no Windows sem depender de console."""
    if os.name == "nt":
        try:
            flags = 0x10 if error else 0x40
            ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags)
            return
        except Exception:
            pass
    try:
        print(f"{title}: {text}", file=sys.stderr if error else sys.stdout)
    except Exception:
        pass


def _safe_log(path: Path | list[Path] | tuple[Path, ...] | set[Path] | None, message: str) -> None:
    """Grava log seguro.

    A partir da 1.100.30, o atualizador grava o mesmo evento em mais de um lugar:
    - log temporário do update atual;
    - log persistente ao lado do CUMA instalado.
    """
    try:
        if path is None:
            return
        if isinstance(path, (list, tuple, set)):
            for item in path:
                _safe_log(item, message)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", errors="replace") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def _path_size(path: Path) -> int:
    """Retorna tamanho aproximado de arquivo/pasta para diagnóstico."""
    try:
        if path.is_file() or path.is_symlink():
            return int(path.stat().st_size)
        if path.is_dir():
            total = 0
            for child in path.rglob("*"):
                try:
                    if child.is_file() or child.is_symlink():
                        total += int(child.stat().st_size)
                except Exception:
                    pass
            return total
    except Exception:
        pass
    return 0


def _path_summary(path: Path) -> str:
    try:
        if path.is_dir():
            files = 0
            dirs = 0
            for child in path.rglob("*"):
                try:
                    if child.is_dir():
                        dirs += 1
                    elif child.is_file() or child.is_symlink():
                        files += 1
                except Exception:
                    pass
            return f"pasta, {files} arquivo(s), {dirs} subpasta(s), {_path_size(path)} bytes"
        if path.exists() or path.is_symlink():
            return f"arquivo, {_path_size(path)} bytes"
        return "não existe"
    except Exception as exc:
        return f"erro ao resumir: {exc}"


def _persistent_update_log_path(install_dir: Path) -> Path:
    """Log persistente da atualização, mantido na pasta instalada do CUMA."""
    try:
        return Path(install_dir).resolve() / "CUMA_update.log"
    except Exception:
        return Path(tempfile.gettempdir()) / "CUMA_updates" / "CUMA_update.log"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def _clean_sha(value: str) -> str:
    text = str(value or "").strip().upper()
    if not text or "COLOQUE" in text or "PLACEHOLDER" in text:
        return ""
    text = "".join(ch for ch in text if ch in "0123456789ABCDEF")
    return text if len(text) == 64 else ""


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            access = 0x1000 | 0x00100000  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
            handle = ctypes.windll.kernel32.OpenProcess(access, False, int(pid))
            if not handle:
                return False
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(ok and code.value == STILL_ACTIVE)
        except Exception:
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=CREATE_NO_WINDOW,
                )
                return str(pid) in (result.stdout or "")
            except Exception:
                return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _force_kill_process(pid: int, log_path: Path | None) -> None:
    if pid <= 0:
        return
    try:
        _safe_log(log_path, f"Forçando encerramento do processo PID {pid}.")
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=CREATE_NO_WINDOW,
            )
        else:
            try:
                os.kill(pid, 15)
                time.sleep(1.0)
                if _is_process_running(pid):
                    os.kill(pid, 9)
            except ProcessLookupError:
                pass
    except Exception as exc:
        _safe_log(log_path, f"Falha ao forçar encerramento do PID {pid}: {exc}")


def _wait_for_main_app_to_close(pid: int, log_path: Path | None, timeout_seconds: float = 20.0) -> None:
    if pid <= 0:
        return
    _safe_log(log_path, f"Aguardando fechamento do CUMA. PID={pid}.")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _is_process_running(pid):
            _safe_log(log_path, "Aplicativo principal fechado.")
            return
        time.sleep(0.25)

    _force_kill_process(pid, log_path)
    deadline = time.time() + 8.0
    while time.time() < deadline:
        if not _is_process_running(pid):
            _safe_log(log_path, "Aplicativo principal encerrado à força.")
            return
        time.sleep(0.25)


def _extract_archive(archive_path: Path, extract_dir: Path, log_path: Path | None, archive_type: str = "") -> None:
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    archive_type = str(archive_type or "").lower().strip()
    name = archive_path.name.lower()
    _safe_log(log_path, f"Extraindo pacote: {archive_path}")
    if archive_type in ("tar.gz", "tgz") or name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(extract_dir)
        return
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(extract_dir)


# Compatibilidade com chamadas antigas.
def _extract_zip(archive_path: Path, extract_dir: Path, log_path: Path | None) -> None:
    _extract_archive(archive_path, extract_dir, log_path, "zip")


def _looks_like_cuma_payload(path: Path, main_exe_name: str) -> bool:
    return (path / main_exe_name).is_file() and (path / "_internal").is_dir()


def _find_payload_root(extract_dir: Path, main_exe_name: str) -> Path:
    if _looks_like_cuma_payload(extract_dir, main_exe_name):
        return extract_dir

    children = [p for p in extract_dir.iterdir() if p.is_dir()]
    for child in children:
        if _looks_like_cuma_payload(child, main_exe_name):
            return child

    for exe in extract_dir.rglob(main_exe_name):
        parent = exe.parent
        if _looks_like_cuma_payload(parent, main_exe_name):
            return parent

    raise RuntimeError(f"O pacote não contém uma pasta válida do CUMA com {main_exe_name} e _internal.")


def _copy_payload_item(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, symlinks=False)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _rollback(install_dir: Path, backup_dir: Path, touched_names: list[str], log_path: Path | None) -> None:
    _safe_log(log_path, "Iniciando rollback.")
    # Remove itens novos/parciais.
    for name in reversed(touched_names):
        target = install_dir / name
        try:
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists() or target.is_symlink():
                target.unlink()
        except Exception as exc:
            _safe_log(log_path, f"Falha removendo item parcial {target}: {exc}")

    # Restaura itens antigos.
    if backup_dir.exists():
        _safe_log(log_path, f"Restaurando backup: {backup_dir} ({_path_summary(backup_dir)})")
        for item in backup_dir.iterdir():
            target = install_dir / item.name
            try:
                if target.exists() or target.is_symlink():
                    if target.is_dir() and not target.is_symlink():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink()
                shutil.move(str(item), str(target))
                _safe_log(log_path, f"Restaurado do backup: {item.name}")
            except Exception as exc:
                _safe_log(log_path, f"Falha restaurando {item.name}: {exc}")


def _install_payload(payload_dir: Path, install_dir: Path, backup_dir: Path, log_path: Path | None) -> None:
    if not install_dir.exists() or not install_dir.is_dir():
        raise RuntimeError(f"Pasta de instalação inválida: {install_dir}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    _safe_log(log_path, f"Backup desta atualização: {backup_dir}")
    _safe_log(log_path, f"Instalação antes da cópia: {_path_summary(install_dir)}")
    skip_names = {
        "config_cuma.json",
        "cuma_settings.json",
        "CUMA.log",
        "erro.txt",
        "limpos",
        ".cuma_user_data",
        ".git",
        "__pycache__",
    }

    items = [p for p in payload_dir.iterdir() if p.name not in skip_names]
    if not items:
        raise RuntimeError("O pacote de atualização está vazio.")

    _safe_log(log_path, f"Itens que serão instalados: {', '.join(p.name for p in items)}")
    touched: list[str] = []
    try:
        for src in items:
            target = install_dir / src.name
            backup_target = backup_dir / src.name

            if target.exists() or target.is_symlink():
                _safe_log(log_path, f"Movendo item antigo para backup: {target} ({_path_summary(target)})")
                if backup_target.exists():
                    if backup_target.is_dir() and not backup_target.is_symlink():
                        shutil.rmtree(backup_target, ignore_errors=True)
                    else:
                        backup_target.unlink()
                shutil.move(str(target), str(backup_target))
                _safe_log(log_path, f"Backup criado para {src.name}: {_path_summary(backup_target)}")
            else:
                _safe_log(log_path, f"Item novo sem versão anterior: {target}")

            _safe_log(log_path, f"Instalando item novo: {src.name} ({_path_summary(src)})")
            _copy_payload_item(src, target)
            _safe_log(log_path, f"Item instalado: {target} ({_path_summary(target)})")
            touched.append(src.name)
    except Exception:
        _safe_log(log_path, "ERRO durante cópia dos arquivos. Iniciando rollback.")
        _rollback(install_dir, backup_dir, touched, log_path)
        raise
    _safe_log(log_path, f"Instalação depois da cópia: {_path_summary(install_dir)}")


def _reopen_app(main_exe: Path, install_dir: Path, log_path: Path | None) -> None:
    if not main_exe.exists():
        _safe_log(log_path, f"Executável principal não encontrado para reabrir: {main_exe}")
        return
    try:
        kwargs = {"cwd": str(install_dir), "close_fds": True}
        if os.name == "nt":
            kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen([str(main_exe)], **kwargs)
        _safe_log(log_path, f"CUMA reaberto: {main_exe}")
    except Exception as exc:
        _safe_log(log_path, f"Falha ao reabrir CUMA: {exc}")
        _message_box("CUMA atualizado", f"A atualização foi instalada, mas não consegui reabrir o CUMA.\n\nAbra manualmente:\n{main_exe}", error=False)


def run_update(request_path: Path) -> int:
    request_path = request_path.resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))

    install_dir = Path(request["install_dir"]).resolve()
    archive_path = Path(request["archive_path"]).resolve()
    main_exe_name = str(request.get("main_exe_name") or _default_main_exe_name_for_platform())
    main_pid = int(request.get("main_pid") or 0)
    expected_sha = _clean_sha(request.get("expected_sha256", ""))
    expected_size = int(request.get("expected_size_bytes") or 0)
    latest_version = str(request.get("latest_version") or "").strip() or "nova"
    archive_type = str(request.get("archive_type") or "").strip()
    backup_keep = bool(request.get("keep_backup", True))

    work_dir = request_path.parent
    extract_dir = work_dir / "extraido"
    # 1.100.30: backup único substituído a cada atualização.
    backup_dir = install_dir.parent / "CUMA_backup_anterior"
    persistent_log = Path(request.get("persistent_log_path") or _persistent_update_log_path(install_dir)).resolve()
    log_path = [work_dir / "CUMA_update.log", persistent_log]

    try:
        _safe_log(log_path, "=" * 88)
        _safe_log(log_path, "INSTALLER iniciado.")
        _safe_log(log_path, f"Atualizador: {Path(sys.argv[0]).resolve() if sys.argv else 'desconhecido'}")
        _safe_log(log_path, f"Instalação: {install_dir}")
        _safe_log(log_path, f"Pacote: {archive_path}")
        _safe_log(log_path, f"Versão atual: {request.get('current_version', '')}")
        _safe_log(log_path, f"Versão nova: {latest_version}")
        _safe_log(log_path, f"Política de backup: backup único substituído ({backup_dir})")

        if not archive_path.exists():
            raise RuntimeError(f"Pacote de atualização não encontrado: {archive_path}")
        if expected_size > 0 and archive_path.stat().st_size != expected_size:
            raise RuntimeError(
                f"Tamanho do pacote diferente do manifesto. "
                f"Esperado: {expected_size}; recebido: {archive_path.stat().st_size}."
            )
        if expected_sha:
            got_sha = _sha256_file(archive_path)
            _safe_log(log_path, f"SHA256 calculado pelo instalador: {got_sha}")
            _safe_log(log_path, f"SHA256 esperado pelo manifesto: {expected_sha}")
            if got_sha != expected_sha:
                _safe_log(log_path, "ERRO: SHA256 inválido no instalador. Instalação bloqueada.")
                raise RuntimeError(f"SHA256 inválido. Esperado {expected_sha}, recebido {got_sha}.")
            _safe_log(log_path, "SHA256 confirmado pelo instalador.")
        else:
            _safe_log(log_path, "AVISO: instalação sem SHA256 esperado.")

        _wait_for_main_app_to_close(main_pid, log_path)
        _extract_archive(archive_path, extract_dir, log_path, archive_type)
        payload_dir = _find_payload_root(extract_dir, main_exe_name)
        _safe_log(log_path, f"Raiz do pacote: {payload_dir}")
        _safe_log(log_path, f"Resumo do pacote: {_path_summary(payload_dir)}")

        if backup_dir.exists():
            _safe_log(log_path, f"Backup anterior encontrado e será substituído: {backup_dir}")
            try:
                if backup_dir.is_dir() and not backup_dir.is_symlink():
                    shutil.rmtree(backup_dir, ignore_errors=True)
                else:
                    backup_dir.unlink()
                _safe_log(log_path, "Backup anterior removido com sucesso.")
            except Exception as exc:
                _safe_log(log_path, f"Falha ao remover backup anterior: {exc}")
                raise

        _install_payload(payload_dir, install_dir, backup_dir, log_path)

        _safe_log(log_path, "Atualização instalada com sucesso.")
        if not backup_keep:
            shutil.rmtree(backup_dir, ignore_errors=True)
        else:
            _safe_log(log_path, f"Backup mantido em: {backup_dir}")

        _reopen_app(install_dir / main_exe_name, install_dir, log_path)
        return 0
    except Exception as exc:
        _safe_log(log_path, f"ERRO: {exc}")
        _safe_log(log_path, traceback.format_exc())
        try:
            _rollback(install_dir, backup_dir, [], log_path)
        except Exception:
            pass

        # Tenta reabrir o app antigo se ele ainda existir.
        try:
            _reopen_app(install_dir / main_exe_name, install_dir, log_path)
        except Exception:
            pass

        _message_box(
            "Falha ao atualizar o CUMA",
            f"Não foi possível concluir a atualização automática.\n\n"
            f"Erro: {exc}\n\n"
            f"O log foi salvo em:\n{persistent_log}",
            error=True,
        )
        return 1
    finally:
        try:
            shutil.rmtree(extract_dir, ignore_errors=True)
        except Exception:
            pass



# =============================================================================
# Modo verificação: o CUMA principal chama este programa com --check.
# A partir daqui, o atualizador externo cuida de tudo.
# =============================================================================


def _current_platform_key() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("linux"):
        return "linux"
    return "unknown"


def _default_main_exe_name_for_platform() -> str:
    return "cuma.exe" if _current_platform_key() == "windows" else "cuma"


def _select_manifest_for_current_platform(manifest: dict) -> dict:
    """Retorna os dados de update da plataforma atual.

    Mantém compatibilidade com o stable.json antigo, mas prefere:
      platforms.windows / platforms.linux / platforms.macos
    """
    platform = _current_platform_key()
    selected = {"platform_key": platform}
    try:
        platforms = manifest.get("platforms", {})
        if isinstance(platforms, dict):
            item = platforms.get(platform) or {}
            if isinstance(item, dict):
                selected.update(item)
    except Exception:
        pass

    # Campos globais continuam como fallback para Windows/manifesto antigo.
    for key in ("version", "download_url", "sha256", "size_bytes", "release_notes", "asset_name", "archive_type", "main_exe_name"):
        if not selected.get(key) and manifest.get(key) is not None:
            selected[key] = manifest.get(key)

    selected["version"] = str(manifest.get("version") or selected.get("version") or "").strip()
    if not selected.get("main_exe_name"):
        selected["main_exe_name"] = _default_main_exe_name_for_platform()
    if not selected.get("asset_name"):
        try:
            url = str(selected.get("download_url") or "")
            selected["asset_name"] = Path(url.split("?", 1)[0]).name or (
                "CUMA_windows.zip" if platform == "windows" else
                "CUMA_macos.zip" if platform == "macos" else
                "CUMA_linux.tar.gz"
            )
        except Exception:
            selected["asset_name"] = "CUMA_windows.zip"
    if not selected.get("archive_type"):
        name = str(selected.get("asset_name") or "").lower()
        if name.endswith(".tar.gz") or name.endswith(".tgz"):
            selected["archive_type"] = "tar.gz"
        else:
            selected["archive_type"] = "zip"
    return selected


DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/soldieg/CUMA/main/updates/stable.json"
DEFAULT_DOWNLOAD_URL = "https://github.com/soldieg/CUMA/releases/download/Stable/CUMA_windows.zip"


def _version_tuple(value: str) -> tuple[int, int, int]:
    import re
    try:
        parts = re.findall(r"\d+", str(value or ""))[:3]
        nums = [int(x) for x in parts]
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums[:3])
    except Exception:
        return (0, 0, 0)


def _human_size(num: int) -> str:
    try:
        n = float(num or 0)
    except Exception:
        n = 0.0
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{int(num or 0)} B"


def _download_file(url: str, dest: Path, expected_size: int = 0, progress_cb=None) -> None:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        str(url),
        headers={"User-Agent": "CUMA-External-Updater/1.100.30"},
    )
    downloaded = 0
    last_report = 0.0
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = expected_size
        try:
            header_size = int(resp.headers.get("Content-Length") or 0)
            if not total and header_size:
                total = header_size
        except Exception:
            pass

        with dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 512)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if progress_cb and now - last_report > 0.25:
                    last_report = now
                    if total:
                        pct = min(100, int(downloaded * 100 / max(1, total)))
                        progress_cb(f"Baixando pacote... {pct}% ({_human_size(downloaded)} de {_human_size(total)})")
                    else:
                        progress_cb(f"Baixando pacote... {_human_size(downloaded)}")

    if expected_size and dest.stat().st_size != int(expected_size):
        raise RuntimeError(
            f"Tamanho do ZIP diferente do manifesto. Esperado: {expected_size}; recebido: {dest.stat().st_size}."
        )


def _copy_self_to_temp(work_dir: Path, request_file: Path) -> list[str]:
    """Gera o comando do instalador real em uma cópia temporária.

    O modo --check pode estar rodando a partir da pasta instalada. Para substituir
    também o próprio cuma_updater.exe, o instalador que recebe --request precisa
    rodar fora da pasta do CUMA.
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    if getattr(sys, "frozen", False):
        src = Path(sys.executable).resolve()
        dst = work_dir / src.name
        shutil.copy2(src, dst)
        return [str(dst), "--request", str(request_file)]

    script = Path(__file__).resolve()
    return [sys.executable, str(script), "--request", str(request_file)]


def _create_update_request(
    *,
    install_dir: Path,
    archive_path: Path,
    main_exe_name: str,
    main_pid: int,
    latest_version: str,
    current_version: str,
    expected_sha: str,
    expected_size: int,
    download_url: str,
    manifest_url: str,
    work_dir: Path,
    archive_type: str = "",
) -> Path:
    request = {
        "schema": "CUMA_UPDATE_REQUEST",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "install_dir": str(install_dir),
        "archive_path": str(archive_path),
        "main_exe_name": str(main_exe_name or "cuma.exe"),
        "main_pid": int(main_pid or 0),
        "latest_version": str(latest_version or "").strip(),
        "current_version": str(current_version or "").strip(),
        "expected_sha256": expected_sha,
        "expected_size_bytes": int(expected_size or 0),
        "download_url": str(download_url or "").strip(),
        "manifest_url": str(manifest_url or "").strip(),
        "archive_type": str(archive_type or "").strip(),
        "platform": _current_platform_key(),
        "keep_backup": True,
        "backup_policy": "single_replace",
        "persistent_log_path": str(_persistent_update_log_path(install_dir)),
    }
    request_file = work_dir / "update_request.json"
    request_file.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    return request_file


def _fetch_manifest(manifest_url: str) -> dict:
    import urllib.request

    req = urllib.request.Request(
        str(manifest_url or DEFAULT_MANIFEST_URL),
        headers={"User-Agent": "CUMA-External-Update-Checker/1.100.30"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _launch_request_installer(request_file: Path, work_dir: Path) -> None:
    cmd = _copy_self_to_temp(work_dir, request_file)
    kwargs = {"cwd": str(work_dir), "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(cmd, **kwargs)


def _simple_console_check(args) -> int:
    """Fallback sem janela gráfica, útil para testes ou ambientes sem Tk."""
    manifest = _fetch_manifest(args.manifest_url)
    selected = _select_manifest_for_current_platform(manifest)
    latest = str(manifest.get("version", "") or selected.get("version", "") or "").strip()
    current = str(args.current_version or "").strip()
    if latest and _version_tuple(latest) > _version_tuple(current):
        print(f"Atualização disponível: {latest}")
        print(f"Plataforma: {_current_platform_key()}")
        print(str(selected.get("download_url") or manifest.get("download_url") or DEFAULT_DOWNLOAD_URL))
        return 2
    print("Você já está usando a versão mais recente.")
    return 0


def run_check(args) -> int:
    """Mostra a janela de verificação do atualizador externo."""
    manifest_url = str(args.manifest_url or DEFAULT_MANIFEST_URL).strip()
    current_version = str(args.current_version or "").strip() or "0.0.0"
    install_dir = Path(args.install_dir or ".").resolve()
    main_pid = int(args.main_pid or 0)
    main_exe_name = str(args.main_exe_name or _default_main_exe_name_for_platform()).strip() or _default_main_exe_name_for_platform()

    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception:
        return _simple_console_check(args)

    try:
        root = tk.Tk()
    except Exception:
        return _simple_console_check(args)

    root.title("Atualizador do CUMA")
    root.geometry("700x500")
    root.minsize(640, 430)
    bg = "#111827"
    surface = "#172033"
    field = "#0f172a"
    fg = "#e5e7eb"
    muted = "#9ca3af"
    accent = "#2563eb"
    danger = "#ef4444"
    success = "#22c55e"

    root.configure(bg=bg)

    container = tk.Frame(root, bg=surface, padx=22, pady=18)
    container.pack(fill="both", expand=True, padx=1, pady=1)

    title_var = tk.StringVar(value="Verificando atualizações...")
    subtitle_var = tk.StringVar(value="Consultando o manifesto do GitHub Releases.")
    status_var = tk.StringVar(value="")
    state = {"manifest": None, "latest": "", "download_url": "", "sha256": "", "size_bytes": 0, "asset_name": "", "archive_type": "", "platform": _current_platform_key()}

    tk.Label(container, textvariable=title_var, bg=surface, fg=fg, font=("Segoe UI", 15, "bold"),
             anchor="w", justify="left").pack(fill="x")
    tk.Label(container, textvariable=subtitle_var, bg=surface, fg=muted, font=("Segoe UI", 9),
             anchor="w", justify="left", wraplength=640).pack(fill="x", pady=(5, 14))

    text_box = tk.Text(container, height=12, wrap="word", bg=field, fg=fg, insertbackground=fg,
                       relief="flat", bd=0, padx=12, pady=10, font=("Segoe UI", 9))
    text_box.pack(fill="both", expand=True)
    text_box.insert("1.0", "Aguarde...\n")
    text_box.configure(state="disabled")

    tk.Label(container, textvariable=status_var, bg=surface, fg=muted, font=("Segoe UI", 9),
             anchor="w", justify="left").pack(fill="x", pady=(10, 8))

    actions = tk.Frame(container, bg=surface)
    actions.pack(fill="x")

    buttons: list[tk.Button] = []

    def set_text(value: str) -> None:
        text_box.configure(state="normal")
        text_box.delete("1.0", "end")
        text_box.insert("1.0", value)
        text_box.configure(state="disabled")

    def set_status(value: str) -> None:
        try:
            root.after(0, lambda: status_var.set(str(value)))
        except Exception:
            status_var.set(str(value))

    def make_button(label: str, command, primary: bool = False, enabled: bool = True):
        btn = tk.Button(
            actions, text=label, command=command,
            bg=accent if primary else field,
            fg="#ffffff" if primary else fg,
            activebackground=accent if primary else bg,
            activeforeground="#ffffff" if primary else fg,
            disabledforeground=muted,
            relief="flat", bd=0, padx=18, pady=9,
            font=("Segoe UI", 9, "bold" if primary else "normal"),
            cursor="hand2" if enabled else "arrow",
            state="normal" if enabled else "disabled",
        )
        btn.pack(side="right", padx=(8, 0))
        buttons.append(btn)
        return btn

    def clear_buttons():
        for b in list(buttons):
            try:
                b.destroy()
            except Exception:
                pass
        buttons.clear()

    def manual_download():
        try:
            import webbrowser
            url = state.get("download_url") or DEFAULT_DOWNLOAD_URL
            webbrowser.open(str(url))
            status_var.set("Download manual aberto no navegador. Você escolhe quando instalar.")
        except Exception as exc:
            messagebox.showerror("Baixar manualmente", str(exc))

    def auto_update():
        for b in buttons:
            try:
                b.configure(state="disabled", cursor="arrow")
            except Exception:
                pass
        status_var.set("Preparando atualização automática...")

        def worker():
            try:
                download_url = str(state.get("download_url") or DEFAULT_DOWNLOAD_URL).strip()
                if not download_url:
                    raise RuntimeError("O manifesto não informou download_url.")

                expected_sha = _clean_sha(state.get("sha256", ""))
                if not expected_sha:
                    raise RuntimeError(
                        "O stable.json ainda não tem SHA256 válido. "
                        "Gere o ZIP pelo BAT e publique o stable.json atualizado antes de usar a atualização automática."
                    )
                expected_size = int(state.get("size_bytes") or 0)

                temp_base = Path(tempfile.gettempdir()) / "CUMA_updates"
                temp_base.mkdir(parents=True, exist_ok=True)
                work_dir = temp_base / f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
                work_dir.mkdir(parents=True, exist_ok=True)
                archive_path = work_dir / str(state.get("asset_name") or ("CUMA_windows.zip" if _current_platform_key() == "windows" else "CUMA_macos.zip" if _current_platform_key() == "macos" else "CUMA_linux.tar.gz"))
                update_log = [work_dir / "CUMA_update.log", _persistent_update_log_path(install_dir)]

                _safe_log(update_log, "=" * 88)
                _safe_log(update_log, "CHECK/AUTO_UPDATE iniciado.")
                _safe_log(update_log, f"Versão instalada: {current_version}")
                _safe_log(update_log, f"Versão disponível: {state.get('latest', '')}")
                _safe_log(update_log, f"Manifesto: {manifest_url}")
                _safe_log(update_log, f"Download: {download_url}")
                _safe_log(update_log, f"Instalação: {install_dir}")
                _safe_log(update_log, f"PID principal: {main_pid}")

                _download_file(download_url, archive_path, expected_size, set_status)
                _safe_log(update_log, f"Download concluído: {archive_path} ({archive_path.stat().st_size if archive_path.exists() else 0} bytes)")

                set_status("Verificando SHA256 do pacote...")
                got_sha = _sha256_file(archive_path)
                _safe_log(update_log, f"SHA256 calculado: {got_sha}")
                _safe_log(update_log, f"SHA256 esperado:  {expected_sha}")
                if got_sha != expected_sha:
                    _safe_log(update_log, "ERRO: SHA256 inválido. Instalação bloqueada.")
                    raise RuntimeError(f"SHA256 inválido. Esperado {expected_sha}, recebido {got_sha}.")
                _safe_log(update_log, "SHA256 validado com sucesso.")

                request_file = _create_update_request(
                    install_dir=install_dir,
                    archive_path=archive_path,
                    main_exe_name=main_exe_name,
                    main_pid=main_pid,
                    latest_version=state.get("latest", ""),
                    current_version=current_version,
                    expected_sha=expected_sha,
                    expected_size=expected_size,
                    download_url=download_url,
                    manifest_url=manifest_url,
                    work_dir=work_dir,
                    archive_type=str(state.get("archive_type") or ""),
                )

                _safe_log(update_log, f"Arquivo de requisição criado: {request_file}")
                set_status("Instalador iniciado. O CUMA será fechado para atualizar os arquivos...")
                _launch_request_installer(request_file, work_dir)
                _safe_log(update_log, "Instalador externo temporário iniciado.")
                try:
                    root.after(700, root.destroy)
                except Exception:
                    pass
            except Exception as exc:
                def fail():
                    for b in buttons:
                        try:
                            b.configure(state="normal", cursor="hand2")
                        except Exception:
                            pass
                    status_var.set("Atualização automática não concluída.")
                    messagebox.showerror("Atualização automática", str(exc))
                try:
                    root.after(0, fail)
                except Exception:
                    pass

        import threading
        threading.Thread(target=worker, daemon=True, name="CUMA-External-Auto-Update").start()

    def render_result(manifest: dict):
        state["manifest"] = manifest
        selected = _select_manifest_for_current_platform(manifest)
        latest = str(manifest.get("version", "") or selected.get("version", "") or "").strip()
        state["latest"] = latest
        state["platform"] = str(selected.get("platform_key") or _current_platform_key())
        state["download_url"] = str(selected.get("download_url", "") or manifest.get("download_url", "") or DEFAULT_DOWNLOAD_URL).strip()
        state["sha256"] = str(selected.get("sha256", "") or manifest.get("sha256", "") or "").strip()
        state["asset_name"] = str(selected.get("asset_name", "") or "").strip()
        state["archive_type"] = str(selected.get("archive_type", "") or "").strip()
        try:
            state["size_bytes"] = int(selected.get("size_bytes", 0) or manifest.get("size_bytes", 0) or 0)
        except Exception:
            state["size_bytes"] = 0

        notes = selected.get("release_notes", manifest.get("release_notes", []))
        if isinstance(notes, list):
            notes_text = "\n".join(f"• {x}" for x in notes[:12])
        else:
            notes_text = str(notes or "")

        clear_buttons()
        make_button("Fechar", root.destroy, primary=False, enabled=True)

        if latest and _version_tuple(latest) > _version_tuple(current_version):
            title_var.set(f"CUMA {latest} está disponível")
            subtitle_var.set("Escolha atualização automática ou download manual.")
            auto_allowed = bool(_clean_sha(state["sha256"]))
            make_button("Baixar manualmente", manual_download, primary=False, enabled=True)
            make_button("Atualizar agora", auto_update, primary=True, enabled=auto_allowed)
            if not auto_allowed:
                status_var.set("Atualização automática bloqueada: SHA256 do stable.json ainda não é válido.")
            else:
                status_var.set("Pronto para atualizar. Ao clicar, o CUMA será fechado para substituir os arquivos.")

            details = [
                f"Versão instalada: {current_version}",
                f"Versão no GitHub: {latest}",
                f"Manifesto: {manifest_url}",
                f"Plataforma: {state.get('platform', _current_platform_key())}",
                f"Pacote: {state.get('asset_name', '') or 'não informado'}",
                "",
                "Link de download:",
                state["download_url"],
                "",
                "SHA256:",
                state["sha256"] or "não informado",
            ]
            if state["size_bytes"]:
                details.extend(["", "Tamanho:", _human_size(state["size_bytes"])])
            if notes_text:
                details.extend(["", "Novidades:", notes_text])
            set_text("\n".join(details))
        else:
            title_var.set("Não há atualizações")
            subtitle_var.set("Você já está usando a versão mais recente disponível para este canal.")
            status_var.set("")
            set_text(
                f"Versão instalada: {current_version}\n"
                f"Versão no GitHub: {latest or 'não informada'}\n"
                f"Manifesto: {manifest_url}\n"
                f"Plataforma: {_current_platform_key()}"
            )

    def render_error(exc: Exception):
        clear_buttons()
        make_button("Fechar", root.destroy, primary=False, enabled=True)
        title_var.set("Não foi possível verificar atualizações")
        subtitle_var.set("Confira sua conexão ou o manifesto de atualização.")
        status_var.set("")
        set_text(f"Erro técnico: {type(exc).__name__}: {exc}")

    def check_worker():
        try:
            manifest = _fetch_manifest(manifest_url)
            if str(manifest.get("app_id", "cuma")).lower() != "cuma":
                raise RuntimeError("O manifesto remoto não parece ser do CUMA.")
            root.after(0, lambda: render_result(manifest))
        except Exception as exc:
            root.after(0, lambda exc=exc: render_error(exc))

    make_button("Fechar", root.destroy, primary=False, enabled=True)

    import threading
    threading.Thread(target=check_worker, daemon=True, name="CUMA-External-Update-Check").start()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atualizador externo do CUMA")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--request", help="Caminho para o JSON de atualização.")
    mode.add_argument("--check", action="store_true", help="Verifica atualizações e mostra a janela do atualizador.")
    parser.add_argument("--manifest-url", default=DEFAULT_MANIFEST_URL, help="URL raw do updates/stable.json.")
    parser.add_argument("--current-version", default="", help="Versão instalada do CUMA.")
    parser.add_argument("--install-dir", default="", help="Pasta onde o CUMA está instalado.")
    parser.add_argument("--main-pid", default="0", help="PID do CUMA principal, usado para fechar antes de instalar.")
    parser.add_argument("--main-exe-name", default="cuma.exe", help="Nome do executável principal.")
    args = parser.parse_args(argv)

    if args.request:
        return run_update(Path(args.request))
    return run_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
