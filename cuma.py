
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CUMA - Avançado com XTEINK.

Abas na ordem solicitada:
1. Limpar PDF
2. Prévia
3. Ferramentas
4. XTEINK
5. Resultados
6. Registros
7. Opções

Conversões XTEINK:
- PDF para EPUB
- PDF para XTCH
- EPUB para XTCH

XTCH agora é gerado nativamente em Python para PDFs e EPUBs baseados em imagens, sem depender de Node/npm/bun.
"""
from __future__ import annotations

import html
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import traceback
import time
import tempfile
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
import hashlib
import struct
import zipfile
import colorsys
from dataclasses import asdict, dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable, Optional

import fitz
import numpy as np
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    DND_AVAILABLE = False

APP_NAME = "CUMA"
APP_VERSION = "1.100.12 CUMA"
CONFIG_FILE = "config_cuma.json"
LOG_FILE = "CUMA.log"
MANUAL_FILE = "manual_do_programa.txt"
XTCJS_REPO_URL = "https://github.com/varo6/xtcjs"

COMPRESSION_OPTIONS = ("Original", "Preservar qualidade máxima", "Compactar moderadamente", "Compactar bastante")
PROFILES = ("Conservador", "Normal", "Agressivo")
MODES = ("auto", "image", "visual")
THEMES = ("Manga Dark", "Moderno Escuro", "Moderno Claro", "CUMA")
THEME_SETTING_MODES = ("Automático", "Claro", "Escuro", "Personalizado")
CUSTOM_THEME_BASES = ("Claro", "Escuro")
SYSTEM_COLOR_PRESETS = ("Manga Dark", "Moderno Escuro", "Moderno Claro", "CUMA")
ACCENT_PRESETS = ("#2563EB", "#22C55E", "#06B6D4", "#F59E0B", "#EF4444", "#A855F7", "#EC4899", "#84CC16")
HARDWARE_MODES = ("Automático", "CPU", "NVIDIA CUDA", "AMD OpenCL", "Intel OpenCL", "OpenCL Genérico", "CPU + GPU")
FONT_SIZES = ("Pequena", "Normal", "Grande", "Muito grande")
UI_DENSITIES = ("Compacta", "Normal", "Espaçosa")
PERFORMANCE_PROFILES = ("Econômico", "Equilibrado", "Rápido", "Máximo desempenho")
PROCESS_PRIORITIES = ("Baixa", "Normal", "Alta")
LOG_LEVELS = ("Básico", "Normal", "Detalhado", "Debug")
PREVIEW_QUALITIES = ("Baixa", "Média", "Alta")
EXPORT_FORMATS = ("PDF", "PDF + CBZ", "CBZ", "Imagens JPG", "Imagens PNG")
XTEINK_DEVICES = ("XTEINK X4", "XTEINK X3", "Personalizado")
XTEINK_DEVICE_PROFILES = {"XTEINK X4": (480, 800), "XTEINK X3": (528, 792), "Personalizado": (600, 800)}
SUPPORTED_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")

PALETTES = {
    "Manga Dark": {
        "bg":"#080b14", "surface":"#11121a", "surface2":"#1b1a24", "field":"#0c101b",
        "fg":"#fff7ed", "muted":"#c7b9a6", "border":"#3a2d22", "accent":"#f59e0b",
        "accent_hover":"#d97706", "success":"#34d399", "danger":"#fb7185", "selection":"#92400e", "drop":"#14101a"
    },
    "Moderno Escuro": {
        "bg":"#0b1020", "surface":"#111827", "surface2":"#172033", "field":"#0f172a",
        "fg":"#e5e7eb", "muted":"#9ca3af", "border":"#263244", "accent":"#3b82f6",
        "accent_hover":"#2563eb", "success":"#22c55e", "danger":"#ef4444", "selection":"#1d4ed8", "drop":"#101827"
    },
    "Moderno Claro": {
        "bg":"#eef2f7", "surface":"#ffffff", "surface2":"#f8fafc", "field":"#ffffff",
        "fg":"#0f172a", "muted":"#64748b", "border":"#d7dee8", "accent":"#2563eb",
        "accent_hover":"#1d4ed8", "success":"#16a34a", "danger":"#dc2626", "selection":"#dbeafe", "drop":"#f1f5f9"
    },
}

@dataclass
class CleanerConfig:
    output_dir: str = ""
    mode: str = "auto"
    profile: str = "Normal"
    compression: str = "Preservar qualidade máxima"
    export_format: str = "PDF"
    suffix: str = "_limpo"
    ranges: str = ""
    password: str = ""
    keep_first: bool = True
    keep_last: int = 0
    overwrite_original: bool = False
    create_backup: bool = True
    open_after: bool = True
    include_subfolders: bool = False
    save_removed_pdf: bool = True
    validate_output: bool = True
    theme: str = "Manga Dark"
    xteink_device: str = "XTEINK X4"
    xteink_quality: int = 88
    xteink_converter_dir: str = ""  # reservado/opcional
    hardware_mode: str = "Automático"
    worker_threads: int = 0
    enable_page_cache: bool = True
    page_cache_mb: int = 256
    auto_save_config: bool = True
    font_size: str = "Normal"
    ui_density: str = "Normal"
    show_tooltips: bool = True
    confirm_actions: bool = True
    remember_window: bool = True
    last_window_geometry: str = ""
    remember_last_tab: bool = True
    last_tab: str = "Limpar PDF"
    performance_profile: str = "Equilibrado"
    process_priority: str = "Normal"
    memory_saver: bool = False
    max_parallel_pdfs: int = 0
    gpu_only_if_faster: bool = False
    gpu_fallback_cpu: bool = True
    clear_cache_on_exit: bool = False
    log_level: str = "Normal"
    auto_save_log: bool = True
    log_retention_days: int = 30
    remember_last_folder: bool = True
    last_input_dir: str = ""
    preview_quality: str = "Média"
    preview_batch_pages: int = 10
    preview_cache: bool = True
    preview_maximized: bool = False
    preview_thumb_width: int = 760
    auto_process_added: bool = False
    skip_existing: bool = False
    detect_duplicates: bool = True
    resume_processing: bool = False
    silent_mode: bool = False
    xteink_output_dir: str = ""

    def __post_init__(self) -> None:
        try:
            clean_dir = Path(str(self.output_dir)).expanduser() if self.output_dir else (app_dir() / "limpos")
            if not clean_dir.is_absolute():
                clean_dir = app_dir() / clean_dir
            self.output_dir = str(clean_dir)
        except Exception:
            self.output_dir = str(app_dir() / "limpos")
        try:
            converter_dir = Path(str(getattr(self, "xteink_output_dir", ""))).expanduser() if getattr(self, "xteink_output_dir", "") else (app_dir() / "limpos" / "Converter")
            if not converter_dir.is_absolute():
                converter_dir = app_dir() / converter_dir
            self.xteink_output_dir = str(converter_dir)
        except Exception:
            self.xteink_output_dir = str(app_dir() / "limpos" / "Converter")
        if self.theme not in THEMES:
            self.theme = "Manga Dark"
        if self.export_format not in EXPORT_FORMATS:
            self.export_format = "PDF"
        if self.xteink_device not in XTEINK_DEVICES:
            self.xteink_device = "XTEINK X4"
        if self.hardware_mode not in HARDWARE_MODES:
            self.hardware_mode = "Automático"
        if self.font_size not in FONT_SIZES:
            self.font_size = "Normal"
        if self.ui_density not in UI_DENSITIES:
            self.ui_density = "Normal"
        if self.performance_profile not in PERFORMANCE_PROFILES:
            self.performance_profile = "Equilibrado"
        if self.process_priority not in PROCESS_PRIORITIES:
            self.process_priority = "Normal"
        if self.log_level not in LOG_LEVELS:
            self.log_level = "Normal"
        if self.preview_quality not in PREVIEW_QUALITIES:
            self.preview_quality = "Média"
        self.worker_threads = max(0, min(64, int(self.worker_threads or 0)))
        self.page_cache_mb = max(0, min(4096, int(self.page_cache_mb or 0)))
        self.max_parallel_pdfs = max(0, min(64, int(self.max_parallel_pdfs or 0)))
        self.log_retention_days = max(0, min(3650, int(self.log_retention_days or 30)))
        self.preview_batch_pages = max(1, min(100, int(self.preview_batch_pages or 10)))
        self.preview_thumb_width = max(320, min(1600, int(self.preview_thumb_width or 760)))

@dataclass
class Thresholds:
    min_image_area: int = 90_000
    min_visual_density: float = 0.50
    image_mode_ratio: float = 0.50
    density_zoom: float = 0.25

@dataclass
class Result:
    source: str
    output: str = ""
    status: str = "OK"
    mode: str = ""
    original_pages: int = 0
    final_pages: int = 0
    removed_pages: int = 0
    original_size: int = 0
    final_size: int = 0
    saved_bytes: int = 0
    backup: str = ""
    removed_pdf: str = ""
    extra_outputs: str = ""
    error: str = ""


def app_dir() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

def resource_path(name: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", app_dir())) / name

def config_path() -> Path: return app_dir() / CONFIG_FILE
def log_path() -> Path: return app_dir() / LOG_FILE
def manual_path() -> Path: return app_dir() / MANUAL_FILE

def write_log(msg: str) -> None:
    try:
        with log_path().open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass

def load_config() -> CleanerConfig:
    cfg = CleanerConfig()
    try:
        if config_path().exists():
            data = json.loads(config_path().read_text(encoding="utf-8"))
            base = asdict(cfg)
            base.update({k: v for k, v in data.items() if k in base})
            return CleanerConfig(**base)
    except Exception as exc:
        write_log(f"Config inválida: {exc}")
    return cfg

def save_config(cfg: CleanerConfig) -> None:
    try:
        config_path().write_text(json.dumps(asdict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        write_log(f"Falha ao salvar config: {exc}")

def ensure_manual() -> Path:
    text = f"""MANUAL - {APP_NAME} {APP_VERSION}
{'=' * 74}

Abas:
1. Limpar PDF: limpeza e exportação PDF/CBZ/imagens.
2. Prévia: miniaturas do PDF selecionado.
3. Ferramentas: extrair imagens e criar PDF a partir de imagens.
4. XTEINK: PDF→EPUB, PDF→XTCH e EPUB→XTCH.
5. Resultados: saída do processamento.
6. Registros: log interno.
7. Opções: tema, limpeza, exportação e conversor.

XTEINK:
- XTEINK X4: 480x800 px.
- XTEINK X3: 528x792 px.
- XTCH é gerado nativamente em Python; xtcjs fica apenas como referência/opcional.

Fluxo XTCH:
PDF/EPUB de imagens → renderização Python → empacotamento XTCH nativo.
"""
    try:
        manual_path().write_text(text, encoding="utf-8")
    except Exception:
        pass
    return manual_path()

def open_path(path: Path | str) -> None:
    path = Path(path)
    if not path.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])

def open_folder(path: Path | str) -> None:
    path = Path(path)
    open_path(path.parent if path.is_file() else path)

def format_bytes(n: int | float) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.with_suffix("")
    suffix = path.suffix
    i = 2
    while True:
        candidate = Path(f"{base}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1

def parse_ranges(spec: str, total: int) -> list[int]:
    if total <= 0:
        return []
    if not spec or not spec.strip():
        return list(range(total))
    selected: set[int] = set()
    for part in spec.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                if not a.strip() or not b.strip():
                    raise ValueError
                start, end = int(a.strip()), int(b.strip())
                if start > end:
                    start, end = end, start
                for n in range(start, end + 1):
                    if 1 <= n <= total:
                        selected.add(n - 1)
            else:
                n = int(part)
                if 1 <= n <= total:
                    selected.add(n - 1)
        except ValueError as exc:
            raise RuntimeError(f"Intervalo de páginas inválido: {part!r}. Use exemplos como 1-5, 8, 10-12.") from exc
    return sorted(selected)

def friendly_error(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    if isinstance(exc, PermissionError) or "password" in low or "senha" in low:
        return "PDF protegido por senha ou senha incorreta."
    if "cannot open" in low or "broken" in low or "invalid" in low:
        return "PDF corrompido ou inválido."
    return text or exc.__class__.__name__

def parse_drop(data: str, root: Optional[tk.Tk] = None) -> list[str]:
    if not data:
        return []
    text = str(data).strip()
    items: list[str] = []
    if root is not None:
        try:
            items = list(root.tk.splitlist(text))
        except Exception:
            pass
    if not items:
        items = [x.strip() for x in text.splitlines() if x.strip()] or [text]
    return [x.strip().strip('"').strip("'") for x in items if x.strip()]

def fit_to_target(img: Image.Image, target: Optional[tuple[int, int]]) -> Image.Image:
    img = img.convert("RGB")
    if target is None:
        return img
    tw, th = target
    canvas = Image.new("RGB", (tw, th), "white")
    copy = img.copy()
    copy.thumbnail((tw, th), Image.Resampling.LANCZOS)
    canvas.paste(copy, ((tw - copy.width) // 2, (th - copy.height) // 2))
    return canvas

def render_pdf_pages_as_images(pdf_path: Path, target: Optional[tuple[int, int]] = None, quality_zoom: float = 2.0) -> list[Image.Image]:
    doc = fitz.open(str(pdf_path))
    images: list[Image.Image] = []
    try:
        for page in doc:
            if target:
                zoom = max(target[0] / max(page.rect.width, 1), target[1] / max(page.rect.height, 1)) * 1.25
            else:
                zoom = quality_zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(fit_to_target(im, target))
    finally:
        doc.close()
    return images

def save_images_to_pdf(image_paths: list[Path], output_pdf: Path) -> None:
    if not image_paths:
        raise RuntimeError("Nenhuma imagem selecionada.")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    images = [Image.open(p).convert("RGB") for p in image_paths]
    try:
        images[0].save(output_pdf, save_all=True, append_images=images[1:])
    finally:
        for im in images:
            im.close()

def create_image_epub(images: list[Image.Image], output_epub: Path, title: str, quality: int = 88) -> None:
    if not images:
        raise RuntimeError("Nenhuma imagem para criar EPUB.")
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    uid = str(uuid.uuid4())
    with zipfile.ZipFile(output_epub, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")
        manifest = []
        spine = []
        nav = []
        for i, im in enumerate(images, 1):
            img_name = f"images/page_{i:04d}.jpg"
            html_name = f"page_{i:04d}.xhtml"
            bio = BytesIO()
            im.save(bio, format="JPEG", quality=quality, optimize=True)
            z.writestr("OEBPS/" + img_name, bio.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("OEBPS/" + html_name, f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Página {i}</title><style>html,body{{margin:0;padding:0;background:white;}} img{{width:100%;height:100%;object-fit:contain;display:block;}}</style></head><body><img src="{img_name}" alt="Página {i}"/></body></html>""", compress_type=zipfile.ZIP_DEFLATED)
            manifest.append(f'<item id="p{i}" href="{html_name}" media-type="application/xhtml+xml"/>')
            manifest.append(f'<item id="img{i}" href="{img_name}" media-type="image/jpeg"/>')
            spine.append(f'<itemref idref="p{i}"/>')
            nav.append(f'<li><a href="{html_name}">Página {i}</a></li>')
        z.writestr("OEBPS/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Sumário</title></head><body><nav epub:type="toc"><ol>{''.join(nav)}</ol></nav></body></html>""", compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:language>pt-BR</dc:language></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>""", compress_type=zipfile.ZIP_DEFLATED)

def xth_page_bytes(img: Image.Image, target: tuple[int, int]) -> bytes:
    """Converte imagem RGB para página XTH (2-bit grayscale) com header de 22 bytes."""
    w, h = target
    gray = fit_to_target(img, target).convert("L")
    px = gray.load()
    col_bytes = (h + 7) // 8
    plane_size = w * col_bytes
    plane1 = bytearray(plane_size)
    plane2 = bytearray(plane_size)
    for x in range(w - 1, -1, -1):
        col_index = w - 1 - x
        base = col_index * col_bytes
        for y in range(h):
            g = px[x, y]
            if g >= 224:
                val = 0      # branco
            elif g >= 160:
                val = 2      # cinza claro
            elif g >= 80:
                val = 1      # cinza escuro
            else:
                val = 3      # preto
            byte_i = base + (y // 8)
            bit = 7 - (y % 8)
            if val & 0b10:
                plane1[byte_i] |= 1 << bit
            if val & 0b01:
                plane2[byte_i] |= 1 << bit
    data = bytes(plane1) + bytes(plane2)
    digest8 = hashlib.md5(data).digest()[:8]
    return struct.pack("<IHHBBI8s", 0x00485458, w, h, 0, 0, len(data), digest8) + data


def create_xtch_from_images(images: list[Image.Image], output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    """Cria contêiner XTCH nativo com páginas XTH 2-bit grayscale."""
    if not images:
        raise RuntimeError("Nenhuma imagem para criar XTCH.")
    output_xtch.parent.mkdir(parents=True, exist_ok=True)
    if len(images) > 65535:
        raise RuntimeError("XTCH suporta no máximo 65535 páginas por arquivo.")
    page_blobs = [xth_page_bytes(im, target) for im in images]
    page_count = len(page_blobs)
    header_size = 56
    table_offset = header_size
    data_offset = header_size + page_count * 16
    offsets = []
    pos = data_offset
    for blob in page_blobs:
        offsets.append(pos)
        pos += len(blob)
    header = struct.pack("<IBBHBBBBIQQQQII", 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0)
    w, h = target
    table = bytearray()
    for off, blob in zip(offsets, page_blobs):
        table.extend(struct.pack("<QIHH", off, len(blob), w, h))
    with output_xtch.open("wb") as f:
        f.write(header)
        f.write(table)
        for blob in page_blobs:
            f.write(blob)


def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def extract_epub_images(epub_path: Path, target: tuple[int, int]) -> list[Image.Image]:
    """Extrai imagens de um EPUB. Funciona para EPUBs baseados em páginas/imagens."""
    if not epub_path.exists():
        raise RuntimeError("EPUB não encontrado.")
    images: list[Image.Image] = []
    with zipfile.ZipFile(epub_path, "r") as z:
        names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_natural_key)
        for name in names:
            try:
                with z.open(name) as f:
                    data = BytesIO(f.read())
                im = Image.open(data).convert("RGB")
                if im.width < 80 or im.height < 80:
                    im.close()
                    continue
                images.append(fit_to_target(im, target))
                im.close()
            except Exception:
                continue
    if not images:
        raise RuntimeError("Não encontrei imagens úteis dentro do EPUB. EPUB textual puro ainda não é renderizado nativamente.")
    return images


def validate_pdf(path: Path) -> None:
    doc = fitz.open(str(path))
    try:
        if len(doc) <= 0:
            raise RuntimeError("PDF final ficou vazio.")
    finally:
        doc.close()


def cuda_status() -> tuple[bool, str]:
    try:
        import cv2  # type: ignore
        cuda = getattr(cv2, "cuda", None)
        if cuda is None or not hasattr(cuda, "getCudaEnabledDeviceCount"):
            return False, "NVIDIA CUDA indisponível: OpenCV sem módulo CUDA."
        count = int(cuda.getCudaEnabledDeviceCount())
        return count > 0, f"NVIDIA CUDA disponível: {count} dispositivo(s)." if count > 0 else "NVIDIA CUDA indisponível: nenhum dispositivo CUDA encontrado."
    except Exception as exc:
        return False, f"NVIDIA CUDA indisponível: {exc}"

def opencl_status(vendor: str = "") -> tuple[bool, str]:
    try:
        if vendor.upper() == "AMD": os.environ.setdefault("OPENCV_OPENCL_DEVICE", "AMD:GPU:")
        elif vendor.upper() == "INTEL": os.environ.setdefault("OPENCV_OPENCL_DEVICE", "Intel:GPU:")
        import cv2  # type: ignore
        ok = hasattr(cv2, "ocl") and bool(cv2.ocl.haveOpenCL())
        if ok: cv2.ocl.setUseOpenCL(True)
        return ok, f"OpenCL {vendor or 'genérico'} disponível." if ok else f"OpenCL {vendor or 'genérico'} indisponível."
    except Exception as exc:
        return False, f"OpenCL indisponível: {exc}"

def acceleration_status() -> tuple[bool, str]:
    data = [cuda_status(), opencl_status("AMD"), opencl_status("Intel"), opencl_status("")]
    return any(ok for ok, _ in data), " | ".join(msg for _, msg in data)

def selected_acceleration_backend(mode: str) -> str:
    mode = (mode or "Automático").lower()
    if mode == "cpu": return "cpu"
    if "cuda" in mode or "nvidia" in mode: return "cuda" if cuda_status()[0] else "cpu"
    if "amd" in mode: return "opencl_amd" if opencl_status("AMD")[0] else "cpu"
    if "intel" in mode: return "opencl_intel" if opencl_status("Intel")[0] else "cpu"
    if "gen" in mode or "opencl" in mode: return "opencl" if opencl_status("")[0] else "cpu"
    if cuda_status()[0]: return "cuda"
    if opencl_status("AMD")[0]: return "opencl_amd"
    if opencl_status("Intel")[0]: return "opencl_intel"
    if opencl_status("")[0]: return "opencl"
    return "cpu"

def resolve_worker_threads(cfg: CleanerConfig, total: int = 1) -> int:
    total = max(1, int(total or 1)); manual = max(0, int(getattr(cfg, "worker_threads", 0) or 0)); par = max(0, int(getattr(cfg, "max_parallel_pdfs", 0) or 0))
    if manual: return max(1, min(64, manual, total))
    if par: return max(1, min(64, par, total))
    return max(1, min(4, os.cpu_count() or 1, total))

class PDFCleaner:
    def __init__(self, cfg: CleanerConfig) -> None:
        self.cfg = cfg
        self.t = self.thresholds(cfg.profile)
        self._density_cache: OrderedDict[tuple[str, int, float], float] = OrderedDict()
        # Cada entrada do cache é pequena, mas PDFs enormes podem acumular milhares de páginas.
        # O limite usa page_cache_mb como referência e evita crescimento indefinido da RAM.
        self._density_cache_limit = max(256, min(50000, int(getattr(cfg, "page_cache_mb", 256) or 256) * 64))
        self._density_cache_bytes = 0
        self._accel_backend = selected_acceleration_backend(cfg.hardware_mode)

    @staticmethod
    def thresholds(profile: str) -> Thresholds:
        p = (profile or "Normal").lower()
        if p.startswith("conserv"):
            return Thresholds(70_000, 0.25, 0.40)
        if p.startswith("agress"):
            return Thresholds(130_000, 1.00, 0.65)
        return Thresholds()

    def open_pdf(self, path: Path) -> fitz.Document:
        try:
            doc = fitz.open(str(path))
        except Exception:
            doc = fitz.open(stream=Path(path).read_bytes(), filetype="pdf")
        if doc.needs_pass:
            if not self.cfg.password or not doc.authenticate(self.cfg.password):
                doc.close()
                raise PermissionError("PDF protegido por senha ou senha incorreta.")
        return doc

    def density(self, page: fitz.Page) -> float:
        key = (str(getattr(page.parent, "name", "")), int(page.number), float(self.t.density_zoom))
        if self.cfg.enable_page_cache and key in self._density_cache:
            self._density_cache.move_to_end(key)
            return self._density_cache[key]
        pix = page.get_pixmap(matrix=fitz.Matrix(self.t.density_zoom, self.t.density_zoom), colorspace=fitz.csGRAY, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        value = float((arr < 245).mean() * 100)
        if self.cfg.enable_page_cache:
            self._density_cache[key] = value
            while len(self._density_cache) > self._density_cache_limit:
                self._density_cache.popitem(last=False)
        return value

    @staticmethod
    def image_blocks(page: fitz.Page) -> list[dict]:
        return [b for b in page.get_text("dict").get("blocks", []) if b.get("type") == 1 and b.get("image")]

    def largest_image(self, page: fitz.Page) -> Optional[dict]:
        blocks = self.image_blocks(page)
        return max(blocks, key=lambda b: int(b.get("width", 0)) * int(b.get("height", 0))) if blocks else None

    def has_large_image(self, page: fitz.Page) -> bool:
        block = self.largest_image(page)
        return bool(block and int(block.get("width", 0)) * int(block.get("height", 0)) >= self.t.min_image_area)
    def largest_image_block(self, page: fitz.Page) -> Optional[dict]:
        """Retorna o maior bloco de imagem real da página, se existir."""
        blocks = self.image_blocks(page)
        if not blocks:
            return None
        return max(blocks, key=lambda b: int(b.get("width", 0)) * int(b.get("height", 0)))

    def add_image_block_page(self, target_doc: fitz.Document, block: dict) -> bool:
        """Adiciona a imagem extraída como página final, sem rasterizar a página inteira."""
        try:
            img_bytes = block.get("image")
            w = int(block.get("width", 0))
            h = int(block.get("height", 0))
            if not img_bytes or w <= 0 or h <= 0:
                return False
            page = target_doc.new_page(width=w, height=h)
            page.insert_image(fitz.Rect(0, 0, w, h), stream=img_bytes, keep_proportion=False)
            return True
        except Exception:
            return False

    def decide_mode(self, doc: fitz.Document, indices: Iterable[int]) -> str:
        useful = large = 0
        for idx in indices:
            page = doc[idx]
            if self.density(page) < self.t.min_visual_density:
                continue
            useful += 1
            if self.has_large_image(page):
                large += 1
        return "image" if (large / useful if useful else 0) >= self.t.image_mode_ratio else "visual"

    def clean(self, source: Path, output_pdf: Path, progress: Optional[Callable[[int, int], None]] = None, cancel: Optional[Callable[[], bool]] = None) -> Result:
        """Limpa o PDF usando a estratégia V4Style.

        - Extrai a imagem real do mangá quando possível.
        - Não força remoção de texto/vetor/camada.
        - Corta margens brancas parcialmente quando extrai imagem real.
        - Evita arquivo gigante no modo image.
        - Usa show_pdf_page como fallback/final.
        """
        source = Path(source)
        output_pdf = Path(output_pdf)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        temp = output_pdf.with_suffix(".tmp.pdf")
        res = Result(source=str(source), output=str(output_pdf), original_size=source.stat().st_size)
        src = out = removed_doc = None
        try:
            src = self.open_pdf(source)
            total = len(src)
            res.original_pages = total
            indices = set(parse_ranges(self.cfg.ranges, total))
            protected_indices: set[int] = set()
            if self.cfg.keep_first and total:
                indices.add(0)
                protected_indices.add(0)
            keep_last = max(0, int(self.cfg.keep_last or 0))
            for idx in range(max(0, total - keep_last), total):
                indices.add(idx)
                protected_indices.add(idx)
            ordered = sorted(indices)
            if not ordered:
                raise RuntimeError("Nenhuma página válida selecionada.")
            mode = self.cfg.mode if self.cfg.mode != "auto" else self.decide_mode(src, ordered)
            res.mode = mode + " / v4-imagem-real"
            kept_indices: list[int] = []
            removed_indices: list[int] = []
            out = fitz.open()
            removed_doc = fitz.open()
            for seq, idx in enumerate(ordered, 1):
                if cancel and cancel():
                    raise RuntimeError("Processamento cancelado pelo usuário.")
                page = src[idx]
                dens = self.density(page)
                if idx in protected_indices:
                    keep = True
                elif idx == 0 and dens < 5:
                    keep = False
                elif mode == "image":
                    keep = self.has_large_image(page)
                else:
                    keep = dens >= self.t.min_visual_density
                target_doc = out if keep else removed_doc
                if keep:
                    inserted = False
                    if mode == "image":
                        block = self.largest_image_block(page)
                        if block is not None and self.has_large_image(page):
                            inserted = self.add_image_block_page(out, block)
                    if not inserted:
                        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
                        new_page.show_pdf_page(page.rect, src, idx)
                    kept_indices.append(idx)
                else:
                    new_page = target_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.show_pdf_page(page.rect, src, idx)
                    removed_indices.append(idx)
                if progress:
                    progress(seq, len(ordered))
            if not kept_indices:
                raise RuntimeError("Nenhuma página útil foi mantida; o PDF final ficaria vazio.")
            res.final_pages = len(kept_indices)
            res.removed_pages = len(removed_indices)
            extra_outputs: list[str] = []
            fmt = self.cfg.export_format
            if fmt in ("PDF", "PDF + CBZ"):
                temp.unlink(missing_ok=True)
                out.save(str(temp), garbage=4, deflate=True, clean=True)
                os.replace(str(temp), str(output_pdf))
                if self.cfg.validate_output:
                    validate_pdf(output_pdf)
            elif fmt == "CBZ":
                res.output = str(output_pdf.with_suffix(".cbz"))
            if fmt in ("PDF + CBZ", "CBZ"):
                cbz = output_pdf.with_suffix(".cbz")
                self.export_cbz(src, kept_indices, cbz)
                extra_outputs.append(str(cbz))
                if fmt == "CBZ":
                    res.output = str(cbz)
            if fmt in ("Imagens JPG", "Imagens PNG"):
                folder = output_pdf.with_suffix("")
                ext_fmt = "PNG" if fmt.endswith("PNG") else "JPEG"
                self.export_images(src, kept_indices, folder, ext_fmt)
                res.output = str(folder)
            if self.cfg.save_removed_pdf and removed_indices:
                removed_path = output_pdf.with_name(output_pdf.stem + "_paginas_removidas.pdf")
                removed_tmp = removed_path.with_suffix(removed_path.suffix + ".tmp")
                removed_tmp.unlink(missing_ok=True)
                try:
                    removed_doc.save(str(removed_tmp), garbage=4, deflate=True, clean=True)
                    os.replace(str(removed_tmp), str(removed_path))
                finally:
                    removed_tmp.unlink(missing_ok=True)
                res.removed_pdf = str(removed_path)
            res.extra_outputs = " | ".join(extra_outputs)
            if fmt in ("PDF", "PDF + CBZ"):
                res.output = str(output_pdf)
                res.final_size = output_pdf.stat().st_size
            elif res.output:
                p = Path(res.output)
                res.final_size = p.stat().st_size if p.is_file() else 0
            res.saved_bytes = max(0, res.original_size - res.final_size) if res.final_size else 0
            return res
        finally:
            for doc in (src, out, removed_doc):
                try:
                    if doc is not None:
                        doc.close()
                except Exception:
                    pass
            temp.unlink(missing_ok=True)

    def render_page_bytes(self, src: fitz.Document, idx: int, fmt: str = "JPEG") -> bytes:
        page = src[idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        bio = BytesIO()
        if fmt == "PNG":
            im.save(bio, format="PNG", optimize=True)
        else:
            im.save(bio, format="JPEG", quality=88, optimize=True)
        return bio.getvalue()

    def export_cbz(self, src: fitz.Document, indices: list[int], out_cbz: Path) -> None:
        out_cbz.parent.mkdir(parents=True, exist_ok=True)
        tmp_cbz = out_cbz.with_suffix(out_cbz.suffix + ".tmp")
        tmp_cbz.unlink(missing_ok=True)
        try:
            count = 0
            with zipfile.ZipFile(tmp_cbz, "w", compression=zipfile.ZIP_DEFLATED) as z:
                for n, idx in enumerate(indices, 1):
                    count += 1
                    z.writestr(f"page_{n:04d}.jpg", self.render_page_bytes(src, idx, "JPEG"))
            if count <= 0:
                raise RuntimeError("Nenhuma página para criar CBZ.")
            os.replace(str(tmp_cbz), str(out_cbz))
        finally:
            tmp_cbz.unlink(missing_ok=True)

    def export_images(self, src: fitz.Document, indices: list[int], folder: Path, fmt: str) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        ext = "png" if fmt == "PNG" else "jpg"
        for n, idx in enumerate(indices, 1):
            (folder / f"page_{n:04d}.{ext}").write_bytes(self.render_page_bytes(src, idx, fmt))

def create_backup(pdf: Path) -> Path:
    folder = pdf.parent / "backup_limpar_mangas_pdf"
    folder.mkdir(exist_ok=True)
    backup = folder / f"{pdf.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    shutil.copy2(pdf, backup)
    return backup


def preview_worker_count(total_pages: int, file_size: int = 0) -> tuple[int, str]:
    """Escolhe paralelismo para a prévia usando recursos de hardware disponíveis.

    PyMuPDF renderiza em CPU, então o ganho real vem de paralelismo controlado. Se OpenCV CUDA
    estiver disponível, apenas registramos que há GPU detectada; a renderização de PDF continua segura em CPU.
    """
    cpu = max(1, os.cpu_count() or 1)
    gpu = False
    try:
        import cv2  # type: ignore
        gpu = hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0
    except Exception:
        gpu = False
    if total_pages < 40 and file_size < 150 * 1024 * 1024:
        return 1, "Prévia leve: renderização sequencial."
    workers = max(2, min(cpu - 1 if cpu > 2 else cpu, 6))
    note = "GPU detectada; prévia usa paralelismo seguro em CPU/PyMuPDF." if gpu else "Documento grande: prévia usa paralelismo de CPU."
    return workers, note


def render_preview_page(pdf_path: Path, password: str, page_index: int, width: int = 760) -> tuple[int, Image.Image | Exception]:
    """Renderiza uma página para miniatura/visualização da janela de prévia."""
    try:
        doc = fitz.open(str(pdf_path))
        try:
            if doc.needs_pass:
                if not password or not doc.authenticate(password):
                    raise PermissionError("PDF protegido por senha ou senha incorreta.")
            page = doc[page_index]
            zoom = max(0.2, min(1.2, width / max(float(page.rect.width), 1.0)))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((width, 1600), Image.Resampling.LANCZOS)
            return page_index, img.copy()
        finally:
            doc.close()
    except Exception as exc:
        return page_index, exc


class BasePreviewWindow:
    """Prévia em janela separada com scroll, scrollbar e carregamento por partes."""
    def __init__(self, parent: "App", pdf_path: Path) -> None:
        self.parent = parent
        self.pdf_path = Path(pdf_path)
        self.password = parent.password.get()
        self.top = tk.Toplevel(parent.root)
        self.top.title(f"Prévia - {self.pdf_path.name}")
        self.top.geometry("980x760")
        self.top.minsize(760, 540)
        palette = PALETTES[parent.theme.get()]
        self.top.configure(bg=palette["bg"])
        self.canvas = tk.Canvas(self.top, highlightthickness=0, bg=palette["bg"])
        self.scrollbar = ttk.Scrollbar(self.top, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner = ttk.Frame(self.canvas, style="Card.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda _e: self._linux_scroll(-1))
        self.canvas.bind("<Button-5>", lambda _e: self._linux_scroll(1))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.photos: list[tuple[ttk.Label, ImageTk.PhotoImage]] = []
        self.max_preview_photos = 60 if getattr(parent.cfg, "memory_saver", False) else 140
        self.cancel = False
        self.loading = False
        self.next_page = 0
        self.total_pages = 0
        try:
            doc = fitz.open(str(self.pdf_path))
            try:
                if doc.needs_pass:
                    if not self.password or not doc.authenticate(self.password):
                        raise PermissionError("PDF protegido por senha ou senha incorreta.")
                self.total_pages = len(doc)
            finally:
                doc.close()
        except Exception as exc:
            messagebox.showerror("Prévia", friendly_error(exc))
            self.close()
            return
        file_size = self.pdf_path.stat().st_size if self.pdf_path.exists() else 0
        self.workers, self.hardware_note = preview_worker_count(self.total_pages, file_size)
        ttk.Label(self.inner, text=f"{self.pdf_path.name} — {self.total_pages} páginas", style="TitleSmall.TLabel").pack(anchor="w", padx=10, pady=(10, 4))
        self.status = ttk.Label(self.inner, text=f"{self.hardware_note} Carregando por partes...", style="Muted.TLabel")
        self.status.pack(anchor="w", padx=10, pady=(0, 8))
        self.load_more(initial=True)

    def _linux_scroll(self, direction: int) -> None:
        self.canvas.yview_scroll(direction, "units")
        self._maybe_load_more()

    def _on_mousewheel(self, event) -> None:
        try:
            if self.top.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                self._maybe_load_more()
        except Exception:
            pass

    def _maybe_load_more(self) -> None:
        try:
            if not self.loading and self.next_page < self.total_pages and self.canvas.yview()[1] > 0.70:
                self.load_more()
        except Exception:
            pass

    def load_more(self, initial: bool = False) -> None:
        if self.cancel or self.loading or self.next_page >= self.total_pages:
            if self.next_page >= self.total_pages:
                self.status.configure(text=f"Prévia completa: {self.total_pages} páginas carregadas.")
            return
        # Carrega mais páginas inicialmente e mantém lotes controlados para não travar memória.
        batch = 18 if initial else 12
        if self.total_pages > 250:
            batch = 24 if initial else 16
        start = self.next_page
        end = min(self.total_pages, start + batch)
        self.next_page = end
        self.loading = True
        threading.Thread(target=self._render_batch, args=(start, end), daemon=True).start()

    def _render_batch(self, start: int, end: int) -> None:
        rendered = []
        try:
            if self.workers > 1 and (end - start) > 2:
                with ThreadPoolExecutor(max_workers=self.workers) as ex:
                    futures = [ex.submit(render_preview_page, self.pdf_path, self.password, i) for i in range(start, end)]
                    for fut in as_completed(futures):
                        if self.cancel:
                            return
                        rendered.append(fut.result())
                rendered.sort(key=lambda x: x[0])
            else:
                for i in range(start, end):
                    if self.cancel:
                        return
                    rendered.append(render_preview_page(self.pdf_path, self.password, i))
        finally:
            try:
                self.top.after(0, lambda: self._add_rendered(rendered))
            except Exception:
                pass

    def _add_rendered(self, rendered) -> None:
        self.loading = False
        for i, item in rendered:
            ttk.Label(self.inner, text=f"Página {i + 1}", style="Muted.TLabel").pack(anchor="w", padx=10, pady=(12, 2))
            if isinstance(item, Image.Image):
                photo = ImageTk.PhotoImage(item)
                lbl = ttk.Label(self.inner, image=photo)
                lbl.pack(anchor="center", pady=4)
                self.photos.append((lbl, photo))
                while len(self.photos) > self.max_preview_photos:
                    old_lbl, _old_photo = self.photos.pop(0)
                    try:
                        old_lbl.configure(image="", text="Miniatura liberada para economizar memória.", style="Muted.TLabel")
                    except Exception:
                        pass
                item.close()
            else:
                ttk.Label(self.inner, text=f"Erro: {friendly_error(item)}", style="Danger.TLabel").pack(anchor="w", padx=10)
        loaded = min(self.next_page, self.total_pages)
        self.status.configure(text=f"{self.hardware_note} Carregadas {loaded}/{self.total_pages}. Role para baixo para carregar mais.")
        self._maybe_load_more()

    def close(self) -> None:
        self.cancel = True
        try:
            self.canvas.unbind_all("<MouseWheel>")
            self.top.destroy()
        except Exception:
            pass

class BaseApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = load_config()
        self.files: list[Path] = []
        self.results: list[Result] = []
        self.q: queue.Queue = queue.Queue()
        self.processing = False
        self.cancel_requested = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.setup_vars()
        self.setup_window()
        self.build()
        self.setup_dnd()
        self.apply_theme()
        ensure_manual()
        self.poll()
        self.log(f"{APP_NAME} {APP_VERSION} pronto.")

    def setup_vars(self) -> None:
        c = self.cfg
        self.output_dir = tk.StringVar(value=c.output_dir)
        self.mode = tk.StringVar(value=c.mode)
        self.profile = tk.StringVar(value=c.profile)
        self.compression = tk.StringVar(value=c.compression)
        self.export_format = tk.StringVar(value=c.export_format)
        self.suffix = tk.StringVar(value=c.suffix)
        self.ranges = tk.StringVar(value=c.ranges)
        self.password = tk.StringVar(value=c.password)
        self.keep_first = tk.BooleanVar(value=c.keep_first)
        self.keep_last = tk.IntVar(value=c.keep_last)
        self.overwrite_original = tk.BooleanVar(value=c.overwrite_original)
        self.create_backup = tk.BooleanVar(value=c.create_backup)
        self.open_after = tk.BooleanVar(value=c.open_after)
        self.include_subfolders = tk.BooleanVar(value=c.include_subfolders)
        self.save_removed_pdf = tk.BooleanVar(value=c.save_removed_pdf)
        self.validate_output = tk.BooleanVar(value=c.validate_output)
        self.theme = tk.StringVar(value=c.theme)
        self.theme_mode = tk.StringVar(value='Claro' if c.theme == 'Moderno Claro' else 'Escuro')
        self.custom_base_theme = tk.StringVar(value='Claro' if c.theme == 'Moderno Claro' else 'Escuro')
        self.custom_accent = tk.StringVar(value=THEME_VISUAL_PRESETS.get(c.theme, THEME_VISUAL_PRESETS['Moderno Escuro'])['accent'])
        self.config_help_text = tk.StringVar(value='As configurações foram organizadas por categoria para facilitar o uso.')
        self.xteink_device = tk.StringVar(value=c.xteink_device)
        self.xteink_quality = tk.IntVar(value=c.xteink_quality)
        self.xteink_converter_dir = tk.StringVar(value=c.xteink_converter_dir)
        self.hardware_mode = tk.StringVar(value=c.hardware_mode)
        self.worker_threads = tk.IntVar(value=c.worker_threads)
        self.enable_page_cache = tk.BooleanVar(value=c.enable_page_cache)
        self.page_cache_mb = tk.IntVar(value=c.page_cache_mb)
        self.auto_save_config = tk.BooleanVar(value=c.auto_save_config)
        self.font_size = tk.StringVar(value=c.font_size)
        self.ui_density = tk.StringVar(value=c.ui_density)
        self.show_tooltips = tk.BooleanVar(value=c.show_tooltips)
        self.confirm_actions = tk.BooleanVar(value=c.confirm_actions)
        self.remember_window = tk.BooleanVar(value=c.remember_window)
        self.remember_last_tab = tk.BooleanVar(value=c.remember_last_tab)
        self.performance_profile = tk.StringVar(value=c.performance_profile)
        self.process_priority = tk.StringVar(value=c.process_priority)
        self.memory_saver = tk.BooleanVar(value=c.memory_saver)
        self.max_parallel_pdfs = tk.IntVar(value=c.max_parallel_pdfs)
        self.gpu_only_if_faster = tk.BooleanVar(value=c.gpu_only_if_faster)
        self.gpu_fallback_cpu = tk.BooleanVar(value=c.gpu_fallback_cpu)
        self.clear_cache_on_exit = tk.BooleanVar(value=c.clear_cache_on_exit)
        self.log_level = tk.StringVar(value=c.log_level)
        self.auto_save_log = tk.BooleanVar(value=c.auto_save_log)
        self.log_retention_days = tk.IntVar(value=c.log_retention_days)
        self.remember_last_folder = tk.BooleanVar(value=c.remember_last_folder)
        self.last_input_dir = tk.StringVar(value=c.last_input_dir)
        self.preview_quality = tk.StringVar(value=c.preview_quality)
        self.preview_batch_pages = tk.IntVar(value=c.preview_batch_pages)
        self.preview_cache = tk.BooleanVar(value=c.preview_cache)
        self.preview_maximized = tk.BooleanVar(value=c.preview_maximized)
        self.preview_thumb_width = tk.IntVar(value=c.preview_thumb_width)
        self.auto_process_added = tk.BooleanVar(value=c.auto_process_added)
        self.skip_existing = tk.BooleanVar(value=c.skip_existing)
        self.detect_duplicates = tk.BooleanVar(value=c.detect_duplicates)
        self.resume_processing = tk.BooleanVar(value=c.resume_processing)
        self.silent_mode = tk.BooleanVar(value=c.silent_mode)
        self.theme.trace_add("write", lambda *_: (hasattr(self, "style") and self.apply_theme(), self.save_current_config()))
        self.font_size.trace_add("write", lambda *_: (hasattr(self, "style") and self.apply_theme(), self.save_current_config()))
        self.ui_density.trace_add("write", lambda *_: (hasattr(self, "style") and self.apply_theme(), self.save_current_config()))
        self.counter = tk.StringVar(value="0 arquivo(s)")
        self.status = tk.StringVar(value="Pronto")
        self.xteink_files: list[Path] = []
        self.xteink_counter = tk.StringVar(value="0 item(ns)")
        self.xteink_status = tk.StringVar(value="Pronto")

    def setup_window(self) -> None:
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1360x880")
        self.root.minsize(1180, 760)
        try:
            ico = resource_path("app_icon.ico")
            if ico.exists():
                self.root.iconbitmap(str(ico))
        except Exception as exc:
            write_log(f"Ícone não aplicado: {exc}")

    def build(self) -> None:
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self.shell = ttk.Frame(self.root, style="App.TFrame", padding=0)
        self.shell.pack(fill="both", expand=True)
        self.header = ttk.Frame(self.shell, style="Header.TFrame", padding=(14, 12))
        self.header.pack(fill="x", padx=0, pady=(0, 12))
        ttk.Label(self.header, text="CUMA", style="Title.TLabel").pack(side="left")
        ttk.Button(self.header, text="Manual", command=lambda: open_path(ensure_manual()), style="Header.TButton").pack(side="right", padx=(8, 12))
        ttk.Button(self.header, text="Log", command=lambda: open_path(log_path()), style="Header.TButton").pack(side="right", padx=(8, 0))
        self.content = ttk.Frame(self.shell, style="App.TFrame", padding=(14, 0, 14, 14))
        self.content.pack(fill="both", expand=True)
        nb = ttk.Notebook(self.content)
        nb.pack(fill="both", expand=True)
        self.tab_files = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_tools = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_xteink = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_results = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.notebook = nb
        self.tab_log = ttk.Frame(nb, padding=12, style="Card.TFrame")
        self.tab_config = ttk.Frame(nb, padding=12, style="Card.TFrame")
        for tab, name in ((self.tab_files, "Limpar PDF"), (self.tab_tools, "Ferramentas"), (self.tab_xteink, "XTEINK"), (self.tab_results, "Resultados"), (self.tab_log, "Registros"), (self.tab_config, "Configurações")):
            nb.add(tab, text=name)
        self.build_files_tab()
        self.build_tools_tab()
        self.build_xteink_tab()
        self.build_results_tab()
        self.build_log_tab()
        self.build_config_tab()
        nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        if self.cfg.remember_last_tab:
            self.select_last_tab()

    def build_files_tab(self) -> None:
        self.drop = ttk.Label(self.tab_files, text="Arraste PDFs ou pastas aqui", style="Drop.TLabel", anchor="center", padding=18)
        self.drop.pack(fill="x")
        b = ttk.Frame(self.tab_files, style="Card.TFrame")
        b.pack(fill="x", pady=10)
        for text, cmd, style in (("Adicionar PDF(s)", self.add_files, "Ghost.TButton"), ("Adicionar pasta", self.add_folder, "Ghost.TButton"), ("Colar caminho", self.paste_paths, "Ghost.TButton"), ("Remover", self.remove_selected, "Ghost.TButton"), ("Limpar lista", self.clear_files, "Ghost.TButton"), ("Prévia", self.open_preview_window, "Accent.TButton"), ("Configurações do PDF", self.open_pdf_settings_window, "Ghost.TButton")):
            btn = ttk.Button(b, text=text, command=cmd, style=style)
            btn.pack(side="left", padx=4)
            if text == "Configurações do PDF":
                self.pdf_settings_btn = btn
        ttk.Checkbutton(b, text="Incluir subpastas", variable=self.include_subfolders, command=self.save_current_config).pack(side="left", padx=10)
        output_box = ttk.LabelFrame(self.tab_files, text="Saída e organização", padding=12, style="Card.TLabelframe")
        output_box.pack(fill="x", pady=(0, 10))
        ttk.Label(output_box, text="Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.", style="Muted.TLabel", wraplength=1080, justify="left").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        ttk.Label(output_box, text="Pasta de saída", style="Muted.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        out_ent = ttk.Entry(output_box, textvariable=self.output_dir, width=58)
        out_ent.grid(row=1, column=1, sticky="ew", pady=4)
        out_ent.bind("<FocusOut>", lambda _e: self.save_current_config(force=True))
        ttk.Button(output_box, text="Escolher", command=self.choose_output, style="Ghost.TButton").grid(row=1, column=2, sticky="w", padx=8)
        ttk.Label(output_box, text="Sufixo", style="Muted.TLabel").grid(row=1, column=3, sticky="w", padx=(18, 8))
        suff_ent = ttk.Entry(output_box, textvariable=self.suffix, width=18)
        suff_ent.grid(row=1, column=4, sticky="w", pady=4)
        suff_ent.bind("<FocusOut>", lambda _e: self.save_current_config(force=True))
        ttk.Label(output_box, text="Formato de exportação", style="Muted.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        exp_cb = ttk.Combobox(output_box, textvariable=self.export_format, values=EXPORT_FORMATS, state="readonly", width=24)
        exp_cb.grid(row=2, column=1, sticky="w", pady=4)
        exp_cb.bind("<<ComboboxSelected>>", lambda _e: self.save_current_config(force=True))
        ttk.Label(output_box, text="Intervalo de páginas", style="Muted.TLabel").grid(row=2, column=3, sticky="w", padx=(18, 8), pady=4)
        range_ent = ttk.Entry(output_box, textvariable=self.ranges, width=18)
        range_ent.grid(row=2, column=4, sticky="w", pady=4)
        range_ent.bind("<FocusOut>", lambda _e: self.save_current_config(force=True))
        ttk.Checkbutton(output_box, text="Abrir resultado ao concluir", variable=self.open_after, command=self.save_current_config).grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
        output_box.columnconfigure(1, weight=1)
        cols = ("arquivo", "status", "modo", "paginas", "removidas", "saida", "resumo")
        tree_frame = ttk.Frame(self.tab_files, style="Card.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7)
        tree_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_y.set)
        for col, width in zip(cols, (280, 90, 70, 90, 80, 410, 230)):
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        tree_y.pack(side="right", fill="y")
        bottom = ttk.Frame(self.tab_files, style="Card.TFrame")
        bottom.pack(fill="x", pady=10)
        ttk.Label(bottom, textvariable=self.counter, style="Muted.TLabel").pack(side="left")
        self.cancel_btn = ttk.Button(bottom, text="Cancelar", command=self.cancel, state="disabled", style="Danger.TButton")
        self.cancel_btn.pack(side="right", padx=4)
        self.pause_btn = ttk.Button(bottom, text="Pause", command=self.pause_processing, state="disabled", style="Ghost.TButton")
        self.pause_btn.pack(side="right", padx=4)
        self.play_btn = ttk.Button(bottom, text="Play", command=self.resume_processing, state="disabled", style="Ghost.TButton")
        self.play_btn.pack(side="right", padx=4)
        ttk.Button(bottom, text="Processar selecionados", command=self.process_selected, style="Ghost.TButton").pack(side="right", padx=4)
        ttk.Button(bottom, text="Processar tudo", command=self.process_all, style="Accent.TButton").pack(side="right", padx=4)
        p = ttk.Frame(self.tab_files, style="Card.TFrame")
        p.pack(fill="x")
        ttk.Label(p, text="Geral", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.total_prog = ttk.Progressbar(p, mode="determinate")
        self.total_prog.grid(row=0, column=1, sticky="ew", padx=8, pady=3)
        ttk.Label(p, text="PDF atual", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        self.current_prog = ttk.Progressbar(p, mode="determinate")
        self.current_prog.grid(row=1, column=1, sticky="ew", padx=8, pady=3)
        p.columnconfigure(1, weight=1)
        ttk.Label(self.tab_files, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))

    def build_preview_tab(self) -> None:
        ttk.Button(self.tab_preview, text="Carregar prévia do selecionado", command=self.load_preview, style="Ghost.TButton").pack(anchor="w")
        self.canvas = tk.Canvas(self.tab_preview, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, pady=10)
        sb = ttk.Scrollbar(self.tab_preview, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.prev_frame = ttk.Frame(self.canvas, style="Card.TFrame")
        self.canvas.create_window((0, 0), window=self.prev_frame, anchor="nw")
        self.prev_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def build_tools_tab(self) -> None:
        ttk.Label(self.tab_tools, text="", style="TitleSmall.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Button(self.tab_tools, text="Extrair páginas dos PDFs selecionados como imagens", command=self.extract_selected_to_images, style="Ghost.TButton").pack(anchor="w", pady=6)
        ttk.Button(self.tab_tools, text="Criar PDF a partir de várias imagens", command=self.create_pdf_from_images_dialog, style="Ghost.TButton").pack(anchor="w", pady=6)

    def build_xteink_tab(self) -> None:
        self.xteink_files: list[Path] = []
        self.xteink_input = tk.StringVar(value="")
        self.xteink_output_dir = tk.StringVar(value=self.output_dir.get())
        self.xteink_status = tk.StringVar(value="XTEINK pronto")
        self.xteink_counter = tk.StringVar(value="Arquivos: 0 | OK: 0 | Erros: 0")
        self.xteink_pdf_epub = tk.BooleanVar(value=False)
        self.xteink_pdf_xtch = tk.BooleanVar(value=True)
        self.xteink_epub_xtch = tk.BooleanVar(value=True)

        self.xteink_drop = ttk.Label(self.tab_xteink, text="Arraste PDFs, EPUBs ou pastas aqui", style="Drop.TLabel", anchor="center", padding=18)
        self.xteink_drop.pack(fill="x")
        top = ttk.Frame(self.tab_xteink, style="Card.TFrame")
        top.pack(fill="x", pady=10)
        for label, cmd, style in (("Adicionar arquivo(s)", self.add_xteink_files, "Ghost.TButton"), ("Adicionar pasta", self.add_xteink_folder, "Ghost.TButton"), ("Colar caminho", self.paste_xteink_paths, "Ghost.TButton"), ("Remover", self.remove_xteink_selected, "Ghost.TButton"), ("Limpar", self.clear_xteink_files, "Ghost.TButton"), ("Prévia", self.open_xteink_preview, "Accent.TButton"), ("Configurações do XTEINK", self.open_xteink_settings_window, "Ghost.TButton")):
            btn = ttk.Button(top, text=label, command=cmd, style=style)
            btn.pack(side="left", padx=4)
            if label == "Configurações do XTEINK":
                self.xteink_settings_btn = btn
        opts = ttk.Frame(self.tab_xteink, style="Card.TFrame")
        opts.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(opts, text="PDF para EPUB", variable=self.xteink_pdf_epub).pack(side="left", padx=6)
        ttk.Checkbutton(opts, text="PDF para XTCH", variable=self.xteink_pdf_xtch).pack(side="left", padx=6)
        ttk.Checkbutton(opts, text="EPUB para XTCH", variable=self.xteink_epub_xtch).pack(side="left", padx=6)

        cols = ("arquivo", "status", "tipo", "saida", "resumo")
        xteink_tree_frame = ttk.Frame(self.tab_xteink, style="Card.TFrame")
        xteink_tree_frame.pack(fill="both", expand=True)
        self.xteink_tree = ttk.Treeview(xteink_tree_frame, columns=cols, show="headings", height=7)
        xteink_tree_y = ttk.Scrollbar(xteink_tree_frame, orient="vertical", command=self.xteink_tree.yview)
        self.xteink_tree.configure(yscrollcommand=xteink_tree_y.set)
        for col, width, title in zip(cols, (330, 110, 80, 500, 300), ("Arquivo", "Status", "Tipo", "Saída", "Resumo")):
            self.xteink_tree.heading(col, text=title)
            self.xteink_tree.column(col, width=width, anchor="w")
        self.xteink_tree.pack(side="left", fill="both", expand=True)
        xteink_tree_y.pack(side="right", fill="y")

        bottom = ttk.Frame(self.tab_xteink, style="Card.TFrame")
        bottom.pack(fill="x", pady=10)
        ttk.Label(bottom, textvariable=self.xteink_counter, style="Muted.TLabel").pack(side="left")
        self.xteink_cancel_btn = ttk.Button(bottom, text="Cancelar", command=self.cancel, state="disabled", style="Danger.TButton")
        self.xteink_cancel_btn.pack(side="right", padx=4)
        self.xteink_pause_btn = ttk.Button(bottom, text="Pause", command=self.pause_processing, state="disabled", style="Ghost.TButton")
        self.xteink_pause_btn.pack(side="right", padx=4)
        self.xteink_play_btn = ttk.Button(bottom, text="Play", command=self.resume_processing, state="disabled", style="Ghost.TButton")
        self.xteink_play_btn.pack(side="right", padx=4)
        ttk.Button(bottom, text="Processar selecionados", command=self.process_xteink_selected, style="Ghost.TButton").pack(side="right", padx=4)
        ttk.Button(bottom, text="Processar tudo", command=self.process_xteink_all, style="Accent.TButton").pack(side="right", padx=4)

        p = ttk.Frame(self.tab_xteink, style="Card.TFrame")
        p.pack(fill="x")
        ttk.Label(p, text="Geral", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.xteink_total_prog = ttk.Progressbar(p, mode="determinate")
        self.xteink_total_prog.grid(row=0, column=1, sticky="ew", padx=8, pady=3)
        ttk.Label(p, text="Arquivo atual", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
        self.xteink_current_prog = ttk.Progressbar(p, mode="determinate")
        self.xteink_current_prog.grid(row=1, column=1, sticky="ew", padx=8, pady=3)
        p.columnconfigure(1, weight=1)
        ttk.Label(self.tab_xteink, textvariable=self.xteink_status, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
    def build_results_tab(self) -> None:
        cols = ("arquivo", "status", "saida", "extras", "erro")
        self.result_tree = ttk.Treeview(self.tab_results, columns=cols, show="headings", height=20)
        for col, width in zip(cols, (280, 90, 360, 430, 220)):
            self.result_tree.heading(col, text=col.capitalize())
            self.result_tree.column(col, width=width, anchor="w")
        self.result_tree.pack(fill="both", expand=True)

    def build_log_tab(self) -> None:
        self.log_text = tk.Text(self.tab_log, state="disabled", wrap="word", relief="flat", padx=12, pady=12)
        self.log_text.pack(fill="both", expand=True)

    def place_window_near_widget(self, top: tk.Toplevel, widget=None, width: int = 820, height: int = 640, min_width: int = 640, min_height: int = 420) -> None:
        """Redimensiona e posiciona uma janela perto do botão que abriu a janela."""
        top.update_idletasks()
        screen_w = max(800, self.root.winfo_screenwidth())
        screen_h = max(600, self.root.winfo_screenheight())
        req_w = max(width, min_width, top.winfo_reqwidth() + 36)
        req_h = max(height, min_height, top.winfo_reqheight() + 36)
        req_w = min(req_w, max(min_width, screen_w - 80))
        req_h = min(req_h, max(min_height, screen_h - 100))
        if widget is not None:
            try:
                x = widget.winfo_rootx()
                y = widget.winfo_rooty() + widget.winfo_height() + 8
            except Exception:
                x, y = self.root.winfo_pointerxy()
        else:
            x, y = self.root.winfo_pointerxy()
        if x + req_w > screen_w - 20:
            x = max(20, screen_w - req_w - 20)
        if y + req_h > screen_h - 40:
            y = max(20, y - req_h - 48)
        top.geometry(f"{int(req_w)}x{int(req_h)}+{int(x)}+{int(y)}")
        top.minsize(min_width, min_height)
        top.resizable(True, True)

    def build_config_tab(self) -> None:
        palette = PALETTES[self.theme.get()]
        canvas = tk.Canvas(self.tab_config, highlightthickness=0, bg=palette["bg"], bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(self.tab_config, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        wrap = ttk.Frame(canvas, style="Card.TFrame")
        canvas_window = canvas.create_window((0, 0), window=wrap, anchor="nw")
        wrap.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(canvas_window, width=e.width))
        def _wheel(event) -> None:
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_wheel(_event=None) -> None:
            canvas.bind_all("<MouseWheel>", _wheel); canvas.bind_all("<Button-4>", _wheel); canvas.bind_all("<Button-5>", _wheel)
        def _unbind_wheel(_event=None) -> None:
            canvas.unbind_all("<MouseWheel>"); canvas.unbind_all("<Button-4>"); canvas.unbind_all("<Button-5>")
        canvas.bind("<Enter>", _bind_wheel); canvas.bind("<Leave>", _unbind_wheel); wrap.bind("<Enter>", _bind_wheel); wrap.bind("<Leave>", _unbind_wheel)
        def combo(parent, row, label, var, values, width=22):
            ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly", width=width)
            cb.grid(row=row, column=1, sticky="w", pady=5); cb.bind("<<ComboboxSelected>>", lambda _e: self.save_current_config())
        def spin(parent, row, label, var, to, hint=""):
            ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            ttk.Spinbox(parent, from_=0, to=to, textvariable=var, width=8, command=self.save_current_config).grid(row=row, column=1, sticky="w", pady=5)
            if hint: ttk.Label(parent, text=hint, style="Muted.TLabel").grid(row=row, column=2, sticky="w", pady=5, padx=(10, 0))
        appearance = ttk.LabelFrame(wrap, text="Aparência e interface", padding=12, style="Card.TLabelframe"); appearance.pack(fill="x", pady=(0, 10))
        ttk.Checkbutton(appearance, text="Salvar automaticamente alterações nas configurações", variable=self.auto_save_config, command=lambda: self.save_current_config(force=True)).grid(row=0, column=0, columnspan=3, sticky="w", pady=4)
        combo(appearance, 1, "Tema", self.theme, THEMES, 28); combo(appearance, 2, "Tamanho da fonte", self.font_size, FONT_SIZES, 18); combo(appearance, 3, "Densidade da interface", self.ui_density, UI_DENSITIES, 18)
        ttk.Checkbutton(appearance, text="Mostrar dicas/tooltips", variable=self.show_tooltips, command=self.save_current_config).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(appearance, text="Confirmar antes de ações perigosas", variable=self.confirm_actions, command=self.save_current_config).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(appearance, text="Lembrar tamanho/posição da janela", variable=self.remember_window, command=self.save_current_config).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(appearance, text="Lembrar última aba aberta", variable=self.remember_last_tab, command=self.save_current_config).grid(row=7, column=0, columnspan=2, sticky="w", pady=4)
        perf = ttk.LabelFrame(wrap, text="Desempenho, CPU/GPU e cache", padding=12, style="Card.TLabelframe"); perf.pack(fill="x", pady=(0, 10))
        combo(perf, 0, "Perfil de desempenho", self.performance_profile, PERFORMANCE_PROFILES, 22); combo(perf, 1, "Uso de CPU/GPU", self.hardware_mode, HARDWARE_MODES, 22)
        ttk.Label(perf, text="Automático: NVIDIA CUDA → AMD OpenCL → Intel OpenCL → OpenCL genérico → CPU.", style="Muted.TLabel").grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 6))
        spin(perf, 3, "Threads", self.worker_threads, 64, "0 = automático"); spin(perf, 4, "PDFs paralelos", self.max_parallel_pdfs, 64, "0 = automático"); combo(perf, 5, "Prioridade do processo", self.process_priority, PROCESS_PRIORITIES, 18)
        for r, (txt, var) in enumerate((("Modo economia de memória", self.memory_saver), ("Usar GPU só se for mais rápida", self.gpu_only_if_faster), ("Fallback automático para CPU se GPU falhar", self.gpu_fallback_cpu), ("Ativar cache de análise de páginas", self.enable_page_cache)), start=6):
            ttk.Checkbutton(perf, text=txt, variable=var, command=self.save_current_config).grid(row=r, column=0, columnspan=2, sticky="w", pady=4)
        spin(perf, 10, "Limite cache (MB)", self.page_cache_mb, 4096, "0 desativa limite prático")
        ttk.Checkbutton(perf, text="Limpar cache ao fechar", variable=self.clear_cache_on_exit, command=self.save_current_config).grid(row=11, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(perf, text="Testar aceleração", command=self.show_gpu_status, style="Ghost.TButton").grid(row=12, column=0, sticky="w", pady=(8, 0)); ttk.Button(perf, text="Benchmark CPU/GPU", command=self.run_gpu_benchmark, style="Ghost.TButton").grid(row=12, column=1, sticky="w", pady=(8, 0))
        files = ttk.LabelFrame(wrap, text="Arquivos, segurança e automação", padding=12, style="Card.TLabelframe"); files.pack(fill="x", pady=(0, 10))
        for row, (txt, var) in enumerate((("Lembrar última pasta aberta", self.remember_last_folder), ("Pular arquivos já processados", self.skip_existing), ("Detectar PDFs duplicados na lista", self.detect_duplicates), ("Continuar de onde parou quando possível", self.resume_processing), ("Processar automaticamente ao adicionar arquivos", self.auto_process_added), ("Modo silencioso", self.silent_mode))):
            ttk.Checkbutton(files, text=txt, variable=var, command=self.save_current_config).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        logs = ttk.LabelFrame(wrap, text="Logs e diagnóstico", padding=12, style="Card.TLabelframe"); logs.pack(fill="x", pady=(0, 10))
        combo(logs, 0, "Nível de log", self.log_level, LOG_LEVELS, 18); ttk.Checkbutton(logs, text="Salvar log automaticamente", variable=self.auto_save_log, command=self.save_current_config).grid(row=1, column=0, columnspan=2, sticky="w", pady=4); spin(logs, 2, "Limpar logs após dias", self.log_retention_days, 3650, "0 = nunca")
        ttk.Button(logs, text="Abrir log", command=lambda: open_path(log_path()), style="Ghost.TButton").grid(row=3, column=0, sticky="w", pady=(8, 0)); ttk.Button(logs, text="Copiar diagnóstico", command=self.copy_diagnostics, style="Ghost.TButton").grid(row=3, column=1, sticky="w", pady=(8, 0))
        preview = ttk.LabelFrame(wrap, text="Prévia e visualização", padding=12, style="Card.TLabelframe"); preview.pack(fill="x", pady=(0, 10))
        combo(preview, 0, "Qualidade da prévia", self.preview_quality, PREVIEW_QUALITIES, 18); spin(preview, 1, "Páginas por lote", self.preview_batch_pages, 100, "Carregamento incremental"); spin(preview, 2, "Largura miniatura", self.preview_thumb_width, 1600, "320 a 1600 px")
        ttk.Checkbutton(preview, text="Usar cache na prévia", variable=self.preview_cache, command=self.save_current_config).grid(row=3, column=0, columnspan=2, sticky="w", pady=4); ttk.Checkbutton(preview, text="Abrir prévia maximizada", variable=self.preview_maximized, command=self.save_current_config).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Button(wrap, text="Salvar configurações", command=lambda: self.save_current_config(force=True), style="Accent.TButton").pack(anchor="w", pady=(4, 12))

    def open_pdf_settings_window(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("Configurações do PDF")
        wrapper = ttk.Frame(top, style="Card.TFrame", padding=14)
        wrapper.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(wrapper, text="Configurações do PDF", style="TitleSmall.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(wrapper, text="Aqui ficam as opções menos frequentes e mais avançadas, para evitar redundância com a aba Limpar.", style="Muted.TLabel", wraplength=760, justify="left").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))
        rows = [("Modo", ttk.Combobox(wrapper, textvariable=self.mode, values=MODES, state="readonly", width=28)), ("Perfil", ttk.Combobox(wrapper, textvariable=self.profile, values=PROFILES, state="readonly", width=28)), ("Compactação", ttk.Combobox(wrapper, textvariable=self.compression, values=COMPRESSION_OPTIONS, state="readonly", width=36)), ("Senha PDF", ttk.Entry(wrapper, textvariable=self.password, show="*", width=38))]
        for offset, (label, widget) in enumerate(rows, start=2):
            ttk.Label(wrapper, text=label, style="Muted.TLabel").grid(row=offset, column=0, sticky="w", pady=6, padx=(0, 12))
            widget.grid(row=offset, column=1, sticky="w", pady=6)
            if isinstance(widget, ttk.Combobox):
                widget.bind("<<ComboboxSelected>>", lambda _e: self.save_current_config(force=True))
            else:
                widget.bind("<FocusOut>", lambda _e: self.save_current_config(force=True))
        row = 6
        for txt, var in (("Sobrescrever originais", self.overwrite_original), ("Criar backup", self.create_backup), ("Sempre manter primeira página", self.keep_first), ("Salvar PDF com páginas removidas", self.save_removed_pdf), ("Validar PDF final", self.validate_output), ("Pular arquivos já processados", self.skip_existing), ("Detectar duplicidades", self.detect_duplicates), ("Processar automaticamente ao adicionar", self.auto_process_added)):
            ttk.Checkbutton(wrapper, text=txt, variable=var, command=self.save_current_config).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
            row += 1
        ttk.Label(wrapper, text="Manter últimas páginas", style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6)
        ttk.Spinbox(wrapper, from_=0, to=20, textvariable=self.keep_last, width=8, command=self.save_current_config).grid(row=row, column=1, sticky="w", pady=6)
        row += 1
        ttk.Button(wrapper, text="Salvar configurações", command=lambda: self.save_current_config(force=True), style="Accent.TButton").grid(row=row, column=0, sticky="w", pady=12)
        ttk.Button(wrapper, text="Fechar", command=top.destroy, style="Ghost.TButton").grid(row=row, column=1, sticky="w", pady=12)
        self.place_window_near_widget(top, getattr(self, "pdf_settings_btn", None), width=860, height=720, min_width=760, min_height=600)

    def gpu_status_text(self) -> str:
        _ok, note = acceleration_status(); mode = self.hardware_mode.get() if hasattr(self, "hardware_mode") else "Automático"
        return f"Modo: {mode}. Backend atual: {selected_acceleration_backend(mode)}. {note}"

    def show_gpu_status(self) -> None: messagebox.showinfo("Aceleração", self.gpu_status_text())
    def run_gpu_benchmark(self) -> None: messagebox.showinfo("Benchmark CPU/GPU", self.gpu_status_text())
    def copy_diagnostics(self) -> None:
        self.root.clipboard_clear(); self.root.clipboard_append(self.gpu_status_text()); messagebox.showinfo("Diagnóstico", "Diagnóstico copiado.")
    def on_tab_changed(self, _event=None) -> None:
        try:
            if self.remember_last_tab.get(): self.cfg.last_tab = self.notebook.tab(self.notebook.select(), "text"); self.save_current_config()
        except Exception: pass
    def select_last_tab(self) -> None:
        try:
            for tab_id in self.notebook.tabs():
                if self.notebook.tab(tab_id, "text") == self.cfg.last_tab: self.notebook.select(tab_id); break
        except Exception: pass

    def setup_dnd(self) -> None:
        if not DND_AVAILABLE:
            return
        for w in (self.root, self.drop, self.tree):
            try:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", lambda e: self.add_paths(parse_drop(e.data, self.root)))
            except Exception:
                pass
        if hasattr(self, "xteink_drop"):
            for w in (self.xteink_drop, self.xteink_tree):
                try:
                    w.drop_target_register(DND_FILES); w.dnd_bind("<<Drop>>", self.drop_xteink)
                except Exception:
                    pass

    def set_windows_titlebar(self, dark: bool) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            value = ctypes.c_int(1 if dark else 0)
            for attr in (20, 19):
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
                except Exception:
                    pass
        except Exception as exc:
            write_log(f"Não foi possível ajustar titlebar: {exc}")

    def apply_theme(self) -> None:
        p = PALETTES.get(self.theme.get(), PALETTES["Manga Dark"])
        dark = self.theme.get() != "Moderno Claro"
        self.set_windows_titlebar(dark)
        self.root.configure(bg=p["bg"])
        self.root.option_add("*TCombobox*Listbox*Background", p["field"])
        self.root.option_add("*TCombobox*Listbox*Foreground", p["fg"])
        self.root.option_add("*TCombobox*Listbox*selectBackground", p["accent"])
        self.root.option_add("*TCombobox*Listbox*selectForeground", "#ffffff")
        s = self.style
        s.configure(".", background=p["surface"], foreground=p["fg"], fieldbackground=p["field"], bordercolor=p["border"], lightcolor=p["border"], darkcolor=p["border"])
        s.configure("App.TFrame", background=p["bg"])
        s.configure("Card.TFrame", background=p["surface"])
        s.configure("Header.TFrame", background=p["surface"], relief="solid", borderwidth=1)
        s.configure("TLabel", background=p["surface"], foreground=p["fg"])
        s.configure("Title.TLabel", background=p["surface"], foreground=p["fg"], font=("Segoe UI", 18, "bold"))
        s.configure("TitleSmall.TLabel", background=p["surface"], foreground=p["fg"], font=("Segoe UI", 13, "bold"))
        s.configure("Muted.TLabel", background=p["surface"], foreground=p["muted"])
        s.configure("Drop.TLabel", background=p["drop"], foreground=p["muted"], relief="solid", borderwidth=1)
        s.configure("TCheckbutton", background=p["surface"], foreground=p["fg"])
        for style, bg, fg, hover in (("Header.TButton", p["surface2"], p["fg"], p["drop"]), ("Ghost.TButton", p["surface2"], p["fg"], p["drop"]), ("Accent.TButton", p["accent"], "#ffffff", p["accent_hover"]), ("Danger.TButton", p["surface2"], p["danger"], p["drop"])):
            s.configure(style, background=bg, foreground=fg, bordercolor=p["border"], padding=(13, 7))
            s.map(style, background=[("active", hover), ("pressed", hover)], foreground=[("active", fg), ("pressed", fg)])
        s.configure("TNotebook", background=p["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=p["surface2"], foreground=p["muted"], bordercolor=p["border"], padding=(16, 9))
        s.map("TNotebook.Tab", background=[("selected", p["surface"]), ("active", p["drop"])], foreground=[("selected", p["fg"]), ("active", p["fg"])])
        s.configure("Treeview", background=p["surface"], foreground=p["fg"], fieldbackground=p["surface"], bordercolor=p["border"], rowheight=28)
        s.configure("Treeview.Heading", background=p["surface2"], foreground=p["fg"], bordercolor=p["border"], font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", p["selection"])], foreground=[("selected", "#ffffff" if dark else p["fg"])])
        s.configure("TEntry", fieldbackground=p["field"], foreground=p["fg"], insertcolor=p["fg"], bordercolor=p["border"], padding=5)
        s.configure("TCombobox", fieldbackground=p["field"], background=p["surface2"], foreground=p["fg"], selectbackground=p["field"], selectforeground=p["fg"], bordercolor=p["border"], arrowcolor=p["fg"], padding=5)
        s.map("TCombobox", fieldbackground=[("readonly", p["field"]), ("!disabled", p["field"])], foreground=[("readonly", p["fg"]), ("!disabled", p["fg"])])
        s.configure("Horizontal.TProgressbar", background=p["accent"], troughcolor=p["surface2"], bordercolor=p["border"])
        if hasattr(self, "canvas"):
            self.canvas.configure(bg=p["surface"])
        if hasattr(self, "log_text"):
            self.log_text.configure(bg=p["field"], fg=p["fg"], insertbackground=p["fg"], selectbackground=p["selection"], selectforeground="#ffffff" if dark else p["fg"])
        if hasattr(self, "tree"):
            self.tree.tag_configure("ok", foreground=p["success"])
            self.tree.tag_configure("erro", foreground=p["danger"])

    def safe_int(self, var: tk.Variable, default: int = 0) -> int:
        try: return int(var.get())
        except Exception: return default

    def save_current_config(self, force: bool = False) -> None:
        if not force and hasattr(self, "auto_save_config") and not self.auto_save_config.get(): return
        last_geo = self.root.geometry() if hasattr(self, "root") and self.remember_window.get() else self.cfg.last_window_geometry
        last_tab = self.cfg.last_tab
        try:
            if hasattr(self, "notebook") and self.remember_last_tab.get(): last_tab = self.notebook.tab(self.notebook.select(), "text")
        except Exception: pass
        self.cfg = CleanerConfig(self.output_dir.get(), self.mode.get(), self.profile.get(), self.compression.get(), self.export_format.get(), self.suffix.get(), self.ranges.get(), self.password.get(), self.keep_first.get(), self.safe_int(self.keep_last, 0), self.overwrite_original.get(), self.create_backup.get(), self.open_after.get(), self.include_subfolders.get(), self.save_removed_pdf.get(), self.validate_output.get(), self.theme.get(), self.xteink_device.get(), self.safe_int(self.xteink_quality, 88), self.xteink_converter_dir.get(), self.hardware_mode.get(), self.safe_int(self.worker_threads, 0), self.enable_page_cache.get(), self.safe_int(self.page_cache_mb, 256), self.auto_save_config.get(), self.font_size.get(), self.ui_density.get(), self.show_tooltips.get(), self.confirm_actions.get(), self.remember_window.get(), last_geo, self.remember_last_tab.get(), last_tab, self.performance_profile.get(), self.process_priority.get(), self.memory_saver.get(), self.safe_int(self.max_parallel_pdfs, 0), self.gpu_only_if_faster.get(), self.gpu_fallback_cpu.get(), self.clear_cache_on_exit.get(), self.log_level.get(), self.auto_save_log.get(), self.safe_int(self.log_retention_days, 30), self.remember_last_folder.get(), self.last_input_dir.get(), self.preview_quality.get(), self.safe_int(self.preview_batch_pages, 10), self.preview_cache.get(), self.preview_maximized.get(), self.safe_int(self.preview_thumb_width, 760), self.auto_process_added.get(), self.skip_existing.get(), self.detect_duplicates.get(), self.resume_processing.get(), self.silent_mode.get())
        save_config(self.cfg)

    def on_close(self) -> None:
        try: self.save_current_config(force=True)
        finally: self.root.destroy()

    def log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", str(msg) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        write_log(str(msg))

    def add_files(self) -> None:
        self.add_paths(filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")]))

    def add_folder(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.add_paths([folder])

    def paste_paths(self) -> None:
        try:
            self.add_paths(parse_drop(self.root.clipboard_get(), self.root))
        except tk.TclError:
            messagebox.showinfo("Colar", "Área de transferência vazia.")

    def add_paths(self, paths: Iterable[str | Path]) -> None:
        added = 0
        existing = {_cuma_11008_path_key(p) for p in self.files}
        expanded: list[Path] = []
        for raw in paths:
            p = Path(str(raw).strip()).expanduser()
            if p.is_dir():
                expanded.extend(sorted(p.glob("**/*.pdf" if self.include_subfolders.get() else "*.pdf")))
            else:
                expanded.append(p)
        for p in expanded:
            if not p.exists() or p.suffix.lower() != ".pdf":
                continue
            key = _cuma_11008_path_key(p)
            if key in existing:
                continue
            existing.add(key)
            self.files.append(p.resolve())
            self.tree.insert("", "end", iid=key, values=(p.name, "Aguardando", "", "", "", "", ""))
            added += 1
        self.update_counter()
        self.log(f"{added} PDF(s) adicionado(s).")

    def selected_paths(self) -> list[Path]:
        selected = set(self.tree.selection())
        return [p for p in self.files if _cuma_11008_path_key(p) in selected]

    def remove_selected(self) -> None:
        selected = set(self.tree.selection())
        self.files = [p for p in self.files if _cuma_11008_path_key(p) not in selected]
        for iid in selected:
            if self.tree.exists(iid):
                self.tree.delete(iid)
        self.update_counter()

    def clear_files(self) -> None:
        self.files.clear()
        self.results.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for iid in self.result_tree.get_children():
            self.result_tree.delete(iid)
        self.update_counter()

    def choose_output(self) -> None:
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)
            self.save_current_config()

    def choose_xteink_converter(self) -> None:
        folder = filedialog.askdirectory(title="Selecione a pasta do repositório conversor antigo/epub-to-xtc-converter")
        if folder:
            self.xteink_converter_dir.set(folder)
            self.save_current_config()

    def update_counter(self) -> None:
        ok = sum(1 for r in self.results if r.status == "OK")
        err = sum(1 for r in self.results if r.status == "ERRO")
        self.counter.set(f"Arquivos: {len(self.files)} | OK: {ok} | Erros: {err}")

    def open_preview_window(self) -> None:
        selected = self.selected_paths()
        if not selected:
            messagebox.showinfo("Prévia", "Selecione um PDF na lista da aba Limpar PDF.")
            return
        PreviewWindow(self, selected[0])
    def load_preview(self) -> None:
        selected = self.selected_paths()
        if not selected:
            messagebox.showinfo("Prévia", "Selecione um PDF.")
            return
        for w in self.prev_frame.winfo_children():
            w.destroy()
        self.preview_images.clear()
        cleaner = PDFCleaner(self.current_config())
        try:
            doc = cleaner.open_pdf(selected[0])
            total = min(len(doc), 80)
            for page_no in range(1, total + 1):
                pix = doc[page_no - 1].get_pixmap(matrix=fitz.Matrix(0.25, 0.25), alpha=False)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                image.thumbnail((170, 230))
                photo = ImageTk.PhotoImage(image)
                self.preview_images.append(photo)
                frame = ttk.Frame(self.prev_frame, style="Card.TFrame", padding=6)
                frame.grid(row=(page_no - 1) // 5, column=(page_no - 1) % 5, padx=6, pady=6)
                ttk.Label(frame, image=photo).pack()
                ttk.Label(frame, text=f"Página {page_no}", style="Muted.TLabel").pack()
            doc.close()
        except Exception as exc:
            messagebox.showerror("Erro", friendly_error(exc))

    def current_config(self) -> CleanerConfig:
        self.save_current_config(force=True)
        return self.cfg

    def pause_processing(self) -> None:
        self.pause_event.clear()
        self.status.set("Pausado")
        if hasattr(self, "xteink_status"): self.xteink_status.set("Pausado")
        self.log("Processamento pausado.")

    def resume_processing(self) -> None:
        self.pause_event.set()
        self.status.set("Processando...")
        if hasattr(self, "xteink_status"): self.xteink_status.set("Processando...")
        self.log("Processamento retomado.")
    def process_selected(self) -> None:
        self.start_processing(self.selected_paths())

    def process_all(self) -> None:
        self.start_processing(list(self.files))

    def cancel(self) -> None:
        self.cancel_requested = True
        self.log("Cancelamento solicitado.")

    def start_processing(self, paths: list[Path]) -> None:
        if self.processing:
            return
        if not paths:
            messagebox.showwarning("Atenção", "Adicione ou selecione PDFs.")
            return
        cfg = self.current_config()
        if cfg.overwrite_original and cfg.confirm_actions and not messagebox.askyesno("Confirmar", "Sobrescrever originais?"):
            return
        Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)
        self.processing = True
        self.cancel_requested = False
        self.results.clear()
        self._converter_auto_queue_count = 0
        self._converter_auto_queue_items = []
        self._converter_auto_queue_iids = []
        self.total_prog["maximum"] = len(paths)
        self.total_prog["value"] = 0
        self.current_prog["value"] = 0
        self.pause_event.set()
        self.cancel_btn.configure(state="normal")
        if hasattr(self, "pause_btn"):
            self.pause_btn.configure(state="normal")
        if hasattr(self, "play_btn"):
            self.play_btn.configure(state="normal")
        self.status.set(f"Processando 0/{len(paths)}...")
        self.log(f"Processamento iniciado: {len(paths)} arquivo(s). Threads: {resolve_worker_threads(cfg, len(paths))}. CPU/GPU: {cfg.hardware_mode}. Backend: {selected_acceleration_backend(cfg.hardware_mode)}.")
        for iid in self.result_tree.get_children():
            self.result_tree.delete(iid)
        threading.Thread(target=self.worker, args=(paths, cfg), daemon=True).start()

    def worker(self, paths: list[Path], cfg: CleanerConfig) -> None:
        cleaner = PDFCleaner(cfg)
        report_dir = Path(cfg.output_dir)
        for index, pdf in enumerate(paths, 1):
            if self.cancel_requested:
                break
            while not self.pause_event.is_set() and not self.cancel_requested:
                time.sleep(0.1)
            iid = _cuma_11008_path_key(pdf)
            self.q.put(("tree", (iid, pdf.name, "Processando", "", "", "", "", "", "")))
            try:
                if cfg.overwrite_original:
                    output = pdf
                    backup = str(create_backup(pdf)) if cfg.create_backup else ""
                    report_dir = pdf.parent
                else:
                    output = unique_path(Path(cfg.output_dir) / f"{pdf.stem}{cfg.suffix or '_limpo'}.pdf")
                    backup = ""
                def prog(done: int, total: int) -> None:
                    while not self.pause_event.is_set() and not self.cancel_requested:
                        time.sleep(0.1)
                    self.q.put(("current", int(done / total * 100) if total else 0))
                result = cleaner.clean(pdf, output, progress=prog, cancel=lambda: self.cancel_requested)
                result.backup = backup
                self.results.append(result)
                pages = f"{result.original_pages} → {result.final_pages}"
                summary = f"{format_bytes(result.original_size)} → {format_bytes(result.final_size)} ({format_bytes(result.saved_bytes)})"
                self.q.put(("tree", (iid, pdf.name, "OK", result.mode, pages, str(result.removed_pages), result.output, summary, "ok")))
                self.q.put(("result", result))
                self.q.put(("log", f"OK: {pdf.name}"))
                if getattr(result, 'output', None):
                    self.q.put(("converter_queue", result.output))
            except Exception as exc:
                err = friendly_error(exc)
                result = Result(source=str(pdf), status="ERRO", error=err)
                self.results.append(result)
                self.q.put(("tree", (iid, pdf.name, "ERRO", "", "", "", "", err, "erro")))
                self.q.put(("result", result))
                self.q.put(("log", f"ERRO em {pdf.name}: {err}"))
                write_log(traceback.format_exc())
            self.q.put(("total", index))
            self.q.put(("counter", None))
        reports: list[Path] = []
        self.q.put(("done", (reports, report_dir)))

    def poll(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "tree":
                    iid, name, status, mode, pages, removed, out, summary, tag = payload
                    if self.tree.exists(iid):
                        self.tree.item(iid, values=(name, status, mode, pages, removed, out, summary), tags=(tag,))
                elif kind == "result":
                    r = payload
                    self.result_tree.insert("", "end", values=(Path(r.source).name, r.status, r.output, r.extra_outputs, r.error))
                elif kind == "current":
                    self.current_prog["value"] = payload
                elif kind == "total":
                    self.total_prog["value"] = payload
                    self.status.set(f"Processando {payload}/{int(float(self.total_prog['maximum'] or 0))}...")
                elif kind == "counter":
                    self.update_counter()
                elif kind == "converter_queue":
                    try:
                        candidate = Path(payload)
                        added = False
                        if candidate.exists() and candidate.suffix.lower() == '.pdf' and hasattr(self, 'add_xteink_path'):
                            added = self.add_xteink_path(candidate)
                        if added:
                            iid = _cuma_11008_path_key(candidate)
                            self._converter_auto_queue_count = int(getattr(self, '_converter_auto_queue_count', 0)) + 1
                            self._converter_auto_queue_items = list(getattr(self, '_converter_auto_queue_items', [])) + [candidate.name]
                            self._converter_auto_queue_iids = list(getattr(self, '_converter_auto_queue_iids', [])) + [iid]
                            if hasattr(self, 'xteink_status'):
                                self.xteink_status.set(f"Converter preparado com {self._converter_auto_queue_count} PDF(s) vindo(s) de Limpar")
                            self.log(f"Limpar → Converter: {candidate.name} adicionado automaticamente à fila de conversão.")
                            if hasattr(self, 'refresh_dashboard'):
                                self.refresh_dashboard()
                    except Exception as exc:
                        self.log(f"Aviso ao enviar PDF para Converter: {friendly_error(exc)}")
                elif kind == "done":
                    _reports, _report_dir = payload
                    self.processing = False
                    self.cancel_btn.configure(state="disabled")
                    if hasattr(self, "pause_btn"):
                        self.pause_btn.configure(state="disabled")
                    if hasattr(self, "play_btn"):
                        self.play_btn.configure(state="disabled")
                    self.update_counter()
                    auto_iids = [iid for iid in dict.fromkeys(getattr(self, '_converter_auto_queue_iids', [])) if hasattr(self, 'xteink_tree') and self.xteink_tree.exists(iid)]
                    auto_count = len(auto_iids)
                    if auto_count and hasattr(self, 'show_page') and hasattr(self, 'xteink_tree'):
                        self.status.set("Arquivos processados e enviados para Converter.")
                        try:
                            self.show_page('Converter', save_state=True)
                        except TypeError:
                            self.show_page('Converter')
                        try:
                            current_selection = self.xteink_tree.selection()
                            if current_selection:
                                self.xteink_tree.selection_remove(*current_selection)
                        except Exception:
                            pass
                        try:
                            self.xteink_tree.selection_set(auto_iids)
                        except Exception:
                            for iid in auto_iids:
                                try:
                                    self.xteink_tree.selection_add(iid)
                                except Exception:
                                    pass
                        if auto_iids:
                            try:
                                self.xteink_tree.focus(auto_iids[0])
                                self.xteink_tree.see(auto_iids[0])
                            except Exception:
                                pass
                        if hasattr(self, 'xteink_status'):
                            self.xteink_status.set(f"{auto_count} arquivo(s) vindo(s) de Limpar selecionado(s) em Converter")
                    else:
                        self.status.set("Finalizado.")
        except queue.Empty:
            pass
        except Exception as exc:
            write_log(f"Erro no loop: {exc}")
        self.root.after(150, self.poll)

    def extract_selected_to_images(self) -> None:
        paths = self.selected_paths()
        if not paths:
            messagebox.showinfo("Extrair imagens", "Selecione PDFs na aba Limpar PDF.")
            return
        out = filedialog.askdirectory(title="Escolha a pasta para salvar as imagens")
        if not out:
            return
        use_png = messagebox.askyesno("Formato", "Sim = PNG / Não = JPG")
        fmt = "PNG" if use_png else "JPEG"
        ext = "png" if use_png else "jpg"
        try:
            for pdf in paths:
                doc = fitz.open(str(pdf))
                folder = Path(out) / pdf.stem
                folder.mkdir(parents=True, exist_ok=True)
                for i, page in enumerate(doc, 1):
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    im = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    file = folder / f"page_{i:04d}.{ext}"
                    if fmt == "PNG":
                        im.save(file, format="PNG", optimize=True)
                    else:
                        im.save(file, format="JPEG", quality=88, optimize=True)
                doc.close()
                self.log(f"Imagens extraídas: {folder}")
            messagebox.showinfo("Concluído", "Extração de imagens finalizada.")
        except Exception as exc:
            messagebox.showerror("Erro", friendly_error(exc))

    def create_pdf_from_images_dialog(self) -> None:
        files = filedialog.askopenfilenames(title="Selecione imagens", filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("Todos", "*.*")])
        if not files:
            return
        out = filedialog.asksaveasfilename(title="Salvar PDF como", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        try:
            image_paths = [Path(f) for f in files if Path(f).suffix.lower() in SUPPORTED_IMAGE_EXT]
            save_images_to_pdf(image_paths, Path(out))
            self.log(f"PDF criado a partir de imagens: {out}")
            messagebox.showinfo("Concluído", f"PDF criado:\n{out}")
        except Exception as exc:
            messagebox.showerror("Erro", friendly_error(exc))














    def add_xteink_path(self, path: Path) -> bool:
        path = Path(path)
        if path.is_dir():
            added = False
            for f in sorted(path.rglob("*")):
                if f.suffix.lower() in (".pdf", ".epub"):
                    added = self.add_xteink_path(f) or added
            return added
        if path.suffix.lower() not in (".pdf", ".epub") or not path.exists() or path in self.xteink_files:
            return False
        self.xteink_files.append(path)
        iid = _cuma_11008_path_key(path)
        if not self.xteink_tree.exists(iid):
            self.xteink_tree.insert("", "end", iid=iid, values=(path.name, "Aguardando", path.suffix[1:].upper(), "", ""))
        self.xteink_input.set(str(path))
        self.update_xteink_counter()
        return True
    def update_xteink_counter(self) -> None:
        ok = err = 0
        if hasattr(self, "xteink_tree"):
            for iid in self.xteink_tree.get_children():
                status = str(self.xteink_tree.set(iid, "status")).upper()
                if status == "OK": ok += 1
                elif status == "ERRO": err += 1
        if hasattr(self, "xteink_counter"):
            self.xteink_counter.set(f"Arquivos: {len(getattr(self, 'xteink_files', []))} | OK: {ok} | Erros: {err}")
    def add_xteink_files(self) -> None:
        for f in filedialog.askopenfilenames(title="Adicionar PDF/EPUB", filetypes=[("PDF/EPUB", "*.pdf *.epub"), ("PDF", "*.pdf"), ("EPUB", "*.epub"), ("Todos", "*.*")]): self.add_xteink_path(Path(f))
    def add_xteink_folder(self) -> None:
        folder = filedialog.askdirectory(title="Adicionar pasta para XTEINK")
        if folder: self.add_xteink_path(Path(folder))
    def paste_xteink_paths(self) -> None:
        try: raw = self.root.clipboard_get()
        except Exception: raw = ""
        for part in re.split(r"[\n;]+", raw):
            part = part.strip().strip('"')
            if part: self.add_xteink_path(Path(part))
    def remove_xteink_selected(self) -> None:
        for iid in self.xteink_tree.selection():
            self.xteink_tree.delete(iid)
            self.xteink_files = [p for p in self.xteink_files if _cuma_11008_path_key(p) != iid]
        self.update_xteink_counter()
    def clear_xteink_files(self) -> None:
        self.xteink_files.clear()
        for iid in self.xteink_tree.get_children(): self.xteink_tree.delete(iid)
        self.xteink_input.set("")
        self.xteink_total_prog["value"] = 0
        self.xteink_current_prog["value"] = 0
        self.xteink_status.set("XTEINK pronto")
        self.update_xteink_counter()
    def open_xteink_preview(self) -> None:
        selected = self.xteink_tree.selection()
        path = next((p for p in self.xteink_files if selected and _cuma_11008_path_key(p) == selected[0]), self.xteink_files[0] if self.xteink_files else None)
        if not path: messagebox.showwarning("Prévia", "Selecione ou adicione um PDF/EPUB."); return
        if path.suffix.lower() == ".pdf": self.files = [path]; self.open_preview_window()
        else: messagebox.showinfo("Prévia", "Prévia direta está disponível para PDF. EPUB será convertido normalmente.")
    def open_xteink_settings_window(self) -> None:
        top = tk.Toplevel(self.root); top.title("Configurações do XTEINK")
        w = ttk.Frame(top, style="Card.TFrame", padding=14); w.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(w, text="Configurações do XTEINK", style="TitleSmall.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Label(w, text="Dispositivo", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=6); ttk.Combobox(w, textvariable=self.xteink_device, values=XTEINK_DEVICES, state="readonly", width=28).grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(w, text="Qualidade JPEG", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=6); ttk.Spinbox(w, from_=50, to=100, textvariable=self.xteink_quality, width=8).grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(w, text="Pasta de saída", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=6); ttk.Entry(w, textvariable=self.xteink_output_dir, width=62).grid(row=3, column=1, sticky="ew", pady=6); ttk.Button(w, text="Escolher", command=self.choose_xteink_output, style="Ghost.TButton").grid(row=3, column=2, sticky="w", padx=8)
        ttk.Label(w, text="PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.", style="Muted.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 2))
        ttk.Label(w, text="PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.", style="Muted.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(w, text="EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.", style="Muted.TLabel").grid(row=6, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Button(w, text="Salvar configurações", command=self.save_current_config, style="Accent.TButton").grid(row=7, column=0, sticky="w", pady=12); ttk.Button(w, text="Fechar", command=top.destroy, style="Ghost.TButton").grid(row=7, column=1, sticky="w", pady=12)
        self.place_window_near_widget(top, getattr(self, "xteink_settings_btn", None), width=760, height=520, min_width=700, min_height=460)
    def drop_xteink(self, event) -> None:
        for item in parse_drop(event.data, self.root): self.add_xteink_path(Path(item))
    def xteink_selected_paths(self) -> list[Path]:
        selected = set(self.xteink_tree.selection())
        return [p for p in self.xteink_files if not selected or _cuma_11008_path_key(p) in selected]
    def process_xteink_selected(self) -> None:
        self.process_xteink_paths(self.xteink_selected_paths())
    def process_xteink_all(self) -> None:
        self.process_xteink_paths(list(self.xteink_files))
    def process_xteink_paths(self, paths: list[Path]) -> None:
        if not paths:
            messagebox.showwarning("XTEINK", "Adicione ou selecione arquivos PDF/EPUB.")
            return
        self.pause_event.set()
        self.cancel_requested = False
        self._xteink_batch_mode = True
        self._xteink_last_out_dir = None
        self.xteink_total_prog["maximum"] = len(paths)
        self.xteink_total_prog["value"] = 0
        self.xteink_current_prog["value"] = 0
        self.xteink_cancel_btn.configure(state="normal")
        self.xteink_pause_btn.configure(state="normal")
        self.xteink_play_btn.configure(state="normal")
        try:
            for idx, src in enumerate(paths, 1):
                if self.cancel_requested:
                    break
                while not self.pause_event.is_set() and not self.cancel_requested:
                    time.sleep(0.1)
                iid = _cuma_11008_path_key(src)
                self.xteink_input.set(str(src))
                self.xteink_current_prog["value"] = 5
                try:
                    outputs: list[Path] = []
                    if src.suffix.lower() == ".pdf" and self.xteink_pdf_epub.get():
                        self.xteink_tree.set(iid, "status", "PDF→EPUB")
                        self.root.update_idletasks()
                        outputs.append(self.xteink_pdf_to_epub())
                    if src.suffix.lower() == ".pdf" and self.xteink_pdf_xtch.get():
                        self.xteink_tree.set(iid, "status", "PDF→XTCH")
                        self.root.update_idletasks()
                        outputs.append(self.xteink_pdf_to_xtch())
                    if src.suffix.lower() == ".epub" and self.xteink_epub_xtch.get():
                        self.xteink_tree.set(iid, "status", "EPUB→XTCH")
                        self.root.update_idletasks()
                        outputs.append(self.xteink_epub_to_xtch())
                    self.xteink_current_prog["value"] = 100
                    if outputs:
                        self.xteink_tree.set(iid, "status", "OK")
                        self.xteink_tree.set(iid, "saida", str(outputs[-1].parent))
                        self.xteink_tree.set(iid, "resumo", ", ".join(p.suffix.upper().lstrip(".") for p in outputs))
                    else:
                        self.xteink_tree.set(iid, "status", "IGNORADO")
                        self.xteink_tree.set(iid, "resumo", "Nenhuma opção marcada compatível")
                except Exception as exc:
                    self.xteink_tree.set(iid, "status", "ERRO")
                    self.xteink_tree.set(iid, "resumo", friendly_error(exc))
                self.xteink_total_prog["value"] = idx
                self.xteink_status.set(f"XTEINK {idx}/{len(paths)}")
                self.update_xteink_counter()
                self.root.update_idletasks()
        finally:
            self._xteink_batch_mode = False
            self.xteink_cancel_btn.configure(state="disabled")
            self.xteink_pause_btn.configure(state="disabled")
            self.xteink_play_btn.configure(state="disabled")
            self.update_xteink_counter()
            if self.open_after.get() and self._xteink_last_out_dir and not self.cancel_requested:
                open_folder(self._xteink_last_out_dir)
    def choose_xteink_input(self) -> None:
        file = filedialog.askopenfilename(title="Selecione PDF ou EPUB", filetypes=[("PDF/EPUB", "*.pdf *.epub"), ("PDF", "*.pdf"), ("EPUB", "*.epub"), ("Todos", "*.*")])
        if file:
            self.xteink_input.set(file)
            self.add_xteink_path(Path(file))
    def choose_xteink_output(self) -> None:
        folder = filedialog.askdirectory(title="Escolha a pasta de saída")
        if folder:
            self.xteink_output_dir.set(folder)
            self.output_dir.set(folder)
            self.save_current_config()

    def xteink_target(self) -> tuple[int, int]:
        return XTEINK_DEVICE_PROFILES.get(self.xteink_device.get(), XTEINK_DEVICE_PROFILES["XTEINK X4"])

    def xteink_paths(self) -> tuple[Path, Path, tuple[int, int], int]:
        src = Path(self.xteink_input.get().strip())
        if not src.exists():
            raise RuntimeError("Arquivo XTEINK não encontrado.")
        base = Path(self.xteink_output_dir.get().strip() or self.output_dir.get().strip() or src.parent)
        out_dir = base if base.name.lower() == "xteink" else base / "XTEINK"
        out_dir.mkdir(parents=True, exist_ok=True)
        return src, out_dir, self.xteink_target(), int(self.xteink_quality.get())

    def xteink_pdf_to_epub(self) -> Path:
        src, out_dir, target, quality = self.xteink_paths()
        if src.suffix.lower() != ".pdf":
            raise RuntimeError("Selecione um PDF.")
        images = render_pdf_pages_as_images(src, target=target)
        output = unique_path(out_dir / f"{src.stem}_xteink.epub")
        try:
            create_image_epub(images, output, src.stem, quality)
        finally:
            for im in images:
                im.close()
        self._xteink_last_out_dir = out_dir
        if not getattr(self, "_xteink_batch_mode", False) and self.open_after.get():
            open_folder(output)
        return output

    def xteink_pdf_to_xtch(self) -> Path:
        src, out_dir, target, _quality = self.xteink_paths()
        if src.suffix.lower() != ".pdf":
            raise RuntimeError("Selecione um PDF.")
        images = render_pdf_pages_as_images(src, target=target)
        output = unique_path(out_dir / f"{src.stem}.xtch")
        try:
            create_xtch_from_images(images, output, src.stem, target)
        finally:
            for im in images:
                im.close()
        self._xteink_last_out_dir = out_dir
        if not getattr(self, "_xteink_batch_mode", False) and self.open_after.get():
            open_folder(output)
        return output

    def xteink_epub_to_xtch(self) -> Path:
        src, out_dir, target, _quality = self.xteink_paths()
        if src.suffix.lower() != ".epub":
            raise RuntimeError("Selecione um EPUB.")
        images = extract_epub_images(src, target)
        output = unique_path(out_dir / f"{src.stem}.xtch")
        try:
            create_xtch_from_images(images, output, src.stem, target)
        finally:
            for im in images:
                im.close()
        self._xteink_last_out_dir = out_dir
        if not getattr(self, "_xteink_batch_mode", False) and self.open_after.get():
            open_folder(output)
        return output

def _base_main() -> None:
    ensure_manual()
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
    App(root)
    root.mainloop()


# =============================================================================
# CUMA - Conversor Ultimate de Mangás 8.4 - HOTFIX FINAL
# Regra permanente: toda interface antiga deve ser removida quando surgir
# uma nova atualização visual.
# =============================================================================
APP_DISPLAY_NAME = "CUMA - Conversor Ultimate de Mangás"
APP_DISPLAY_VERSION = "1.081.3"
APP_SUBTITLE = "Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH."
INTERFACE_MAINTENANCE_RULE = (
    "Sempre que houver nova atualização visual, a interface antiga deve ser removida "
    "e substituída pela interface mais recente."
)
INTERFACE_COLOR_FILE = "cuma_interface_colors.json"
ERROR_FILE_NAME = "erro.txt"

CHANGELOG_LATEST = {
    "version": APP_DISPLAY_VERSION,
    "date": "2026-06-19",
    "items": [
        "Base 1.0.6.0.2 com correção da seleção visual das abas.",
        "Tratamento global de exceções escreve em erro.txt ao lado do executável/script.",
        "Debug completo revisado para reduzir redundâncias e pontos frágeis.",
    ],
    "maintenance_note": INTERFACE_MAINTENANCE_RULE,
}

SIDEBAR_ITEMS = [
    ("Limpar", "⌂"),
    ("Ferramentas", "⚒"),
    ("Converter", "✦"),
    ("Resultados", "☰"),
    ("Registros", "✎"),
    ("Configurações", "⚙"),
    ("Sobre", "ℹ"),
]

THEME_VISUAL_PRESETS = {
    "Moderno Claro": {
        "accent": "#2563EB", "accent_hover": "#1D4ED8", "secondary": "#B7FF00",
        "bg": "#F5F7FB", "surface": "#FFFFFF", "surface2": "#EDF2F8",
        "sidebar_bg": "#E8EDF5", "sidebar_item": "#FFFFFF", "sidebar_item_active": "#DBE7FF",
        "field": "#FFFFFF", "fg": "#111827", "muted": "#6B7280", "border": "#D6DBE6",
        "selection": "#DBEAFE", "drop": "#EDF2FF", "danger": "#DC2626", "kind": "claro-azul",
    },
    "Moderno Escuro": {
        "accent": "#2563EB", "accent_hover": "#1D4ED8", "secondary": "#03A9F4",
        "bg": "#0F1318", "surface": "#20262F", "surface2": "#2B3340",
        "sidebar_bg": "#161A20", "sidebar_item": "#1D232C", "sidebar_item_active": "#2C3139",
        "field": "#141920", "fg": "#E5E7EB", "muted": "#9CA3AF", "border": "#38414E",
        "selection": "#324353", "drop": "#151B22", "danger": "#FF6B6B", "kind": "escuro-azul",
    },
    "Manga Dark": {
        "accent": "#86EF00", "accent_hover": "#6FD300", "secondary": "#03A9F4",
        "bg": "#0F1318", "surface": "#20262F", "surface2": "#2B3340",
        "sidebar_bg": "#161A20", "sidebar_item": "#1D232C", "sidebar_item_active": "#2C3139",
        "field": "#141920", "fg": "#E5E7EB", "muted": "#9CA3AF", "border": "#38414E",
        "selection": "#324353", "drop": "#151B22", "danger": "#FF6B6B", "kind": "manga-verde",
    },
}

COLOR_ROLE_LABELS = [
    ("Primário (botão/sucesso)", "primary"), ("Secundário", "secondary"),
    ("Fundo", "background"), ("Superfície", "surface"), ("Painel secundário", "surface2"),
    ("Barra lateral", "sidebar_bg"), ("Texto", "text"), ("Borda", "border"), ("Alerta", "danger"),
]

_MODERN_SWITCH_PALETTE = {
    "surface": "#20262F", "surface2": "#2B3340", "fg": "#E5E7EB",
    "muted": "#9CA3AF", "accent": "#2563EB", "border": "#38414E", "disabled": "#7B8694",
}
_MODERN_SWITCHES = []


def runtime_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return app_dir()


def error_log_path() -> Path:
    return runtime_dir() / ERROR_FILE_NAME


def write_error_log(exc_type, exc_value, exc_tb, context: str = 'Erro não tratado') -> None:
    try:
        from datetime import datetime
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        concise = f"[{ts}] {context}: {exc_type.__name__}: {exc_value}"
        detailed = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        block = (
            '=' * 88 + "\n"
            + f"RESUMO: {concise}\n"
            + '-' * 88 + "\n"
            + "DETALHES:\n"
            + f"{detailed}\n"
        )
        previous = error_log_path().read_text(encoding='utf-8') if error_log_path().exists() else ''
        error_log_path().write_text(previous + block, encoding='utf-8')
    except Exception:
        pass


def install_global_error_handlers(root=None) -> None:
    def _sys_hook(exc_type, exc_value, exc_tb):
        write_error_log(exc_type, exc_value, exc_tb, 'Exceção global do aplicativo')
    sys.excepthook = _sys_hook
    try:
        import threading
        def _thread_hook(args):
            write_error_log(args.exc_type, args.exc_value, args.exc_traceback, f'Exceção em thread: {getattr(args, "thread", None)}')
        threading.excepthook = _thread_hook
    except Exception:
        pass
    if root is not None:
        def _tk_hook(exc_type, exc_value, exc_tb):
            write_error_log(exc_type, exc_value, exc_tb, 'Exceção Tkinter')
        try:
            root.report_callback_exception = _tk_hook
        except Exception:
            pass


def interface_color_path() -> Path:
    return runtime_dir() / INTERFACE_COLOR_FILE


def normalize_hex(value: str, fallback: str = '#FFFFFF') -> str:
    text = str(value or '').strip().lstrip('#')
    if len(text) == 3:
        text = ''.join(ch * 2 for ch in text)
    if len(text) != 6:
        return fallback
    try:
        int(text, 16)
        return '#' + text.upper()
    except Exception:
        return fallback


def load_interface_colors_file() -> dict[str, object]:
    default = {
        'theme_name': 'Moderno Escuro',
        'roles': {},
        'theme_mode': 'Escuro',
        'custom_base': 'Escuro',
        'custom_accent': THEME_VISUAL_PRESETS['Moderno Escuro']['accent'],
    }
    try:
        p = interface_color_path()
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                theme_name = data.get('theme_name', default['theme_name'])
                if theme_name not in THEME_VISUAL_PRESETS:
                    theme_name = default['theme_name']
                roles_in = data.get('roles', {})
                roles = roles_in if isinstance(roles_in, dict) else {}
                normalized_roles = {str(k): normalize_hex(v, '#FFFFFF') for k, v in roles.items()}
                theme_mode = data.get('theme_mode', default['theme_mode'])
                if theme_mode not in THEME_SETTING_MODES:
                    theme_mode = default['theme_mode']
                custom_base = data.get('custom_base', default['custom_base'])
                if custom_base not in CUSTOM_THEME_BASES:
                    custom_base = default['custom_base']
                custom_accent = normalize_hex(data.get('custom_accent', THEME_VISUAL_PRESETS[theme_name]['accent']), THEME_VISUAL_PRESETS[theme_name]['accent'])
                return {
                    'theme_name': theme_name,
                    'roles': normalized_roles,
                    'theme_mode': theme_mode,
                    'custom_base': custom_base,
                    'custom_accent': custom_accent,
                }
    except Exception:
        pass
    return default


def save_interface_colors_file(theme_name: str, roles: dict[str, str], metadata: Optional[dict[str, object]] = None) -> None:
    try:
        safe_theme = theme_name if theme_name in THEME_VISUAL_PRESETS else 'Moderno Escuro'
        safe_roles = {str(k): normalize_hex(v, '#FFFFFF') for k, v in (roles or {}).items()}
        payload = {'theme_name': safe_theme, 'roles': safe_roles}
        if isinstance(metadata, dict):
            if metadata.get('theme_mode') in THEME_SETTING_MODES:
                payload['theme_mode'] = metadata.get('theme_mode')
            if metadata.get('custom_base') in CUSTOM_THEME_BASES:
                payload['custom_base'] = metadata.get('custom_base')
            if metadata.get('custom_accent') is not None:
                payload['custom_accent'] = normalize_hex(str(metadata.get('custom_accent')), THEME_VISUAL_PRESETS[safe_theme]['accent'])
        interface_color_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        write_log(f'Falha ao salvar cores da interface: {exc}')


def set_modern_switch_palette(**updates) -> None:
    _MODERN_SWITCH_PALETTE.update({k: v for k, v in updates.items() if v is not None})
    alive = []
    for widget in list(_MODERN_SWITCHES):
        try:
            widget.refresh_palette()
            alive.append(widget)
        except Exception:
            continue
    _MODERN_SWITCHES[:] = alive


class CompactSwitch(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        self._text = kwargs.pop('text', '')
        self._command = kwargs.pop('command', None)
        self._variable = kwargs.pop('variable', None) or tk.BooleanVar(value=False)
        self._onvalue = kwargs.pop('onvalue', True)
        self._offvalue = kwargs.pop('offvalue', False)
        self._state = kwargs.pop('state', 'normal')
        self._canvas_w = int(kwargs.pop('switchwidth', 54) or 54)
        self._canvas_h = int(kwargs.pop('switchheight', 30) or 30)
        self._knob_d = int(kwargs.pop('knobdiameter', 24) or 24)
        padding = kwargs.pop('padding', 0)
        cursor = kwargs.pop('cursor', 'hand2')
        super().__init__(master, style='Switch.TFrame', padding=padding)
        ttk.Frame.configure(self, cursor=cursor)
        self._canvas = tk.Canvas(self, width=self._canvas_w, height=self._canvas_h, bd=0, highlightthickness=0, relief='flat', cursor=cursor)
        self._canvas.pack(side='left')
        self._label = ttk.Label(self, text=self._text, style='SwitchText.TLabel', cursor=cursor)
        if self._text:
            self._label.pack(side='left', padx=(10, 0))
        for widget in (self, self._canvas, self._label):
            widget.bind('<Button-1>', self._on_click)
        _MODERN_SWITCHES.append(self)
        self.refresh_palette()

    def _on_click(self, _event=None):
        self.invoke(); return 'break'

    def _state_is_on(self):
        try:
            return self._variable.get() == self._onvalue
        except Exception:
            return False

    def invoke(self):
        if str(self._state) == 'disabled':
            return None
        self._variable.set(self._offvalue if self._state_is_on() else self._onvalue)
        self.refresh_palette()
        if callable(self._command):
            return self._command()
        return None

    def state(self, statespec=None):
        if statespec is None:
            return ('disabled',) if str(self._state) == 'disabled' else ()
        items = [statespec] if isinstance(statespec, str) else list(statespec)
        for item in items:
            item = str(item)
            if item == 'disabled': self._state = 'disabled'
            elif item == '!disabled': self._state = 'normal'
        self.refresh_palette(); return self.state()

    def instate(self, statespec):
        current = self.state()
        for item in statespec:
            item = str(item)
            if item.startswith('!'):
                if item[1:] in current: return False
            elif item not in current:
                return False
        return True

    def configure(self, cnf=None, **kw):
        opts = {}
        if cnf and isinstance(cnf, dict): opts.update(cnf)
        opts.update(kw)
        if 'text' in opts:
            self._text = opts.pop('text'); self._label.configure(text=self._text)
        if 'command' in opts: self._command = opts.pop('command')
        if 'variable' in opts: self._variable = opts.pop('variable')
        if 'state' in opts: self._state = opts.pop('state')
        if 'onvalue' in opts: self._onvalue = opts.pop('onvalue')
        if 'offvalue' in opts: self._offvalue = opts.pop('offvalue')
        result = ttk.Frame.configure(self, **opts) if opts else None
        self.refresh_palette(); return result

    config = configure

    def _rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        pts = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius, x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2, x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
        return self._canvas.create_polygon(pts, smooth=True, splinesteps=36, **kwargs)

    def refresh_palette(self):
        p = _MODERN_SWITCH_PALETTE
        disabled = str(self._state) == 'disabled'
        on = self._state_is_on()
        track_fill = p['accent'] if on else p['surface2']
        track_border = p['accent'] if on else p['border']
        knob_fill = '#FFFFFF'
        label_fg = p['disabled'] if disabled else p['fg']
        if disabled:
            track_fill = p['disabled']; track_border = p['disabled']; knob_fill = '#F8FAFC'
        self._canvas.configure(bg=p['surface']); self._label.configure(style='SwitchText.TLabel', foreground=label_fg)
        self._canvas.delete('all')
        track_w, track_h = 36, 16
        tx = (self._canvas_w - track_w) // 2; ty = (self._canvas_h - track_h) // 2
        self._rounded_rect(tx, ty, tx + track_w, ty + track_h, track_h // 2, fill=track_fill, outline=track_border, width=1)
        knob_y = (self._canvas_h - self._knob_d) // 2
        knob_x = tx + track_w - self._knob_d + 1 if on else tx - 1
        self._canvas.create_oval(knob_x, knob_y, knob_x + self._knob_d, knob_y + self._knob_d, fill=knob_fill, outline='')


# Checkbutton original preservado; switches podem ser reativados por tema.
try:
    ttk.Checkbutton = CompactSwitch
except Exception:
    pass


class SidebarNotebookAdapter:
    def __init__(self, app): self.app = app
    def select(self, tab_id=None):
        if tab_id is not None: self.app.show_page(tab_id, save_state=False)
        return getattr(self.app, '_current_tab_label', 'Início')
    def tab(self, tab_id, option=None):
        tab_id = tab_id or getattr(self.app, '_current_tab_label', 'Início')
        return tab_id if option == 'text' else {'text': tab_id}
    def tabs(self): return list(self.app.pages.keys())


def environment_diagnostics() -> dict[str, object]:
    data = {'python': sys.version.split()[0], 'frozen': bool(getattr(sys, 'frozen', False)), 'app_dir': str(runtime_dir()), 'dnd_available': bool(DND_AVAILABLE), 'display_name': APP_DISPLAY_NAME, 'display_version': APP_DISPLAY_VERSION, 'error_file': str(error_log_path()), 'modules': {}}
    for name in ('fitz', 'numpy', 'PIL', 'tkinterdnd2'):
        try:
            __import__(name); data['modules'][name] = 'OK'
        except Exception as exc:
            data['modules'][name] = f'ERRO: {exc}'
    return data


def print_environment_diagnostics() -> None:
    print(json.dumps(environment_diagnostics(), ensure_ascii=False, indent=2))


class PreviewWindow(BasePreviewWindow):
    def __init__(self, parent, pdf_path):
        super().__init__(parent, pdf_path)
        try:
            parent.fit_window_to_screen(self.top, width_ratio=0.92, height_ratio=0.92, min_width=860, min_height=640)
        except Exception as exc:
            write_log(f'Falha ao ajustar prévia: {exc}')


class App(BaseApp):
    def show_cuma_manual(self):
        ensure_manual()
        top = tk.Toplevel(self.root)
        top.title('Manual - CUMA')
        top.geometry('900x700')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass
        wrap = ttk.Frame(top, style='Card.TFrame', padding=12)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='CUMA - Conversor Ultimate de Mangás', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 8))
        ttk.Label(wrap, text=CUMA_ABOUT_TEXT, style='Muted.TLabel', wraplength=840, justify='left').pack(anchor='w', pady=(0, 10))
        txt = tk.Text(wrap, wrap='word', height=24, relief='flat', bd=0)
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', CUMA_MANUAL_TEXT)
        txt.configure(state='disabled')
        ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(10, 0))

    def _cuma_update_accent_preview(self, value=None):
        color = normalize_hex(value or self.custom_accent.get(), '#2563EB')
        try:
            self.custom_accent.set(color)
        except Exception:
            pass
        canvas = getattr(self, 'cuma_accent_preview', None)
        if canvas is not None:
            try:
                canvas.delete('all')
                canvas.configure(bg=color)
                canvas.create_rectangle(2, 2, 30, 22, fill=color, outline='#E5E7EB')
            except Exception:
                pass
        return color

    def _cuma_apply_accent_from_entry(self, value=None):
        color = self._cuma_update_accent_preview(value or self.custom_accent.get())
        self._set_custom_accent(color)
        self._cuma_update_accent_preview(color)

    def _cuma_open_color_picker(self):
        current = normalize_hex(self.custom_accent.get(), '#2563EB')
        try:
            r0 = int(current[1:3], 16) / 255.0
            g0 = int(current[3:5], 16) / 255.0
            b0 = int(current[5:7], 16) / 255.0
            h0, s0, v0 = colorsys.rgb_to_hsv(r0, g0, b0)
        except Exception:
            h0, s0, v0 = 0.6, 0.8, 0.9
        state = {'h': h0, 's': s0, 'v': v0}
        top = tk.Toplevel(self.root)
        top.title('Personalizar cor')
        top.geometry('620x455')
        top.transient(self.root)
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass
        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Seletor de cores', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 10))
        sv = tk.Canvas(wrap, width=540, height=220, highlightthickness=1, highlightbackground='#38414E', bd=0)
        sv.pack(fill='x')
        hue = tk.Canvas(wrap, width=540, height=22, highlightthickness=0, bd=0)
        hue.pack(fill='x', pady=(14, 8))
        sample = tk.Canvas(wrap, width=42, height=28, highlightthickness=1, highlightbackground='#38414E', bd=0)
        row1 = ttk.Frame(wrap, style='Card.TFrame')
        row1.pack(fill='x', pady=(6, 4))
        ttk.Label(row1, text='HEX', style='Muted.TLabel').pack(side='left')
        hex_var = tk.StringVar(value=current)
        hex_entry = ttk.Entry(row1, textvariable=hex_var, width=14)
        hex_entry.pack(side='left', padx=(10, 10))
        sample.pack(in_=row1, side='left', padx=(0, 10))
        def hsv_hex():
            rr, gg, bb = colorsys.hsv_to_rgb(state['h'], state['s'], state['v'])
            return '#%02X%02X%02X' % (int(rr * 255), int(gg * 255), int(bb * 255))
        def draw_hue():
            hue.delete('all')
            w = max(1, hue.winfo_width() or 540)
            h = max(1, hue.winfo_height() or 22)
            for x in range(w):
                rr, gg, bb = colorsys.hsv_to_rgb(x / max(1, w - 1), 1, 1)
                hue.create_line(x, 0, x, h, fill='#%02X%02X%02X' % (int(rr*255), int(gg*255), int(bb*255)))
            hx = int(state['h'] * (w - 1))
            hue.create_oval(hx-5, 2, hx+5, h-2, outline='white', width=2)
        def draw_sv():
            sv.delete('all')
            w = max(1, sv.winfo_width() or 540)
            h = max(1, sv.winfo_height() or 220)
            for x in range(w):
                s = x / max(1, w - 1)
                for y in range(h):
                    v = 1 - y / max(1, h - 1)
                    rr, gg, bb = colorsys.hsv_to_rgb(state['h'], s, v)
                    sv.create_line(x, y, x, y, fill='#%02X%02X%02X' % (int(rr*255), int(gg*255), int(bb*255)))
            px = int(state['s'] * (w - 1)); py = int((1 - state['v']) * (h - 1))
            sv.create_oval(px-7, py-7, px+7, py+7, outline='white', width=2)
        def refresh_all(update_entry=True):
            color = hsv_hex()
            if update_entry:
                hex_var.set(color)
            sample.delete('all')
            sample.configure(bg=color)
            sample.create_rectangle(2, 2, 40, 26, fill=color, outline='#E5E7EB')
            self.custom_accent.set(color)
            self._cuma_update_accent_preview(color)
            draw_hue(); draw_sv()
        def sv_pick(event):
            w = max(1, sv.winfo_width() or 540); h = max(1, sv.winfo_height() or 220)
            state['s'] = min(1, max(0, event.x / max(1, w - 1)))
            state['v'] = min(1, max(0, 1 - event.y / max(1, h - 1)))
            refresh_all(True)
        def hue_pick(event):
            w = max(1, hue.winfo_width() or 540)
            state['h'] = min(1, max(0, event.x / max(1, w - 1)))
            refresh_all(True)
        def entry_pick(_event=None):
            val = normalize_hex(hex_var.get(), hsv_hex())
            hex_var.set(val)
            rr = int(val[1:3], 16) / 255.0; gg = int(val[3:5], 16) / 255.0; bb = int(val[5:7], 16) / 255.0
            state['h'], state['s'], state['v'] = colorsys.rgb_to_hsv(rr, gg, bb)
            refresh_all(False)
        sv.bind('<Button-1>', sv_pick); sv.bind('<B1-Motion>', sv_pick)
        hue.bind('<Button-1>', hue_pick); hue.bind('<B1-Motion>', hue_pick)
        hex_entry.bind('<Return>', entry_pick); hex_entry.bind('<FocusOut>', entry_pick)
        btns = ttk.Frame(wrap, style='Card.TFrame')
        btns.pack(fill='x', pady=(12, 0))
        ttk.Button(btns, text='Aplicar cor', command=lambda: (self._cuma_apply_accent_from_entry(hex_var.get()), top.destroy()), style='Accent.TButton').pack(side='right', padx=(8, 0))
        ttk.Button(btns, text='Cancelar', command=top.destroy, style='Ghost.TButton').pack(side='right')
        top.after(120, refresh_all)

    def setup_window(self):
        self.interface_color_state = load_interface_colors_file()
        self.color_role_vars = {}
        self.color_picker_visible = tk.BooleanVar(value=True)
        if not hasattr(self, 'config_help_text'):
            self.config_help_text = tk.StringVar(value='As configurações foram organizadas por categoria para facilitar o uso.')
        saved_theme = self.interface_color_state.get('theme_name', self.theme.get()) if isinstance(self.interface_color_state, dict) else self.theme.get()
        saved_mode = self.interface_color_state.get('theme_mode', self.theme_mode.get()) if isinstance(self.interface_color_state, dict) else self.theme_mode.get()
        saved_base = self.interface_color_state.get('custom_base', self.custom_base_theme.get()) if isinstance(self.interface_color_state, dict) else self.custom_base_theme.get()
        saved_accent = self.interface_color_state.get('custom_accent', self.custom_accent.get()) if isinstance(self.interface_color_state, dict) else self.custom_accent.get()
        if saved_mode in THEME_SETTING_MODES:
            self.theme_mode.set(saved_mode)
        if saved_base in CUSTOM_THEME_BASES:
            self.custom_base_theme.set(saved_base)
        self.custom_accent.set(normalize_hex(saved_accent, self.custom_accent.get()))
        self.theme.set(saved_theme if saved_theme in THEME_VISUAL_PRESETS else self.theme.get())
        self.theme_palette = self._build_theme_palette(self.theme.get())
        self._theme_palette = dict(self.theme_palette)
        self.root.title(f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}')
        self.root.minsize(1040, 680)
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        install_global_error_handlers(self.root)
        try:
            ico = resource_path('app_icon.ico')
            if ico.exists(): self.root.iconbitmap(str(ico))
        except Exception as exc:
            write_log(f'Ícone não aplicado: {exc}')
        self.root.after(40, lambda: self.fit_window_to_screen(self.root, width_ratio=0.82, height_ratio=0.82, min_width=1120, min_height=720))

    def toggle_theme_quick(self):
        if getattr(self, 'theme_mode', None) and self.theme_mode.get() in ('Automático', 'Claro', 'Escuro', 'Personalizado'):
            if self.theme_mode.get() == 'Claro':
                self.theme_mode.set('Escuro')
            else:
                self.theme_mode.set('Claro')
            self.custom_base_theme.set(self.theme_mode.get() if self.theme_mode.get() in ('Claro', 'Escuro') else self.custom_base_theme.get())
            self._apply_theme_mode_selection(save=True)
        else:
            self.theme.set('Moderno Claro' if self.theme.get() != 'Moderno Claro' else 'Moderno Escuro')
            self.on_theme_choice_change()

    def _create_summary_card(self, parent, title, value, subtitle):
        frame = ttk.Frame(parent, style='SummaryCard.TFrame', padding=(16, 14))
        value_var = tk.StringVar(value=value); subtitle_var = tk.StringVar(value=subtitle)
        ttk.Label(frame, text=title, style='SummaryCardTitle.TLabel').pack(anchor='w')
        ttk.Label(frame, textvariable=value_var, style='SummaryCardValue.TLabel').pack(anchor='w', pady=(4, 2))
        ttk.Label(frame, textvariable=subtitle_var, style='SummaryCardNote.TLabel', wraplength=260, justify='left').pack(anchor='w')
        return frame, value_var, subtitle_var

    def fit_window_to_screen(self, top, width_ratio=0.94, height_ratio=0.92, min_width=900, min_height=620):
        try:
            top.update_idletasks(); sw = max(1024, int(top.winfo_screenwidth())); sh = max(720, int(top.winfo_screenheight()))
            width = min(max(min_width, int(sw * width_ratio)), sw - 40); height = min(max(min_height, int(sh * height_ratio)), sh - 80)
            x = max(10, (sw - width) // 2); y = max(10, (sh - height) // 2 - 10)
            top.geometry(f'{width}x{height}+{x}+{y}'); top.minsize(min_width, min_height)
            try:
                if os.name == 'nt' and isinstance(top, tk.Tk): top.state('zoomed')
            except Exception:
                pass
        except Exception as exc:
            write_log(f'Falha no ajuste de janela: {exc}')

    def fit_window_to_content(self, top, max_ratio_w=0.96, max_ratio_h=0.92, min_w=760, min_h=520):
        try:
            top.update_idletasks(); sw, sh = int(top.winfo_screenwidth()), int(top.winfo_screenheight())
            req_w = max(min_w, int(top.winfo_reqwidth()) + 26); req_h = max(min_h, int(top.winfo_reqheight()) + 30)
            width = min(req_w, int(sw * max_ratio_w)); height = min(req_h, int(sh * max_ratio_h)); x = max(10, (sw - width) // 2); y = max(10, (sh - height) // 2 - 10)
            top.geometry(f'{width}x{height}+{x}+{y}')
        except Exception as exc:
            write_log(f'Falha ao ajustar janela por conteúdo: {exc}')

    def place_window_near_widget(self, top, widget=None, width=820, height=640, min_width=640, min_height=420):
        super().place_window_near_widget(top, widget=widget, width=width, height=height, min_width=min_width, min_height=min_height)
        self.fit_window_to_content(top, max_ratio_w=0.94, max_ratio_h=0.90, min_w=min_width, min_h=min_height)

    def _build_theme_palette(self, theme_name):
        base = THEME_VISUAL_PRESETS.get(theme_name, THEME_VISUAL_PRESETS['Moderno Escuro'])
        return {'accent': base['accent'], 'bg': base['bg'], 'surface': base['surface'], 'surface2': base['surface2'], 'sidebar_bg': base['sidebar_bg'], 'fg': base['fg'], 'muted': base['muted'], 'border': base['border'], 'drop': base['drop'], 'selection': base['selection'], 'danger': base['danger'], 'accent_hover': base['accent_hover'], 'sidebar_active': base['sidebar_item_active'], 'kind': base['kind']}

    def default_role_colors(self, theme_name):
        p = THEME_VISUAL_PRESETS.get(theme_name, THEME_VISUAL_PRESETS['Moderno Escuro'])
        return {'primary': p['accent'], 'secondary': p['secondary'], 'background': p['bg'], 'surface': p['surface'], 'surface2': p['surface2'], 'sidebar_bg': p['sidebar_bg'], 'text': p['fg'], 'border': p['border'], 'danger': p['danger']}

    def ensure_color_role_vars(self):
        if self.color_role_vars: return
        saved_roles = self.interface_color_state.get('roles', {}) if isinstance(self.interface_color_state, dict) else {}
        defaults = self.default_role_colors(self.theme.get())
        for _label, key in COLOR_ROLE_LABELS: self.color_role_vars[key] = tk.StringVar(value=normalize_hex(saved_roles.get(key, defaults.get(key, '#FFFFFF')), defaults.get(key, '#FFFFFF')))

    def current_role_colors(self):
        self.ensure_color_role_vars(); defaults = self.default_role_colors(self.theme.get())
        return {key: normalize_hex(var.get(), defaults.get(key, '#FFFFFF')) for key, var in self.color_role_vars.items()}

    def save_role_colors(self):
        roles = self.current_role_colors()
        metadata = {'theme_mode': self.theme_mode.get(), 'custom_base': self.custom_base_theme.get(), 'custom_accent': self.custom_accent.get()}
        self.interface_color_state = {'theme_name': self.theme.get(), 'roles': roles, **metadata}
        save_interface_colors_file(self.theme.get(), roles, metadata=metadata)

    def _system_theme_mode(self):
        try:
            if sys.platform.startswith('win'):
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return 'Claro' if int(value) == 1 else 'Escuro'
        except Exception:
            pass
        return 'Escuro'

    def _effective_theme_for_mode(self):
        mode = self.theme_mode.get()
        if mode == 'Automático':
            return 'Moderno Claro' if self._system_theme_mode() == 'Claro' else 'Moderno Escuro'
        if mode == 'Claro':
            return 'Moderno Claro'
        if mode == 'Escuro':
            return 'Moderno Escuro'
        return 'Moderno Claro' if self.custom_base_theme.get() == 'Claro' else 'Moderno Escuro'

    def _accent_variants(self, accent_hex):
        accent_hex = normalize_hex(accent_hex, '#2563EB')
        hsv = self._hex_to_hsv(accent_hex)
        secondary = self._hsv_to_hex(hsv['h'], max(0.25, min(0.95, hsv['s'] * 0.65 + 0.10)), min(1.0, hsv['v'] * 0.96 + 0.04))
        border = self._hsv_to_hex(hsv['h'], max(0.08, min(0.55, hsv['s'] * 0.22 + 0.08)), max(0.36, min(0.88, hsv['v'] * 0.58)))
        return {'secondary': secondary, 'border': border}

    def _apply_system_preset(self, preset_name, force_custom=False):
        preset_name = preset_name if preset_name in THEME_VISUAL_PRESETS else 'Moderno Escuro'
        self.theme.set(preset_name)
        defaults = self.default_role_colors(preset_name)
        self.ensure_color_role_vars()
        for key, var in self.color_role_vars.items():
            var.set(defaults.get(key, '#FFFFFF'))
        self.custom_accent.set(defaults.get('primary', '#2563EB'))
        self.custom_base_theme.set('Claro' if preset_name == 'Moderno Claro' else 'Escuro')
        if force_custom:
            self.theme_mode.set('Personalizado')
        self.sync_picker_states_from_roles()
        self.save_role_colors()
        self.apply_theme()
        self.save_current_config(force=True)

    def _apply_theme_mode_selection(self, save=True):
        effective_theme = self._effective_theme_for_mode()
        self.theme.set(effective_theme)
        defaults = self.default_role_colors(effective_theme)
        self.ensure_color_role_vars()
        for key, var in self.color_role_vars.items():
            if self.theme_mode.get() != 'Personalizado':
                var.set(defaults.get(key, '#FFFFFF'))
        if self.theme_mode.get() == 'Personalizado':
            accent = normalize_hex(self.custom_accent.get(), defaults.get('primary', '#2563EB'))
            variants = self._accent_variants(accent)
            self.color_role_vars['primary'].set(accent)
            self.color_role_vars['secondary'].set(variants['secondary'])
            self.color_role_vars['border'].set(variants['border'])
            self.custom_accent.set(accent)
        self.sync_picker_states_from_roles()
        self.save_role_colors()
        self.apply_theme()
        if save:
            self.save_current_config(force=True)
        if hasattr(self, 'config_help_text'):
            self.config_help_text.set('Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.')
        if hasattr(self, 'refresh_dashboard'):
            self.refresh_dashboard()

    def _set_custom_accent(self, accent_hex):
        self.theme_mode.set('Personalizado')
        self.custom_accent.set(normalize_hex(accent_hex, '#2563EB'))
        self._apply_theme_mode_selection(save=True)

    def _rgb(self, hx):
        hx = normalize_hex(hx, '#FFFFFF').lstrip('#'); return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))

    def _hex_to_hsv(self, hx):
        import colorsys
        r, g, b = [v / 255.0 for v in self._rgb(hx)]; h, s, v = colorsys.rgb_to_hsv(r, g, b); return {'h': h, 's': s, 'v': v}

    def _hsv_to_hex(self, h, s, v):
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(max(0.0, min(1.0, h)), max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
        return f'#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}'

    def sync_picker_states_from_roles(self):
        roles = self.current_role_colors(); self.primary_picker_state = self._hex_to_hsv(roles['primary']); self.secondary_picker_state = self._hex_to_hsv(roles['secondary'])

    def _generate_theme_gradient(self, hue_hex, width=340, height=190):
        accent = np.array(self._rgb(hue_hex), dtype=float); white = np.array([255, 255, 255], dtype=float); black = np.array([0, 0, 0], dtype=float); arr = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            fy = y / max(height - 1, 1)
            for x in range(width):
                fx = x / max(width - 1, 1); top = white * (1.0 - fx) + accent * fx; rgb = top * (1.0 - fy) + black * fy; arr[y, x] = rgb.clip(0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode='RGB')

    def _generate_hue_strip(self, width=240, height=12):
        import colorsys
        img = Image.new('RGB', (width, height)); px = img.load()
        for x in range(width):
            h = x / max(width - 1, 1); r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0); color = (int(r * 255), int(g * 255), int(b * 255))
            for y in range(height): px[x, y] = color
        return img

    def _picker_state(self, key):
        return self.primary_picker_state if key == 'primary' else self.secondary_picker_state

    def _update_picker_from_canvas(self, key, x, y):
        state = self._picker_state(key); state['s'] = max(0.0, min(1.0, x / 339)); state['v'] = max(0.0, min(1.0, 1.0 - (y / 189))); self._apply_picker_state(key)

    def _update_picker_hue(self, key, x):
        state = self._picker_state(key); state['h'] = max(0.0, min(1.0, x / 239)); self._apply_picker_state(key)

    def _apply_picker_state(self, key):
        role_key = 'primary' if key == 'primary' else 'secondary'; state = self._picker_state(key); self.color_role_vars[role_key].set(self._hsv_to_hex(state['h'], state['s'], state['v'])); self.save_role_colors(); self.apply_theme()

    def _bind_picker_events(self):
        self.primary_canvas.bind('<Button-1>', lambda e: self._update_picker_from_canvas('primary', e.x, e.y)); self.primary_canvas.bind('<B1-Motion>', lambda e: self._update_picker_from_canvas('primary', e.x, e.y))
        self.secondary_canvas.bind('<Button-1>', lambda e: self._update_picker_from_canvas('secondary', e.x, e.y)); self.secondary_canvas.bind('<B1-Motion>', lambda e: self._update_picker_from_canvas('secondary', e.x, e.y))
        self.primary_hue.bind('<Button-1>', lambda e: self._update_picker_hue('primary', e.x)); self.primary_hue.bind('<B1-Motion>', lambda e: self._update_picker_hue('primary', e.x))
        self.secondary_hue.bind('<Button-1>', lambda e: self._update_picker_hue('secondary', e.x)); self.secondary_hue.bind('<B1-Motion>', lambda e: self._update_picker_hue('secondary', e.x))

    def _render_color_choice(self):
        palette = getattr(self, '_theme_palette', self._build_theme_palette(self.theme.get()))
        roles = self.current_role_colors(); primary_hex = roles['primary']; secondary_hex = roles['secondary']; primary_hue_hex = self._hsv_to_hex(self.primary_picker_state['h'], 1.0, 1.0); secondary_hue_hex = self._hsv_to_hex(self.secondary_picker_state['h'], 1.0, 1.0)
        self._color_choice_images = [ImageTk.PhotoImage(self._generate_theme_gradient(primary_hue_hex)), ImageTk.PhotoImage(self._generate_theme_gradient(secondary_hue_hex)), ImageTk.PhotoImage(self._generate_hue_strip())]
        for canvas in (self.primary_canvas, self.secondary_canvas, self.primary_hue, self.secondary_hue): canvas.configure(bg=roles['surface'], highlightthickness=0)
        self.primary_canvas.delete('all'); self.secondary_canvas.delete('all'); self.primary_canvas.create_image(0, 0, anchor='nw', image=self._color_choice_images[0]); self.secondary_canvas.create_image(0, 0, anchor='nw', image=self._color_choice_images[1])
        px = int(self.primary_picker_state['s'] * 339); py = int((1.0 - self.primary_picker_state['v']) * 189); sx = int(self.secondary_picker_state['s'] * 339); sy = int((1.0 - self.secondary_picker_state['v']) * 189)
        self.primary_canvas.create_oval(px - 11, py - 11, px + 11, py + 11, outline='#F8FAFC', width=2); self.secondary_canvas.create_oval(sx - 11, sy - 11, sx + 11, sy + 11, outline='#F8FAFC', width=2)
        self.primary_hue.delete('all'); self.secondary_hue.delete('all'); self.primary_hue.create_image(0, 0, anchor='nw', image=self._color_choice_images[2]); self.secondary_hue.create_image(0, 0, anchor='nw', image=self._color_choice_images[2])
        hx1 = int(self.primary_picker_state['h'] * 239); hx2 = int(self.secondary_picker_state['h'] * 239)
        self.primary_hue.create_oval(hx1 - 8, -2, hx1 + 8, 14, fill=primary_hex, outline='#FFFFFF', width=2); self.secondary_hue.create_oval(hx2 - 8, -2, hx2 + 8, 14, fill=secondary_hex, outline='#FFFFFF', width=2)
        for _label, role_key in COLOR_ROLE_LABELS:
            swatch, label = self.color_rows[role_key]; value = roles[role_key]; swatch.configure(bg=value); label.configure(text=value)
        fg = roles['text']; muted = palette['muted']; accent = roles['primary']; border = roles['border']; is_light = self.theme.get() == 'Moderno Claro'; card_tones = [roles['surface2'], roles['surface2'], roles['surface2'], roles['surface']]
        for idx, card in enumerate(self.preview_cards):
            tone = card_tones[idx]; card['canvas'].configure(bg=tone, highlightbackground=border, highlightcolor=border); card['canvas'].delete('all'); card['canvas'].create_rectangle(0, 0, 188, 74, fill=tone, outline=''); card['canvas'].create_text(14, 16, text='Texto de', fill=fg, anchor='w', font=('Segoe UI', 9)); card['canvas'].create_text(14, 34, text='Exemplo', fill=fg, anchor='w', font=('Segoe UI', 11, 'bold')); card['canvas'].create_text(90, 16, text='Entrada', fill=muted, anchor='w', font=('Segoe UI', 8)); card['canvas'].create_text(90, 34, text='50', fill=fg, anchor='w', font=('Segoe UI', 10)); card['canvas'].create_text(126, 16, text='+', fill=accent, anchor='w', font=('Segoe UI', 10, 'bold')); card['canvas'].create_text(126, 36, text='–', fill=muted, anchor='w', font=('Segoe UI', 10, 'bold')); card['canvas'].create_rectangle(138, 10, 184, 44, fill=accent, outline=accent); card['canvas'].create_text(161, 27, text='Ok', fill='#FFFFFF' if is_light else '#101317', font=('Segoe UI', 10, 'bold')); card['canvas'].create_line(16, 56, 120, 56, fill='#F8FAFC' if is_light else '#9CA3AF')

    def build(self):
        self.style = ttk.Style(self.root)
        try: self.style.theme_use('clam')
        except Exception: pass
        self.shell = ttk.Frame(self.root, style='App.TFrame', padding=0); self.shell.pack(fill='both', expand=True)
        self.header = ttk.Frame(self.shell, style='Header.TFrame', padding=(16, 14)); self.header.pack(fill='x', padx=14, pady=(14, 10))
        head_left = ttk.Frame(self.header, style='Header.TFrame'); head_left.pack(side='left', fill='x', expand=True)
        ttk.Label(head_left, text=APP_DISPLAY_NAME, style='Title.TLabel').pack(anchor='w'); ttk.Label(head_left, text=APP_SUBTITLE, style='HeaderSub.TLabel').pack(anchor='w', pady=(4, 0))
        head_right = ttk.Frame(self.header, style='Header.TFrame'); head_right.pack(side='right')
        self.toggle_btn = ttk.Button(head_right, text='☀ Tema claro', command=self.toggle_theme_quick, style='Accent.TButton'); self.toggle_btn.pack(side='right', padx=(8, 0))
        ttk.Button(head_right, text='Manual', command=self.show_cuma_manual, style='Header.TButton').pack(side='right', padx=(8, 0)); ttk.Button(head_right, text='Log', command=lambda: open_path(log_path()), style='Header.TButton').pack(side='right')
        self.summary_bar = ttk.Frame(self.shell, style='App.TFrame', padding=(14, 0, 14, 10)); self.summary_bar.pack(fill='x')
        self.dashboard_cards = {}
        for key, title, value, subtitle in (('files', 'Fila principal', '0 arquivo(s)', 'OK: 0  •  Erros: 0'), ('xteink', 'Converter', '0 item(ns)', 'Fila de conversão EPUB / XTCH'), ('update', 'Versão', CHANGELOG_LATEST['version'], f'Atualizado em {CHANGELOG_LATEST["date"]}')):
            frame, value_var, subtitle_var = self._create_summary_card(self.summary_bar, title, value, subtitle); frame.pack(side='left', fill='both', expand=True, padx=(0, 10)); self.dashboard_cards[key] = {'frame': frame, 'value': value_var, 'subtitle': subtitle_var}
        self.dashboard_cards['update']['frame'].pack_configure(padx=(0, 0))
        self.content = ttk.Frame(self.shell, style='App.TFrame', padding=(14, 0, 14, 14)); self.content.pack(fill='both', expand=True)
        self.workspace = ttk.Frame(self.content, style='App.TFrame'); self.workspace.pack(fill='both', expand=True)
        self.sidebar = tk.Frame(self.workspace, width=132, bd=0, highlightthickness=0); self.sidebar.pack(side='left', fill='y'); self.sidebar.pack_propagate(False)
        self.pages_container = ttk.Frame(self.workspace, style='Card.TFrame', padding=0); self.pages_container.pack(side='left', fill='both', expand=True, padx=(12, 0))
        self.nav_items = {}; self._current_tab_label = 'Limpar'; self.notebook = SidebarNotebookAdapter(self)
        self.tab_files = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_tools = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_xteink = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_results = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_log = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_config = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame'); self.tab_about = ttk.Frame(self.pages_container, padding=12, style='Card.TFrame')
        self.pages = {'Limpar': self.tab_files, 'Ferramentas': self.tab_tools, 'Converter': self.tab_xteink, 'Resultados': self.tab_results, 'Registros': self.tab_log, 'Configurações': self.tab_config, 'Sobre': self.tab_about}
        self.build_sidebar(); self.build_files_tab(); self.build_tools_tab(); self.build_xteink_tab(); self.build_results_tab(); self.build_log_tab(); self.build_config_tab(); self.build_about_tab();
        wanted_tab = self.cfg.last_tab if self.cfg.remember_last_tab and self.cfg.last_tab in self.pages else 'Limpar'
        if wanted_tab == 'Início': wanted_tab = 'Limpar'
        if wanted_tab == 'XTEINK': wanted_tab = 'Converter'
        self.show_page(wanted_tab, save_state=False); self.refresh_dashboard(); self._apply_theme_mode_selection(save=False)

    def build_sidebar(self):
        self.sidebar_top = tk.Frame(self.sidebar, bd=0, highlightthickness=0); self.sidebar_top.pack(fill='x', pady=(10, 8))
        for label, icon in SIDEBAR_ITEMS:
            container = tk.Frame(self.sidebar_top, width=116, height=76, bd=0, highlightthickness=0); container.pack(fill='x', pady=3, padx=8); container.pack_propagate(False)
            indicator = tk.Frame(container, width=4, bd=0, highlightthickness=0); indicator.pack(side='left', fill='y')
            body = tk.Frame(container, bd=0, highlightthickness=0, cursor='hand2'); body.pack(side='left', fill='both', expand=True)
            icon_lbl = tk.Label(body, text=icon, font=('Segoe UI Symbol', 17, 'bold'), cursor='hand2'); icon_lbl.pack(pady=(10, 2)); text_lbl = tk.Label(body, text=label, font=('Segoe UI', 10, 'bold'), cursor='hand2'); text_lbl.pack()
            for widget in (container, body, icon_lbl, text_lbl, indicator): widget.bind('<Button-1>', lambda _e, tab=label: self.show_page(tab))
            self.nav_items[label] = {'container': container, 'indicator': indicator, 'body': body, 'icon': icon_lbl, 'text': text_lbl}

    def show_page(self, label, save_state=True):
        if label not in self.pages: label = 'Limpar' if 'Limpar' in self.pages else next(iter(self.pages))
        for page in self.pages.values(): page.pack_forget()
        self.pages[label].pack(fill='both', expand=True)
        self._current_tab_label = label
        if save_state and getattr(self, 'remember_last_tab', None) and self.remember_last_tab.get():
            self.cfg.last_tab = label
            save_config(self.cfg)

    def update_sidebar_selection(self):
        colors = getattr(self, '_sidebar_colors', {})
        outer_bg = colors.get('sidebar_bg', self._theme_palette.get('sidebar_bg', '#161A20'))
        for label, item in self.nav_items.items():
            active = label == self._current_tab_label
            container_bg = colors.get('active_bg' if active else 'item_bg', '#1A1F27'); text_fg = colors.get('active_fg' if active else 'item_fg', '#9CA3AF'); indicator_bg = colors.get('accent' if active else 'sidebar_bg', '#171A1F')
            item['container'].configure(bg=outer_bg); item['indicator'].configure(bg=indicator_bg); item['body'].configure(bg=container_bg); item['icon'].configure(bg=container_bg, fg=text_fg); item['text'].configure(bg=container_bg, fg=text_fg)
        self.sidebar.configure(bg=outer_bg); self.sidebar_top.configure(bg=outer_bg)

    def on_tab_changed(self, _event=None):
        try:
            if self.remember_last_tab.get(): self.cfg.last_tab = self._current_tab_label; self.save_current_config()
        except Exception: pass

    def build_config_tab(self):
        if not hasattr(self, 'config_help_text'):
            self.config_help_text = tk.StringVar(value='As configurações foram organizadas por categoria para facilitar o uso.')
        self.ensure_color_role_vars(); self.sync_picker_states_from_roles()
        config_canvas = tk.Canvas(self.tab_config, highlightthickness=0, bd=0)
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            config_canvas.configure(bg=pal.get('surface', '#20262F'))
        except Exception:
            pass
        config_scrollbar = ttk.Scrollbar(self.tab_config, orient='vertical', command=config_canvas.yview)
        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        config_canvas.pack(side='left', fill='both', expand=True)
        config_scrollbar.pack(side='right', fill='y')
        wrap = ttk.Frame(config_canvas, style='Card.TFrame')
        config_window = config_canvas.create_window((0, 0), window=wrap, anchor='nw')
        def _cuma_config_update_scroll(_event=None):
            try: config_canvas.configure(scrollregion=config_canvas.bbox('all'))
            except Exception: pass
        def _cuma_config_resize(event):
            try:
                config_canvas.itemconfigure(config_window, width=event.width)
                _cuma_config_update_scroll()
            except Exception: pass
        def _cuma_config_mousewheel(event):
            try:
                if getattr(event, 'num', None) == 4: config_canvas.yview_scroll(-3, 'units')
                elif getattr(event, 'num', None) == 5: config_canvas.yview_scroll(3, 'units')
                else: config_canvas.yview_scroll(int(-1 * (getattr(event, 'delta', 0) / 120)) * 3, 'units')
            except Exception: pass
            return 'break'
        def _cuma_bind_config_scroll_recursive(widget):
            try:
                widget.bind('<MouseWheel>', _cuma_config_mousewheel, add='+')
                widget.bind('<Button-4>', _cuma_config_mousewheel, add='+')
                widget.bind('<Button-5>', _cuma_config_mousewheel, add='+')
            except Exception: pass
            try:
                for child in widget.winfo_children(): _cuma_bind_config_scroll_recursive(child)
            except Exception: pass
        wrap.bind('<Configure>', _cuma_config_update_scroll)
        config_canvas.bind('<Configure>', _cuma_config_resize)
        ttk.Label(wrap, text='Configurações organizadas por categoria', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 4))
        ttk.Label(wrap, textvariable=self.config_help_text, style='Muted.TLabel', wraplength=1080, justify='left').pack(anchor='w', pady=(0, 10))
        notebook = ttk.Notebook(wrap); notebook.pack(fill='both', expand=True)
        tab_theme = ttk.Frame(notebook, padding=14, style='Card.TFrame'); tab_perf = ttk.Frame(notebook, padding=14, style='Card.TFrame'); tab_hw = ttk.Frame(notebook, padding=14, style='Card.TFrame'); tab_help = ttk.Frame(notebook, padding=14, style='Card.TFrame'); tab_safe = ttk.Frame(notebook, padding=14, style='Card.TFrame')
        notebook.add(tab_theme, text='Temas e cores'); notebook.add(tab_perf, text='Qualidade e desempenho'); notebook.add(tab_hw, text='Hardware'); notebook.add(tab_help, text='Facilidades'); notebook.add(tab_safe, text='Segurança e logs')
        def section(parent, title, subtitle=''):
            box = ttk.LabelFrame(parent, text=title, padding=12, style='Card.TLabelframe'); box.pack(fill='x', pady=(0, 12))
            if subtitle: ttk.Label(box, text=subtitle, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(0, 8))
            return box
        def row(parent): r = ttk.Frame(parent, style='Card.TFrame'); r.pack(fill='x', pady=4); return r
        def add_combo(parent, label, var, values, help_text='', width=24, on_change=None):
            r = row(parent); ttk.Label(r, text=label, style='TitleSmall.TLabel').pack(side='left'); cb = ttk.Combobox(r, textvariable=var, values=values, state='readonly', width=width); cb.pack(side='left', padx=(12, 0)); cb.bind('<<ComboboxSelected>>', lambda _e: on_change() if on_change else self.save_current_config(force=True))
            if help_text: ttk.Label(parent, text=help_text, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(0, 6))
            return cb
        def add_check(parent, label, var, help_text=''):
            r = row(parent); ttk.Checkbutton(r, text=label, variable=var, command=self.save_current_config).pack(side='left')
            if help_text: ttk.Label(parent, text=help_text, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(0, 6))
        def add_spin(parent, label, var, start, end, help_text='', width=8):
            r = row(parent); ttk.Label(r, text=label, style='TitleSmall.TLabel').pack(side='left'); sp = ttk.Spinbox(r, from_=start, to=end, textvariable=var, width=width, command=self.save_current_config); sp.pack(side='left', padx=(12, 0)); sp.bind('<FocusOut>', lambda _e: self.save_current_config(force=True))
            if help_text: ttk.Label(parent, text=help_text, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(0, 6))
            return sp
        mode_box = section(tab_theme, 'Quatro modos visuais', 'Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.')
        add_combo(mode_box, 'Modo visual', self.theme_mode, THEME_SETTING_MODES, 'Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.', 20, lambda: self._apply_theme_mode_selection(save=True))
        add_combo(mode_box, 'Base do personalizado', self.custom_base_theme, CUSTOM_THEME_BASES, 'Escolha se o modo personalizado parte de uma base clara ou escura.', 18, lambda: self._apply_theme_mode_selection(save=True))
        accent_row = row(mode_box)
        ttk.Label(accent_row, text='Cor principal do botão', style='TitleSmall.TLabel').pack(side='left')
        self.cuma_accent_preview = tk.Canvas(accent_row, width=32, height=24, highlightthickness=1, highlightbackground='#38414E', bd=0)
        self.cuma_accent_preview.pack(side='left', padx=(10, 8))
        accent_entry = ttk.Entry(accent_row, textvariable=self.custom_accent, width=12)
        accent_entry.pack(side='left', padx=(0, 8))
        accent_entry.bind('<Return>', lambda _e: self._cuma_apply_accent_from_entry(self.custom_accent.get()))
        accent_entry.bind('<FocusOut>', lambda _e: self._cuma_update_accent_preview(self.custom_accent.get()))
        ttk.Button(accent_row, text='Personalizar cor', command=self._cuma_open_color_picker, style='Ghost.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(accent_row, text='Aplicar cor', command=lambda: self._cuma_apply_accent_from_entry(self.custom_accent.get()), style='Ghost.TButton').pack(side='left')
        self.root.after_idle(self._cuma_update_accent_preview)
        quick_box = section(tab_theme, 'Cores padrão do sistema', 'Metade do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.')
        quick_buttons = ttk.Frame(quick_box, style='Card.TFrame'); quick_buttons.pack(fill='x', pady=(0, 8))
        ttk.Button(quick_buttons, text='Preset Manga Dark', command=lambda: self._apply_system_preset('Manga Dark', force_custom=True), style='Ghost.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(quick_buttons, text='Preset Escuro', command=lambda: self._apply_system_preset('Moderno Escuro', force_custom=True), style='Ghost.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(quick_buttons, text='Preset Claro', command=lambda: self._apply_system_preset('Moderno Claro', force_custom=True), style='Ghost.TButton').pack(side='left')
        sw_frame = ttk.Frame(quick_box, style='Card.TFrame'); sw_frame.pack(fill='x', pady=(0, 4))
        for accent in ACCENT_PRESETS:
            tk.Button(sw_frame, text='   ', width=2, bg=accent, activebackground=accent, relief='flat', bd=0, command=lambda c=accent: self._set_custom_accent(c)).pack(side='left', padx=3, pady=2)
        adv_box = section(tab_theme, 'Ajuste avançado das cores', 'Deixei o ajuste avançado mais intuitivo: campos organizados em duas colunas, descrição curta e aplicação imediata. Você só mexe aqui quando quiser controle fino.')
        cols = ttk.Frame(adv_box, style='Card.TFrame'); cols.pack(fill='x')
        left = ttk.Frame(cols, style='Card.TFrame'); left.pack(side='left', fill='both', expand=True)
        right = ttk.Frame(cols, style='Card.TFrame'); right.pack(side='left', fill='both', expand=True, padx=(24, 0))
        for idx, (label, role_key) in enumerate(COLOR_ROLE_LABELS):
            parent = left if idx < (len(COLOR_ROLE_LABELS)+1)//2 else right
            r = ttk.Frame(parent, style='Card.TFrame'); r.pack(fill='x', pady=4)
            ttk.Label(r, text=label, style='Muted.TLabel', width=26).pack(side='left')
            sw = tk.Label(r, width=2, height=1, bg=self.color_role_vars[role_key].get(), bd=0, relief='flat')
            sw.pack(side='left', padx=(0, 8))
            ent = ttk.Entry(r, textvariable=self.color_role_vars[role_key], width=12)
            ent.pack(side='left', padx=(0, 6))
            def _mk_update(var=self.color_role_vars[role_key], lab=sw):
                return lambda *_: lab.configure(bg=normalize_hex(var.get(), '#FFFFFF'))
            self.color_role_vars[role_key].trace_add('write', _mk_update())
            ent.bind('<Return>', lambda _e: self.apply_manual_color_entries())
            ent.bind('<FocusOut>', lambda _e: self.apply_manual_color_entries())
        adv_actions = ttk.Frame(adv_box, style='Card.TFrame'); adv_actions.pack(fill='x', pady=(10, 0))
        ttk.Button(adv_actions, text='Aplicar ajustes avançados', command=self.apply_manual_color_entries, style='Accent.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(adv_actions, text='Restaurar tema escolhido', command=lambda: self._apply_theme_mode_selection(save=True), style='Ghost.TButton').pack(side='left')
        ttk.Label(adv_box, text='Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.', style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(8, 0))
        perf_box = section(tab_perf, 'Qualidade e desempenho', 'Aqui ficam as escolhas ligadas diretamente ao resultado do PDF.'); add_combo(perf_box, 'Modo de detecção', self.mode, MODES, 'Auto escolhe a estratégia. Image e Visual servem para forçar comportamento.', 18); add_combo(perf_box, 'Perfil de limpeza', self.profile, PROFILES, 'Conservador remove menos páginas; agressivo tenta limpar mais.', 18); add_combo(perf_box, 'Compactação', self.compression, COMPRESSION_OPTIONS, 'Preservar qualidade máxima é mais fiel; compactar reduz tamanho.', 30); add_combo(perf_box, 'Qualidade da prévia', self.preview_quality, PREVIEW_QUALITIES, 'Ajusta nitidez e velocidade da prévia.', 14); add_spin(perf_box, 'Páginas por lote na prévia', self.preview_batch_pages, 1, 100); add_spin(perf_box, 'Largura das miniaturas', self.preview_thumb_width, 240, 1800); add_check(perf_box, 'Usar cache de prévia', self.preview_cache); add_check(perf_box, 'Abrir prévia maximizada', self.preview_maximized)
        hw_box = section(tab_hw, 'Hardware e paralelismo', 'Esta subaba reúne CPU, GPU, threads e cache para combinar melhor com a estética e a lógica do programa.'); add_combo(hw_box, 'Modo de hardware', self.hardware_mode, HARDWARE_MODES, 'Automático tenta encontrar o backend mais adequado.', 20); add_combo(hw_box, 'Perfil de desempenho', self.performance_profile, PERFORMANCE_PROFILES, 'Escolha entre economia, equilíbrio e velocidade.', 20); add_spin(hw_box, 'Threads de trabalho (0 = automático)', self.worker_threads, 0, 64); add_spin(hw_box, 'PDFs paralelos (0 = automático)', self.max_parallel_pdfs, 0, 64); add_spin(hw_box, 'Cache de páginas (MB)', self.page_cache_mb, 0, 4096); add_check(hw_box, 'Ativar cache de páginas', self.enable_page_cache); add_check(hw_box, 'Usar GPU somente se for mais rápida', self.gpu_only_if_faster); add_check(hw_box, 'Voltar para CPU se a GPU falhar', self.gpu_fallback_cpu); add_check(hw_box, 'Economia de memória', self.memory_saver)
        hw_actions = ttk.Frame(hw_box, style='Card.TFrame'); hw_actions.pack(fill='x', pady=(8, 0)); ttk.Button(hw_actions, text='Ver status do hardware', command=self.show_gpu_status, style='Ghost.TButton').pack(side='left', padx=(0, 8)); ttk.Button(hw_actions, text='Benchmark rápido', command=self.run_gpu_benchmark, style='Ghost.TButton').pack(side='left', padx=(0, 8)); ttk.Button(hw_actions, text='Copiar diagnóstico', command=self.copy_diagnostics, style='Ghost.TButton').pack(side='left')
        help_box = section(tab_help, 'Facilidades de uso', 'Estas opções ajudam o usuário a operar o app de formas diferentes, mais automáticas ou mais seguras.'); add_check(help_box, 'Salvar configurações automaticamente', self.auto_save_config); add_check(help_box, 'Mostrar dicas e tooltips', self.show_tooltips); add_check(help_box, 'Confirmar antes de ações perigosas', self.confirm_actions); add_check(help_box, 'Lembrar tamanho e posição da janela', self.remember_window); add_check(help_box, 'Lembrar última aba aberta', self.remember_last_tab); add_check(help_box, 'Lembrar última pasta utilizada', self.remember_last_folder); add_check(help_box, 'Retomar processamento pendente', self.resume_processing); add_check(help_box, 'Modo silencioso', self.silent_mode); add_check(help_box, 'Limpar cache ao sair', self.clear_cache_on_exit)
        safe_box = section(tab_safe, 'Segurança e logs', 'Proteção dos arquivos, validação e histórico técnico em uma área própria.'); add_check(safe_box, 'Criar backup dos originais', self.create_backup); add_check(safe_box, 'Salvar PDF com páginas removidas', self.save_removed_pdf); add_check(safe_box, 'Validar saída final', self.validate_output); add_check(safe_box, 'Abrir resultado ao concluir', self.open_after); add_check(safe_box, 'Sobrescrever arquivo original', self.overwrite_original); add_check(safe_box, 'Salvar log automaticamente', self.auto_save_log); add_combo(safe_box, 'Nível de log', self.log_level, LOG_LEVELS, 'Debug registra mais detalhes; básico gera menos histórico.', 16); add_spin(safe_box, 'Retenção de logs (dias)', self.log_retention_days, 1, 3650)
        self.root.after_idle(lambda: _cuma_bind_config_scroll_recursive(wrap))

    def set_color_choice(self, theme_name):
        self.theme.set(theme_name); self.on_theme_choice_change()

    def on_theme_choice_change(self, _event=None):
        if self.theme.get() == 'Moderno Claro':
            self.theme_mode.set('Claro')
            self.custom_base_theme.set('Claro')
        elif self.theme.get() == 'Manga Dark':
            self.theme_mode.set('Personalizado')
            self.custom_base_theme.set('Escuro')
        else:
            self.theme_mode.set('Escuro')
            self.custom_base_theme.set('Escuro')
        self._apply_theme_mode_selection(save=True)

    def apply_manual_color_entries(self):
        self.ensure_color_role_vars()
        defaults = self.default_role_colors(self.theme.get())
        for key, var in self.color_role_vars.items():
            var.set(normalize_hex(var.get(), defaults.get(key, '#FFFFFF')))
        self.theme_mode.set('Personalizado')
        self.custom_accent.set(self.color_role_vars['primary'].get())
        self.sync_picker_states_from_roles()
        self.save_role_colors()
        self.apply_theme()
        self.save_current_config(force=True)

    def build_about_tab(self):
        wrap = ttk.Frame(self.tab_about, style='Card.TFrame', padding=4); wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Sobre o CUMA', style='TitleSmall.TLabel').pack(anchor='w', pady=(2, 4))
        ttk.Label(wrap, text=f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}', style='Muted.TLabel').pack(anchor='w')
        ttk.Label(wrap, text=APP_SUBTITLE, style='Muted.TLabel', wraplength=920, justify='left').pack(anchor='w', pady=(8, 10))
        ttk.Label(wrap, text=CUMA_ABOUT_TEXT, style='Muted.TLabel', wraplength=1040, justify='left').pack(anchor='w', pady=(4, 10))
        ttk.Button(wrap, text='Abrir manual completo', command=self.show_cuma_manual, style='Accent.TButton').pack(anchor='w', pady=(4, 0))

    def refresh_dashboard(self):
        cards = getattr(self, 'dashboard_cards', {})
        if not cards: return
        files_total = len(getattr(self, 'files', [])); results = getattr(self, 'results', []); ok = sum(1 for r in results if getattr(r, 'status', '') == 'OK'); err = sum(1 for r in results if getattr(r, 'status', '') == 'ERRO'); xteink_total = len(getattr(self, 'xteink_files', []))
        cards['files']['value'].set(f'{files_total} arquivo(s)'); cards['files']['subtitle'].set(f'OK: {ok}  •  Erros: {err}'); cards['xteink']['value'].set(f'{xteink_total} item(ns)'); cards['xteink']['subtitle'].set('Fila da aba Converter (EPUB / XTCH)'); cards['update']['value'].set(CHANGELOG_LATEST['version']); cards['update']['subtitle'].set(f'Atualizado em {CHANGELOG_LATEST["date"]}')
        if hasattr(self, 'toggle_btn'): self.toggle_btn.configure(text='☀ Tema claro' if self.theme.get() != 'Moderno Claro' else '🌙 Tema escuro')
        if hasattr(self, 'color_choice_note'): self.color_choice_note.set(f'Preset ativo: {THEME_VISUAL_PRESETS.get(self.theme.get(), THEME_VISUAL_PRESETS["Moderno Escuro"])["kind"]}.')

    def apply_theme(self):
        roles = self.current_role_colors(); base_theme = THEME_VISUAL_PRESETS.get(self.theme.get(), THEME_VISUAL_PRESETS['Moderno Escuro'])
        accent = roles['primary']; accent_hover = base_theme['accent_hover']; bg = roles['background']; surface = roles['surface']; surface2 = roles['surface2']; sidebar_bg = roles['sidebar_bg']; sidebar_item = surface if self.theme.get() == 'Moderno Claro' else '#1D232C'; sidebar_active = base_theme['sidebar_item_active']; fg = roles['text']; muted = base_theme['muted']; border = roles['border']; dark = self.theme.get() != 'Moderno Claro'; selection = base_theme['selection']; drop = base_theme['drop']; danger = roles['danger']; success = roles['primary']; field = surface
        self._theme_palette = {'accent': accent, 'bg': bg, 'surface': surface, 'surface2': surface2, 'sidebar_bg': sidebar_bg, 'fg': fg, 'muted': muted, 'border': border, 'drop': drop, 'selection': selection, 'danger': danger}; self._sidebar_colors = {'sidebar_bg': sidebar_bg, 'item_bg': sidebar_item, 'active_bg': sidebar_active, 'item_fg': muted, 'active_fg': fg, 'accent': accent, 'muted': muted}
        set_modern_switch_palette(surface=surface, surface2=surface2, fg=fg, muted=muted, accent=accent, border=border)
        self.set_windows_titlebar(dark)
        self.root.configure(bg=bg); self.root.option_add('*TCombobox*Listbox*Background', field); self.root.option_add('*TCombobox*Listbox*Foreground', fg); self.root.option_add('*TCombobox*Listbox*selectBackground', accent); self.root.option_add('*TCombobox*Listbox*selectForeground', '#ffffff')
        s = self.style
        s.configure('.', background=surface, foreground=fg, fieldbackground=field, bordercolor=border, lightcolor=border, darkcolor=border, relief='flat'); s.configure('App.TFrame', background=bg); s.configure('Card.TFrame', background=surface, relief='flat', borderwidth=0); s.configure('Header.TFrame', background=surface, relief='flat', borderwidth=0); s.configure('SummaryCard.TFrame', background=surface2, relief='flat', borderwidth=0)
        s.configure('TLabel', background=surface, foreground=fg); s.configure('Title.TLabel', background=surface, foreground=fg, font=('Segoe UI', 18, 'bold')); s.configure('HeaderSub.TLabel', background=surface, foreground=muted, font=('Segoe UI', 10)); s.configure('TitleSmall.TLabel', background=surface, foreground=fg, font=('Segoe UI', 12, 'bold')); s.configure('Muted.TLabel', background=surface, foreground=muted, font=('Segoe UI', 9)); s.configure('SummaryCardTitle.TLabel', background=surface2, foreground=muted, font=('Segoe UI', 9, 'bold')); s.configure('SummaryCardValue.TLabel', background=surface2, foreground=fg, font=('Segoe UI', 17, 'bold')); s.configure('SummaryCardNote.TLabel', background=surface2, foreground=muted, font=('Segoe UI', 9)); s.configure('Drop.TLabel', background=drop, foreground=muted, relief='flat', borderwidth=0, padding=14); s.configure('TNotebook', background=bg, borderwidth=0, tabmargins=(0, 0, 0, 0)); s.configure('TNotebook.Tab', background=surface2, foreground=muted, bordercolor=border, lightcolor=surface2, darkcolor=surface2, padding=(16, 9)); s.map('TNotebook.Tab', background=[('selected', surface), ('active', drop)], foreground=[('selected', fg), ('active', fg)]); s.configure('Card.TLabelframe', background=surface, bordercolor=border, relief='flat'); s.configure('Card.TLabelframe.Label', background=surface, foreground=fg)
        for style_name, style_bg, style_fg, hover in (('Header.TButton', surface2, fg, drop), ('Ghost.TButton', surface2, fg, drop), ('Accent.TButton', accent, '#ffffff', accent_hover), ('Danger.TButton', surface2, danger, drop)):
            s.configure(style_name, background=style_bg, foreground=style_fg, bordercolor=style_bg, focusthickness=0, focuscolor=style_bg, relief='flat', borderwidth=0, padding=(14, 10), font=('Segoe UI', 9, 'bold' if style_name == 'Accent.TButton' else 'normal')); s.map(style_name, background=[('active', hover), ('pressed', hover), ('disabled', surface2)], foreground=[('disabled', muted), ('active', style_fg), ('pressed', style_fg)])
        s.configure('Treeview', background=surface, foreground=fg, fieldbackground=surface, bordercolor=border, relief='flat', borderwidth=0, rowheight=32); s.configure('Treeview.Heading', background=surface2, foreground=fg, bordercolor=surface2, relief='flat', borderwidth=0, font=('Segoe UI', 9, 'bold'), padding=(10, 8)); s.map('Treeview', background=[('selected', selection)], foreground=[('selected', fg if not dark else '#ffffff')]); s.configure('TEntry', fieldbackground=field, foreground=fg, insertcolor=fg, bordercolor=border, lightcolor=border, darkcolor=border, relief='flat', borderwidth=1, padding=(10, 8)); s.configure('TCombobox', fieldbackground=field, background=surface2, foreground=fg, selectbackground=field, selectforeground=fg, bordercolor=border, arrowcolor=fg, relief='flat', borderwidth=1, padding=(10, 8)); s.map('TCombobox', fieldbackground=[('readonly', field), ('!disabled', field)], foreground=[('readonly', fg), ('!disabled', fg)])
        s.configure('Horizontal.TProgressbar', background=accent, troughcolor=surface2, bordercolor=surface2, lightcolor=accent, darkcolor=accent); s.configure('Vertical.TScrollbar', background=surface2, troughcolor=bg, bordercolor=surface2, arrowcolor=fg, relief='flat', borderwidth=0); s.configure('Switch.TFrame', background=surface); s.configure('SwitchText.TLabel', background=surface, foreground=fg, font=('Segoe UI', 9)); set_modern_switch_palette(surface=surface, surface2=surface2, fg=fg, muted=muted, accent=accent, border=border, disabled=muted)
        if hasattr(self, 'config_canvas'): self.config_canvas.configure(bg=bg)
        if hasattr(self, 'canvas'): self.canvas.configure(bg=surface)
        if hasattr(self, 'log_text'): self.log_text.configure(bg=field, fg=fg, insertbackground=fg, selectbackground=selection, selectforeground='#ffffff' if dark else fg, relief='flat', bd=0)
        if hasattr(self, 'sidebar'): self.update_sidebar_selection()
        if hasattr(self, 'result_tree'):
            try: self.result_tree.tag_configure('ok', foreground=success); self.result_tree.tag_configure('err', foreground=danger)
            except Exception: pass
        if getattr(self, 'color_choice_ready', False): self._render_color_choice()
        self.refresh_dashboard()

    def update_counter(self):
        super().update_counter(); self.refresh_dashboard()



# =============================================================================
# CUMA - Conversor Ultimate de Mangás - Base 1.0.6.0.2 + correção do bug visual das abas
# =============================================================================
# Entrega solicitada: voltar para CUMA_1_0_6_0_2_progressos_ferramentas
# e aplicar SOMENTE a correção da seleção visual das abas/sidebar.
# =============================================================================

# =============================================================================
# CUMA - textos do manual
# =============================================================================
CUMA_ABOUT_TEXT = """Partes do sistema:
• Limpar: organiza PDFs na fila e executa a limpeza/exportação conforme as opções escolhidas.
• Ferramentas: extrai páginas de PDFs como imagens e cria PDF a partir de imagens.
• Converter: reúne conversões para EPUB e XTCH, com perfis de dispositivo e qualidade.
• Resultados: mostra o retorno dos processamentos concluídos.
• Registros: centraliza mensagens de log e diagnóstico.
• Configurações: controla aparência, comportamento, desempenho, prévia, logs e pastas.
• Sobre: apresenta o resumo do CUMA e acesso ao manual completo."""
CUMA_MANUAL_TEXT = """MANUAL DO PROGRAMA - CUMA - Conversor Ultimate de Mangás

Use rodar_cuma.bat para abrir o programa.
Use criar_exe_windows_e_zip.bat para criar o executável Windows e compactar a saída em ZIP.
"""
def ensure_manual() -> Path:
    try:
        manual_path().write_text(CUMA_MANUAL_TEXT, encoding="utf-8")
    except Exception:
        pass
    return manual_path()

CUMA_BASE_VERSION = '1.080.0'
CUMA_UPDATE_SCALE = 'small_patch_sidebar_selection'
CUMA_VERSION_HISTORY_FILE = 'cuma_version_history.json'
CUMA_TAB_OUTPUT_NAMES = {'Limpar':'Limpar','Limpar PDF':'Limpar','Converter':'Converter','XTEINK':'Converter','Ferramentas':'Ferramentas'}


def cuma_calculate_dynamic_version(base_version: str = CUMA_BASE_VERSION, update_scale: str = CUMA_UPDATE_SCALE) -> str:
    nums = [int(x) for x in re.findall(r'\d+', str(base_version))[:5]]
    while len(nums) < 5:
        nums.append(0)
    major, minor, feature, recovery, patch = nums[:5]
    if update_scale == 'full_rebuild':
        minor += 1; feature = 0; recovery = 0; patch = 0
    elif update_scale == 'recovery_partial':
        recovery += 5; patch = 0
    elif update_scale == 'half_patch':
        patch += 5
    else:
        patch += 1
    return f'{major}.{minor}.{feature}.{recovery}.{patch}'

APP_DISPLAY_VERSION = '1.080.0'


def cuma_register_version_event(update_scale: str, description: str) -> None:
    try:
        path = runtime_dir() / CUMA_VERSION_HISTORY_FILE
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'events': []}
        if not isinstance(data, dict):
            data = {'events': []}
        events = data.get('events', []) if isinstance(data.get('events', []), list) else []
        events.append({'version': APP_DISPLAY_VERSION, 'base_version': CUMA_BASE_VERSION, 'update_scale': update_scale, 'description': description, 'timestamp': datetime.now().isoformat(timespec='seconds')})
        data['events'] = events[-50:]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def _cuma_default_output_root() -> Path:
    root = runtime_dir() / 'limpos'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cuma_tab_output_dir(tab_label: str, create: bool = True) -> Path:
    target = _cuma_default_output_root() / CUMA_TAB_OUTPUT_NAMES.get(tab_label, tab_label or 'Ferramentas')
    if create:
        target.mkdir(parents=True, exist_ok=True)
    return target

# =============================================================================
# Correção da seleção visual da sidebar/abas
# =============================================================================
def _cuma_normalize_tab_label(self, label):
    try:
        if label in self.pages:
            return label
        aliases = {'Limpeza':'Limpar','Limpar PDF':'Limpar','Config':'Configurações','Configuracoes':'Configurações','XTEINK':'Converter'}
        alias = aliases.get(str(label), label)
        if alias in self.pages:
            return alias
        return 'Limpar' if 'Limpar' in self.pages else next(iter(self.pages))
    except Exception:
        return label


def _cuma_force_sidebar_selection(self, active_label=None):
    try:
        active_label = _cuma_normalize_tab_label(self, active_label or getattr(self, '_current_tab_label', None))
        self._current_tab_label = active_label
        colors = getattr(self, '_sidebar_colors', {}) or {}
        pal = getattr(self, '_theme_palette', {}) or {}
        outer_bg = colors.get('sidebar_bg', pal.get('sidebar_bg', '#161A20'))
        active_bg = colors.get('active_bg', pal.get('sidebar_item_active', '#1F2937'))
        inactive_bg = colors.get('item_bg', pal.get('sidebar_item', '#111827'))
        active_fg = colors.get('active_fg', pal.get('fg', '#FFFFFF'))
        inactive_fg = colors.get('item_fg', pal.get('muted', '#9CA3AF'))
        accent = colors.get('accent', pal.get('accent', '#2563EB'))
        for label, item in getattr(self, 'nav_items', {}).items():
            active = label == active_label
            bg = active_bg if active else inactive_bg
            fg = active_fg if active else inactive_fg
            indicator_bg = accent if active else outer_bg
            try: item['container'].configure(bg=outer_bg)
            except Exception: pass
            for key in ('body','icon','text'):
                try: item[key].configure(bg=bg)
                except Exception: pass
            try: item['icon'].configure(fg=fg)
            except Exception: pass
            try: item['text'].configure(fg=fg)
            except Exception: pass
            try: item['indicator'].configure(bg=indicator_bg)
            except Exception: pass
        try: self.sidebar.configure(bg=outer_bg)
        except Exception: pass
        try: self.sidebar_top.configure(bg=outer_bg)
        except Exception: pass
        return active_label
    except Exception as exc:
        try: write_log(f'Erro na seleção visual da sidebar: {exc}')
        except Exception: pass
        return active_label


def _cuma_update_sidebar_selection_fixed(self):
    return _cuma_force_sidebar_selection(self, getattr(self, '_current_tab_label', None))
App.update_sidebar_selection = _cuma_update_sidebar_selection_fixed


def _cuma_show_page_fixed(self, label, save_state=True):
    label = _cuma_normalize_tab_label(self, label)
    for page in self.pages.values():
        try: page.pack_forget()
        except Exception: pass
    self.pages[label].pack(fill='both', expand=True)
    self._current_tab_label = label
    _cuma_force_sidebar_selection(self, label)
    try:
        self.root.update_idletasks()
        self.root.after_idle(lambda lab=label: _cuma_force_sidebar_selection(self, lab))
        self.root.after(50, lambda lab=label: _cuma_force_sidebar_selection(self, lab))
    except Exception:
        pass
    if save_state and getattr(self, 'remember_last_tab', None) and self.remember_last_tab.get():
        self.cfg.last_tab = label
        save_config(self.cfg)
    return label
App.show_page = _cuma_show_page_fixed

_OLD_BUILD_SIDEBAR_FIX = App.build_sidebar
def _cuma_build_sidebar_fixed(self):
    result = _OLD_BUILD_SIDEBAR_FIX(self)
    try:
        for label, item in self.nav_items.items():
            for key in ('container','indicator','body','icon','text'):
                try:
                    item[key].bind('<Button-1>', lambda _e, tab=label: self.show_page(tab))
                    item[key].bind('<ButtonRelease-1>', lambda _e, tab=label: self.root.after_idle(lambda: self.show_page(tab)))
                except Exception:
                    pass
        _cuma_force_sidebar_selection(self, getattr(self, '_current_tab_label', 'Limpar'))
    except Exception as exc:
        try: write_log(f'Falha ao reforçar sidebar: {exc}')
        except Exception: pass
    return result
App.build_sidebar = _cuma_build_sidebar_fixed

_OLD_APPLY_THEME_FIX = App.apply_theme
def _cuma_apply_theme_fixed(self):
    result = _OLD_APPLY_THEME_FIX(self)
    try:
        _cuma_force_sidebar_selection(self, getattr(self, '_current_tab_label', 'Limpar'))
        self.root.after_idle(lambda: _cuma_force_sidebar_selection(self, getattr(self, '_current_tab_label', 'Limpar')))
    except Exception:
        pass
    return result
App.apply_theme = _cuma_apply_theme_fixed

# =============================================================================
# Base 1.0.6.0.2: Ferramentas estilo Limpar + barras de progresso
# =============================================================================
def _tools_accept_path(path: Path, kind: str) -> bool:
    return path.is_file() and (path.suffix.lower() == '.pdf' if kind == 'extract' else path.suffix.lower() in SUPPORTED_IMAGE_EXT)


def _tools_expand_paths(raw_paths, kind: str) -> list[Path]:
    out = []
    for raw in raw_paths:
        p = Path(str(raw).strip().strip('"').strip("'"))
        if p.is_dir():
            iterator = p.rglob('*.pdf') if kind == 'extract' else p.rglob('*')
            for f in iterator:
                if _tools_accept_path(f, kind): out.append(f)
        elif _tools_accept_path(p, kind):
            out.append(p)
    seen, unique = set(), []
    for p in out:
        try: key = str(p.resolve())
        except Exception: key = str(p)
        if key not in seen:
            seen.add(key); unique.append(p)
    return unique


def _tools_update_progress(self, kind: str, current: int, current_max: int, total: int, total_max: int, status: str = '') -> None:
    prefix = 'tools_extract' if kind == 'extract' else 'tools_create'
    try:
        current_bar = getattr(self, f'{prefix}_current_prog', None)
        total_bar = getattr(self, f'{prefix}_total_prog', None)
        status_var = getattr(self, f'{prefix}_status', None)
        if current_bar is not None:
            current_bar['maximum'] = max(1, int(current_max)); current_bar['value'] = max(0, min(int(current), int(current_max)))
        if total_bar is not None:
            total_bar['maximum'] = max(1, int(total_max)); total_bar['value'] = max(0, min(int(total), int(total_max)))
        if status_var is not None and status:
            status_var.set(status)
        self.root.update_idletasks()
    except Exception:
        pass


def _tools_tree_insert(self, kind: str, paths) -> None:
    files_attr = 'tools_extract_files' if kind == 'extract' else 'tools_create_files'
    tree_attr = 'tools_extract_tree' if kind == 'extract' else 'tools_create_tree'
    counter_attr = 'tools_extract_counter' if kind == 'extract' else 'tools_create_counter'
    files = list(getattr(self, files_attr, []))
    existing = {str(p.resolve()) for p in files if p.exists()}
    added = 0
    for p in _tools_expand_paths(paths, kind):
        key = str(p.resolve())
        if key in existing: continue
        files.append(p); existing.add(key); added += 1
        try: size = format_bytes(p.stat().st_size)
        except Exception: size = '-'
        getattr(self, tree_attr).insert('', 'end', values=(p.name, str(p.parent), size, 'Pronto'))
    setattr(self, files_attr, files)
    getattr(self, counter_attr).set(f'Arquivos: {len(files)} | adicionados agora: {added}')
    _tools_update_progress(self, kind, 0, 1, 0, max(1, len(files)), 'Pronto')


def _tools_selected_paths(self, kind: str) -> list[Path]:
    files = list(getattr(self, 'tools_extract_files' if kind == 'extract' else 'tools_create_files', []))
    tree = getattr(self, 'tools_extract_tree' if kind == 'extract' else 'tools_create_tree')
    all_items = list(tree.get_children())
    result = []
    for item in tree.selection():
        try:
            idx = all_items.index(item)
            if 0 <= idx < len(files): result.append(files[idx])
        except Exception: pass
    return result


def _tools_set_tree_status(self, kind: str, path: Path, status: str) -> None:
    tree = getattr(self, 'tools_extract_tree' if kind == 'extract' else 'tools_create_tree')
    files = list(getattr(self, 'tools_extract_files' if kind == 'extract' else 'tools_create_files', []))
    try:
        idx = next(i for i, p in enumerate(files) if str(p.resolve()) == str(path.resolve()))
        item = list(tree.get_children())[idx]
        vals = list(tree.item(item, 'values'))
        if len(vals) >= 4:
            vals[3] = status; tree.item(item, values=vals)
    except Exception: pass


def _tools_remove_selected(self, kind: str) -> None:
    files_attr = 'tools_extract_files' if kind == 'extract' else 'tools_create_files'
    tree_attr = 'tools_extract_tree' if kind == 'extract' else 'tools_create_tree'
    counter_attr = 'tools_extract_counter' if kind == 'extract' else 'tools_create_counter'
    files = list(getattr(self, files_attr, [])); tree = getattr(self, tree_attr); all_items = list(tree.get_children())
    remove_idxs = []
    for item in list(tree.selection()):
        try: remove_idxs.append(all_items.index(item))
        except Exception: pass
    for item in list(tree.selection()):
        try: tree.delete(item)
        except Exception: pass
    files = [p for i, p in enumerate(files) if i not in set(remove_idxs)]
    setattr(self, files_attr, files); getattr(self, counter_attr).set(f'Arquivos: {len(files)}')
    _tools_update_progress(self, kind, 0, 1, 0, max(1, len(files)), 'Lista atualizada')


def _tools_clear(self, kind: str) -> None:
    files_attr = 'tools_extract_files' if kind == 'extract' else 'tools_create_files'
    tree_attr = 'tools_extract_tree' if kind == 'extract' else 'tools_create_tree'
    counter_attr = 'tools_extract_counter' if kind == 'extract' else 'tools_create_counter'
    setattr(self, files_attr, [])
    tree = getattr(self, tree_attr)
    for item in tree.get_children(): tree.delete(item)
    getattr(self, counter_attr).set('Arquivos: 0')
    _tools_update_progress(self, kind, 0, 1, 0, 1, 'Lista limpa')


def _tools_add_files(self, kind: str) -> None:
    if kind == 'extract': files = filedialog.askopenfilenames(title='Adicionar PDFs', filetypes=[('PDF', '*.pdf')])
    else: files = filedialog.askopenfilenames(title='Adicionar imagens', filetypes=[('Imagens', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff')])
    _tools_tree_insert(self, kind, files)


def _tools_add_folder(self, kind: str) -> None:
    folder = filedialog.askdirectory(title='Adicionar pasta')
    if folder: _tools_tree_insert(self, kind, [folder])


def _tools_paste(self, kind: str) -> None:
    try: data = self.root.clipboard_get()
    except Exception: data = ''
    _tools_tree_insert(self, kind, parse_drop(data, self.root))


def _tools_preview(self, kind: str) -> None:
    paths = _tools_selected_paths(self, kind) or list(getattr(self, 'tools_extract_files' if kind == 'extract' else 'tools_create_files', []))[:1]
    if not paths:
        messagebox.showinfo('Prévia', 'Adicione ou selecione um arquivo.'); return
    p = paths[0]
    if kind == 'extract':
        try: PreviewWindow(self, p)
        except Exception as exc: messagebox.showerror('Prévia', friendly_error(exc))
    else:
        top = tk.Toplevel(self.root); top.title(f'Prévia - {p.name}'); top.geometry('720x820')
        try:
            im = Image.open(p).convert('RGB'); im.thumbnail((680, 760), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im); lbl = ttk.Label(top, image=photo); lbl.image = photo; lbl.pack(padx=10, pady=10)
            ttk.Label(top, text=str(p), style='Muted.TLabel', wraplength=680).pack(); im.close()
        except Exception as exc:
            messagebox.showerror('Prévia', friendly_error(exc)); top.destroy()


def _tools_bind_drop(self, widget, kind: str) -> None:
    if not DND_AVAILABLE: return
    try:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind('<<Drop>>', lambda e, k=kind: _tools_tree_insert(self, k, parse_drop(e.data, self.root)))
    except Exception: pass


def _tools_make_clean_like_tab(self, parent, kind: str, title: str, subtitle: str) -> None:
    drop = ttk.Label(parent, text=f'Arraste arquivos ou pastas aqui — {title}', style='Drop.TLabel', anchor='center', padding=18)
    drop.pack(fill='x', pady=(0, 10)); _tools_bind_drop(self, drop, kind)
    top = ttk.Frame(parent, style='Card.TFrame'); top.pack(fill='x', pady=(0, 10))
    for label, cmd, style in [
        ('Adicionar arquivo(s)', lambda k=kind: _tools_add_files(self, k), 'Ghost.TButton'),
        ('Adicionar pasta', lambda k=kind: _tools_add_folder(self, k), 'Ghost.TButton'),
        ('Colar caminho', lambda k=kind: _tools_paste(self, k), 'Ghost.TButton'),
        ('Remover', lambda k=kind: _tools_remove_selected(self, k), 'Ghost.TButton'),
        ('Limpar lista', lambda k=kind: _tools_clear(self, k), 'Ghost.TButton'),
        ('Prévia', lambda k=kind: _tools_preview(self, k), 'Accent.TButton'),
        ('Abrir pasta Ferramentas', lambda: open_folder(_cuma_tab_output_dir('Ferramentas', True)), 'Ghost.TButton')]:
        ttk.Button(top, text=label, command=cmd, style=style).pack(side='left', padx=4)
    ttk.Label(parent, text=subtitle, style='Muted.TLabel', wraplength=1100, justify='left').pack(anchor='w', pady=(0, 8))
    opts = ttk.Frame(parent, style='Card.TFrame'); opts.pack(fill='x', pady=(0, 8))
    if kind == 'extract':
        ttk.Checkbutton(opts, text='Salvar como PNG; desligado salva JPG', variable=self.tools_extract_png).pack(side='left', padx=(0, 14))
        ttk.Checkbutton(opts, text='Abrir pasta ao concluir', variable=self.tools_extract_open_after).pack(side='left', padx=(0, 14))
        ttk.Label(opts, text='Zoom/renderização', style='Muted.TLabel').pack(side='left', padx=(10, 6)); ttk.Spinbox(opts, from_=1, to=4, textvariable=self.tools_extract_zoom, width=5).pack(side='left')
    else:
        ttk.Label(opts, text='Nome do PDF', style='Muted.TLabel').pack(side='left'); ttk.Entry(opts, textvariable=self.tools_pdf_name, width=34).pack(side='left', padx=(10, 16))
        ttk.Checkbutton(opts, text='Abrir pasta ao concluir', variable=self.tools_pdf_open_after).pack(side='left')
    cols = ('arquivo', 'pasta', 'tamanho', 'status')
    tree_frame = ttk.Frame(parent, style='Card.TFrame')
    tree_frame.pack(fill='both', expand=True, pady=(0, 6))
    tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=7)
    tree_y = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=tree_y.set)
    for col, width, title_col in zip(cols, (260, 540, 100, 140), ('Arquivo', 'Pasta', 'Tamanho', 'Status')):
        tree.heading(col, text=title_col); tree.column(col, width=width, anchor='w')
    tree.pack(side='left', fill='both', expand=True)
    tree_y.pack(side='right', fill='y')
    _tools_bind_drop(self, tree, kind)
    progress = ttk.LabelFrame(parent, text='Progresso', padding=8, style='Card.TLabelframe'); progress.pack(fill='x', pady=(8, 0))
    status_var = tk.StringVar(value='Pronto')
    ttk.Label(progress, textvariable=status_var, style='Muted.TLabel').pack(anchor='w', pady=(0, 4))
    ttk.Label(progress, text='Arquivo atual', style='Muted.TLabel').pack(anchor='w')
    current_prog = ttk.Progressbar(progress, mode='determinate'); current_prog.pack(fill='x', pady=(0, 6))
    ttk.Label(progress, text='Total', style='Muted.TLabel').pack(anchor='w')
    total_prog = ttk.Progressbar(progress, mode='determinate'); total_prog.pack(fill='x')
    bottom = ttk.Frame(parent, style='Card.TFrame'); bottom.pack(fill='x', pady=10)
    counter = tk.StringVar(value='Arquivos: 0'); ttk.Label(bottom, textvariable=counter, style='Muted.TLabel').pack(side='left')
    if kind == 'extract':
        self.tools_extract_tree = tree; self.tools_extract_counter = counter; self.tools_extract_current_prog = current_prog; self.tools_extract_total_prog = total_prog; self.tools_extract_status = status_var
        ttk.Button(bottom, text='Processar selecionados', command=lambda: _tools_process_extract(self, True), style='Accent.TButton').pack(side='right', padx=4)
        ttk.Button(bottom, text='Processar todos', command=lambda: _tools_process_extract(self, False), style='Ghost.TButton').pack(side='right', padx=4)
    else:
        self.tools_create_tree = tree; self.tools_create_counter = counter; self.tools_create_current_prog = current_prog; self.tools_create_total_prog = total_prog; self.tools_create_status = status_var
        ttk.Button(bottom, text='Criar PDF dos selecionados', command=lambda: _tools_process_create_pdf(self, True), style='Accent.TButton').pack(side='right', padx=4)
        ttk.Button(bottom, text='Criar PDF de todos', command=lambda: _tools_process_create_pdf(self, False), style='Ghost.TButton').pack(side='right', padx=4)


def _build_tools_tab_base_10602(self) -> None:
    for child in list(self.tab_tools.winfo_children()):
        try: child.destroy()
        except Exception: pass
    self.tools_extract_files = []; self.tools_create_files = []
    self.tools_extract_png = tk.BooleanVar(value=True); self.tools_extract_open_after = tk.BooleanVar(value=True); self.tools_extract_zoom = tk.IntVar(value=2)
    self.tools_pdf_open_after = tk.BooleanVar(value=True); self.tools_pdf_name = tk.StringVar(value='imagens_unidas.pdf')
    wrap = ttk.Frame(self.tab_tools, style='Card.TFrame'); wrap.pack(fill='both', expand=True)
    # Título removido para economizar espaço visual
    # Texto técnico removido da interface final
    nb = ttk.Notebook(wrap); nb.pack(fill='both', expand=True)
    tab_extract = ttk.Frame(nb, padding=10, style='Card.TFrame'); tab_create = ttk.Frame(nb, padding=10, style='Card.TFrame')
    nb.add(tab_extract, text='Extrair páginas'); nb.add(tab_create, text='Criar PDF de imagens')
    _tools_make_clean_like_tab(self, tab_extract, 'extract', 'Extrair páginas', 'Extrai páginas dos PDFs desta lista como PNG/JPG. A saída vai para limpos/Ferramentas/<nome do PDF>.')
    _tools_make_clean_like_tab(self, tab_create, 'create', 'Criar PDF de imagens', 'Cria um PDF único usando as imagens desta lista. A saída vai para limpos/Ferramentas.')
    diag = ttk.LabelFrame(wrap, text='', padding=10, style='Card.TLabelframe'); diag.pack(fill='x', pady=(10, 0))
    self.tools_debug_var = tk.StringVar(value='Ferramentas 1.0.6.0.2 carregadas; seleção visual das abas corrigida.')
    ttk.Label(diag, textvariable=self.tools_debug_var, style='Muted.TLabel', wraplength=1100, justify='left').pack(anchor='w')
BaseApp.build_tools_tab = _build_tools_tab_base_10602


def _tools_process_extract(self, selected=False) -> None:
    paths = _tools_selected_paths(self, 'extract') if selected else list(getattr(self, 'tools_extract_files', []))
    if not paths: messagebox.showinfo('Extrair páginas', 'Adicione ou selecione PDFs nesta ferramenta.'); return
    out = _cuma_tab_output_dir('Ferramentas', True); use_png = bool(self.tools_extract_png.get()); ext = 'png' if use_png else 'jpg'; fmt = 'PNG' if use_png else 'JPEG'
    try: zoom = max(1, min(4, int(self.tools_extract_zoom.get())))
    except Exception: zoom = 2
    debug = {'acao':'extrair_paginas_pdf_como_imagens','versao':APP_DISPLAY_VERSION,'arquivos':[str(p) for p in paths],'saida':str(out),'formato':fmt,'zoom':zoom,'status':'iniciado','resultados':[]}
    try:
        for file_index, pdf in enumerate(paths, 1):
            _tools_set_tree_status(self, 'extract', pdf, 'Processando')
            doc = fitz.open(str(pdf)); folder = out / pdf.stem; folder.mkdir(parents=True, exist_ok=True); page_count = len(doc); count = 0
            try:
                for i, page in enumerate(doc, 1):
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False); im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                    target = folder / f'page_{i:04d}.{ext}'
                    if fmt == 'PNG': im.save(target, format='PNG', optimize=True)
                    else: im.save(target, format='JPEG', quality=95, optimize=True)
                    im.close(); count += 1
                    _tools_update_progress(self, 'extract', i, max(1, page_count), file_index-1, len(paths), f'{pdf.name}: página {i}/{page_count}')
            finally: doc.close()
            _tools_set_tree_status(self, 'extract', pdf, 'OK'); _tools_update_progress(self, 'extract', page_count, max(1, page_count), file_index, len(paths), f'Concluído: {pdf.name}')
            debug['resultados'].append({'pdf':str(pdf),'pasta':str(folder),'paginas_exportadas':count}); self.log(f'Ferramentas / Extrair páginas: {pdf.name} → {folder} ({count} imagens)')
        debug['status'] = 'ok'; self.tools_debug_var.set(f'Extração concluída: {len(paths)} PDF(s), saída em {out}')
        if self.tools_extract_open_after.get(): open_folder(out)
        messagebox.showinfo('Extrair páginas', f'Extração concluída em:\n{out}')
    except Exception as exc:
        debug['status']='erro'; debug['erro']=friendly_error(exc); write_error_log(type(exc), exc, exc.__traceback__, 'Erro na ferramenta Extrair páginas'); messagebox.showerror('Extrair páginas', friendly_error(exc))
    finally:
        try: (runtime_dir() / 'debug_ferramentas_extrair_paginas.json').write_text(json.dumps(debug, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        except Exception: pass


def _tools_process_create_pdf(self, selected=False) -> None:
    paths = _tools_selected_paths(self, 'create') if selected else list(getattr(self, 'tools_create_files', []))
    if not paths: messagebox.showinfo('Criar PDF', 'Adicione ou selecione imagens nesta ferramenta.'); return
    out_dir = _cuma_tab_output_dir('Ferramentas', True); name = self.tools_pdf_name.get().strip() or 'imagens_unidas.pdf'
    if not name.lower().endswith('.pdf'): name += '.pdf'
    output = unique_path(out_dir / name); image_paths = [Path(p) for p in paths if Path(p).suffix.lower() in SUPPORTED_IMAGE_EXT]
    debug = {'acao':'criar_pdf_a_partir_de_imagens','versao':APP_DISPLAY_VERSION,'imagens':[str(p) for p in image_paths],'saida':str(output),'status':'iniciado'}
    pil_images = []
    try:
        if not image_paths: raise RuntimeError('Nenhuma imagem válida na lista.')
        for i, p in enumerate(image_paths, 1):
            _tools_set_tree_status(self, 'create', p, 'Carregando')
            im = Image.open(p).convert('RGB'); pil_images.append(im); _tools_set_tree_status(self, 'create', p, 'OK')
            _tools_update_progress(self, 'create', i, len(image_paths), 0, 1, f'Carregando imagem {i}/{len(image_paths)}')
        output.parent.mkdir(parents=True, exist_ok=True); _tools_update_progress(self, 'create', len(image_paths), len(image_paths), 0, 1, 'Salvando PDF...')
        pil_images[0].save(output, save_all=True, append_images=pil_images[1:])
        _tools_update_progress(self, 'create', len(image_paths), len(image_paths), 1, 1, f'PDF criado: {output.name}')
        debug['status']='ok'; debug['total_imagens']=len(image_paths); self.log(f'Ferramentas / Criar PDF de imagens: {len(image_paths)} imagem(ns) → {output}')
        self.tools_debug_var.set(f'PDF criado com {len(image_paths)} imagem(ns): {output}')
        if self.tools_pdf_open_after.get(): open_folder(output)
        messagebox.showinfo('Criar PDF', f'PDF criado:\n{output}')
    except Exception as exc:
        debug['status']='erro'; debug['erro']=friendly_error(exc); write_error_log(type(exc), exc, exc.__traceback__, 'Erro na ferramenta Criar PDF de imagens'); messagebox.showerror('Criar PDF', friendly_error(exc))
    finally:
        for im in pil_images:
            try: im.close()
            except Exception: pass
        try: (runtime_dir() / 'debug_ferramentas_criar_pdf_imagens.json').write_text(json.dumps(debug, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        except Exception: pass
BaseApp.extract_selected_to_images = lambda self: _tools_process_extract(self, selected=False)
BaseApp.create_pdf_from_images_dialog = lambda self: _tools_process_create_pdf(self, selected=False)

# =============================================================================
# Conversor antigo removido do código-base
# =============================================================================

def cuma_base_10602_fix_debug() -> dict:
    return {
        'base_solicitada': 'CUMA_1_0_6_0_2_progressos_ferramentas.zip',
        'runtime_version': APP_DISPLAY_VERSION,
        'base_preservada': ['Ferramentas estilo Limpar', 'Barras de progresso nas duas ferramentas', 'Converter com pasta/qualidade'],
        'correcao_aplicada': ['show_page força seleção da sidebar', 'update_sidebar_selection robusto', 'after_idle e after(50) para impedir aba antiga azul']
    }


def write_full_debug_report() -> Path:
    path = runtime_dir() / 'debug_completo_cuma.txt'
    root = _cuma_default_output_root()
    payload = {
        'app': {'name': APP_DISPLAY_NAME, 'version': APP_DISPLAY_VERSION, 'runtime_dir': str(runtime_dir()), 'frozen': bool(getattr(sys, 'frozen', False))},
        'environment': environment_diagnostics() if 'environment_diagnostics' in globals() else {},
        'output': {'root': str(root), 'limpar': str(root/'Limpar'), 'converter': str(root/'Converter'), 'ferramentas': str(root/'Ferramentas')},
        'base_10602_fix_abas': cuma_base_10602_fix_debug(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return path

# Registro antigo desativado: o sistema 1.080.0 registra eventos com ID único para não duplicar a cada execução.
# cuma_register_version_event(CUMA_UPDATE_SCALE, 'Base 1.0.6.0.2 restaurada com correção visual das abas.')



# =============================================================================
# CUMA HOTFIX SEGURO - seletor de cor otimizado sem alterar conversões
# =============================================================================
def _cuma_open_color_picker_fast(self):
    """Seletor de cor otimizado: durante o arraste só move marcadores;
    HEX/prévia são atualizados no ButtonRelease ou após pausa curta.
    """
    current = normalize_hex(self.custom_accent.get(), '#2563EB')
    try:
        r0 = int(current[1:3], 16) / 255.0
        g0 = int(current[3:5], 16) / 255.0
        b0 = int(current[5:7], 16) / 255.0
        h0, s0, v0 = colorsys.rgb_to_hsv(r0, g0, b0)
    except Exception:
        h0, s0, v0 = 0.6, 0.8, 0.9
    state = {'h': h0, 's': s0, 'v': v0, 'pending_after': None, 'sv_dirty': True}
    top = tk.Toplevel(self.root)
    top.title('Personalizar cor')
    top.geometry('620x455')
    top.transient(self.root)
    try:
        pal = getattr(self, '_theme_palette', {}) or {}
        top.configure(bg=pal.get('bg', '#0F1318'))
    except Exception:
        pass
    wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
    wrap.pack(fill='both', expand=True)
    ttk.Label(wrap, text='Seletor de cores', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 10))
    sv = tk.Canvas(wrap, width=540, height=220, highlightthickness=1, highlightbackground='#38414E', bd=0)
    sv.pack(fill='x')
    hue = tk.Canvas(wrap, width=540, height=22, highlightthickness=0, bd=0)
    hue.pack(fill='x', pady=(14, 8))
    row1 = ttk.Frame(wrap, style='Card.TFrame')
    row1.pack(fill='x', pady=(6, 4))
    ttk.Label(row1, text='HEX', style='Muted.TLabel').pack(side='left')
    hex_var = tk.StringVar(value=current)
    hex_entry = ttk.Entry(row1, textvariable=hex_var, width=14)
    hex_entry.pack(side='left', padx=(10, 10))
    sample = tk.Canvas(row1, width=42, height=28, highlightthickness=1, highlightbackground='#38414E', bd=0)
    sample.pack(side='left', padx=(0, 10))
    def hsv_hex():
        rr, gg, bb = colorsys.hsv_to_rgb(state['h'], state['s'], state['v'])
        return '#%02X%02X%02X' % (int(rr*255), int(gg*255), int(bb*255))
    def put_img(canvas, img, attr):
        photo = ImageTk.PhotoImage(img)
        setattr(canvas, attr, photo)
        canvas.create_image(0, 0, image=photo, anchor='nw')
    def draw_hue_bg():
        hue.delete('all')
        w=max(20,int(hue.winfo_width() or 540)); h=max(6,int(hue.winfo_height() or 22))
        img=Image.new('RGB',(w,h)); pix=img.load()
        for x in range(w):
            rr,gg,bb=colorsys.hsv_to_rgb(x/max(1,w-1),1,1); col=(int(rr*255),int(gg*255),int(bb*255))
            for y in range(h): pix[x,y]=col
        put_img(hue,img,'_cuma_hue_photo'); draw_hue_marker()
    def draw_hue_marker():
        hue.delete('hue_marker')
        w=max(20,int(hue.winfo_width() or 540)); h=max(6,int(hue.winfo_height() or 22)); hx=int(state['h']*(w-1))
        hue.create_oval(hx-5,1,hx+5,h-1,outline='white',width=2,tags=('hue_marker',))
    def draw_sv_bg():
        sv.delete('all')
        w=max(20,int(sv.winfo_width() or 540)); h=max(20,int(sv.winfo_height() or 220))
        img=Image.new('RGB',(w,h)); pix=img.load()
        for x in range(w):
            ss=x/max(1,w-1)
            for y in range(h):
                vv=1-y/max(1,h-1); rr,gg,bb=colorsys.hsv_to_rgb(state['h'],ss,vv); pix[x,y]=(int(rr*255),int(gg*255),int(bb*255))
        put_img(sv,img,'_cuma_sv_photo'); state['sv_dirty']=False; draw_sv_marker()
    def draw_sv_marker():
        sv.delete('sv_marker')
        w=max(20,int(sv.winfo_width() or 540)); h=max(20,int(sv.winfo_height() or 220))
        px=int(state['s']*(w-1)); py=int((1-state['v'])*(h-1))
        sv.create_oval(px-7,py-7,px+7,py+7,outline='white',width=2,tags=('sv_marker',))
    def update_dialog_only(update_entry=True):
        color=hsv_hex()
        if update_entry: hex_var.set(color)
        sample.delete('all'); sample.configure(bg=color); sample.create_rectangle(2,2,40,26,fill=color,outline='#E5E7EB')
        self._cuma_update_accent_preview(color)
        return color
    def commit_color(update_entry=True, apply_to_app=False):
        if state.get('pending_after'):
            try: top.after_cancel(state['pending_after'])
            except Exception: pass
            state['pending_after']=None
        if state.get('sv_dirty'): draw_sv_bg()
        color=update_dialog_only(update_entry)
        try: self.custom_accent.set(color)
        except Exception: pass
        if apply_to_app: self._cuma_apply_accent_from_entry(color)
        return color
    def schedule_commit(delay=220):
        if state.get('pending_after'):
            try: top.after_cancel(state['pending_after'])
            except Exception: pass
        state['pending_after']=top.after(delay, lambda: commit_color(True, False))
    def sv_move(event):
        w=max(1,sv.winfo_width() or 540); h=max(1,sv.winfo_height() or 220)
        state['s']=min(1,max(0,event.x/max(1,w-1))); state['v']=min(1,max(0,1-event.y/max(1,h-1)))
        draw_sv_marker(); schedule_commit()
    def sv_release(event):
        sv_move(event); commit_color(True, False)
    def hue_move(event):
        w=max(1,hue.winfo_width() or 540); state['h']=min(1,max(0,event.x/max(1,w-1))); state['sv_dirty']=True
        draw_hue_marker(); schedule_commit()
    def hue_release(event):
        hue_move(event); commit_color(True, False)
    def entry_pick(_event=None):
        val=normalize_hex(hex_var.get(), hsv_hex()); hex_var.set(val)
        rr=int(val[1:3],16)/255.0; gg=int(val[3:5],16)/255.0; bb=int(val[5:7],16)/255.0
        state['h'],state['s'],state['v']=colorsys.rgb_to_hsv(rr,gg,bb); state['sv_dirty']=True; draw_hue_marker(); commit_color(False, False)
    sv.bind('<Button-1>', sv_move); sv.bind('<B1-Motion>', sv_move); sv.bind('<ButtonRelease-1>', sv_release)
    hue.bind('<Button-1>', hue_move); hue.bind('<B1-Motion>', hue_move); hue.bind('<ButtonRelease-1>', hue_release)
    hex_entry.bind('<Return>', entry_pick); hex_entry.bind('<FocusOut>', entry_pick)
    btns=ttk.Frame(wrap, style='Card.TFrame'); btns.pack(fill='x', pady=(12,0))
    ttk.Button(btns,text='Aplicar cor',command=lambda:(commit_color(True, True), top.destroy()),style='Accent.TButton').pack(side='right',padx=(8,0))
    ttk.Button(btns,text='Cancelar',command=top.destroy,style='Ghost.TButton').pack(side='right')
    top.after(120, lambda:(draw_hue_bg(), draw_sv_bg(), update_dialog_only(True)))

try:
    App._cuma_open_color_picker = _cuma_open_color_picker_fast
except Exception:
    pass


# =============================================================================
# CUMA 1.0.6.1.5 - CONVERTER REORGANIZADO + PERFIS DE DISPOSITIVO + UPDATE
# =============================================================================
CUMA_CONVERTER_DEVICE_UPDATE_VERSION = '1.080.0'
APP_DISPLAY_VERSION = CUMA_CONVERTER_DEVICE_UPDATE_VERSION
APP_VERSION = CUMA_CONVERTER_DEVICE_UPDATE_VERSION + ' CUMA'
APP_NAME = 'CUMA'
try:
    if 'Personalizado' not in XTEINK_DEVICES:
        XTEINK_DEVICES = tuple(list(XTEINK_DEVICES) + ['Personalizado'])
    XTEINK_DEVICE_PROFILES.setdefault('Personalizado', (600, 800))
except Exception:
    pass

def _cuma_runtime_json(name: str, default):
    p = app_dir() / name
    try:
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        pass
    return default

def _cuma_write_runtime_json(name: str, data) -> None:
    try:
        (app_dir() / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        try: write_log(f'Falha ao salvar {name}: {exc}')
        except Exception: pass

def _cuma_device_profiles() -> dict:
    data = _cuma_runtime_json('cuma_device_profiles.json', {})
    defaults = {
        'XTEINK X4': {'width': 480, 'height': 800, 'dpi': 212, 'jpeg_quality': 88, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0},
        'XTEINK X3': {'width': 528, 'height': 792, 'dpi': 212, 'jpeg_quality': 88, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0},
        'Personalizado': {'width': 600, 'height': 800, 'dpi': 200, 'jpeg_quality': 90, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0},
    }
    for k,v in defaults.items():
        data.setdefault(k, v)
    return data

def _cuma_save_device_profile(device: str, profile: dict) -> None:
    data = _cuma_device_profiles()
    data[device] = profile
    _cuma_write_runtime_json('cuma_device_profiles.json', data)
    try:
        XTEINK_DEVICE_PROFILES[device] = (int(profile.get('width', 600)), int(profile.get('height', 800)))
    except Exception:
        pass

def _cuma_sync_selected_device(self):
    try:
        dev = self.xteink_device.get()
        prof = _cuma_device_profiles().get(dev, {})
        if hasattr(self, 'xteink_quality') and prof.get('jpeg_quality') is not None:
            try: self.xteink_quality.set(int(prof.get('jpeg_quality', self.xteink_quality.get())))
            except Exception: pass
        if hasattr(self, 'xteink_device_note'):
            self.xteink_device_note.set(f"{dev}: {prof.get('width','?')}×{prof.get('height','?')} px, DPI {prof.get('dpi','?')}.")
    except Exception as exc:
        try: write_log(f'Falha ao sincronizar dispositivo: {exc}')
        except Exception: pass

def _cuma_choose_xteink_output(self):
    try:
        folder = filedialog.askdirectory(title='Escolher pasta de saída do Converter')
        if folder:
            self.xteink_output_dir.set(folder)
            try: self.output_dir.set(folder)
            except Exception: pass
            self.save_current_config()
    except Exception as exc:
        messagebox.showerror('Pasta de saída', friendly_error(exc))

def _cuma_build_xteink_tab_final(self) -> None:
    self.xteink_files = []
    self.xteink_input = tk.StringVar(value='')
    self.xteink_output_dir = tk.StringVar(value=getattr(self, 'output_dir', tk.StringVar(value='')).get() if hasattr(self, 'output_dir') else '')
    self.xteink_status = tk.StringVar(value='Converter pronto')
    self.xteink_counter = tk.StringVar(value='Arquivos: 0 | OK: 0 | Erros: 0')
    self.xteink_pdf_epub = tk.BooleanVar(value=False)
    self.xteink_pdf_xtch = tk.BooleanVar(value=True)
    self.xteink_epub_xtch = tk.BooleanVar(value=True)
    self.xteink_device_note = tk.StringVar(value='Selecione um dispositivo para aplicar resolução e perfil.')
    try:
        if self.xteink_device.get() not in XTEINK_DEVICES:
            self.xteink_device.set('XTEINK X4')
    except Exception:
        self.xteink_device = tk.StringVar(value='XTEINK X4')

    main = ttk.Frame(self.tab_xteink, style='Card.TFrame', padding=10); main.pack(fill='both', expand=True)
    top = ttk.LabelFrame(main, text='Dispositivos e conversões', padding=12, style='Card.TLabelframe'); top.pack(fill='x', pady=(0,10))
    ttk.Label(top, text='Dispositivo', style='Strong.TLabel').grid(row=0, column=0, sticky='w', padx=(0,8), pady=4)
    dev_combo = ttk.Combobox(top, textvariable=self.xteink_device, values=XTEINK_DEVICES, state='readonly', width=28)
    dev_combo.grid(row=0, column=1, sticky='w', padx=(0,8), pady=4)
    dev_combo.bind('<<ComboboxSelected>>', lambda _e: _cuma_sync_selected_device(self))
    ttk.Button(top, text='Aplicar perfil', command=lambda: _cuma_sync_selected_device(self), style='Accent.TButton').grid(row=0, column=2, padx=4, pady=4)
    ttk.Button(top, text='Editor de perfis', command=self.open_profile_editor, style='Ghost.TButton').grid(row=0, column=3, padx=4, pady=4)
    ttk.Label(top, text='Pasta de saída', style='Strong.TLabel').grid(row=1, column=0, sticky='w', padx=(0,8), pady=4)
    ttk.Entry(top, textvariable=self.xteink_output_dir, width=72).grid(row=1, column=1, columnspan=2, sticky='ew', padx=(0,8), pady=4)
    ttk.Button(top, text='Escolher', command=lambda: _cuma_choose_xteink_output(self), style='Ghost.TButton').grid(row=1, column=3, padx=4, pady=4)
    ttk.Label(top, text='Qualidade do arquivo (%)', style='Strong.TLabel').grid(row=2, column=0, sticky='w', padx=(0,8), pady=4)
    ttk.Spinbox(top, from_=40, to=100, textvariable=self.xteink_quality, width=8).grid(row=2, column=1, sticky='w', pady=4)
    ttk.Label(top, textvariable=self.xteink_device_note, style='Muted.TLabel').grid(row=2, column=2, columnspan=2, sticky='w', pady=4)
    top.columnconfigure(1, weight=1)

    self.xteink_drop = ttk.Label(main, text='Arraste PDFs, EPUBs ou pastas aqui', style='Drop.TLabel', anchor='center', padding=18); self.xteink_drop.pack(fill='x')
    buttons = ttk.Frame(main, style='Card.TFrame'); buttons.pack(fill='x', pady=10)
    for label, cmd, style in (("Adicionar arquivo(s)", self.add_xteink_files, "Ghost.TButton"), ("Adicionar pasta", self.add_xteink_folder, "Ghost.TButton"), ("Colar caminho", self.paste_xteink_paths, "Ghost.TButton"), ("Remover", self.remove_xteink_selected, "Ghost.TButton"), ("Limpar", self.clear_xteink_files, "Ghost.TButton"), ("Prévia", self.open_xteink_preview, "Accent.TButton"), ("Funções por tipo", self.open_xteink_settings_window, "Ghost.TButton"), ("Abrir pasta Converter", lambda: open_folder(Path(self.xteink_output_dir.get() or self.output_dir.get())), "Ghost.TButton")):
        ttk.Button(buttons, text=label, command=cmd, style=style).pack(side='left', padx=4)
    opts = ttk.Frame(main, style='Card.TFrame'); opts.pack(fill='x', pady=(0,8))
    ttk.Checkbutton(opts, text='PDF para EPUB', variable=self.xteink_pdf_epub).pack(side='left', padx=6)
    ttk.Checkbutton(opts, text='PDF para XTCH', variable=self.xteink_pdf_xtch).pack(side='left', padx=6)
    ttk.Checkbutton(opts, text='EPUB para XTCH', variable=self.xteink_epub_xtch).pack(side='left', padx=6)

    cols = ('arquivo','status','tipo','saida','resumo')
    frame = ttk.Frame(main, style='Card.TFrame'); frame.pack(fill='both', expand=True)
    self.xteink_tree = ttk.Treeview(frame, columns=cols, show='headings', height=7)
    y = ttk.Scrollbar(frame, orient='vertical', command=self.xteink_tree.yview); self.xteink_tree.configure(yscrollcommand=y.set)
    for col,width,title in zip(cols,(330,110,80,500,300),('Arquivo','Status','Tipo','Saída','Resumo')):
        self.xteink_tree.heading(col, text=title); self.xteink_tree.column(col, width=width, anchor='w')
    self.xteink_tree.pack(side='left', fill='both', expand=True); y.pack(side='right', fill='y')

    bottom = ttk.Frame(main, style='Card.TFrame'); bottom.pack(fill='x', pady=10)
    ttk.Label(bottom, textvariable=self.xteink_counter, style='Muted.TLabel').pack(side='left')
    self.xteink_cancel_btn = ttk.Button(bottom, text='Cancelar', command=self.cancel, state='disabled', style='Danger.TButton'); self.xteink_cancel_btn.pack(side='right', padx=4)
    self.xteink_pause_btn = ttk.Button(bottom, text='Pause', command=self.pause_processing, state='disabled', style='Ghost.TButton'); self.xteink_pause_btn.pack(side='right', padx=4)
    self.xteink_play_btn = ttk.Button(bottom, text='Play', command=self.resume_processing, state='disabled', style='Ghost.TButton'); self.xteink_play_btn.pack(side='right', padx=4)
    ttk.Button(bottom, text='Processar selecionados', command=lambda: self.process_xteink_selected(), style='Ghost.TButton').pack(side='right', padx=4)
    ttk.Button(bottom, text='Processar tudo', command=self.process_xteink_all, style='Accent.TButton').pack(side='right', padx=4)
    self.xteink_prog_total = ttk.Progressbar(main, mode='determinate'); self.xteink_prog_total.pack(fill='x', pady=(0,6))
    self.xteink_prog_current = ttk.Progressbar(main, mode='determinate'); self.xteink_prog_current.pack(fill='x')
    _cuma_sync_selected_device(self)
    try: self.enable_drop(self.xteink_drop, self.add_xteink_paths)
    except Exception: pass

def _cuma_open_xteink_functions_window(self):
    top = tk.Toplevel(self.root); top.title('Funções específicas do Converter'); top.geometry('780x560'); top.transient(self.root)
    wrap = ttk.Frame(top, style='Card.TFrame', padding=12); wrap.pack(fill='both', expand=True)
    ttk.Label(wrap, text='Funções por tipo de arquivo', style='TitleSmall.TLabel').pack(anchor='w', pady=(0,8))
    nb = ttk.Notebook(wrap); nb.pack(fill='both', expand=True)
    sections = {
        'PDF': [('PDF → EPUB', self.xteink_pdf_epub, 'Renderiza páginas do PDF como imagens e cria EPUB.'), ('PDF → XTCH', self.xteink_pdf_xtch, 'Converte PDF para XTCH com perfil de dispositivo.')],
        'EPUB': [('EPUB → XTCH', self.xteink_epub_xtch, 'Converte EPUB baseado em imagens para XTCH nativo.'), ('Manter ordem das imagens', tk.BooleanVar(value=True), 'Preserva a ordem original do EPUB.')],
        'XTCH': [('Otimizar para dispositivo selecionado', tk.BooleanVar(value=True), 'Aplica largura, altura, DPI e qualidade do perfil.'), ('Validar pacote XTCH', tk.BooleanVar(value=True), 'Confere se o arquivo final foi criado corretamente.')],
    }
    for name, rows in sections.items():
        f = ttk.Frame(nb, style='Card.TFrame', padding=12); nb.add(f, text=name)
        for label,var,desc in rows:
            ttk.Checkbutton(f, text=label, variable=var).pack(anchor='w', pady=(4,0))
            ttk.Label(f, text=desc, style='Muted.TLabel', wraplength=680).pack(anchor='w', padx=22, pady=(0,8))
    ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(10,0))

def _cuma_open_profile_editor_device(self):
    device = self.xteink_device.get()
    profiles = _cuma_device_profiles()
    prof = dict(profiles.get(device, profiles.get('Personalizado', {})))
    top = tk.Toplevel(self.root); top.title(f'Editor de perfis - {device}'); top.geometry('760x620'); top.transient(self.root)
    wrap = ttk.Frame(top, style='Card.TFrame', padding=12); wrap.pack(fill='both', expand=True)
    ttk.Label(wrap, text=f'Perfil do dispositivo: {device}', style='TitleSmall.TLabel').pack(anchor='w', pady=(0,8))
    device_name = tk.StringVar(value=device)
    if device == 'Personalizado':
        row = ttk.Frame(wrap, style='Card.TFrame'); row.pack(fill='x', pady=4)
        ttk.Label(row, text='Nome do dispositivo', width=22, style='Strong.TLabel').pack(side='left')
        ttk.Entry(row, textvariable=device_name, width=32).pack(side='left', padx=6)
    vars_map = {
        'width': tk.IntVar(value=int(prof.get('width', 600))), 'height': tk.IntVar(value=int(prof.get('height', 800))),
        'dpi': tk.IntVar(value=int(prof.get('dpi', 200))), 'jpeg_quality': tk.IntVar(value=int(prof.get('jpeg_quality', self.xteink_quality.get()))),
        'gamma': tk.DoubleVar(value=float(prof.get('gamma', 1.0))), 'contrast': tk.DoubleVar(value=float(prof.get('contrast', 1.0))),
        'sharpen': tk.DoubleVar(value=float(prof.get('sharpen', 0.0))), 'margin': tk.IntVar(value=int(prof.get('margin', 0))),
    }
    labels = [('width','Largura px'),('height','Altura px'),('dpi','DPI'),('jpeg_quality','Qualidade JPEG'),('gamma','Gamma'),('contrast','Contraste'),('sharpen','Nitidez'),('margin','Margem px')]
    for key,label in labels:
        row = ttk.Frame(wrap, style='Card.TFrame'); row.pack(fill='x', pady=4)
        ttk.Label(row, text=label, width=22, style='Strong.TLabel').pack(side='left')
        ttk.Entry(row, textvariable=vars_map[key], width=12).pack(side='left', padx=6)
    note = ttk.Label(wrap, text='Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.', style='Muted.TLabel', wraplength=700, justify='left'); note.pack(anchor='w', pady=12)
    def save_profile():
        name = device_name.get().strip() or 'Personalizado'
        data = {k:v.get() for k,v in vars_map.items()}
        _cuma_save_device_profile(name, data)
        if name not in XTEINK_DEVICES:
            try:
                globals()['XTEINK_DEVICES'] = tuple(list(XTEINK_DEVICES) + [name])
            except Exception: pass
        self.xteink_device.set(name)
        _cuma_sync_selected_device(self)
        messagebox.showinfo('Editor de perfis', f'Perfil salvo: {name}')
    btns = ttk.Frame(wrap, style='Card.TFrame'); btns.pack(fill='x', pady=(8,0))
    ttk.Button(btns, text='Salvar perfil', command=save_profile, style='Accent.TButton').pack(side='left')
    ttk.Button(btns, text='Fechar', command=top.destroy, style='Ghost.TButton').pack(side='left', padx=8)

try:
    App.build_xteink_tab = _cuma_build_xteink_tab_final
    App.open_xteink_settings_window = _cuma_open_xteink_functions_window
    App.open_profile_editor = _cuma_open_profile_editor_device
except Exception:
    pass

# Nome do sistema apenas "cuma".
try:
    _CUMA_OLD_SETUP_WINDOW_NAME = App.setup_window
    def _cuma_setup_window_name(self):
        r = _CUMA_OLD_SETUP_WINDOW_NAME(self)
        try: self.root.title('cuma')
        except Exception: pass
        return r
    App.setup_window = _cuma_setup_window_name
except Exception:
    pass

# Botão simples de atualização, não intrusivo. Usa URL configurável no config_cuma.json.
def _cuma_check_updates_button(self):
    try:
        cfg_path = app_dir() / 'config_cuma.json'
        data = {}
        try:
            if cfg_path.exists(): data = json.loads(cfg_path.read_text(encoding='utf-8'))
        except Exception: data = {}
        url = data.get('update_manifest_url', '')
        if not url:
            messagebox.showinfo('Procurar atualizações', 'Nenhum repositório configurado. Crie um arquivo version.json no GitHub e coloque a URL raw em config_cuma.json no campo update_manifest_url.')
            return
        import urllib.request
        with urllib.request.urlopen(url, timeout=8) as resp:
            remote = json.loads(resp.read().decode('utf-8'))
        latest = str(remote.get('version',''))
        if latest and latest != APP_DISPLAY_VERSION:
            messagebox.showinfo('Atualização encontrada', f'Versão disponível: {latest}\nBaixe em: {remote.get("download_url", "sem link informado")}')
        else:
            messagebox.showinfo('Procurar atualizações', 'Você já está usando a versão mais recente informada no repositório.')
    except Exception as exc:
        messagebox.showerror('Procurar atualizações', friendly_error(exc))
try:
    _CUMA_OLD_BUILD_UPDATE_BUTTON = App.build
    def _cuma_build_update_button(self):
        r = _CUMA_OLD_BUILD_UPDATE_BUTTON(self)
        try:
            if hasattr(self, 'header') and not getattr(self, '_update_button_added', False):
                self.update_btn = ttk.Button(self.header, text='Procurar atualizações', command=lambda: _cuma_check_updates_button(self), style='Header.TButton')
                self.update_btn.pack(side='right', padx=(8,0))
                self._update_button_added = True
        except Exception as exc:
            try: write_log(f'Falha ao adicionar botão de atualização: {exc}')
            except Exception: pass
        try: self.root.title('cuma')
        except Exception: pass
        return r
    App.build = _cuma_build_update_button
except Exception:
    pass


# =============================================================================
# CUMA - PATCH UNIFICADO (ESTABILIDADE + TEXTO/ÍCONES + CONVERTER)
# Baseado na versão estável e incorporando os hotfixes corretos sem retroceder.
# =============================================================================

_CUMA_MERGED_PATCH = 'stable_plus_text_ui_2026_06_22'


def _cuma_patch_debug_write(name: str, payload) -> None:
    try:
        p = runtime_dir() / name
        if isinstance(payload, str):
            p.write_text(payload, encoding='utf-8')
        else:
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    except Exception:
        pass


def _cuma_patch_log_exception(context: str, exc: Exception) -> None:
    try:
        write_log(f'[{_CUMA_MERGED_PATCH}] {context}: {exc}')
    except Exception:
        pass
    try:
        write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_patch_var_get(var, default=''):
    try:
        return var.get()
    except Exception:
        return default


def _cuma_patch_var_set(var, value) -> None:
    try:
        var.set(value)
    except Exception:
        pass


def _cuma_fix_mojibake_text(value: str) -> str:
    text = str(value or '')
    replacements = {
        'Pr√©via': 'Prévia', 'Configura√ß√µes': 'Configurações', 'Configurar√ß√µes': 'Configurações',
        'Op√ß√µes': 'Opções', 'Dispositivos e convers√µes': 'Dispositivos e conversões',
        'Dispositivos e convers/µes': 'Dispositivos e conversões', 'Pasta de sa√≠da': 'Pasta de saída',
        'Pasta de sa√­da': 'Pasta de saída', 'Qualidade padr√£o atual': 'Qualidade padrão atual',
        'Padr√£o': 'Padrão', 'Atualiza√ß√£o encontrada': 'Atualização encontrada',
        'Procurar atualiza√ß√µes': 'Procurar atualizações',
        'Falha ao adicionar bot√£o de atualiza√ß√£o': 'Falha ao adicionar botão de atualização',
        'Voc√™ j√° est√° usando a vers√£o mais recente informada no reposit√≥rio.': 'Você já está usando a versão mais recente informada no repositório.',
        'Nenhum reposit√≥rio configurado.': 'Nenhum repositório configurado.', 'Vers√£o dispon√≠vel': 'Versão disponível',
        'Selecione um dispositivo para aplicar resolu√ß√£o e perfil.': 'Selecione um dispositivo para aplicar resolução e perfil.',
        'Autom├ítico': 'Automático', '√©': 'é', '√£': 'ã', '√§': 'ç', '√µ': 'õ', '√°': 'á',
        '√º': 'ú', '√í': 'í', '√¢': 'â', '√™': 'ê', '√´': 'ô',
        '‚åÇ': '⌂', '‚ú¶': '✦', '‚ò∞': '☰', '‚öô': '⚙', '‚Ñπ': 'ℹ', '\uf8ffüìù': '✎', '\uf8ffüõ†': '⚒',
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    return text


def _cuma_converter_output_dir(self, preferred: str = '') -> Path:
    raw = str(preferred or _cuma_patch_var_get(getattr(self, 'xteink_output_dir', None), '') or _cuma_patch_var_get(getattr(self, 'output_dir', None), '')).strip()
    if raw:
        p = Path(raw).expanduser()
    else:
        p = runtime_dir() / 'limpos' / 'Converter'
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cuma_sync_converter_model(self, preferred_output: str = '') -> Path:
    # única fonte de verdade do Converter
    if not hasattr(self, 'xteink_device'):
        self.xteink_device = tk.StringVar(value='XTEINK X4')
    if not hasattr(self, 'xteink_quality'):
        self.xteink_quality = tk.IntVar(value=100)
    _cuma_patch_var_set(self.xteink_quality, 100)


    out_dir = _cuma_converter_output_dir(self, preferred_output)
    if not hasattr(self, 'xteink_output_dir'):
        self.xteink_output_dir = tk.StringVar(value=str(out_dir))
    _cuma_patch_var_set(self.xteink_output_dir, str(out_dir))
    if hasattr(self, 'output_dir'):
        _cuma_patch_var_set(self.output_dir, str(out_dir))
    try:
        self.cfg.output_dir = str(out_dir)
    except Exception:
        pass
    return out_dir


def _cuma_repair_runtime_strings(self) -> None:
    attr_names = ['xteink_device_note', 'xteink_status', 'xteink_counter', 'tools_debug_var', 'status']
    for attr in attr_names:
        var = getattr(self, attr, None)
        if var is not None:
            cur = _cuma_patch_var_get(var, '')
            fixed = _cuma_fix_mojibake_text(cur)
            if fixed != cur:
                _cuma_patch_var_set(var, fixed)


def _cuma_repair_widget_texts(root_widget) -> None:
    try:
        queue_widgets = [root_widget]
        while queue_widgets:
            widget = queue_widgets.pop(0)
            try:
                txt = widget.cget('text')
            except Exception:
                txt = None
            if isinstance(txt, str) and txt:
                fixed = _cuma_fix_mojibake_text(txt)
                if fixed != txt:
                    try:
                        widget.configure(text=fixed)
                    except Exception:
                        pass
            try:
                queue_widgets.extend(list(widget.winfo_children()))
            except Exception:
                pass
    except Exception as exc:
        _cuma_patch_log_exception('Reparo recursivo dos widgets', exc)


def _cuma_converter_flags(self) -> dict:
    return {
        'pdf_epub': bool(_cuma_patch_var_get(getattr(self, 'xteink_pdf_epub', None), False)),
        'pdf_xtch': bool(_cuma_patch_var_get(getattr(self, 'xteink_pdf_xtch', None), True)),
        'epub_xtch': bool(_cuma_patch_var_get(getattr(self, 'xteink_epub_xtch', None), True)),
    }


def _cuma_xteink_paths_consistent(self) -> tuple[Path, Path, tuple[int, int], int]:
    src = Path(str(_cuma_patch_var_get(getattr(self, 'xteink_input', None), '')).strip())
    if not src.exists():
        raise RuntimeError('Arquivo XTEINK não encontrado.')
    out_dir = _cuma_sync_converter_model(self)
    return src, out_dir, self.xteink_target(), 100


def _cuma_run_xteink_job(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    suffix = src.suffix.lower()
    if suffix == '.pdf' and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        images = render_pdf_pages_as_images(src, target=target)
        try:
            if flags.get('pdf_epub'):
                out = unique_path(out_dir / f'{src.stem}_xteink.epub')
                create_image_epub(images, out, src.stem, quality)
                outputs.append(out)
            if flags.get('pdf_xtch'):
                out = unique_path(out_dir / f'{src.stem}.xtch')
                create_xtch_from_images(images, out, src.stem, target)
                outputs.append(out)
        finally:
            for im in images:
                try: im.close()
                except Exception as exc: _cuma_patch_log_exception('Fechamento de imagem renderizada PDF', exc)
    if suffix == '.epub' and flags.get('epub_xtch'):
        images = extract_epub_images(src, target)
        out = unique_path(out_dir / f'{src.stem}.xtch')
        try:
            create_xtch_from_images(images, out, src.stem, target)
        finally:
            for im in images:
                try: im.close()
                except Exception as exc: _cuma_patch_log_exception('Fechamento de imagem extraída EPUB', exc)
        outputs.append(out)
    return outputs


def _cuma_xteink_status_for_src(src: Path, flags: dict) -> str:
    suffix = src.suffix.lower()
    if suffix == '.pdf' and flags.get('pdf_epub') and not flags.get('pdf_xtch'):
        return 'PDF→EPUB'
    if suffix == '.pdf' and flags.get('pdf_xtch'):
        return 'PDF→XTCH'
    if suffix == '.epub' and flags.get('epub_xtch'):
        return 'EPUB→XTCH'
    return 'Processando'


def _cuma_finish_xteink_ui(self, last_out_dir: str = '') -> None:
    try:
        self.xteink_cancel_btn.configure(state='disabled')
        self.xteink_pause_btn.configure(state='disabled')
        self.xteink_play_btn.configure(state='disabled')
    except Exception as exc:
        _cuma_patch_log_exception('Finalização dos botões XTEINK', exc)
    self.processing = False
    _cuma_patch_var_set(getattr(self, 'xteink_status', None), 'XTEINK cancelado' if self.cancel_requested else 'XTEINK concluído')
    try:
        self.update_xteink_counter()
    except Exception as exc:
        _cuma_patch_log_exception('Atualização do contador XTEINK', exc)
    try:
        out_dir = Path(last_out_dir) if last_out_dir else None
        if out_dir and getattr(self, 'open_after', None) and self.open_after.get():
            open_folder(out_dir)
    except Exception as exc:
        _cuma_patch_log_exception('Abertura automática da pasta Converter', exc)


def _cuma_poll_xteink_queue(self) -> None:
    q = getattr(self, '_xteink_async_queue', None)
    if q is None:
        return
    try:
        while True:
            item = q.get_nowait()
            kind = item.get('kind')
            if kind == 'item_start':
                src = Path(item['src'])
                iid = _cuma_11008_path_key(src)
                _cuma_patch_var_set(getattr(self, 'xteink_input', None), str(src))
                try: self.xteink_tree.set(iid, 'status', _cuma_fix_mojibake_text(item.get('status', 'Processando')))
                except Exception: pass
                try: self.xteink_current_prog['value'] = 5
                except Exception: pass
                _cuma_patch_var_set(getattr(self, 'xteink_status', None), f"XTEINK {item.get('index', 0)}/{item.get('total', 0)}")
            elif kind == 'item_done':
                src = Path(item['src'])
                iid = _cuma_11008_path_key(src)
                try:
                    self.xteink_tree.set(iid, 'status', _cuma_fix_mojibake_text(item.get('status', 'OK')))
                    self.xteink_tree.set(iid, 'saida', _cuma_fix_mojibake_text(item.get('saida', '')))
                    self.xteink_tree.set(iid, 'resumo', _cuma_fix_mojibake_text(item.get('resumo', '')))
                except Exception: pass
                try:
                    self.xteink_total_prog['value'] = item.get('index', 0)
                    self.xteink_current_prog['value'] = 100
                except Exception: pass
                try: self.update_xteink_counter()
                except Exception as exc: _cuma_patch_log_exception('Atualização do contador XTEINK/poll', exc)
            elif kind == 'batch_done':
                self._xteink_async_queue = None
                _cuma_finish_xteink_ui(self, item.get('last_out_dir', ''))
                return
            elif kind == 'batch_error':
                self._xteink_async_queue = None
                exc_text = _cuma_fix_mojibake_text(item.get('error', 'Erro desconhecido no lote XTEINK'))
                _cuma_patch_var_set(getattr(self, 'xteink_status', None), 'Erro no lote XTEINK')
                messagebox.showerror('XTEINK', exc_text)
                _cuma_finish_xteink_ui(self, item.get('last_out_dir', ''))
                return
    except queue.Empty:
        pass
    try:
        self.root.after(80, lambda: _cuma_poll_xteink_queue(self))
    except Exception as exc:
        _cuma_patch_log_exception('Agenda do poll XTEINK', exc)


def _cuma_process_xteink_paths_async(self, paths: list[Path]) -> None:
    if not paths:
        messagebox.showwarning('XTEINK', 'Adicione ou selecione arquivos PDF/EPUB.')
        return
    if getattr(self, '_xteink_async_queue', None) is not None or getattr(self, 'processing', False):
        return
    base = _cuma_sync_converter_model(self)
    flags = _cuma_converter_flags(self)
    self.pause_event.set(); self.cancel_requested = False; self.processing = True
    self._xteink_batch_mode = True; self._xteink_last_out_dir = str(base); self._xteink_async_queue = queue.Queue()
    try:
        self.xteink_total_prog['maximum'] = len(paths); self.xteink_total_prog['value'] = 0; self.xteink_current_prog['value'] = 0
        self.xteink_cancel_btn.configure(state='normal'); self.xteink_pause_btn.configure(state='normal'); self.xteink_play_btn.configure(state='normal')
    except Exception as exc:
        _cuma_patch_log_exception('Preparação visual do lote XTEINK', exc)
    src_list = [Path(p) for p in paths]; target = self.xteink_target(); quality = 100
    def worker():
        last_out_dir = str(base)
        try:
            for idx, src in enumerate(src_list, 1):
                if self.cancel_requested: break
                while not self.pause_event.is_set() and not self.cancel_requested: time.sleep(0.10)
                self._xteink_async_queue.put({'kind':'item_start','src':str(src),'index':idx,'total':len(src_list),'status':_cuma_xteink_status_for_src(src, flags)})
                try:
                    outputs = _cuma_run_xteink_job(src, base, target, quality, flags)
                    resumo = ', '.join(p.suffix.upper().lstrip('.') for p in outputs) if outputs else 'Nenhuma opção marcada compatível'
                    status = 'OK' if outputs else 'IGNORADO'; saida = str(outputs[-1].parent) if outputs else str(base); last_out_dir = saida or last_out_dir
                    self._xteink_async_queue.put({'kind':'item_done','src':str(src),'index':idx,'status':status,'saida':saida,'resumo':resumo})
                except Exception as exc:
                    _cuma_patch_log_exception(f'Processamento XTEINK de {src.name}', exc)
                    self._xteink_async_queue.put({'kind':'item_done','src':str(src),'index':idx,'status':'ERRO','saida':str(base),'resumo':friendly_error(exc)})
            self._xteink_async_queue.put({'kind':'batch_done','last_out_dir':last_out_dir})
        except Exception as exc:
            _cuma_patch_log_exception('Lote XTEINK/worker', exc)
            self._xteink_async_queue.put({'kind':'batch_error','last_out_dir':last_out_dir,'error':friendly_error(exc)})
    threading.Thread(target=worker, daemon=True, name='CUMA-XTEINK-Worker').start(); _cuma_poll_xteink_queue(self)


def _cuma_choose_xteink_output_consistent(self) -> None:
    try:
        folder = filedialog.askdirectory(title='Escolher pasta de saída do Converter')
        if folder:
            _cuma_sync_converter_model(self, folder)
            try: self.save_current_config()
            except Exception as exc: _cuma_patch_log_exception('Salvar config após escolher pasta do Converter', exc)
    except Exception as exc:
        _cuma_patch_log_exception('Escolha de pasta do Converter', exc)
        messagebox.showerror('Pasta de saída', friendly_error(exc))


def _cuma_check_updates_button_async(self):
    if getattr(self, '_update_manifest_check_running', False): return
    self._update_manifest_check_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None: btn.configure(state='disabled')
    except Exception: pass
    def finish(kind: str, title: str, message: str) -> None:
        self._update_manifest_check_running = False
        try:
            if btn is not None: btn.configure(state='normal')
        except Exception: pass
        (messagebox.showerror if kind == 'error' else messagebox.showinfo)(title, _cuma_fix_mojibake_text(message))
    def worker():
        try:
            cfg_path = app_dir() / 'config_cuma.json'; data = {}
            if cfg_path.exists():
                try: data = json.loads(cfg_path.read_text(encoding='utf-8'))
                except Exception as exc: _cuma_patch_log_exception('Leitura do config para atualização', exc); data = {}
            url = data.get('update_manifest_url', '')
            if not url:
                self.root.after(0, lambda: finish('info', 'Procurar atualizações', 'Nenhum repositório configurado. Crie um arquivo version.json no GitHub e coloque a URL raw em config_cuma.json no campo update_manifest_url.'))
                return
            import urllib.request
            with urllib.request.urlopen(url, timeout=8) as resp: remote = json.loads(resp.read().decode('utf-8'))
            latest = str(remote.get('version', ''))
            msg = f'Versão disponível: {latest}\nBaixe em: {remote.get("download_url", "sem link informado")}' if latest and latest != APP_DISPLAY_VERSION else 'Você já está usando a versão mais recente informada no repositório.'
            self.root.after(0, lambda: finish('info', 'Procurar atualizações', msg))
        except Exception as exc:
            _cuma_patch_log_exception('Verificação de atualizações', exc)
            self.root.after(0, lambda: finish('error', 'Procurar atualizações', friendly_error(exc)))
    threading.Thread(target=worker, daemon=True, name='CUMA-Update-Checker').start()


def _cuma_make_unified_converter_panel(self) -> None:
    container = getattr(self, 'tab_xteink', None)
    if container is None: return
    try:
        if hasattr(self, 'xteink_prog_total'): self.xteink_total_prog = self.xteink_prog_total
        if hasattr(self, 'xteink_prog_current'): self.xteink_current_prog = self.xteink_prog_current
    except Exception as exc:
        _cuma_patch_log_exception('Alias de barras de progresso', exc)
    try:
        _cuma_sync_converter_model(self)
    except Exception as exc:
        _cuma_patch_log_exception('Sincronização do modelo do Converter', exc)

    main_frame = None
    for child in list(container.winfo_children()):
        try:
            if isinstance(child, ttk.Frame): main_frame = child; break
        except Exception: continue

    # remover apenas painéis duplicados de dispositivos/conversões
    for child in list(container.winfo_children()):
        try:
            if isinstance(child, ttk.LabelFrame):
                txt = _cuma_fix_mojibake_text(str(child.cget('text')))
                if 'Dispositivos e conversões' in txt: child.destroy()
        except Exception: pass
    if main_frame is not None:
        for child in list(main_frame.winfo_children()):
            try:
                if isinstance(child, ttk.LabelFrame):
                    txt = _cuma_fix_mojibake_text(str(child.cget('text')))
                    if 'Dispositivos e conversões' in txt: child.destroy()
            except Exception: pass

    kwargs = {'fill': 'x', 'pady': (0, 10)}
    children = list(container.winfo_children())
    if children: kwargs['before'] = children[0]
    top = ttk.LabelFrame(container, text='Dispositivos e conversões', padding=12, style='Card.TLabelframe')
    top.pack(**kwargs)

    ttk.Label(top, text='Dispositivo', style='Strong.TLabel').grid(row=0, column=0, sticky='w', padx=(0,8), pady=4)
    dev_combo = ttk.Combobox(top, textvariable=self.xteink_device, values=XTEINK_DEVICES, state='readonly', width=28)
    dev_combo.grid(row=0, column=1, sticky='w', padx=(0,8), pady=4)
    dev_combo.bind('<<ComboboxSelected>>', lambda _e: _cuma_sync_selected_device(self))
    ttk.Button(top, text='Aplicar perfil', command=lambda: _cuma_sync_selected_device(self), style='Accent.TButton').grid(row=0, column=2, padx=4, pady=4)
    ttk.Button(top, text='Editor de perfis', command=self.open_profile_editor, style='Ghost.TButton').grid(row=0, column=3, padx=4, pady=4)
    ttk.Button(top, text='Abrir pasta Converter', command=lambda: open_folder(_cuma_converter_output_dir(self)), style='Ghost.TButton').grid(row=0, column=4, padx=4, pady=4)

    ttk.Label(top, text='Pasta de saída', style='Strong.TLabel').grid(row=1, column=0, sticky='w', padx=(0,8), pady=4)
    ttk.Entry(top, textvariable=self.xteink_output_dir, width=88).grid(row=1, column=1, columnspan=3, sticky='ew', padx=(0,8), pady=4)
    ttk.Button(top, text='Escolher', command=self.choose_xteink_output, style='Ghost.TButton').grid(row=1, column=4, padx=4, pady=4)

    try: self.xteink_quality.set(100)
    except Exception: pass
    ttk.Label(top, text='Qualidade do arquivo (%)', style='Strong.TLabel').grid(row=2, column=0, sticky='w', padx=(0,8), pady=4)
    ttk.Spinbox(top, from_=100, to=100, textvariable=self.xteink_quality, width=8, state='readonly').grid(row=2, column=1, sticky='w', pady=4)
    ttk.Label(top, textvariable=self.xteink_device_note, style='Muted.TLabel').grid(row=2, column=2, columnspan=3, sticky='w', pady=4)
    top.columnconfigure(1, weight=1)
    try:
        _cuma_sync_selected_device(self)
    except Exception as exc:
        _cuma_patch_log_exception('Atualização da nota do dispositivo', exc)


def _cuma_safe_save_current_config(self, force: bool = False) -> None:
    try:
        _cuma_sync_converter_model(self)
        return _CUMA_MERGED_RUNTIME['save_current_config'](self, force)
    except Exception as exc:
        _cuma_patch_log_exception('save_current_config consolidado', exc)
        if force: raise


def _cuma_final_setup_window(self):
    result = _CUMA_MERGED_RUNTIME['setup_window'](self)
    try: _cuma_sync_converter_model(self)
    except Exception as exc: _cuma_patch_log_exception('setup_window consolidado', exc)
    return result


def _cuma_final_build_xteink_tab(self):
    result = _CUMA_MERGED_RUNTIME['build_xteink_tab'](self)
    try:
        if hasattr(self, 'xteink_prog_total'): self.xteink_total_prog = self.xteink_prog_total
        if hasattr(self, 'xteink_prog_current'): self.xteink_current_prog = self.xteink_prog_current
        _cuma_sync_converter_model(self)
    except Exception as exc:
        _cuma_patch_log_exception('build_xteink_tab consolidado', exc)
    return result


def _cuma_final_build(self):
    result = _CUMA_MERGED_RUNTIME['build'](self)
    try:
        if hasattr(self, 'xteink_prog_total'): self.xteink_total_prog = self.xteink_prog_total
        if hasattr(self, 'xteink_prog_current'): self.xteink_current_prog = self.xteink_prog_current
        _cuma_make_unified_converter_panel(self)
        _cuma_repair_runtime_strings(self)
        _cuma_repair_widget_texts(self.root)
    except Exception as exc:
        _cuma_patch_log_exception('build final unificado', exc)
    return result


def _cuma_final_show_page(self, label, save_state=True):
    result = _CUMA_MERGED_RUNTIME['show_page'](self, label, save_state)
    try:
        _cuma_repair_runtime_strings(self)
        _cuma_repair_widget_texts(self.root)
    except Exception as exc:
        _cuma_patch_log_exception('Reparo após show_page', exc)
    return result


def _cuma_final_apply_theme(self):
    result = _CUMA_MERGED_RUNTIME['apply_theme'](self)
    try:
        _cuma_repair_runtime_strings(self)
        _cuma_repair_widget_texts(self.root)
    except Exception as exc:
        _cuma_patch_log_exception('Reparo após apply_theme', exc)
    return result


def _cuma_emit_merged_patch_report() -> None:
    payload = {
        'patch': _CUMA_MERGED_PATCH,
        'resolved_now': {
            'stable_runtime_kept': 'processamento XTEINK assíncrono, pastas consistentes, update assíncrono e aliases de progresso',
            'broken_sidebar_icons': 'sidebar corrigida com ícones seguros',
            'broken_ptbr_words': 'reparo de textos quebrados em runtime/widgets',
            'duplicated_converter_panel': 'painel duplicado removido e painel único recriado no topo do Converter',
            'working_buttons_kept': 'Editor de perfis / Escolher / Abrir pasta Converter / Aplicar perfil preservados no painel único'
        }
    }
    _cuma_patch_debug_write('debug_patch_mesclado.json', payload)


def _cuma_install_merged_patch() -> None:
    if getattr(App, '_cuma_merged_patch_installed', False):
        return
    App._cuma_merged_patch_installed = True
    App.setup_window = _cuma_final_setup_window
    App.build_xteink_tab = _cuma_final_build_xteink_tab
    App.build = _cuma_final_build
    App.show_page = _cuma_final_show_page
    App.apply_theme = _cuma_final_apply_theme
    App.save_current_config = _cuma_safe_save_current_config
    App.process_xteink_paths = _cuma_process_xteink_paths_async
    App.xteink_paths = _cuma_xteink_paths_consistent
    App.choose_xteink_output = _cuma_choose_xteink_output_consistent
    globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_async
    # Relatório antigo condensado em RELATORIO_RELEASE_1_081_1.txt; não gerar debug_patch_mesclado.json em runtime.


_CUMA_MERGED_RUNTIME = {
    'setup_window': App.setup_window,
    'build_xteink_tab': getattr(App, 'build_xteink_tab', None),
    'build': App.build,
    'show_page': App.show_page,
    'apply_theme': App.apply_theme,
    'save_current_config': App.save_current_config,
}
_cuma_install_merged_patch()



# =============================================================================
# CUMA - PATCH FINAL: LIMPEZA DO CONVERSOR LEGADO + PERFIS DE DISPOSITIVO + IDIOMAS
# =============================================================================

_CUMA_FINAL_PATCH = 'final_devices_languages_2026_06_22'


def _cuma_final_log(context: str, exc: Exception | None = None) -> None:
    try:
        if exc is None:
            write_log(f'[{_CUMA_FINAL_PATCH}] {context}')
        else:
            write_log(f'[{_CUMA_FINAL_PATCH}] {context}: {exc}')
            write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_final_write_debug(name: str, payload) -> None:
    try:
        p = runtime_dir() / name
        if isinstance(payload, str):
            p.write_text(payload, encoding='utf-8')
        else:
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    except Exception as exc:
        _cuma_final_log(f'Falha ao escrever debug {name}', exc)


# ------------------------------------------------------------------
# Idiomas
# ------------------------------------------------------------------
APP_LANGUAGE_OPTIONS = {
    'system': 'Sistema (Automático)',
    'pt_BR': 'Português (Brasil)',
    'en_US': 'English',
    'es_ES': 'Español',
    'fr_FR': 'Français',
    'de_DE': 'Deutsch',
    'it_IT': 'Italiano',
    'ja_JP': '日本語',
    'ko_KR': '한국어',
    'zh_TW': '繁體中文',
    'tr_TR': 'Türkçe',
}


def _cuma_detect_system_language() -> str:
    import locale
    candidates = []
    try:
        candidates.append(locale.getdefaultlocale()[0])
    except Exception:
        pass
    try:
        candidates.append(locale.getlocale()[0])
    except Exception:
        pass
    env_lang = os.environ.get('LANG', '')
    if env_lang:
        candidates.append(env_lang)
    for item in candidates:
        if not item:
            continue
        token = str(item).replace('-', '_')
        low = token.lower()
        if low.startswith('pt_br') or low.startswith('pt_'): return 'pt_BR'
        if low.startswith('en'): return 'en_US'
        if low.startswith('es'): return 'es_ES'
        if low.startswith('fr'): return 'fr_FR'
        if low.startswith('de'): return 'de_DE'
        if low.startswith('it'): return 'it_IT'
        if low.startswith('ja'): return 'ja_JP'
        if low.startswith('ko'): return 'ko_KR'
        if low.startswith('zh_tw') or low.startswith('zh_hk') or low.startswith('zh'): return 'zh_TW'
        if low.startswith('tr'): return 'tr_TR'
    return 'pt_BR'


def _cuma_load_app_language() -> str:
    data = load_interface_colors_file() if 'load_interface_colors_file' in globals() else {}
    lang = data.get('app_language', 'system') if isinstance(data, dict) else 'system'
    return lang if lang in APP_LANGUAGE_OPTIONS else 'system'


def _cuma_save_app_language(lang: str) -> None:
    try:
        p = interface_color_path()
        data = load_interface_colors_file() if 'load_interface_colors_file' in globals() else {}
        if not isinstance(data, dict):
            data = {}
        data['app_language'] = lang if lang in APP_LANGUAGE_OPTIONS else 'system'
        # corrigir mojibake já existente no arquivo de cores
        theme_mode = str(data.get('theme_mode', 'Escuro'))
        if 'Autom' in theme_mode:
            data['theme_mode'] = 'Automático'
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        _cuma_final_log('Falha ao salvar idioma do aplicativo', exc)


I18N = {
    'pt_BR': {},
    'en_US': {
        'Limpar': 'Clean', 'Prévia': 'Preview', 'Ferramentas': 'Tools', 'Converter': 'Converter', 'Resultados': 'Results', 'Registros': 'Logs', 'Configurações': 'Settings', 'Sobre': 'About',
        'Limpar PDF': 'Clean PDF', 'Opções': 'Options',
        'Dispositivos e conversões': 'Devices and conversions', 'Dispositivo': 'Device', 'Pasta de saída': 'Output folder', 'Qualidade do arquivo (%)': 'File quality (%)',
        'Aplicar perfil': 'Apply profile', 'Editor de perfis': 'Profile editor', 'Abrir pasta Converter': 'Open Converter folder', 'Escolher': 'Choose',
        'Configurações do XTEINK': 'XTEINK settings', 'Funções por tipo de arquivo': 'Functions by file type',
        'Idioma': 'Language', 'Idioma do aplicativo': 'Application language', 'Idioma do sistema detectado': 'Detected system language',
        'Procurar atualizações': 'Check for updates', 'Atualização encontrada': 'Update found',
        'Pronto': 'Ready', 'Pausado': 'Paused', 'Processando...': 'Processing...', 'Converter pronto': 'Converter ready', 'XTEINK pronto': 'XTEINK ready', 'XTEINK concluído': 'XTEINK completed', 'XTEINK cancelado': 'XTEINK canceled',
        'Adicionar arquivo(s)': 'Add file(s)', 'Adicionar pasta': 'Add folder', 'Colar caminho': 'Paste path', 'Remover': 'Remove', 'Limpar lista': 'Clear list', 'Abrir pasta Ferramentas': 'Open Tools folder',
        'Extrair páginas': 'Extract pages', 'Criar PDF de imagens': 'Create PDF from images', 'Nome do PDF': 'PDF name', 'Abrir pasta ao concluir': 'Open folder when done',
        'Progresso': 'Progress', 'Arquivo atual': 'Current file', 'Total': 'Total', 'Processar selecionados': 'Process selected', 'Processar todos': 'Process all', 'Criar PDF dos selecionados': 'Create PDF from selected', 'Criar PDF de todos': 'Create PDF from all',
    },
    'es_ES': {
        'Limpar': 'Limpiar', 'Prévia': 'Vista previa', 'Ferramentas': 'Herramientas', 'Converter': 'Convertidor', 'Resultados': 'Resultados', 'Registros': 'Registros', 'Configurações': 'Configuración', 'Sobre': 'Acerca de', 'Limpar PDF': 'Limpiar PDF', 'Opções': 'Opciones',
        'Dispositivos e conversões': 'Dispositivos y conversiones', 'Dispositivo': 'Dispositivo', 'Pasta de saída': 'Carpeta de salida', 'Qualidade do arquivo (%)': 'Calidad del archivo (%)', 'Aplicar perfil': 'Aplicar perfil', 'Editor de perfis': 'Editor de perfiles', 'Abrir pasta Converter': 'Abrir carpeta del Convertidor', 'Escolher': 'Elegir',
        'Idioma': 'Idioma', 'Idioma do aplicativo': 'Idioma de la aplicación', 'Idioma do sistema detectado': 'Idioma del sistema detectado',
        'Pronto': 'Listo', 'Pausado': 'Pausado', 'Processando...': 'Procesando...', 'Converter pronto': 'Convertidor listo', 'XTEINK pronto': 'XTEINK listo',
    },
    'fr_FR': {
        'Limpar': 'Nettoyer', 'Prévia': 'Aperçu', 'Ferramentas': 'Outils', 'Converter': 'Convertisseur', 'Resultados': 'Résultats', 'Registros': 'Journaux', 'Configurações': 'Paramètres', 'Sobre': 'À propos', 'Limpar PDF': 'Nettoyer PDF',
        'Dispositivos e conversões': 'Appareils et conversions', 'Dispositivo': 'Appareil', 'Pasta de saída': 'Dossier de sortie', 'Qualidade do arquivo (%)': 'Qualité du fichier (%)', 'Aplicar perfil': 'Appliquer le profil', 'Editor de perfis': 'Éditeur de profils', 'Abrir pasta Converter': 'Ouvrir le dossier Convertisseur', 'Escolher': 'Choisir',
        'Idioma': 'Langue', 'Idioma do aplicativo': "Langue de l'application", 'Idioma do sistema detectado': 'Langue système détectée',
    },
    'de_DE': {
        'Limpar': 'Bereinigen', 'Prévia': 'Vorschau', 'Ferramentas': 'Werkzeuge', 'Converter': 'Konverter', 'Resultados': 'Ergebnisse', 'Registros': 'Protokolle', 'Configurações': 'Einstellungen', 'Sobre': 'Info', 'Limpar PDF': 'PDF bereinigen',
        'Dispositivos e conversões': 'Geräte und Konvertierungen', 'Dispositivo': 'Gerät', 'Pasta de saída': 'Ausgabeordner', 'Qualidade do arquivo (%)': 'Dateiqualität (%)', 'Aplicar perfil': 'Profil anwenden', 'Editor de perfis': 'Profileditor', 'Abrir pasta Converter': 'Konverter-Ordner öffnen', 'Escolher': 'Wählen',
        'Idioma': 'Sprache', 'Idioma do aplicativo': 'App-Sprache', 'Idioma do sistema detectado': 'Erkannte Systemsprache',
    },
    'it_IT': {
        'Limpar': 'Pulisci', 'Prévia': 'Anteprima', 'Ferramentas': 'Strumenti', 'Converter': 'Convertitore', 'Resultados': 'Risultati', 'Registros': 'Registri', 'Configurações': 'Impostazioni', 'Sobre': 'Informazioni', 'Limpar PDF': 'Pulisci PDF',
        'Dispositivos e conversões': 'Dispositivi e conversioni', 'Dispositivo': 'Dispositivo', 'Pasta de saída': 'Cartella di output', 'Qualidade do arquivo (%)': 'Qualità del file (%)', 'Aplicar perfil': 'Applica profilo', 'Editor de perfis': 'Editor profili', 'Abrir pasta Converter': 'Apri cartella Convertitore', 'Escolher': 'Scegli',
        'Idioma': 'Lingua', 'Idioma do aplicativo': 'Lingua dell’applicazione', 'Idioma do sistema detectado': 'Lingua di sistema rilevata',
    },
    'ja_JP': {
        'Limpar': 'クリーン', 'Prévia': 'プレビュー', 'Ferramentas': 'ツール', 'Converter': '変換', 'Resultados': '結果', 'Registros': 'ログ', 'Configurações': '設定', 'Sobre': '情報', 'Limpar PDF': 'PDFをクリーン',
        'Dispositivos e conversões': 'デバイスと変換', 'Dispositivo': 'デバイス', 'Pasta de saída': '出力フォルダー', 'Qualidade do arquivo (%)': 'ファイル品質 (%)', 'Aplicar perfil': 'プロファイル適用', 'Editor de perfis': 'プロファイル編集', 'Abrir pasta Converter': '変換フォルダーを開く', 'Escolher': '選択',
        'Idioma': '言語', 'Idioma do aplicativo': 'アプリの言語', 'Idioma do sistema detectado': '検出されたシステム言語',
    },
    'ko_KR': {
        'Limpar': '정리', 'Prévia': '미리보기', 'Ferramentas': '도구', 'Converter': '변환기', 'Resultados': '결과', 'Registros': '기록', 'Configurações': '설정', 'Sobre': '정보', 'Limpar PDF': 'PDF 정리',
        'Dispositivos e conversões': '장치 및 변환', 'Dispositivo': '장치', 'Pasta de saída': '출력 폴더', 'Qualidade do arquivo (%)': '파일 품질 (%)', 'Aplicar perfil': '프로필 적용', 'Editor de perfis': '프로필 편집기', 'Abrir pasta Converter': '변환기 폴더 열기', 'Escolher': '선택',
        'Idioma': '언어', 'Idioma do aplicativo': '앱 언어', 'Idioma do sistema detectado': '감지된 시스템 언어',
    },
    'zh_TW': {
        'Limpar': '清理', 'Prévia': '預覽', 'Ferramentas': '工具', 'Converter': '轉換器', 'Resultados': '結果', 'Registros': '記錄', 'Configurações': '設定', 'Sobre': '關於', 'Limpar PDF': '清理 PDF',
        'Dispositivos e conversões': '裝置與轉換', 'Dispositivo': '裝置', 'Pasta de saída': '輸出資料夾', 'Qualidade do arquivo (%)': '檔案品質 (%)', 'Aplicar perfil': '套用設定檔', 'Editor de perfis': '設定檔編輯器', 'Abrir pasta Converter': '開啟轉換器資料夾', 'Escolher': '選擇',
        'Idioma': '語言', 'Idioma do aplicativo': '應用程式語言', 'Idioma do sistema detectado': '偵測到的系統語言',
    },
    'tr_TR': {
        'Limpar': 'Temizle', 'Prévia': 'Önizleme', 'Ferramentas': 'Araçlar', 'Converter': 'Dönüştürücü', 'Resultados': 'Sonuçlar', 'Registros': 'Kayıtlar', 'Configurações': 'Ayarlar', 'Sobre': 'Hakkında', 'Limpar PDF': 'PDF Temizle',
        'Dispositivos e conversões': 'Cihazlar ve dönüştürmeler', 'Dispositivo': 'Cihaz', 'Pasta de saída': 'Çıkış klasörü', 'Qualidade do arquivo (%)': 'Dosya kalitesi (%)', 'Aplicar perfil': 'Profili uygula', 'Editor de perfis': 'Profil düzenleyici', 'Abrir pasta Converter': 'Dönüştürücü klasörünü aç', 'Escolher': 'Seç',
        'Idioma': 'Dil', 'Idioma do aplicativo': 'Uygulama dili', 'Idioma do sistema detectado': 'Algılanan sistem dili',
    },
}


def _cuma_resolved_language(self=None) -> str:
    lang = 'system'
    if self is not None and hasattr(self, 'app_language'):
        try:
            lang = self.app_language.get()
        except Exception:
            lang = _cuma_load_app_language()
    else:
        lang = _cuma_load_app_language()
    return _cuma_detect_system_language() if lang == 'system' else lang


def _cuma_tr(text: str, lang: str) -> str:
    base = _cuma_fix_mojibake_text(text)
    if lang == 'pt_BR':
        return base
    mapping = I18N.get(lang, {})
    return mapping.get(base, base)


# ------------------------------------------------------------------
# Perfis de dispositivo (e-readers + smartphones populares)
# ------------------------------------------------------------------
DEFAULT_DEVICE_PROFILE_CATALOG = {
    'XTEINK X4': {'width': 480, 'height': 800, 'dpi': 212, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0, 'category': 'XTEINK'},
    'XTEINK X3': {'width': 528, 'height': 792, 'dpi': 212, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0, 'category': 'XTEINK'},
    'Kindle Paperwhite 12ª gen': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.1, 'margin': 0, 'category': 'Kindle'},
    'Kindle Colorsoft': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.1, 'margin': 0, 'category': 'Kindle'},
    'Kobo Clara Colour': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.1, 'margin': 0, 'category': 'Kobo'},
    'Kobo Libra Colour': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.1, 'margin': 0, 'category': 'Kobo'},
    'Kobo Elipsa 2E': {'width': 1404, 'height': 1872, 'dpi': 227, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0, 'category': 'Kobo'},
    'BOOX Page': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'BOOX'},
    'BOOX Go 10.3': {'width': 1860, 'height': 2480, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0, 'category': 'BOOX'},
    'PocketBook Verse Pro': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'PocketBook'},
    'Smartphone - iPhone 16': {'width': 1179, 'height': 2556, 'dpi': 460, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - iPhone 16 Plus': {'width': 1290, 'height': 2796, 'dpi': 460, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - iPhone 16 Pro': {'width': 1206, 'height': 2622, 'dpi': 460, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - iPhone 16 Pro Max': {'width': 1320, 'height': 2868, 'dpi': 460, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Samsung Galaxy S25': {'width': 1080, 'height': 2340, 'dpi': 416, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Samsung Galaxy S25+': {'width': 1440, 'height': 3120, 'dpi': 513, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Samsung Galaxy S25 Ultra': {'width': 1440, 'height': 3120, 'dpi': 498, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Google Pixel 9': {'width': 1080, 'height': 2424, 'dpi': 422, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Google Pixel 9 Pro XL': {'width': 1344, 'height': 2992, 'dpi': 486, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Motorola Edge 40 Pro': {'width': 1080, 'height': 2400, 'dpi': 395, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Xiaomi 15 Pro': {'width': 1440, 'height': 3200, 'dpi': 522, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - OnePlus 12': {'width': 1440, 'height': 3168, 'dpi': 510, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Smartphone - Redmi Note 14 Pro+': {'width': 1220, 'height': 2712, 'dpi': 446, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.05, 'margin': 0, 'category': 'Smartphone'},
    'Personalizado': {'width': 600, 'height': 800, 'dpi': 200, 'jpeg_quality': 100, 'gamma': 1.0, 'contrast': 1.0, 'sharpen': 0.0, 'margin': 0, 'category': 'Custom'},
}


def _cuma_profile_json_path() -> Path:
    return app_dir() / 'cuma_device_profiles.json'


def _cuma_device_profiles() -> dict:
    data = {}
    p = _cuma_profile_json_path()
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                data = {}
    except Exception as exc:
        _cuma_final_log('Falha ao carregar cuma_device_profiles.json', exc)
        data = {}
    for k, v in DEFAULT_DEVICE_PROFILE_CATALOG.items():
        data.setdefault(k, dict(v))
    return data


def _cuma_save_all_device_profiles(data: dict) -> None:
    try:
        _cuma_profile_json_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        _cuma_final_log('Falha ao salvar catálogo de dispositivos', exc)


def _cuma_save_device_profile(device: str, profile: dict) -> None:
    data = _cuma_device_profiles()
    merged = dict(DEFAULT_DEVICE_PROFILE_CATALOG.get('Personalizado', {}))
    merged.update(profile or {})
    data[device] = merged
    _cuma_save_all_device_profiles(data)
    globals()['XTEINK_DEVICE_PROFILES'][device] = (int(merged.get('width', 600)), int(merged.get('height', 800)))
    globals()['XTEINK_DEVICES'] = tuple(sorted(data.keys(), key=lambda x: (0 if x.startswith('XTEINK') else 1 if x.startswith('Kindle') else 2 if x.startswith('Kobo') else 3 if x.startswith('BOOX') else 4 if x.startswith('PocketBook') else 5 if x.startswith('Smartphone') else 9, x.lower())))


def _cuma_refresh_device_globals() -> None:
    data = _cuma_device_profiles()
    globals()['XTEINK_DEVICE_PROFILES'] = {k: (int(v.get('width', 600)), int(v.get('height', 800))) for k, v in data.items()}
    globals()['XTEINK_DEVICES'] = tuple(sorted(data.keys(), key=lambda x: (0 if x.startswith('XTEINK') else 1 if x.startswith('Kindle') else 2 if x.startswith('Kobo') else 3 if x.startswith('BOOX') else 4 if x.startswith('PocketBook') else 5 if x.startswith('Smartphone') else 9, x.lower())))


_cuma_refresh_device_globals()


def _cuma_sync_selected_device(self):
    try:
        _cuma_refresh_device_globals()
        dev = self.xteink_device.get()
        prof = _cuma_device_profiles().get(dev, _cuma_device_profiles().get('Personalizado', {}))
        try:
            self.xteink_quality.set(int(prof.get('jpeg_quality', 100)))
        except Exception:
            pass
        note = f"{prof.get('width', '?')}×{prof.get('height', '?')} px, DPI {prof.get('dpi', '?')}"
        if hasattr(self, 'xteink_device_note'):
            self.xteink_device_note.set(note)
    except Exception as exc:
        _cuma_final_log('Falha ao sincronizar dispositivo selecionado', exc)


def _cuma_open_profile_editor_device(self):
    _cuma_refresh_device_globals()
    all_profiles = _cuma_device_profiles()
    current = self.xteink_device.get() if hasattr(self, 'xteink_device') else 'Personalizado'
    top = tk.Toplevel(self.root)
    top.title('Editor de perfis de dispositivo')
    top.geometry('860x700')
    top.transient(self.root)
    wrap = ttk.Frame(top, style='Card.TFrame', padding=12)
    wrap.pack(fill='both', expand=True)

    ttk.Label(wrap, text='Editor de perfis de dispositivo', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 8))
    ttk.Label(wrap, text='Selecione um perfil existente, ajuste os parâmetros e salve. Use “Salvar como novo personalizado” para criar um perfil próprio a partir do atual.', style='Muted.TLabel', wraplength=820, justify='left').pack(anchor='w', pady=(0, 10))

    selected = tk.StringVar(value=current if current in all_profiles else 'Personalizado')
    custom_name = tk.StringVar(value=selected.get())

    row0 = ttk.Frame(wrap, style='Card.TFrame'); row0.pack(fill='x', pady=4)
    ttk.Label(row0, text='Perfil carregado', width=22, style='Strong.TLabel').pack(side='left')
    combo = ttk.Combobox(row0, textvariable=selected, values=list(XTEINK_DEVICES), state='readonly', width=44)
    combo.pack(side='left', padx=6)

    row0b = ttk.Frame(wrap, style='Card.TFrame'); row0b.pack(fill='x', pady=4)
    ttk.Label(row0b, text='Salvar como nome', width=22, style='Strong.TLabel').pack(side='left')
    ttk.Entry(row0b, textvariable=custom_name, width=46).pack(side='left', padx=6)

    vars_map = {
        'width': tk.IntVar(value=600), 'height': tk.IntVar(value=800), 'dpi': tk.IntVar(value=200), 'jpeg_quality': tk.IntVar(value=100),
        'gamma': tk.DoubleVar(value=1.0), 'contrast': tk.DoubleVar(value=1.0), 'sharpen': tk.DoubleVar(value=0.0), 'margin': tk.IntVar(value=0),
        'category': tk.StringVar(value='Custom')
    }
    fields = [('width', 'Largura (px)'), ('height', 'Altura (px)'), ('dpi', 'DPI'), ('jpeg_quality', 'Qualidade JPEG'), ('gamma', 'Gamma'), ('contrast', 'Contraste'), ('sharpen', 'Nitidez'), ('margin', 'Margem (px)'), ('category', 'Categoria')]

    form = ttk.Frame(wrap, style='Card.TFrame'); form.pack(fill='x', pady=(8, 12))
    for idx, (key, label) in enumerate(fields):
        row = ttk.Frame(form, style='Card.TFrame'); row.pack(fill='x', pady=4)
        ttk.Label(row, text=label, width=22, style='Strong.TLabel').pack(side='left')
        ttk.Entry(row, textvariable=vars_map[key], width=14).pack(side='left', padx=6)

    preview_var = tk.StringVar(value='')
    ttk.Label(wrap, textvariable=preview_var, style='Muted.TLabel', wraplength=820).pack(anchor='w', pady=(0, 10))

    def load_profile(*_):
        name = selected.get()
        prof = dict(all_profiles.get(name, all_profiles.get('Personalizado', {})))
        custom_name.set(name)
        for key, var in vars_map.items():
            try:
                var.set(prof.get(key, var.get()))
            except Exception:
                pass
        preview_var.set(f"Pré-visualização: {name} → {prof.get('width', '?')}×{prof.get('height', '?')} px | DPI {prof.get('dpi', '?')} | Categoria {prof.get('category', 'Custom')}")

    combo.bind('<<ComboboxSelected>>', load_profile)
    load_profile()

    btns = ttk.Frame(wrap, style='Card.TFrame'); btns.pack(fill='x', pady=(8, 0))

    def save_into_selected():
        target_name = selected.get().strip() or 'Personalizado'
        payload = {k: (v.get() if hasattr(v, 'get') else v) for k, v in vars_map.items()}
        _cuma_save_device_profile(target_name, payload)
        _cuma_refresh_device_globals()
        self.xteink_device.set(target_name)
        _cuma_sync_selected_device(self)
        messagebox.showinfo('Editor de perfis', f'Perfil salvo: {target_name}')
        top.destroy()

    def save_as_new_custom():
        target_name = custom_name.get().strip() or 'Meu dispositivo'
        payload = {k: (v.get() if hasattr(v, 'get') else v) for k, v in vars_map.items()}
        payload['category'] = 'Custom'
        _cuma_save_device_profile(target_name, payload)
        _cuma_refresh_device_globals()
        self.xteink_device.set(target_name)
        _cuma_sync_selected_device(self)
        messagebox.showinfo('Editor de perfis', f'Novo perfil personalizado salvo: {target_name}')
        top.destroy()

    def restore_defaults():
        _cuma_save_all_device_profiles(dict(DEFAULT_DEVICE_PROFILE_CATALOG))
        _cuma_refresh_device_globals()
        self.xteink_device.set('XTEINK X4')
        _cuma_sync_selected_device(self)
        messagebox.showinfo('Editor de perfis', 'Perfis padrão restaurados com sucesso.')
        top.destroy()

    ttk.Button(btns, text='Salvar no perfil atual', command=save_into_selected, style='Accent.TButton').pack(side='left')
    ttk.Button(btns, text='Salvar como novo personalizado', command=save_as_new_custom, style='Ghost.TButton').pack(side='left', padx=8)
    ttk.Button(btns, text='Restaurar perfis padrão', command=restore_defaults, style='Ghost.TButton').pack(side='left', padx=8)
    ttk.Button(btns, text='Fechar', command=top.destroy, style='Ghost.TButton').pack(side='right')


# ------------------------------------------------------------------
# Integração do idioma na aba Configurações
# ------------------------------------------------------------------

def _cuma_setup_vars_language(self):
    _CUMA_FINAL_RUNTIME['setup_vars'](self)
    try:
        lang = _cuma_load_app_language()
        self.app_language = tk.StringVar(value=lang)
        self.app_language_help = tk.StringVar(value='')
    except Exception as exc:
        _cuma_final_log('Falha ao criar variáveis de idioma', exc)


def _cuma_apply_language_to_widgets(self) -> None:
    lang = _cuma_resolved_language(self)
    try:
        if hasattr(self, 'app_language_help'):
            self.app_language_help.set(f"{_cuma_tr('Idioma do sistema detectado', lang)}: {APP_LANGUAGE_OPTIONS.get(_cuma_detect_system_language(), _cuma_detect_system_language())}")
    except Exception:
        pass

    def fix_widget(widget):
        try:
            txt = widget.cget('text')
        except Exception:
            txt = None
        if isinstance(txt, str) and txt:
            fixed = _cuma_tr(txt, lang)
            if fixed != txt:
                try:
                    widget.configure(text=fixed)
                except Exception:
                    pass
        try:
            if isinstance(widget, ttk.LabelFrame):
                base = widget.cget('text')
                fixed = _cuma_tr(base, lang)
                if fixed != base:
                    widget.configure(text=fixed)
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                fix_widget(child)
        except Exception:
            pass

    try:
        fix_widget(self.root)
    except Exception as exc:
        _cuma_final_log('Falha ao aplicar idioma nos widgets', exc)

    # status vars/notes/sidebar title strings
    try:
        if hasattr(self, 'xteink_device_note'):
            note = _cuma_patch_var_get(self.xteink_device_note, '') if '_cuma_patch_var_get' in globals() else self.xteink_device_note.get()
            self.xteink_device_note.set(_cuma_tr(note, lang))
    except Exception:
        pass


def _cuma_on_language_changed(self, *_):
    try:
        lang = self.app_language.get() if hasattr(self, 'app_language') else 'system'
        _cuma_save_app_language(lang)
        _cuma_apply_language_to_widgets(self)
    except Exception as exc:
        _cuma_final_log('Falha ao trocar idioma', exc)


def _cuma_insert_language_section(self):
    if getattr(self, '_language_section_installed', False):
        return
    tab = getattr(self, 'tab_config', None)
    if tab is None:
        return
    target_parent = None
    # build_config_tab usa Canvas -> Frame interno (wrap)
    for child in tab.winfo_children():
        if isinstance(child, tk.Canvas):
            for grand in child.winfo_children():
                if isinstance(grand, ttk.Frame):
                    target_parent = grand
                    break
    if target_parent is None:
        return
    section = ttk.LabelFrame(target_parent, text='Idioma do aplicativo', padding=12, style='Card.TLabelframe')
    children = list(target_parent.winfo_children())
    if children:
        section.pack(fill='x', pady=(0, 12), before=children[0])
    else:
        section.pack(fill='x', pady=(0, 12))
    row = ttk.Frame(section, style='Card.TFrame'); row.pack(fill='x')
    ttk.Label(row, text='Idioma', width=22, style='Strong.TLabel').pack(side='left')
    combo = ttk.Combobox(row, textvariable=self.app_language, values=list(APP_LANGUAGE_OPTIONS.keys()), state='readonly', width=24)
    combo.pack(side='left', padx=(8, 10))

    def _display_selected(*_):
        help_text = f"{APP_LANGUAGE_OPTIONS.get(self.app_language.get(), self.app_language.get())}"
        if hasattr(self, 'app_language_help'):
            self.app_language_help.set(f"{_cuma_tr('Idioma do sistema detectado', _cuma_resolved_language(self))}: {APP_LANGUAGE_OPTIONS.get(_cuma_detect_system_language(), _cuma_detect_system_language())} | Selecionado: {help_text}")

    combo.bind('<<ComboboxSelected>>', lambda _e: (_display_selected(), _cuma_on_language_changed(self)))
    ttk.Label(section, textvariable=self.app_language_help, style='Muted.TLabel', wraplength=920, justify='left').pack(anchor='w', pady=(8, 0))
    self._language_section_installed = True
    _display_selected()


def _cuma_build_config_tab_with_language(self):
    result = _CUMA_FINAL_RUNTIME['build_config_tab'](self)
    try:
        _cuma_insert_language_section(self)
    except Exception as exc:
        _cuma_final_log('Falha ao inserir seção de idioma', exc)
    return result


def _cuma_final_build(self):
    result = _CUMA_FINAL_RUNTIME['build'](self)
    try:
        _cuma_insert_language_section(self)
        _cuma_apply_language_to_widgets(self)
        _cuma_sync_selected_device(self)
    except Exception as exc:
        _cuma_final_log('Falha no build final do patch', exc)
    return result


def _cuma_final_show_page(self, label, save_state=True):
    result = _CUMA_FINAL_RUNTIME['show_page'](self, label, save_state)
    try:
        _cuma_apply_language_to_widgets(self)
    except Exception as exc:
        _cuma_final_log('Falha ao reaplicar idioma após show_page', exc)
    return result


def _cuma_final_apply_theme(self):
    result = _CUMA_FINAL_RUNTIME['apply_theme'](self)
    try:
        _cuma_apply_language_to_widgets(self)
    except Exception as exc:
        _cuma_final_log('Falha ao reaplicar idioma após apply_theme', exc)
    return result


def _cuma_emit_final_patch_report() -> None:
    try:
        data = {
            'patch': _CUMA_FINAL_PATCH,
            'legacy_converter_removed': True,
            'languages': APP_LANGUAGE_OPTIONS,
            'device_count': len(_cuma_device_profiles()),
            'device_names': list(_cuma_device_profiles().keys())[:80],
        }
        _cuma_final_write_debug('debug_patch_final_devices_languages.json', data)
    except Exception as exc:
        _cuma_final_log('Falha ao gerar relatório do patch final', exc)


def _cuma_install_final_patch() -> None:
    if getattr(App, '_cuma_final_patch_installed', False):
        return
    App._cuma_final_patch_installed = True
    App.setup_vars = _cuma_setup_vars_language
    App.build_config_tab = _cuma_build_config_tab_with_language
    App.open_profile_editor = _cuma_open_profile_editor_device
    App.build = _cuma_final_build
    App.show_page = _cuma_final_show_page
    App.apply_theme = _cuma_final_apply_theme
    # Relatório antigo condensado em RELATORIO_RELEASE_1_081_1.txt; não gerar debug_patch_final_devices_languages.json em runtime.


_CUMA_FINAL_RUNTIME = {
    'setup_vars': App.setup_vars,
    'build_config_tab': App.build_config_tab,
    'build': App.build,
    'show_page': App.show_page,
    'apply_theme': App.apply_theme,
}
_cuma_install_final_patch()



# =============================================================================
# CUMA - PATCH FINAL V6
# Base utilizada: última linha estável acessível nesta conversa.
# Objetivo: reforço global de tradução + manual realmente localizado + espaçamento do cabeçalho.
# =============================================================================

_CUMA_FINAL_V6_PATCH = 'final_v6_translation_completion_header_spacing_2026_06_22'

V6_LANGUAGE_DISPLAY = {
    'system': 'Automático',
    'pt_BR': 'Português (Brasil)',
    'en_US': 'English',
    'es_ES': 'Español',
    'fr_FR': 'Français',
    'de_DE': 'Deutsch',
    'it_IT': 'Italiano',
    'ja_JP': '日本語',
    'ko_KR': '한국어',
    'zh_TW': '繁體中文',
    'tr_TR': 'Türkçe',
}
V6_DISPLAY_TO_CODE = {v: k for k, v in V6_LANGUAGE_DISPLAY.items()}

# Traduções extras focadas no que permaneceu híbrido na interface.
V6_EXTRA_TEXT = {
    'en_US': {
        'Configurações organizadas por categoria': 'Settings organized by category',
        'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Visual mode adjusted. Use Custom to freely edit colors or choose a system preset to get started faster.',
        'Temas e cores': 'Themes and colors', 'Qualidade e desempenho': 'Quality and performance', 'Hardware': 'Hardware', 'Facilidades': 'Conveniences', 'Segurança e logs': 'Security and logs',
        'Quatro modos visuais': 'Four visual modes',
        'Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.': 'There are now four modes: Automatic, Light, Dark and Custom. Automatic tries to follow the system. Custom combines presets with fine color adjustment.',
        'Modo visual': 'Visual mode', 'Base do personalizado': 'Custom base', 'Cor principal do botão': 'Main button color',
        'Personalizar cor': 'Customize color', 'Aplicar cor': 'Apply color', 'Cores padrão do sistema': 'System default colors', 'Ajuste avançado das cores': 'Advanced color adjustment',
        'Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.': 'Choose the application language. “Automatic” follows the system language when possible. Names are shown in each language\'s native form.',
        'Idioma do aplicativo': 'Application language', 'Idioma': 'Language', 'Idioma do sistema detectado': 'Detected system language', 'Selecionado': 'Selected',
        'Sobre o CUMA': 'About CUMA', 'Resumo rápido do que cada aba faz:': 'Quick summary of what each tab does:', 'Abas do aplicativo': 'Application tabs',
        'Abrir manual interativo': 'Open interactive manual', 'Abrir manual TXT completo': 'Open full TXT manual',
        'Manual interativo do CUMA': 'CUMA interactive manual', 'Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.': 'Choose a section on the left to see a detailed explanation. Use the “Open full TXT” button if you want the manual separated from the system.',
        'Seções': 'Sections', 'Conteúdo': 'Content', 'Botões do topo': 'Top buttons', 'Perfis de dispositivo': 'Device profiles', 'FAQ rápido': 'Quick FAQ',
        'Fila principal': 'Main queue', 'Versão': 'Version', 'Atualizado em': 'Updated on', 'Fila da aba Converter (EPUB / XTCH)': 'Converter tab queue (EPUB / XTCH)',
        'Tema claro': 'Light theme', 'Tema escuro': 'Dark theme', 'Fechar': 'Close',
        'Main queue': 'Main queue', 'Version': 'Version',
        'Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Use Custom to freely edit colors or choose a system preset to get started faster.',
        'Escolha se o modo personalizado parte de uma base clara ou escura.': 'Choose whether the custom mode starts from a light or dark base.',
        'Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.': 'Automatic follows the system when possible. Light and Dark apply a direct mode. Custom unlocks full editing.',
        'Metade do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.': 'Part of the flow was simplified with quick presets. Start from Manga Dark, Modern Dark or Modern Light and refine later if you want.',
        'Pasta de saída': 'Output folder', 'Escolher': 'Choose', 'Dispositivo': 'Device', 'Aplicar perfil': 'Apply profile', 'Editor de perfis': 'Profile editor', 'Abrir pasta Converter': 'Open Converter folder', 'Qualidade do arquivo (%)': 'File quality (%)',
    },
    'ko_KR': {
        'Configurações organizadas por categoria': '범주별로 정리된 설정',
        'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': '시각 모드가 조정되었습니다. 색상을 자유롭게 편집하려면 사용자 지정을 사용하거나, 더 빨리 시작하려면 시스템 프리셋을 선택하세요.',
        'Temas e cores': '테마 및 색상', 'Qualidade e desempenho': '품질 및 성능', 'Hardware': '하드웨어', 'Facilidades': '편의 기능', 'Segurança e logs': '보안 및 로그',
        'Quatro modos visuais': '네 가지 시각 모드',
        'Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.': '이제 자동, 라이트, 다크, 사용자 지정의 네 가지 모드가 있습니다. 자동은 시스템을 따르려고 하며, 사용자 지정은 프리셋과 세부 색상 조정을 결합합니다.',
        'Modo visual': '시각 모드', 'Base do personalizado': '사용자 지정 기본값', 'Cor principal do botão': '기본 버튼 색상',
        'Personalizar cor': '색상 사용자 지정', 'Aplicar cor': '색상 적용', 'Cores padrão do sistema': '시스템 기본 색상', 'Ajuste avançado das cores': '고급 색상 조정',
        'Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.': '애플리케이션 언어를 선택하세요. “자동”은 가능하면 시스템 언어를 따릅니다. 이름은 각 언어의 고유 표기로 표시됩니다.',
        'Idioma do aplicativo': '애플리케이션 언어', 'Idioma': '언어', 'Idioma do sistema detectado': '감지된 시스템 언어', 'Selecionado': '선택됨',
        'Sobre o CUMA': 'CUMA 정보', 'Resumo rápido do que cada aba faz:': '각 탭의 빠른 요약:', 'Abas do aplicativo': '애플리케이션 탭',
        'Abrir manual interativo': '대화형 설명서 열기', 'Abrir manual TXT completo': '전체 TXT 설명서 열기',
        'Manual interativo do CUMA': 'CUMA 대화형 설명서', 'Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.': '왼쪽에서 섹션을 선택하면 자세한 설명을 볼 수 있습니다. 시스템과 분리된 설명서를 원하면 “전체 TXT 설명서 열기” 버튼을 사용하세요.',
        'Seções': '섹션', 'Conteúdo': '내용', 'Botões do topo': '상단 버튼', 'Perfis de dispositivo': '장치 프로필', 'FAQ rápido': '빠른 FAQ',
        'Fila principal': '메인 대기열', 'Versão': '버전', 'Atualizado em': '업데이트 날짜', 'Fila da aba Converter (EPUB / XTCH)': '변환기 탭 대기열 (EPUB / XTCH)',
        'Tema claro': '라이트 테마', 'Tema escuro': '다크 테마', 'Fechar': '닫기',
        'Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': '색상을 자유롭게 편집하려면 사용자 지정을 사용하고, 더 빨리 시작하려면 시스템 프리셋을 선택하세요.',
        'Escolha se o modo personalizado parte de uma base clara ou escura.': '사용자 지정 모드가 밝은 기반에서 시작할지 어두운 기반에서 시작할지 선택하세요.',
        'Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.': '자동은 가능하면 시스템을 따릅니다. 라이트와 다크는 즉시 적용됩니다. 사용자 지정은 전체 편집을 허용합니다.',
        'Metade do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.': '흐름의 일부는 빠른 프리셋으로 단순화되었습니다. Manga Dark, Moderno Escuro 또는 Moderno Claro에서 시작한 뒤 나중에 세부 조정할 수 있습니다.',
        'Pasta de saída': '출력 폴더', 'Escolher': '선택', 'Dispositivo': '장치', 'Aplicar perfil': '프로필 적용', 'Editor de perfis': '프로필 편집기', 'Abrir pasta Converter': '변환기 폴더 열기', 'Qualidade do arquivo (%)': '파일 품질 (%)',
    },
}
# fallback: usa inglês para idiomas sem dicionário extra completo nesta rodada
for _code in ['es_ES','fr_FR','de_DE','it_IT','ja_JP','zh_TW','tr_TR']:
    V6_EXTRA_TEXT.setdefault(_code, dict(V6_EXTRA_TEXT['en_US']))

V6_OPTION_DISPLAY = {
    'theme_mode': {
        'pt_BR': {'Automático':'Automático','Claro':'Claro','Escuro':'Escuro','Personalizado':'Personalizado'},
        'en_US': {'Automático':'Automatic','Claro':'Light','Escuro':'Dark','Personalizado':'Custom'},
        'ko_KR': {'Automático':'자동','Claro':'라이트','Escuro':'다크','Personalizado':'사용자 지정'},
    },
    'custom_base_theme': {
        'pt_BR': {'Claro':'Claro','Escuro':'Escuro'},
        'en_US': {'Claro':'Light','Escuro':'Dark'},
        'ko_KR': {'Claro':'라이트','Escuro':'다크'},
    },
}
for _k in list(V6_OPTION_DISPLAY.keys()):
    for _code in ['es_ES','fr_FR','de_DE','it_IT','ja_JP','zh_TW','tr_TR']:
        V6_OPTION_DISPLAY[_k].setdefault(_code, dict(V6_OPTION_DISPLAY[_k]['en_US']))

V6_MANUAL_TEXTS = {
    'pt_BR': {
        'Visão geral': 'CUMA - Conversor Ultimate de Mangás\n\nO CUMA foi organizado em áreas claras para que cada parte cumpra um papel específico no fluxo. Limpar trabalha com a fila principal de PDFs, Ferramentas reúne utilidades auxiliares, Converter prepara EPUB e XTCH com perfis de dispositivo, Resultados mostra o que foi gerado, Registros centraliza diagnósticos, Configurações controla aparência e comportamento e Sobre resume o aplicativo e dá acesso aos manuais.',
        'Limpar': 'ABA LIMPAR\n\nUse esta aba para o fluxo principal de PDFs. Adicione arquivos ou pastas, defina pasta de saída, sufixo, formato de exportação, intervalo de páginas e execute o processamento.',
        'Ferramentas': 'ABA FERRAMENTAS\n\nContém funções auxiliares fora do fluxo principal. Ela pode extrair páginas de PDF como imagens e também criar um novo PDF a partir de várias imagens.',
        'Converter': 'ABA CONVERTER\n\nUsada para preparar arquivos para e-readers e smartphones. Trabalha com PDF → EPUB, PDF → XTCH e EPUB → XTCH usando perfis de dispositivo para ajustar resolução, DPI e qualidade.',
        'Resultados': 'ABA RESULTADOS\n\nMostra o status final, as saídas geradas e um resumo de cada processo.',
        'Registros': 'ABA REGISTROS\n\nCentraliza mensagens internas, logs e diagnósticos para facilitar conferência e suporte.',
        'Configurações': 'ABA CONFIGURAÇÕES\n\nReúne temas, cores, idioma do aplicativo, desempenho, hardware, facilidades, segurança e logs. O idioma do aplicativo fica no início de Temas e cores.',
        'Sobre': 'ABA SOBRE\n\nApresenta um resumo do sistema e oferece acesso ao manual interativo e ao manual TXT separado do sistema.',
        'Botões do topo': 'BOTÕES DO TOPO\n\nProcurar atualizações verifica a versão configurada, Log abre o arquivo de log, Manual abre o manual interativo e o botão de tema alterna o modo visual.',
        'Perfis de dispositivo': 'PERFIS DE DISPOSITIVO\n\nO editor de perfis permite carregar um perfil existente, ajustar largura, altura, DPI, qualidade e outras opções, salvar alterações ou criar um perfil personalizado.',
        'FAQ rápido': 'FAQ RÁPIDO\n\nUse PDF → EPUB para leitura mais flexível. Use perfis de dispositivo na aba Converter para adaptar arquivos a um aparelho real. Se algo falhar, verifique Registros e erro.txt.'
    },
    'en_US': {
        'Visão geral': 'CUMA - Ultimate Manga Converter\n\nCUMA is organized into clear areas so each part has a specific role in the workflow. Clean handles the main PDF queue, Tools contains helper utilities, Converter prepares EPUB and XTCH with device profiles, Results shows generated output, Logs centralizes diagnostics, Settings controls appearance and behavior, and About summarizes the application and gives access to the manuals.',
        'Limpar': 'CLEAN TAB\n\nUse this tab for the main PDF workflow. Add files or folders, define output folder, suffix, export format, page range and execute processing.',
        'Ferramentas': 'TOOLS TAB\n\nContains helper functions outside the main workflow. It can extract PDF pages as images and also create a new PDF from multiple images.',
        'Converter': 'CONVERTER TAB\n\nUsed to prepare files for e-readers and smartphones. It works with PDF → EPUB, PDF → XTCH and EPUB → XTCH using device profiles to adjust resolution, DPI and quality.',
        'Resultados': 'RESULTS TAB\n\nShows final status, generated outputs and a summary of each process.',
        'Registros': 'LOGS TAB\n\nCentralizes internal messages, logs and diagnostics to simplify checking and support.',
        'Configurações': 'SETTINGS TAB\n\nGroups themes, colors, application language, performance, hardware, conveniences, security and logs. Application language appears at the beginning of Themes and colors.',
        'Sobre': 'ABOUT TAB\n\nPresents a short system summary and gives access to the interactive manual and the separate TXT manual.',
        'Botões do topo': 'TOP BUTTONS\n\nCheck for updates verifies the configured version, Log opens the log file, Manual opens the interactive manual and the theme button switches the visual mode.',
        'Perfis de dispositivo': 'DEVICE PROFILES\n\nThe profile editor lets you load an existing profile, adjust width, height, DPI, quality and other options, save changes or create a custom profile.',
        'FAQ rápido': 'QUICK FAQ\n\nUse PDF → EPUB for more flexible reading. Use device profiles in Converter to adapt files to a real device. If something fails, check Logs and erro.txt.'
    },
    'ko_KR': {
        'Visão geral': 'CUMA - 만화 변환 애플리케이션\n\nCUMA 는 각 영역이 분명한 역할을 가지도록 구성되어 있습니다. 정리는 메인 PDF 대기열, 도구는 보조 기능, 변환기는 장치 프로필과 함께 EPUB 및 XTCH 준비, 결과는 생성된 출력 표시, 기록은 진단 정보 집중, 설정은 외형과 동작 제어, 정보는 애플리케이션 요약과 설명서 접근을 담당합니다.',
        'Limpar': '정리 탭\n\n메인 PDF 작업 흐름에 사용됩니다. 파일 또는 폴더를 추가하고, 출력 폴더, 접미사, 내보내기 형식, 페이지 범위를 설정한 뒤 처리를 실행합니다.',
        'Ferramentas': '도구 탭\n\n메인 흐름 밖의 보조 기능을 포함합니다. PDF 페이지를 이미지로 추출하고 여러 이미지에서 새 PDF를 만들 수 있습니다.',
        'Converter': '변환기 탭\n\n전자책 단말기와 스마트폰용 파일 준비에 사용됩니다. PDF → EPUB, PDF → XTCH, EPUB → XTCH를 지원하며 장치 프로필로 해상도, DPI, 품질을 조정합니다.',
        'Resultados': '결과 탭\n\n최종 상태, 생성된 출력, 각 작업 요약을 보여줍니다.',
        'Registros': '기록 탭\n\n내부 메시지, 로그 및 진단 정보를 한곳에 모아 확인과 지원을 쉽게 합니다.',
        'Configurações': '설정 탭\n\n테마, 색상, 애플리케이션 언어, 성능, 하드웨어, 편의 기능, 보안 및 로그를 모읍니다. 애플리케이션 언어는 테마 및 색상 맨 앞에 있습니다.',
        'Sobre': '정보 탭\n\n시스템 요약을 보여 주고 대화형 설명서 및 분리된 TXT 설명서에 접근할 수 있습니다.',
        'Botões do topo': '상단 버튼\n\n업데이트 확인은 버전 확인, Log 는 로그 파일 열기, Manual 은 대화형 설명서 열기, 테마 버튼은 시각 모드 전환을 수행합니다.',
        'Perfis de dispositivo': '장치 프로필\n\n프로필 편집기는 기존 프로필 로드, 너비, 높이, DPI, 품질 및 기타 옵션 조정, 변경 저장 또는 사용자 지정 프로필 생성을 지원합니다.',
        'FAQ rápido': '빠른 FAQ\n\n더 유연한 읽기를 원하면 PDF → EPUB를 사용하세요. 실제 장치에 맞추려면 변환기 탭의 장치 프로필을 사용하세요. 문제가 있으면 기록 탭과 erro.txt 를 확인하세요.'
    },
}
for _code in ['es_ES','fr_FR','de_DE','it_IT','ja_JP','zh_TW','tr_TR']:
    V6_MANUAL_TEXTS.setdefault(_code, dict(V6_MANUAL_TEXTS['en_US']))


def _cuma_v6_log(context, exc=None):
    try:
        if exc is None:
            write_log(f'[{_CUMA_FINAL_V6_PATCH}] {context}')
        else:
            write_log(f'[{_CUMA_FINAL_V6_PATCH}] {context}: {exc}')
            write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_v6_load_lang_code(self=None):
    try:
        if self is not None and hasattr(self, 'app_language'):
            val = self.app_language.get()
            if val in V6_LANGUAGE_DISPLAY:
                return val
        data = load_interface_colors_file() if 'load_interface_colors_file' in globals() else {}
        if isinstance(data, dict):
            val = str(data.get('app_language', 'system'))
            if val in V6_LANGUAGE_DISPLAY:
                return val
    except Exception:
        pass
    return 'system'


def _cuma_v6_resolved_lang(self=None):
    code = _cuma_v6_load_lang_code(self)
    return _cuma_detect_system_language() if code == 'system' else code


def _cuma_v6_save_lang_code(code):
    try:
        p = interface_color_path()
        data = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        if not isinstance(data, dict):
            data = {}
        data['app_language'] = code if code in V6_LANGUAGE_DISPLAY else 'system'
        theme_mode = str(data.get('theme_mode', 'Escuro'))
        if 'Autom' in theme_mode:
            data['theme_mode'] = 'Automático'
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as exc:
        _cuma_v6_log('Falha ao salvar idioma V6', exc)


def _cuma_v6_tr(text, lang):
    if not isinstance(text, str) or not text:
        return text
    if text == APP_DISPLAY_NAME:
        return text
    if text in V6_LANGUAGE_DISPLAY.values():
        return text
    if lang == 'pt_BR':
        return text
    base = _cuma_fix_mojibake_text(text) if '_cuma_fix_mojibake_text' in globals() else text
    extra = V6_EXTRA_TEXT.get(lang, V6_EXTRA_TEXT.get('en_US', {}))
    if base in extra:
        return extra[base]
    mapping = I18N.get(lang, {}) if isinstance(I18N.get(lang, {}), dict) else {}
    if base in mapping:
        return mapping[base]
    return base


def _cuma_v6_translate_notebooks(widget, lang):
    try:
        if isinstance(widget, ttk.Notebook):
            for tab_id in widget.tabs():
                txt = widget.tab(tab_id, 'text')
                widget.tab(tab_id, text=_cuma_v6_tr(txt, lang))
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _cuma_v6_translate_notebooks(child, lang)
    except Exception:
        pass


def _cuma_v6_translate_tree_headers(widget, lang):
    heading_map = {'arquivo':'Arquivo','pasta':'Pasta','tamanho':'Tamanho','status':'Status','saida':'Saída','resumo':'Resumo'}
    try:
        if isinstance(widget, ttk.Treeview):
            for col in widget['columns']:
                base = heading_map.get(str(col), str(col))
                widget.heading(col, text=_cuma_v6_tr(base, lang))
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _cuma_v6_translate_tree_headers(child, lang)
    except Exception:
        pass


def _cuma_v6_translate_recursive(widget, lang):
    try:
        txt = widget.cget('text')
    except Exception:
        txt = None
    if isinstance(txt, str) and txt:
        try:
            widget.configure(text=_cuma_v6_tr(txt, lang))
        except Exception:
            pass
    try:
        for child in widget.winfo_children():
            _cuma_v6_translate_recursive(child, lang)
    except Exception:
        pass


def _cuma_v6_sync_header_spacing(self):
    try:
        buttons = []
        for child in self.header.winfo_children():
            try:
                txt = str(child.cget('text'))
            except Exception:
                txt = ''
            if txt:
                buttons.append((txt, child))
        # reaplica espaçamento consistente
        for txt, btn in buttons:
            try:
                btn.pack_forget()
            except Exception:
                pass
        ordered = []
        # preservar ordem visual da direita para esquerda do layout atual
        theme_btn = next((b for t,b in buttons if 'Tema' in t or 'theme' in t.lower()), None)
        manual_btn = next((b for t,b in buttons if 'Manual' in t or 'manual' in t.lower()), None)
        log_btn = next((b for t,b in buttons if t.lower() == 'log' or ' log' in t.lower()), None)
        update_btn = next((b for t,b in buttons if 'atualiza' in t.lower() or 'update' in t.lower()), None)
        others = [b for t,b in buttons if b not in {theme_btn, manual_btn, log_btn, update_btn}]
        for btn in [theme_btn, manual_btn, log_btn, update_btn]:
            if btn is not None:
                ordered.append(btn)
        ordered.extend(others)
        for i, btn in enumerate(ordered):
            pad = (8, 12) if i == 0 else (8, 0)
            btn.pack(side='right', padx=pad)
    except Exception as exc:
        _cuma_v6_log('Falha ao ajustar espaçamento do cabeçalho', exc)


def _cuma_v6_update_vars(self, lang):
    try:
        if hasattr(self, 'app_language_help'):
            sys_label = V6_LANGUAGE_DISPLAY.get(_cuma_detect_system_language(), _cuma_detect_system_language())
            sel_code = _cuma_v6_load_lang_code(self)
            sel_label = V6_LANGUAGE_DISPLAY.get(sel_code, sel_code)
            self.app_language_help.set(f"{_cuma_v6_tr('Idioma do sistema detectado', lang)}: {sys_label} | {_cuma_v6_tr('Selecionado', lang)}: {sel_label}")
    except Exception:
        pass
    for attr in ['xteink_status', 'tools_debug_var', 'xteink_device_note']:
        try:
            var = getattr(self, attr, None)
            if var is not None:
                var.set(_cuma_v6_tr(var.get(), lang))
        except Exception:
            pass


def _cuma_v6_setup_display_option_vars(self):
    if not hasattr(self, 'theme_mode_display'):
        self.theme_mode_display = tk.StringVar(value='')
    if not hasattr(self, 'custom_base_display'):
        self.custom_base_display = tk.StringVar(value='')


def _cuma_v6_option_display(raw_value, group, lang):
    mapping = V6_OPTION_DISPLAY.get(group, {})
    locale_map = mapping.get(lang, mapping.get('en_US', {}))
    return locale_map.get(raw_value, raw_value)


def _cuma_v6_option_raw(display_value, group, lang):
    mapping = V6_OPTION_DISPLAY.get(group, {})
    locale_map = mapping.get(lang, mapping.get('en_US', {}))
    inv = {v:k for k,v in locale_map.items()}
    return inv.get(display_value, display_value)


def _cuma_v6_setup_vars(self):
    _CUMA_FINAL_V6_RUNTIME['setup_vars'](self)
    try:
        code = _cuma_v6_load_lang_code(self)
        self.app_language = tk.StringVar(value=code)
        self.app_language_display = tk.StringVar(value=V6_LANGUAGE_DISPLAY.get(code, 'Automático'))
        self.app_language_help = tk.StringVar(value='')
        _cuma_v6_setup_display_option_vars(self)
    except Exception as exc:
        _cuma_v6_log('Falha ao preparar variáveis V6', exc)


def _cuma_v6_remove_duplicate_language_sections(self):
    try:
        queue_widgets = [self.tab_config]
        victims = []
        accepted = {'Idioma do aplicativo', 'Application language', '애플리케이션 언어'}
        while queue_widgets:
            widget = queue_widgets.pop(0)
            try:
                txt = str(widget.cget('text'))
            except Exception:
                txt = ''
            if txt in accepted:
                victims.append(widget)
            try:
                queue_widgets.extend(list(widget.winfo_children()))
            except Exception:
                pass
        for w in victims:
            try:
                w.destroy()
            except Exception:
                pass
        self._language_section_v6_installed = False
    except Exception as exc:
        _cuma_v6_log('Falha ao remover idiomas duplicados', exc)


def _cuma_v6_find_notebook(root_widget):
    if root_widget is None:
        return None
    queue_widgets = [root_widget]
    while queue_widgets:
        widget = queue_widgets.pop(0)
        if isinstance(widget, ttk.Notebook):
            return widget
        try:
            queue_widgets.extend(list(widget.winfo_children()))
        except Exception:
            pass
    return None


def _cuma_v6_bind_combo_translation(self, tab_theme, lang):
    try:
        combos = []
        queue_widgets = [tab_theme]
        while queue_widgets:
            widget = queue_widgets.pop(0)
            if isinstance(widget, ttk.Combobox):
                combos.append(widget)
            try:
                queue_widgets.extend(list(widget.winfo_children()))
            except Exception:
                pass
        # Esperado: [idioma_app, modo_visual, base_personalizado, ...]
        if len(combos) >= 3:
            lang_combo, mode_combo, base_combo = combos[0], combos[1], combos[2]
            self._v6_language_combo = lang_combo
            self._v6_theme_mode_combo = mode_combo
            self._v6_custom_base_combo = base_combo
            _cuma_v6_setup_display_option_vars(self)
            self.theme_mode_display.set(_cuma_v6_option_display(self.theme_mode.get(), 'theme_mode', lang))
            self.custom_base_display.set(_cuma_v6_option_display(self.custom_base_theme.get(), 'custom_base_theme', lang))
            mode_combo.configure(textvariable=self.theme_mode_display, values=list(V6_OPTION_DISPLAY['theme_mode'].get(lang, V6_OPTION_DISPLAY['theme_mode']['en_US']).values()))
            base_combo.configure(textvariable=self.custom_base_display, values=list(V6_OPTION_DISPLAY['custom_base_theme'].get(lang, V6_OPTION_DISPLAY['custom_base_theme']['en_US']).values()))
            def on_mode_change(_e=None):
                raw = _cuma_v6_option_raw(self.theme_mode_display.get(), 'theme_mode', lang)
                self.theme_mode.set(raw)
                try:
                    self._apply_theme_mode_selection(save=True)
                except Exception:
                    self.save_current_config(force=True)
            def on_base_change(_e=None):
                raw = _cuma_v6_option_raw(self.custom_base_display.get(), 'custom_base_theme', lang)
                self.custom_base_theme.set(raw)
                try:
                    self._apply_theme_mode_selection(save=True)
                except Exception:
                    self.save_current_config(force=True)
            mode_combo.bind('<<ComboboxSelected>>', on_mode_change)
            base_combo.bind('<<ComboboxSelected>>', on_base_change)
    except Exception as exc:
        _cuma_v6_log('Falha ao traduzir combos principais', exc)


def _cuma_v6_insert_language_section(self):
    if getattr(self, '_language_section_v6_installed', False):
        return
    notebook = _cuma_v6_find_notebook(getattr(self, 'tab_config', None))
    if notebook is None:
        return
    lang = _cuma_v6_resolved_lang(self)
    try:
        tabs = notebook.tabs()
        if not tabs:
            return
        tab_theme = notebook.nametowidget(tabs[0])
        section = ttk.LabelFrame(tab_theme, text=_cuma_v6_tr('Idioma do aplicativo', lang), padding=12, style='Card.TLabelframe')
        children = list(tab_theme.winfo_children())
        if children:
            section.pack(fill='x', pady=(0, 12), before=children[0])
        else:
            section.pack(fill='x', pady=(0, 12))
        row = ttk.Frame(section, style='Card.TFrame'); row.pack(fill='x')
        ttk.Label(row, text=_cuma_v6_tr('Idioma', lang), style='TitleSmall.TLabel').pack(side='left')
        self.app_language_display.set(V6_LANGUAGE_DISPLAY.get(_cuma_v6_load_lang_code(self), 'Automático'))
        combo = ttk.Combobox(row, textvariable=self.app_language_display, values=list(V6_LANGUAGE_DISPLAY.values()), state='readonly', width=26)
        combo.pack(side='left', padx=(12, 0))
        def on_lang_select(_e=None):
            code = V6_DISPLAY_TO_CODE.get(self.app_language_display.get(), 'system')
            self.app_language.set(code)
            _cuma_v6_save_lang_code(code)
            _cuma_v6_apply_language(self)
        combo.bind('<<ComboboxSelected>>', on_lang_select)
        ttk.Label(section, text=_cuma_v6_tr('Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.', lang), style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(8, 4))
        _cuma_v6_update_vars(self, lang)
        ttk.Label(section, textvariable=self.app_language_help, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w')
        self._language_section_v6_installed = True
        _cuma_v6_bind_combo_translation(self, tab_theme, lang)
    except Exception as exc:
        _cuma_v6_log('Falha ao inserir seção de idioma V6', exc)


def _cuma_v6_apply_language(self):
    lang = _cuma_v6_resolved_lang(self)
    try:
        _cuma_v6_translate_recursive(self.root, lang)
        _cuma_v6_translate_notebooks(self.root, lang)
        _cuma_v6_translate_tree_headers(self.root, lang)
        _cuma_v6_update_vars(self, lang)
        try:
            if hasattr(self, 'nav_items'):
                for label, item in self.nav_items.items():
                    try: item['text'].configure(text=_cuma_v6_tr(label, lang))
                    except Exception: pass
        except Exception:
            pass
        try:
            if hasattr(self, 'dashboard_cards'):
                cards = self.dashboard_cards
                cards['files']['title'].configure(text=_cuma_v6_tr('Fila principal', lang))
                cards['xteink']['title'].configure(text=_cuma_v6_tr('Converter', lang))
                cards['update']['title'].configure(text=_cuma_v6_tr('Versão', lang))
        except Exception:
            pass
        try:
            self.build_about_tab()
        except Exception:
            pass
        try:
            ensure_manual()
        except Exception:
            pass
        _cuma_v6_sync_header_spacing(self)
        try:
            notebook = _cuma_v6_find_notebook(getattr(self, 'tab_config', None))
            if notebook is not None and notebook.tabs():
                tab_theme = notebook.nametowidget(notebook.tabs()[0])
                _cuma_v6_bind_combo_translation(self, tab_theme, lang)
        except Exception:
            pass
    except Exception as exc:
        _cuma_v6_log('Falha ao aplicar idioma global V6', exc)


def _cuma_v6_manual_sections(lang):
    return V6_MANUAL_TEXTS.get(lang, V6_MANUAL_TEXTS['en_US' if lang != 'pt_BR' else 'pt_BR'])


def _cuma_v6_manual_text(lang):
    intro_map = {
        'pt_BR': 'MANUAL DO PROGRAMA - CUMA - Conversor Ultimate de Mangás\n\nEste arquivo TXT acompanha o aplicativo e deve acompanhar a compilação do executável Windows.\n\nUse o botão Manual do aplicativo para abrir a versão interativa.\n\n',
        'en_US': 'CUMA APPLICATION MANUAL\n\nThis TXT file accompanies the application and should also accompany the Windows executable build.\n\nUse the Manual button to open the interactive version.\n\n',
        'ko_KR': 'CUMA 애플리케이션 설명서\n\n이 TXT 파일은 애플리케이션과 함께 제공되며 Windows 실행 파일에도 함께 포함되어야 합니다.\n\nManual 버튼으로 대화형 버전을 엽니다.\n\n',
    }
    for _code in ['es_ES','fr_FR','de_DE','it_IT','ja_JP','zh_TW','tr_TR']:
        intro_map.setdefault(_code, intro_map['en_US'])
    parts = _cuma_v6_manual_sections(lang)
    body = '\n\n'.join(f"## {_cuma_v6_tr(title, lang)}\n\n{content}" for title, content in parts.items())
    return intro_map.get(lang, intro_map['en_US']) + body + '\n'


def ensure_manual() -> Path:
    lang = _cuma_v6_resolved_lang(None)
    try:
        manual_path().write_text(_cuma_v6_manual_text(lang), encoding='utf-8')
    except Exception as exc:
        _cuma_v6_log('Falha ao gerar manual V6', exc)
    return manual_path()


def _cuma_v6_show_manual(self):
    lang = _cuma_v6_resolved_lang(self)
    ensure_manual()
    top = tk.Toplevel(self.root)
    top.title(f"{_cuma_v6_tr('Manual interativo do CUMA', lang)} - CUMA")
    top.geometry('1140x760')
    top.transient(self.root)
    pal = getattr(self, '_theme_palette', {}) or {}
    bg = pal.get('bg', '#0F1318'); surface = pal.get('surface', '#20262F'); fg = pal.get('fg', '#E5E7EB'); border = pal.get('border', '#38414E')
    top.configure(bg=bg)
    wrap = ttk.Frame(top, style='Card.TFrame', padding=12); wrap.pack(fill='both', expand=True)
    ttk.Label(wrap, text=_cuma_v6_tr('Manual interativo do CUMA', lang), style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 6))
    ttk.Label(wrap, text=_cuma_v6_tr('Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.', lang), style='Muted.TLabel', wraplength=1080, justify='left').pack(anchor='w', pady=(0, 12))
    body = ttk.Frame(wrap, style='Card.TFrame'); body.pack(fill='both', expand=True)
    left = ttk.LabelFrame(body, text=_cuma_v6_tr('Seções', lang), padding=10, style='Card.TLabelframe'); left.pack(side='left', fill='y', padx=(0, 12))
    right = ttk.LabelFrame(body, text=_cuma_v6_tr('Conteúdo', lang), padding=10, style='Card.TLabelframe'); right.pack(side='left', fill='both', expand=True)
    title_var = tk.StringVar(value=_cuma_v6_tr('Visão geral', lang))
    ttk.Label(right, textvariable=title_var, style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 8))
    txt = tk.Text(right, wrap='word', relief='flat', bd=0, bg=surface, fg=fg, insertbackground=fg, highlightthickness=1, highlightbackground=border, padx=10, pady=10)
    txt.pack(fill='both', expand=True)
    txt.configure(state='disabled')
    parts = _cuma_v6_manual_sections(lang)
    order = ['Visão geral','Limpar','Ferramentas','Converter','Resultados','Registros','Configurações','Sobre','Botões do topo','Perfis de dispositivo','FAQ rápido']
    def open_sec(sec):
        title_var.set(_cuma_v6_tr(sec, lang))
        txt.configure(state='normal')
        txt.delete('1.0','end')
        txt.insert('1.0', parts.get(sec,''))
        txt.configure(state='disabled')
    for sec in order:
        ttk.Button(left, text=_cuma_v6_tr(sec, lang), command=lambda s=sec: open_sec(s), style='Ghost.TButton').pack(fill='x', pady=3)
    open_sec('Visão geral')
    btns = ttk.Frame(wrap, style='Card.TFrame'); btns.pack(fill='x', pady=(10,0))
    ttk.Button(btns, text=_cuma_v6_tr('Abrir manual TXT completo', lang), command=lambda: open_path(ensure_manual()), style='Ghost.TButton').pack(side='left')
    ttk.Button(btns, text=_cuma_v6_tr('Fechar', lang), command=top.destroy, style='Accent.TButton').pack(side='right')


def _cuma_v6_build_about_tab(self):
    lang = _cuma_v6_resolved_lang(self)
    try:
        for child in list(self.tab_about.winfo_children()):
            try: child.destroy()
            except Exception: pass
        wrap = ttk.Frame(self.tab_about, style='Card.TFrame', padding=8); wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text=_cuma_v6_tr('Sobre o CUMA', lang), style='TitleSmall.TLabel').pack(anchor='w', pady=(2,4))
        ttk.Label(wrap, text=f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}', style='Muted.TLabel').pack(anchor='w')
        ttk.Label(wrap, text=_cuma_v6_tr('Resumo rápido do que cada aba faz:', lang), style='Muted.TLabel').pack(anchor='w', pady=(10,6))
        summary_box = ttk.LabelFrame(wrap, text=_cuma_v6_tr('Abas do aplicativo', lang), padding=12, style='Card.TLabelframe'); summary_box.pack(fill='x', pady=(0,10))
        summary = {
            'Limpar': 'Use esta aba para o fluxo principal de PDFs.',
            'Ferramentas': 'Reúne funções auxiliares fora do fluxo principal.',
            'Converter': 'Prepara arquivos para e-readers e smartphones com perfis de dispositivo.',
            'Resultados': 'Mostra o status final e as saídas geradas.',
            'Registros': 'Centraliza logs e diagnósticos.',
            'Configurações': 'Controla aparência, idioma, desempenho e segurança.',
            'Sobre': 'Resume o aplicativo e leva aos manuais.'
        }
        for tab_name, desc in summary.items():
            ttk.Label(summary_box, text=f"• {_cuma_v6_tr(tab_name, lang)}: {_cuma_v6_tr(desc, lang)}", style='Muted.TLabel', wraplength=1020, justify='left').pack(anchor='w', pady=2)
        btns = ttk.Frame(wrap, style='Card.TFrame'); btns.pack(fill='x')
        ttk.Button(btns, text=_cuma_v6_tr('Abrir manual interativo', lang), command=self.show_cuma_manual, style='Accent.TButton').pack(side='left')
        ttk.Button(btns, text=_cuma_v6_tr('Abrir manual TXT completo', lang), command=lambda: open_path(ensure_manual()), style='Ghost.TButton').pack(side='left', padx=8)
    except Exception as exc:
        _cuma_v6_log('Falha ao reconstruir Sobre V6', exc)


def _cuma_v6_build_config_tab(self):
    result = _CUMA_FINAL_V6_RUNTIME['build_config_tab'](self)
    try:
        _cuma_v6_remove_duplicate_language_sections(self)
        _cuma_v6_insert_language_section(self)
        _cuma_v6_apply_language(self)
    except Exception as exc:
        _cuma_v6_log('Falha no build_config_tab V6', exc)
    return result


def _cuma_v6_build(self):
    result = _CUMA_FINAL_V6_RUNTIME['build'](self)
    try:
        _cuma_v6_remove_duplicate_language_sections(self)
        _cuma_v6_insert_language_section(self)
        _cuma_v6_apply_language(self)
        _cuma_v6_sync_header_spacing(self)
    except Exception as exc:
        _cuma_v6_log('Falha no build V6', exc)
    return result


def _cuma_v6_show_page(self, label, save_state=True):
    result = _CUMA_FINAL_V6_RUNTIME['show_page'](self, label, save_state)
    try:
        _cuma_v6_apply_language(self)
    except Exception as exc:
        _cuma_v6_log('Falha no show_page V6', exc)
    return result


def _cuma_v6_apply_theme(self):
    result = _CUMA_FINAL_V6_RUNTIME['apply_theme'](self)
    try:
        _cuma_v6_apply_language(self)
        _cuma_v6_sync_header_spacing(self)
    except Exception as exc:
        _cuma_v6_log('Falha no apply_theme V6', exc)
    return result


def _cuma_install_final_v6_patch():
    if getattr(App, '_cuma_final_v6_patch_installed', False):
        return
    App._cuma_final_v6_patch_installed = True
    App.setup_vars = _cuma_v6_setup_vars
    App.build_config_tab = _cuma_v6_build_config_tab
    App.show_cuma_manual = _cuma_v6_show_manual
    App.build_about_tab = _cuma_v6_build_about_tab
    App.build = _cuma_v6_build
    App.show_page = _cuma_v6_show_page
    App.apply_theme = _cuma_v6_apply_theme
    globals()['_cuma_apply_language_to_widgets'] = _cuma_v6_apply_language
    globals()['_cuma_on_language_changed'] = _cuma_v6_apply_language
    globals()['_cuma_tr'] = _cuma_v6_tr

_CUMA_FINAL_V6_RUNTIME = {
    'setup_vars': App.setup_vars,
    'build_config_tab': getattr(App, 'build_config_tab', None),
    'build': App.build,
    'show_page': App.show_page,
    'apply_theme': App.apply_theme,
}
_cuma_install_final_v6_patch()



# =============================================================================
# CUMA - PATCH FINAL V8
# Objetivo: reforço amplo de tradução de TODOS os textos clicáveis/visíveis
# (botões, abas, títulos de seções, headings, sidebar, cabeçalho, textos fixos).
# =============================================================================

_CUMA_FINAL_V8_PATCH = 'final_v8_full_visible_text_translation_2026_06_22'

V8_UI_I18N = {
    'en_US': {
        'Fechar':'Close','Cancelar':'Cancel','Texto de':'Sample text','Exemplo':'Example','Entrada':'Input','Ok':'OK',
        '☀ Tema claro':'☀ Light theme','Manual':'Manual','Log':'Log','Configurações organizadas por categoria':'Settings organized by category',
        'Temas e cores':'Themes and colors','Qualidade e desempenho':'Quality and performance','Hardware':'Hardware','Facilidades':'Conveniences','Segurança e logs':'Security and logs',
        'Cor principal do botão':'Main button color','Personalizar cor':'Customize color','Preset Manga Dark':'Preset Manga Dark','Preset Escuro':'Dark preset','Preset Claro':'Light preset',
        'Aplicar ajustes avançados':'Apply advanced adjustments','Restaurar tema escolhido':'Restore selected theme','Ver status do hardware':'View hardware status','Benchmark rápido':'Quick benchmark','Copiar diagnóstico':'Copy diagnostics',
        'Sobre o CUMA':'About CUMA','Abrir manual completo':'Open full manual','Salvar como PNG; desligado salva JPG':'Save as PNG; off saves JPG','Abrir pasta ao concluir':'Open folder when done','Zoom/renderização':'Zoom/rendering',
        'Nome do PDF':'PDF name','Progresso':'Progress','Arquivo atual':'Current file','Total':'Total','Processar selecionados':'Process selected','Processar todos':'Process all',
        'Criar PDF dos selecionados':'Create PDF from selected','Criar PDF de todos':'Create PDF from all','Extrair páginas':'Extract pages','Criar PDF de imagens':'Create PDF from images',
        'Dispositivos e conversões':'Devices and conversions','Dispositivo':'Device','Aplicar perfil':'Apply profile','Editor de perfis':'Profile editor','Pasta de saída':'Output folder','Escolher':'Choose',
        'Arraste PDFs, EPUBs ou pastas aqui':'Drag PDFs, EPUBs or folders here','PDF para EPUB':'PDF to EPUB','PDF para XTCH':'PDF to XTCH','EPUB para XTCH':'EPUB to XTCH',
        'Pause':'Pause','Play':'Play','Processar tudo':'Process all','Funções por tipo de arquivo':'Functions by file type','Nome do dispositivo':'Device name',
        'Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.':'These options are saved per device. In Custom you can create a new name and resolution.',
        'Salvar perfil':'Save profile','Procurar atualizações':'Check for updates','Abrir pasta Converter':'Open Converter folder','Editor de perfis de dispositivo':'Device profile editor','Perfil carregado':'Loaded profile',
        'Salvar como nome':'Save as name','Salvar no perfil atual':'Save to current profile','Salvar como novo personalizado':'Save as new custom','Restaurar perfis padrão':'Restore default profiles',
        'Idioma do aplicativo':'Application language','Idioma':'Language','CUMA':'CUMA','Arraste PDFs ou pastas aqui':'Drag PDFs or folders here','Incluir subpastas':'Include subfolders','Saída e organização':'Output and organization',
        'Sufixo':'Suffix','Formato de exportação':'Export format','Intervalo de páginas':'Page range','Abrir resultado ao concluir':'Open result when done','Geral':'General','PDF atual':'Current PDF',
        'Carregar prévia do selecionado':'Load preview of selected','Extrair páginas dos PDFs selecionados como imagens':'Extract selected PDF pages as images','Criar PDF a partir de várias imagens':'Create PDF from multiple images',
        'Aparência e interface':'Appearance and interface','Salvar automaticamente alterações nas configurações':'Automatically save settings changes','Mostrar dicas/tooltips':'Show tips/tooltips',
        'Confirmar antes de ações perigosas':'Confirm before dangerous actions','Lembrar tamanho/posição da janela':'Remember window size/position','Lembrar última aba aberta':'Remember last opened tab',
        'Desempenho, CPU/GPU e cache':'Performance, CPU/GPU and cache','Automático: NVIDIA CUDA → AMD OpenCL → Intel OpenCL → OpenCL genérico → CPU.':'Automatic: NVIDIA CUDA → AMD OpenCL → Intel OpenCL → generic OpenCL → CPU.',
        'Limpar cache ao fechar':'Clear cache on close','Testar aceleração':'Test acceleration','Benchmark CPU/GPU':'CPU/GPU benchmark','Arquivos, segurança e automação':'Files, security and automation',
        'Logs e diagnóstico':'Logs and diagnostics','Salvar log automaticamente':'Save log automatically','Abrir log':'Open log','Prévia e visualização':'Preview and visualization','Usar cache na prévia':'Use cache in preview',
        'Abrir prévia maximizada':'Open preview maximized','Salvar configurações':'Save settings','Configurações do PDF':'PDF settings',
        'Aqui ficam as opções menos frequentes e mais avançadas, para evitar redundância com a aba Limpar.':'Less frequent and advanced options stay here to avoid redundancy with the Clean tab.',
        'Manter últimas páginas':'Keep last pages','Configurações do XTEINK':'XTEINK settings','Qualidade JPEG':'JPEG quality',
        'PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.':'PDF → EPUB: renders the PDF, adapts to the device and creates an EPUB with image pages.',
        'PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.':'PDF → XTCH: generates native 2-bit grayscale XTCH directly from the PDF. It does not run xtcjs workers.',
        'EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.':'EPUB → XTCH: converts image-based EPUB to native XTCH.','Manual - CUMA':'Manual - CUMA','Funções específicas do Converter':'Converter-specific functions',
        'Prévia':'Preview','Limpar PDF':'Clean PDF','Limpar':'Clean','Ferramentas':'Tools','Converter':'Converter','Resultados':'Results','Registros':'Logs','Configurações':'Settings','Sobre':'About',
    },
    'es_ES': {
        'Fechar':'Cerrar','Cancelar':'Cancelar','☀ Tema claro':'☀ Tema claro','Manual':'Manual','Log':'Log','Configurações organizadas por categoria':'Configuración organizada por categoría',
        'Temas e cores':'Temas y colores','Qualidade e desempenho':'Calidad y rendimiento','Hardware':'Hardware','Facilidades':'Facilidades','Segurança e logs':'Seguridad y registros',
        'Cor principal do botão':'Color principal del botón','Personalizar cor':'Personalizar color','Aplicar ajustes avançados':'Aplicar ajustes avanzados','Restaurar tema escolhido':'Restaurar tema elegido','Ver status do hardware':'Ver estado del hardware','Benchmark rápido':'Benchmark rápido','Copiar diagnóstico':'Copiar diagnóstico',
        'Sobre o CUMA':'Acerca de CUMA','Abrir manual completo':'Abrir manual completo','Abrir pasta ao concluir':'Abrir carpeta al finalizar','Nome do PDF':'Nombre del PDF','Progresso':'Progreso','Arquivo atual':'Archivo actual','Total':'Total',
        'Processar selecionados':'Procesar seleccionados','Processar todos':'Procesar todos','Criar PDF dos selecionados':'Crear PDF de los seleccionados','Criar PDF de todos':'Crear PDF de todos','Extrair páginas':'Extraer páginas','Criar PDF de imagens':'Crear PDF de imágenes',
        'Dispositivos e conversões':'Dispositivos y conversiones','Dispositivo':'Dispositivo','Aplicar perfil':'Aplicar perfil','Editor de perfis':'Editor de perfiles','Pasta de saída':'Carpeta de salida','Escolher':'Elegir','Procurar atualizações':'Buscar actualizaciones',
        'Abrir pasta Converter':'Abrir carpeta del Convertidor','Idioma do aplicativo':'Idioma de la aplicación','Idioma':'Idioma','Arraste PDFs ou pastas aqui':'Arrastre PDFs o carpetas aquí','Incluir subpastas':'Incluir subcarpetas','Saída e organização':'Salida y organización',
        'Sufixo':'Sufijo','Formato de exportação':'Formato de exportación','Intervalo de páginas':'Rango de páginas','Abrir resultado ao concluir':'Abrir resultado al finalizar','Geral':'General','PDF atual':'PDF actual','Carregar prévia do selecionado':'Cargar vista previa del seleccionado',
        'Aparência e interface':'Apariencia e interfaz','Salvar configurações':'Guardar configuración','Configurações do PDF':'Configuración del PDF','Configurações do XTEINK':'Configuración de XTEINK','Qualidade JPEG':'Calidad JPEG','Prévia':'Vista previa','Limpar PDF':'Limpiar PDF','Limpar':'Limpiar','Ferramentas':'Herramientas','Converter':'Convertidor','Resultados':'Resultados','Registros':'Registros','Configurações':'Configuración','Sobre':'Acerca de',
    },
    'fr_FR': {'Fechar':'Fermer','Cancelar':'Annuler','☀ Tema claro':'☀ Thème clair','Manual':'Manuel','Log':'Journal','Temas e cores':'Thèmes et couleurs','Qualidade e desempenho':'Qualité et performances','Segurança e logs':'Sécurité et journaux','Idioma do aplicativo':"Langue de l'application",'Idioma':'Langue','Procurar atualizações':'Rechercher des mises à jour','Abrir pasta Converter':'Ouvrir le dossier Convertisseur','Prévia':'Aperçu','Limpar':'Nettoyer','Ferramentas':'Outils','Converter':'Convertisseur','Resultados':'Résultats','Registros':'Journaux','Configurações':'Paramètres','Sobre':'À propos','Fechar':'Fermer'},
    'de_DE': {'Fechar':'Schließen','Cancelar':'Abbrechen','☀ Tema claro':'☀ Helles Thema','Manual':'Handbuch','Log':'Protokoll','Temas e cores':'Themen und Farben','Qualidade e desempenho':'Qualität und Leistung','Segurança e logs':'Sicherheit und Protokolle','Idioma do aplicativo':'App-Sprache','Idioma':'Sprache','Procurar atualizações':'Nach Updates suchen','Abrir pasta Converter':'Konverter-Ordner öffnen','Prévia':'Vorschau','Limpar':'Bereinigen','Ferramentas':'Werkzeuge','Converter':'Konverter','Resultados':'Ergebnisse','Registros':'Protokolle','Configurações':'Einstellungen','Sobre':'Info'},
    'it_IT': {'Fechar':'Chiudi','Cancelar':'Annulla','☀ Tema claro':'☀ Tema chiaro','Manual':'Manuale','Log':'Log','Temas e cores':'Temi e colori','Qualidade e desempenho':'Qualità e prestazioni','Segurança e logs':'Sicurezza e log','Idioma do aplicativo':'Lingua dell’applicazione','Idioma':'Lingua','Procurar atualizações':'Controlla aggiornamenti','Abrir pasta Converter':'Apri cartella Convertitore','Prévia':'Anteprima','Limpar':'Pulisci','Ferramentas':'Strumenti','Converter':'Convertitore','Resultados':'Risultati','Registros':'Registri','Configurações':'Impostazioni','Sobre':'Informazioni'},
    'ja_JP': {'Fechar':'閉じる','Cancelar':'キャンセル','☀ Tema claro':'☀ ライトテーマ','Manual':'マニュアル','Log':'ログ','Temas e cores':'テーマと色','Qualidade e desempenho':'品質とパフォーマンス','Segurança e logs':'セキュリティとログ','Idioma do aplicativo':'アプリの言語','Idioma':'言語','Procurar atualizações':'更新を確認','Abrir pasta Converter':'変換フォルダーを開く','Prévia':'プレビュー','Limpar':'クリーン','Ferramentas':'ツール','Converter':'変換','Resultados':'結果','Registros':'ログ','Configurações':'設定','Sobre':'情報'},
    'ko_KR': { 'Fechar':'닫기','Cancelar':'취소','☀ Tema claro':'☀ 라이트 테마','Manual':'설명서','Log':'로그','Configurações organizadas por categoria':'범주별로 정리된 설정','Temas e cores':'테마 및 색상','Qualidade e desempenho':'품질 및 성능','Hardware':'하드웨어','Facilidades':'편의 기능','Segurança e logs':'보안 및 로그','Cor principal do botão':'버튼 기본 색상','Personalizar cor':'색상 사용자 지정','Abrir manual completo':'전체 설명서 열기','Progresso':'진행률','Arquivo atual':'현재 파일','Total':'전체','Dispositivos e conversões':'장치 및 변환','Dispositivo':'장치','Aplicar perfil':'프로필 적용','Editor de perfis':'프로필 편집기','Pasta de saída':'출력 폴더','Escolher':'선택','Idioma do aplicativo':'애플리케이션 언어','Idioma':'언어','Salvar configurações':'설정 저장','Abrir log':'로그 열기','Prévia':'미리보기','Limpar':'정리','Ferramentas':'도구','Converter':'변환기','Resultados':'결과','Registros':'기록','Configurações':'설정','Sobre':'정보'},
    'zh_TW': {'Fechar':'關閉','Cancelar':'取消','☀ Tema claro':'☀ 淺色主題','Manual':'手冊','Log':'記錄','Temas e cores':'主題與色彩','Qualidade e desempenho':'品質與效能','Segurança e logs':'安全與記錄','Idioma do aplicativo':'應用程式語言','Idioma':'語言','Procurar atualizações':'檢查更新','Abrir pasta Converter':'開啟轉換器資料夾','Prévia':'預覽','Limpar':'清理','Ferramentas':'工具','Converter':'轉換器','Resultados':'結果','Registros':'記錄','Configurações':'設定','Sobre':'關於'},
    'tr_TR': {'Fechar':'Kapat','Cancelar':'İptal','☀ Tema claro':'☀ Açık tema','Manual':'Kılavuz','Log':'Günlük','Temas e cores':'Temalar ve renkler','Qualidade e desempenho':'Kalite ve performans','Segurança e logs':'Güvenlik ve günlükler','Idioma do aplicativo':'Uygulama dili','Idioma':'Dil','Procurar atualizações':'Güncellemeleri kontrol et','Abrir pasta Converter':'Dönüştürücü klasörünü aç','Prévia':'Önizleme','Limpar':'Temizle','Ferramentas':'Araçlar','Converter':'Dönüştürücü','Resultados':'Sonuçlar','Registros':'Kayıtlar','Configurações':'Ayarlar','Sobre':'Hakkında'},
}

# fallback para idiomas menos completos: usa inglês como base extra
for _code in ['es_ES','fr_FR','de_DE','it_IT','ja_JP','ko_KR','zh_TW','tr_TR']:
    _base = dict(V8_UI_I18N.get('en_US', {}))
    _base.update(V8_UI_I18N.get(_code, {}))
    V8_UI_I18N[_code] = _base


def _cuma_v8_log(context, exc=None):
    try:
        if exc is None:
            write_log(f'[{_CUMA_FINAL_V8_PATCH}] {context}')
        else:
            write_log(f'[{_CUMA_FINAL_V8_PATCH}] {context}: {exc}')
            write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_v8_canonical(text):
    if not isinstance(text, str) or not text:
        return text
    fixed = _cuma_fix_mojibake_text(text) if '_cuma_fix_mojibake_text' in globals() else text
    # mapear textos já traduzidos de volta para chave PT-BR quando possível
    for _lang, _mapping in V8_UI_I18N.items():
        if _lang == 'pt_BR':
            continue
        for _pt, _translated in _mapping.items():
            if fixed == _translated:
                return _pt
    for _lang, _mapping in I18N.items():
        if _lang == 'pt_BR' or not isinstance(_mapping, dict):
            continue
        for _pt, _translated in _mapping.items():
            if fixed == _translated:
                return _pt
    return fixed


def _cuma_v8_tr(text, lang):
    base = _cuma_v8_canonical(text)
    if not isinstance(base, str) or not base or lang == 'pt_BR':
        return base
    if base == APP_DISPLAY_NAME:
        return base
    if base in V6_LANGUAGE_DISPLAY.values():
        return base
    extra = V8_UI_I18N.get(lang, {})
    if base in extra:
        return extra[base]
    # reaproveita o tradutor V6 para outros textos já cobertos por V6/I18N
    try:
        return _cuma_v6_tr(base, lang)
    except Exception:
        return base


def _cuma_v8_translate_widget_tree(widget, lang):
    try:
        txt = widget.cget('text')
    except Exception:
        txt = None
    if isinstance(txt, str) and txt:
        try:
            if not hasattr(widget, '_cuma_base_text'):
                setattr(widget, '_cuma_base_text', _cuma_v8_canonical(txt))
            base = getattr(widget, '_cuma_base_text', txt)
            if base != APP_DISPLAY_NAME:
                widget.configure(text=_cuma_v8_tr(base, lang))
        except Exception:
            pass
    # notebook tabs
    try:
        if isinstance(widget, ttk.Notebook):
            if not hasattr(widget, '_cuma_base_tabs'):
                base_tabs = {}
                for tab_id in widget.tabs():
                    base_tabs[tab_id] = _cuma_v8_canonical(widget.tab(tab_id, 'text'))
                setattr(widget, '_cuma_base_tabs', base_tabs)
            base_tabs = getattr(widget, '_cuma_base_tabs', {})
            for tab_id in widget.tabs():
                base = base_tabs.get(tab_id, _cuma_v8_canonical(widget.tab(tab_id, 'text')))
                widget.tab(tab_id, text=_cuma_v8_tr(base, lang))
        if isinstance(widget, ttk.Treeview):
            if not hasattr(widget, '_cuma_base_headings'):
                heading_map = {}
                for col in widget['columns']:
                    heading_map[col] = _cuma_v8_canonical(widget.heading(col, 'text'))
                setattr(widget, '_cuma_base_headings', heading_map)
            heading_map = getattr(widget, '_cuma_base_headings', {})
            for col in widget['columns']:
                base = heading_map.get(col, _cuma_v8_canonical(widget.heading(col, 'text')))
                widget.heading(col, text=_cuma_v8_tr(base, lang))
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _cuma_v8_translate_widget_tree(child, lang)
    except Exception:
        pass


def _cuma_v8_apply_language(self):
    lang = _cuma_v6_resolved_lang(self) if '_cuma_v6_resolved_lang' in globals() else _cuma_resolved_language(self)
    try:
        _cuma_v8_translate_widget_tree(self.root, lang)
        # vars auxiliares
        try:
            if hasattr(self, 'app_language_help'):
                sys_label = V6_LANGUAGE_DISPLAY.get(_cuma_detect_system_language(), _cuma_detect_system_language())
                sel_code = _cuma_v6_load_lang_code(self)
                sel_label = V6_LANGUAGE_DISPLAY.get(sel_code, sel_code)
                self.app_language_help.set(f"{_cuma_v8_tr('Idioma do sistema detectado', lang)}: {sys_label} | {_cuma_v8_tr('Selecionado', lang)}: {sel_label}")
        except Exception:
            pass
        for attr in ['xteink_status', 'tools_debug_var', 'xteink_device_note', 'xteink_counter', 'status']:
            try:
                var = getattr(self, attr, None)
                if var is not None:
                    cur = var.get()
                    if not hasattr(var, '_cuma_base_value'):
                        setattr(var, '_cuma_base_value', _cuma_v8_canonical(cur))
                    base = getattr(var, '_cuma_base_value', cur)
                    var.set(_cuma_v8_tr(base, lang))
            except Exception:
                pass
        # manter nome do app
        try:
            self.root.title('cuma')
        except Exception:
            pass
        try:
            if hasattr(self, 'sidebar'):
                _cuma_force_sidebar_selection(self, getattr(self, '_current_tab_label', 'Limpar'))
        except Exception:
            pass
    except Exception as exc:
        _cuma_v8_log('Falha ao aplicar tradução total V8', exc)


def _cuma_v8_build(self):
    result = _CUMA_FINAL_V8_RUNTIME['build'](self)
    try:
        _cuma_v6_remove_duplicate_language_sections(self)
        _cuma_v6_insert_language_section(self)
        _cuma_v8_apply_language(self)
        _cuma_v6_sync_header_spacing(self)
    except Exception as exc:
        _cuma_v8_log('Falha no build V8', exc)
    return result


def _cuma_v8_build_config_tab(self):
    result = _CUMA_FINAL_V8_RUNTIME['build_config_tab'](self)
    try:
        _cuma_v6_remove_duplicate_language_sections(self)
        _cuma_v6_insert_language_section(self)
        _cuma_v8_apply_language(self)
    except Exception as exc:
        _cuma_v8_log('Falha na aba Configurações V8', exc)
    return result


def _cuma_v8_show_page(self, label, save_state=True):
    result = _CUMA_FINAL_V8_RUNTIME['show_page'](self, label, save_state)
    try:
        _cuma_v8_apply_language(self)
    except Exception as exc:
        _cuma_v8_log('Falha no show_page V8', exc)
    return result


def _cuma_v8_apply_theme(self):
    result = _CUMA_FINAL_V8_RUNTIME['apply_theme'](self)
    try:
        _cuma_v8_apply_language(self)
        _cuma_v6_sync_header_spacing(self)
    except Exception as exc:
        _cuma_v8_log('Falha no apply_theme V8', exc)
    return result


def _cuma_v8_show_manual(self):
    return _cuma_v6_show_manual(self)


def _cuma_install_final_v8_patch():
    if getattr(App, '_cuma_final_v8_patch_installed', False):
        return
    App._cuma_final_v8_patch_installed = True
    App.build = _cuma_v8_build
    App.build_config_tab = _cuma_v8_build_config_tab
    App.show_page = _cuma_v8_show_page
    App.apply_theme = _cuma_v8_apply_theme
    App.show_cuma_manual = _cuma_v8_show_manual
    globals()['_cuma_apply_language_to_widgets'] = _cuma_v8_apply_language
    globals()['_cuma_on_language_changed'] = _cuma_v8_apply_language
    globals()['_cuma_tr'] = _cuma_v8_tr

_CUMA_FINAL_V8_RUNTIME = {
    'build': App.build,
    'build_config_tab': getattr(App, 'build_config_tab', None),
    'show_page': App.show_page,
    'apply_theme': App.apply_theme,
}
_cuma_install_final_v8_patch()


# =============================================================================
# CUMA - PATCH V9: CORREÇÃO DEFINITIVA DA CAIXA DE IDIOMA
# =============================================================================
# Problema resolvido:
# - A caixa "Idioma" na aba Configurações > Temas e cores podia receber os valores
#   "Claro/Escuro" por causa de uma detecção por ordem dos Comboboxes.
# - A ordem de winfo_children() segue a ordem de criação, não necessariamente a ordem
#   visual após pack(before=...). Assim o combobox de idioma podia ser confundido
#   com o combobox de "Base do personalizado".
# Solução:
# - Cada combobox agora é identificado pelo textvariable/ponteiro direto, nunca por
#   posição na lista.
# - A caixa de idioma mantém sempre os nomes de idiomas nativos.
# - As caixas de modo visual/base continuam traduzíveis sem interferir no idioma.
# =============================================================================

_CUMA_TRANSLATION_COMBO_FIX_PATCH = 'v9_language_combobox_role_fix_2026_06_22'


def _cuma_v9_log(context: str, exc: Exception | None = None) -> None:
    try:
        if exc is None:
            write_log(f'[{_CUMA_TRANSLATION_COMBO_FIX_PATCH}] {context}')
        else:
            write_log(f'[{_CUMA_TRANSLATION_COMBO_FIX_PATCH}] {context}: {exc}')
            if 'write_error_log' in globals():
                write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_v9_var_name(var_or_name) -> str:
    try:
        return str(var_or_name)
    except Exception:
        return ''


def _cuma_v9_widget_text(widget) -> str:
    try:
        return str(widget.cget('text'))
    except Exception:
        return ''


def _cuma_v9_find_theme_tab(self):
    """Retorna a primeira aba interna de Configurações, onde ficam Temas e cores."""
    try:
        notebook = _cuma_v6_find_notebook(getattr(self, 'tab_config', None))
        if notebook is None:
            return None
        tabs = notebook.tabs()
        if not tabs:
            return None
        return notebook.nametowidget(tabs[0])
    except Exception:
        return None


def _cuma_v9_collect_children(root_widget):
    items = []
    queue_widgets = [root_widget] if root_widget is not None else []
    while queue_widgets:
        widget = queue_widgets.pop(0)
        items.append(widget)
        try:
            queue_widgets.extend(list(widget.winfo_children()))
        except Exception:
            pass
    return items


def _cuma_v9_is_language_section(widget) -> bool:
    try:
        if getattr(widget, '_cuma_language_section_v9', False):
            return True
    except Exception:
        pass
    txt = _cuma_v9_widget_text(widget)
    known_titles = {
        'Idioma do aplicativo', 'Application language', 'Idioma de la aplicación',
        "Langue de l'application", 'App-Sprache', 'Lingua dell’applicazione',
        'アプリの言語', '앱 언어', '애플리케이션 언어', '應用程式語言', 'Uygulama dili'
    }
    if txt in known_titles:
        return True
    # Detecção adicional: seção que contém um Combobox com exatamente os idiomas nativos.
    try:
        lang_values = set(V6_LANGUAGE_DISPLAY.values())
        for child in _cuma_v9_collect_children(widget):
            if isinstance(child, ttk.Combobox):
                values = set(str(v) for v in child.cget('values'))
                if lang_values and values == lang_values:
                    return True
    except Exception:
        pass
    return False


def _cuma_v9_remove_duplicate_language_sections(self):
    """Remove seções de idioma antigas/duplicadas de forma robusta antes de recriar."""
    try:
        victims = []
        for widget in _cuma_v9_collect_children(getattr(self, 'tab_config', None)):
            if isinstance(widget, ttk.LabelFrame) and _cuma_v9_is_language_section(widget):
                victims.append(widget)
        for widget in victims:
            try:
                widget.destroy()
            except Exception:
                pass
        self._language_section_v6_installed = False
        self._language_section_v9_installed = False
        self._cuma_language_section = None
        self._cuma_language_combo = None
    except Exception as exc:
        _cuma_v9_log('Falha ao remover seções duplicadas de idioma', exc)


def _cuma_v9_find_combobox_by_textvariable(root_widget, *variables):
    wanted = {_cuma_v9_var_name(v) for v in variables if v is not None}
    wanted.discard('')
    for widget in _cuma_v9_collect_children(root_widget):
        try:
            if isinstance(widget, ttk.Combobox):
                tv = str(widget.cget('textvariable'))
                if tv in wanted:
                    return widget
        except Exception:
            pass
    return None


def _cuma_v9_bind_language_combo(self, combo):
    """Configura exclusivamente a caixa de idioma."""
    try:
        if combo is None:
            return
        combo._cuma_combo_role = 'app_language'
        code = _cuma_v6_load_lang_code(self) if '_cuma_v6_load_lang_code' in globals() else 'system'
        if code not in V6_LANGUAGE_DISPLAY:
            code = 'system'
        if not hasattr(self, 'app_language_display'):
            self.app_language_display = tk.StringVar(value=V6_LANGUAGE_DISPLAY.get(code, 'Automático'))
        if not hasattr(self, 'app_language'):
            self.app_language = tk.StringVar(value=code)
        self.app_language.set(code)
        self.app_language_display.set(V6_LANGUAGE_DISPLAY.get(code, 'Automático'))
        combo.configure(
            textvariable=self.app_language_display,
            values=list(V6_LANGUAGE_DISPLAY.values()),
            state='readonly',
            width=26,
        )
        def on_lang_select(_event=None):
            selected = self.app_language_display.get()
            new_code = V6_DISPLAY_TO_CODE.get(selected, 'system')
            self.app_language.set(new_code)
            _cuma_v6_save_lang_code(new_code)
            self.app_language_display.set(V6_LANGUAGE_DISPLAY.get(new_code, 'Automático'))
            try:
                _cuma_v8_apply_language(self)
            except Exception:
                _cuma_v6_apply_language(self)
            # Reforço pós-tradução: o tradutor global nunca deve mexer nos valores do idioma.
            try:
                combo.configure(textvariable=self.app_language_display, values=list(V6_LANGUAGE_DISPLAY.values()))
            except Exception:
                pass
            # Atualiza também Modo visual/Base do personalizado no idioma recém-selecionado,
            # sem reutilizar a posição visual dos Comboboxes.
            try:
                tab_theme = _cuma_v9_find_theme_tab(self)
                _cuma_v9_bind_combo_translation(self, tab_theme, _cuma_v6_resolved_lang(self))
            except Exception as exc:
                _cuma_v9_log('Falha ao sincronizar combos após troca de idioma', exc)
        combo.bind('<<ComboboxSelected>>', on_lang_select)
        self._cuma_language_combo = combo
    except Exception as exc:
        _cuma_v9_log('Falha ao configurar combobox de idioma', exc)


def _cuma_v9_bind_visual_combo(self, combo, lang):
    """Configura exclusivamente a caixa Modo visual."""
    try:
        if combo is None:
            return
        combo._cuma_combo_role = 'theme_mode'
        _cuma_v6_setup_display_option_vars(self)
        self.theme_mode_display.set(_cuma_v6_option_display(self.theme_mode.get(), 'theme_mode', lang))
        combo.configure(
            textvariable=self.theme_mode_display,
            values=list(V6_OPTION_DISPLAY['theme_mode'].get(lang, V6_OPTION_DISPLAY['theme_mode']['en_US']).values()),
            state='readonly',
        )
        def on_mode_change(_event=None):
            raw = _cuma_v6_option_raw(self.theme_mode_display.get(), 'theme_mode', lang)
            self.theme_mode.set(raw)
            try:
                self._apply_theme_mode_selection(save=True)
            except Exception:
                self.save_current_config(force=True)
        combo.bind('<<ComboboxSelected>>', on_mode_change)
        self._v9_theme_mode_combo = combo
    except Exception as exc:
        _cuma_v9_log('Falha ao configurar combobox de modo visual', exc)


def _cuma_v9_bind_base_combo(self, combo, lang):
    """Configura exclusivamente a caixa Base do personalizado."""
    try:
        if combo is None:
            return
        combo._cuma_combo_role = 'custom_base_theme'
        _cuma_v6_setup_display_option_vars(self)
        self.custom_base_display.set(_cuma_v6_option_display(self.custom_base_theme.get(), 'custom_base_theme', lang))
        combo.configure(
            textvariable=self.custom_base_display,
            values=list(V6_OPTION_DISPLAY['custom_base_theme'].get(lang, V6_OPTION_DISPLAY['custom_base_theme']['en_US']).values()),
            state='readonly',
        )
        def on_base_change(_event=None):
            raw = _cuma_v6_option_raw(self.custom_base_display.get(), 'custom_base_theme', lang)
            self.custom_base_theme.set(raw)
            try:
                self._apply_theme_mode_selection(save=True)
            except Exception:
                self.save_current_config(force=True)
        combo.bind('<<ComboboxSelected>>', on_base_change)
        self._v9_custom_base_combo = combo
    except Exception as exc:
        _cuma_v9_log('Falha ao configurar combobox de base personalizada', exc)


def _cuma_v9_bind_combo_translation(self, tab_theme, lang):
    """Traduz/configura combos por função, não por ordem visual/criação."""
    try:
        if tab_theme is None:
            return
        # 1) Idioma: referência direta criada pela seção V9 ou fallback por variável.
        lang_combo = getattr(self, '_cuma_language_combo', None)
        if lang_combo is None or not getattr(lang_combo, 'winfo_exists', lambda: False)():
            lang_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'app_language_display', None), getattr(self, 'app_language', None))
        _cuma_v9_bind_language_combo(self, lang_combo)

        # 2) Modo visual e base: encontrar por textvariable real, sem encostar na caixa de idioma.
        mode_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'theme_mode', None), getattr(self, 'theme_mode_display', None))
        base_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'custom_base_theme', None), getattr(self, 'custom_base_display', None))

        if mode_combo is not None and mode_combo is not lang_combo:
            _cuma_v9_bind_visual_combo(self, mode_combo, lang)
        if base_combo is not None and base_combo is not lang_combo:
            _cuma_v9_bind_base_combo(self, base_combo, lang)

        # Revalidação defensiva: se por algum motivo o combo de idioma ficou com valores Claro/Escuro, restaura imediatamente.
        if lang_combo is not None:
            values = list(lang_combo.cget('values'))
            if values != list(V6_LANGUAGE_DISPLAY.values()):
                _cuma_v9_bind_language_combo(self, lang_combo)
    except Exception as exc:
        _cuma_v9_log('Falha ao vincular combos por função', exc)


def _cuma_v9_insert_language_section(self):
    if getattr(self, '_language_section_v9_installed', False):
        # Mesmo quando já existe, reforça os valores corretos.
        try:
            tab_theme = _cuma_v9_find_theme_tab(self)
            _cuma_v9_bind_combo_translation(self, tab_theme, _cuma_v6_resolved_lang(self))
        except Exception:
            pass
        return
    tab_theme = _cuma_v9_find_theme_tab(self)
    if tab_theme is None:
        return
    lang = _cuma_v6_resolved_lang(self)
    try:
        # Garante que nenhuma seção velha fique no caminho.
        existing = [w for w in _cuma_v9_collect_children(tab_theme) if isinstance(w, ttk.LabelFrame) and _cuma_v9_is_language_section(w)]
        for w in existing:
            try:
                w.destroy()
            except Exception:
                pass

        section = ttk.LabelFrame(tab_theme, text=_cuma_v8_tr('Idioma do aplicativo', lang) if '_cuma_v8_tr' in globals() else _cuma_v6_tr('Idioma do aplicativo', lang), padding=12, style='Card.TLabelframe')
        section._cuma_language_section_v9 = True
        children = list(tab_theme.winfo_children())
        if children:
            section.pack(fill='x', pady=(0, 12), before=children[0])
        else:
            section.pack(fill='x', pady=(0, 12))

        row = ttk.Frame(section, style='Card.TFrame')
        row.pack(fill='x')
        ttk.Label(row, text=_cuma_v8_tr('Idioma', lang) if '_cuma_v8_tr' in globals() else _cuma_v6_tr('Idioma', lang), style='TitleSmall.TLabel').pack(side='left')

        code = _cuma_v6_load_lang_code(self) if '_cuma_v6_load_lang_code' in globals() else 'system'
        if code not in V6_LANGUAGE_DISPLAY:
            code = 'system'
        if not hasattr(self, 'app_language'):
            self.app_language = tk.StringVar(value=code)
        if not hasattr(self, 'app_language_display'):
            self.app_language_display = tk.StringVar(value=V6_LANGUAGE_DISPLAY.get(code, 'Automático'))
        self.app_language.set(code)
        self.app_language_display.set(V6_LANGUAGE_DISPLAY.get(code, 'Automático'))

        combo = ttk.Combobox(row, textvariable=self.app_language_display, values=list(V6_LANGUAGE_DISPLAY.values()), state='readonly', width=26)
        combo.pack(side='left', padx=(12, 0))
        self._cuma_language_section = section
        self._cuma_language_combo = combo
        _cuma_v9_bind_language_combo(self, combo)

        help_label = ttk.Label(
            section,
            text=_cuma_v8_tr('Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.', lang) if '_cuma_v8_tr' in globals() else _cuma_v6_tr('Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.', lang),
            style='Muted.TLabel', wraplength=980, justify='left'
        )
        help_label.pack(anchor='w', pady=(8, 4))
        _cuma_v6_update_vars(self, lang)
        ttk.Label(section, textvariable=self.app_language_help, style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w')

        self._language_section_v6_installed = True
        self._language_section_v9_installed = True
        _cuma_v9_bind_combo_translation(self, tab_theme, lang)
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_v9_log('Falha ao inserir seção de idioma V9', exc)


def _cuma_v9_apply_language(self):
    """Aplica tradução e força a caixa Idioma a permanecer como lista de idiomas."""
    try:
        _cuma_v8_apply_language(self)
    except Exception:
        try:
            _cuma_v6_apply_language(self)
        except Exception:
            pass
    try:
        tab_theme = _cuma_v9_find_theme_tab(self)
        _cuma_v9_bind_combo_translation(self, tab_theme, _cuma_v6_resolved_lang(self))
    except Exception as exc:
        _cuma_v9_log('Falha ao reforçar combobox de idioma após tradução', exc)


# Substitui as funções globais usadas pelos wrappers V8. As chamadas já instaladas em App
# resolvem estes nomes em tempo de execução, então não é necessário reescrever a classe.
try:
    _cuma_v6_remove_duplicate_language_sections = _cuma_v9_remove_duplicate_language_sections
    _cuma_v6_bind_combo_translation = _cuma_v9_bind_combo_translation
    _cuma_v6_insert_language_section = _cuma_v9_insert_language_section
    globals()['_cuma_apply_language_to_widgets'] = _cuma_v9_apply_language
    globals()['_cuma_on_language_changed'] = _cuma_v9_apply_language
    # Instalação normal sem log em runtime; falhas continuam registradas.
except Exception as _cuma_v9_install_exc:
    _cuma_v9_log('Falha ao instalar patch V9 de idioma', _cuma_v9_install_exc)



# =============================================================================
# CUMA - PATCH V10: TRADUÇÃO GLOBAL E CANONICALIZAÇÃO COMPLETA DA INTERFACE
# =============================================================================
# Objetivo:
# - Evitar que idiomas como Japonês/Coreano/Chinês caiam para textos em inglês.
# - Guardar o texto original/canônico de cada widget e traduzir sempre a partir dele.
# - Traduzir Notebook, Treeview, LabelFrame, botões, labels, checkbuttons, radiobuttons
#   e variáveis auxiliares de status sem mexer nos valores internos salvos.
# - Manter a caixa Idioma isolada com nomes nativos e traduzir corretamente Modo visual/Base.
# =============================================================================

_CUMA_TRANSLATION_TOTAL_V10_PATCH = 'v10_full_ui_translation_2026_06_22'
V10_UI_I18N = {
  "pt_BR": {},
  "en_US": {
    "Configurações organizadas por categoria": "Settings organized by category",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Visual mode adjusted. Use Custom to freely edit colors or choose a system preset to get started faster.",
    "Temas e cores": "Themes and colors",
    "Qualidade e desempenho": "Quality and performance",
    "Hardware": "Hardware",
    "Facilidades": "Conveniences",
    "Segurança e logs": "Security and logs",
    "Idioma do aplicativo": "Application language",
    "Idioma": "Language",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Choose the application language. “Automatic” follows the system language when possible. Names are shown in each language’s native form.",
    "Idioma do sistema detectado": "Detected system language",
    "Selecionado": "Selected",
    "Quatro modos visuais": "Four visual modes",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "There are now four modes: Automatic, Light, Dark and Custom. Automatic tries to follow the system. Custom combines presets with fine color adjustment.",
    "Modo visual": "Visual mode",
    "Base do personalizado": "Custom base",
    "Cor principal do botão": "Main button color",
    "Personalizar cor": "Customize color",
    "Aplicar cor": "Apply color",
    "Cores padrão do sistema": "System default colors",
    "Ajuste avançado das cores": "Advanced color adjustment",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Choose whether the custom mode starts from a light or dark base.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automatic follows the system when possible. Light and Dark apply a direct mode. Custom unlocks full editing.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Part of the flow was simplified with quick presets. Start from Manga Dark, Modern Dark or Modern Light and refine later if you want.",
    "Preset Manga Dark": "Manga Dark preset",
    "Preset Escuro": "Dark preset",
    "Preset Claro": "Light preset",
    "Primário (botão/sucesso)": "Primary (button/success)",
    "Secundário": "Secondary",
    "Fundo": "Background",
    "Superfície": "Surface",
    "Painel secundário": "Secondary panel",
    "Barra lateral": "Sidebar",
    "Texto": "Text",
    "Borda": "Border",
    "Alerta": "Alert",
    "Amostra": "Sample",
    "Texto de amostra": "Sample text",
    "Aplicar ajustes avançados": "Apply advanced adjustments",
    "Restaurar tema escolhido": "Restore selected theme",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Tip: usually adjust only Primary, Secondary and Border. Background and surfaces only need changes when you want a truly different look.",
    "Limpar": "Clean",
    "Ferramentas": "Tools",
    "Converter": "Converter",
    "Resultados": "Results",
    "Registros": "Logs",
    "Configurações": "Settings",
    "Sobre": "About",
    "Prévia": "Preview",
    "Manual": "Manual",
    "Log": "Log",
    "Procurar atualizações": "Check for updates",
    "Tema claro": "Light theme",
    "Tema escuro": "Dark theme",
    "☀ Tema claro": "☀ Light theme",
    "🌙 Tema escuro": "🌙 Dark theme",
    "Fila principal": "Main queue",
    "Fila da aba Converter (EPUB / XTCH)": "Converter tab queue (EPUB / XTCH)",
    "Versão": "Version",
    "Atualizado em": "Updated on",
    "arquivo(s)": "file(s)",
    "item(ns)": "item(s)",
    "OK": "OK",
    "Erros": "Errors",
    "Arraste PDFs ou pastas aqui": "Drag PDFs or folders here",
    "Adicionar PDF(s)": "Add PDF(s)",
    "Adicionar arquivo(s)": "Add file(s)",
    "Adicionar pasta": "Add folder",
    "Colar caminho": "Paste path",
    "Remover": "Remove",
    "Limpar lista": "Clear list",
    "Incluir subpastas": "Include subfolders",
    "Configurações do PDF": "PDF settings",
    "Saída e organização": "Output and organization",
    "Pasta de saída": "Output folder",
    "Sufixo": "Suffix",
    "Formato de exportação": "Export format",
    "Intervalo de páginas": "Page range",
    "Abrir resultado ao concluir": "Open result when done",
    "Processar selecionados": "Process selected",
    "Processar tudo": "Process all",
    "Geral": "Overall",
    "PDF atual": "Current PDF",
    "Pronto": "Ready",
    "Pausado": "Paused",
    "Processando...": "Processing...",
    "Cancelar": "Cancel",
    "Pause": "Pause",
    "Play": "Play",
    "Escolher": "Choose",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "The most used main-flow items stay here: output folder, name/suffix, format, page range and open result.",
    "Extrair páginas dos PDFs selecionados como imagens": "Extract selected PDF pages as images",
    "Criar PDF a partir de várias imagens": "Create PDF from multiple images",
    "Carregar prévia do selecionado": "Load preview of selected",
    "Extrair páginas": "Extract pages",
    "Criar PDF de imagens": "Create PDF from images",
    "Criar PDF": "Create PDF",
    "Criar PDF dos selecionados": "Create PDF from selected",
    "Criar PDF de todos": "Create PDF from all",
    "Abrir pasta Ferramentas": "Open Tools folder",
    "Nome do PDF": "PDF name",
    "Abrir pasta ao concluir": "Open folder when done",
    "Arraste PDFs, EPUBs ou pastas aqui": "Drag PDFs, EPUBs or folders here",
    "PDF para EPUB": "PDF to EPUB",
    "PDF para XTCH": "PDF to XTCH",
    "EPUB para XTCH": "EPUB to XTCH",
    "Configurações do XTEINK": "XTEINK settings",
    "Dispositivos e conversões": "Devices and conversions",
    "Dispositivo": "Device",
    "Qualidade do arquivo (%)": "File quality (%)",
    "Aplicar perfil": "Apply profile",
    "Editor de perfis": "Profile editor",
    "Abrir pasta Converter": "Open Converter folder",
    "Processar todos": "Process all",
    "Arquivo atual": "Current file",
    "Total": "Total",
    "Converter pronto": "Converter ready",
    "XTEINK pronto": "XTEINK ready",
    "XTEINK concluído": "XTEINK completed",
    "XTEINK cancelado": "XTEINK canceled",
    "Funções por tipo de arquivo": "Functions by file type",
    "Aparência e interface": "Appearance and interface",
    "Salvar automaticamente alterações nas configurações": "Automatically save settings changes",
    "Mostrar dicas/tooltips": "Show tips/tooltips",
    "Confirmar antes de ações perigosas": "Confirm before dangerous actions",
    "Lembrar tamanho/posição da janela": "Remember window size/position",
    "Lembrar última aba aberta": "Remember last opened tab",
    "Densidade da interface": "Interface density",
    "Tamanho da fonte": "Font size",
    "Desempenho, CPU/GPU e cache": "Performance, CPU/GPU and cache",
    "Perfil de desempenho": "Performance profile",
    "Uso de CPU/GPU": "CPU/GPU usage",
    "Modo de hardware": "Hardware mode",
    "Threads de trabalho (0 = automático)": "Worker threads (0 = automatic)",
    "PDFs paralelos (0 = automático)": "Parallel PDFs (0 = automatic)",
    "Prioridade do processo": "Process priority",
    "Ativar cache de páginas": "Enable page cache",
    "Cache de páginas (MB)": "Page cache (MB)",
    "Economia de memória": "Memory saver",
    "Usar GPU somente se for mais rápida": "Use GPU only if faster",
    "Voltar para CPU se a GPU falhar": "Fall back to CPU if GPU fails",
    "Benchmark rápido": "Quick benchmark",
    "Copiar diagnóstico": "Copy diagnostics",
    "Ver status do hardware": "View hardware status",
    "Testar aceleração": "Test acceleration",
    "Aceleração": "Acceleration",
    "Diagnóstico": "Diagnostics",
    "Diagnóstico copiado.": "Diagnostics copied.",
    "Arquivos, segurança e automação": "Files, security and automation",
    "Criar backup dos originais": "Create backup of originals",
    "Sobrescrever arquivo original": "Overwrite original file",
    "Sobrescrever originais": "Overwrite originals",
    "Validar saída final": "Validate final output",
    "Salvar PDF com páginas removidas": "Save PDF with removed pages",
    "Senha PDF": "PDF password",
    "Detectar duplicidades": "Detect duplicates",
    "Pular arquivos já processados": "Skip already processed files",
    "Processar automaticamente ao adicionar": "Process automatically when adding",
    "Continuar de onde parou quando possível": "Resume where possible",
    "Modo silencioso": "Silent mode",
    "Lembrar última pasta utilizada": "Remember last used folder",
    "Limpar cache ao sair": "Clear cache on exit",
    "Salvar configurações": "Save settings",
    "Salvar configurações automaticamente": "Save settings automatically",
    "Logs e diagnóstico": "Logs and diagnostics",
    "Nível de log": "Log level",
    "Salvar log automaticamente": "Save log automatically",
    "Retenção de logs (dias)": "Log retention (days)",
    "Abrir log": "Open log",
    "Básico": "Basic",
    "Normal": "Normal",
    "Detalhado": "Detailed",
    "Debug": "Debug",
    "Prévia e visualização": "Preview and visualization",
    "Qualidade da prévia": "Preview quality",
    "Páginas por lote": "Pages per batch",
    "Largura miniatura": "Thumbnail width",
    "Largura das miniaturas": "Thumbnail width",
    "Usar cache de prévia": "Use preview cache",
    "Usar cache na prévia": "Use cache in preview",
    "Abrir prévia maximizada": "Open preview maximized",
    "Carregamento incremental": "Incremental loading",
    "Baixa": "Low",
    "Média": "Medium",
    "Alta": "High",
    "Pequena": "Small",
    "Grande": "Large",
    "Muito grande": "Very large",
    "Compacta": "Compact",
    "Espaçosa": "Spacious",
    "Econômico": "Economy",
    "Equilibrado": "Balanced",
    "Rápido": "Fast",
    "Máximo desempenho": "Maximum performance",
    "Sobre o CUMA": "About CUMA",
    "Resumo rápido do que cada aba faz:": "Quick summary of what each tab does:",
    "Abas do aplicativo": "Application tabs",
    "Abrir manual interativo": "Open interactive manual",
    "Abrir manual TXT completo": "Open full TXT manual",
    "Manual interativo do CUMA": "CUMA interactive manual",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Choose a section on the left to see a detailed explanation. Use the “Open full TXT” button if you want the separate system manual.",
    "Seções": "Sections",
    "Conteúdo": "Content",
    "Botões do topo": "Top buttons",
    "Perfis de dispositivo": "Device profiles",
    "FAQ rápido": "Quick FAQ",
    "Abrir manual completo": "Open full manual",
    "Fechar": "Close",
    "Limpar PDF": "Clean PDF",
    "Opções": "Options",
    "Compactação": "Compression",
    "Modo de detecção": "Detection mode",
    "Perfil de limpeza": "Cleaning profile",
    "Preservar qualidade máxima": "Preserve maximum quality",
    "Compactar moderadamente": "Moderate compression",
    "Compactar bastante": "High compression",
    "Original": "Original",
    "Sempre manter primeira página": "Always keep first page",
    "Manter últimas páginas": "Keep last pages",
    "Validar PDF final": "Validate final PDF",
    "Criar backup": "Create backup",
    "Detectar PDFs duplicados na lista": "Detect duplicate PDFs in the list",
    "Processar automaticamente ao adicionar arquivos": "Process automatically when adding files",
    "Lembrar última pasta aberta": "Remember last opened folder",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renders the PDF, adapts it to the device and creates an EPUB with image pages.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: generates native 2-bit grayscale XTCH directly from the PDF. It does not run xtcjs workers.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converts image-based EPUB to native XTCH.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "These options are saved per device. In Custom you can create a new name and resolution.",
    "Nome do dispositivo": "Device name",
    "Perfil carregado": "Loaded profile",
    "Salvar perfil": "Save profile",
    "Salvar no perfil atual": "Save to current profile",
    "Salvar como novo personalizado": "Save as new custom",
    "Salvar como nome": "Save as name",
    "Restaurar perfis padrão": "Restore default profiles"
  },
  "es_ES": {
    "Configurações organizadas por categoria": "Configuración organizada por categoría",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.",
    "Temas e cores": "Temas y colores",
    "Qualidade e desempenho": "Calidad y rendimiento",
    "Hardware": "Hardware",
    "Facilidades": "Facilidades",
    "Segurança e logs": "Seguridad y registros",
    "Idioma do aplicativo": "Idioma de la aplicación",
    "Idioma": "Idioma",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Elija el idioma de la aplicación. “Automático” sigue el idioma del sistema cuando sea posible. Los nombres se muestran en la forma nativa de cada idioma.",
    "Idioma do sistema detectado": "Idioma del sistema detectado",
    "Selecionado": "Seleccionado",
    "Quatro modos visuais": "Cuatro modos visuales",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "Ahora hay cuatro modos: Automático, Claro, Oscuro y Personalizado. Automático intenta seguir el sistema. Personalizado combina preajustes con ajuste fino de colores.",
    "Modo visual": "Modo visual",
    "Base do personalizado": "Base del personalizado",
    "Cor principal do botão": "Color principal del botón",
    "Personalizar cor": "Personalizar color",
    "Aplicar cor": "Aplicar color",
    "Cores padrão do sistema": "Colores predeterminados del sistema",
    "Ajuste avançado das cores": "Ajuste avanzado de colores",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Elija si el modo personalizado parte de una base clara u oscura.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automático sigue el sistema cuando es posible. Claro y Oscuro aplican modo directo. Personalizado libera la edición completa.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Parte del flujo se simplificó con preajustes rápidos. Empiece por Manga Dark, Moderno Oscuro o Moderno Claro y refine después si quiere.",
    "Preset Manga Dark": "Preajuste Manga Dark",
    "Preset Escuro": "Preajuste oscuro",
    "Preset Claro": "Preajuste claro",
    "Primário (botão/sucesso)": "Primario (botón/éxito)",
    "Secundário": "Secundario",
    "Fundo": "Fondo",
    "Superfície": "Superficie",
    "Painel secundário": "Panel secundario",
    "Barra lateral": "Barra lateral",
    "Texto": "Texto",
    "Borda": "Borde",
    "Alerta": "Alerta",
    "Aplicar ajustes avançados": "Aplicar ajustes avanzados",
    "Restaurar tema escolhido": "Restaurar tema elegido",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Consejo: normalmente ajuste solo Primario, Secundario y Borde. El fondo y las superficies solo necesitan cambios cuando quiera un aspecto realmente diferente.",
    "Limpar": "Limpiar",
    "Ferramentas": "Herramientas",
    "Converter": "Convertidor",
    "Resultados": "Resultados",
    "Registros": "Registros",
    "Configurações": "Configuración",
    "Sobre": "Acerca de",
    "Prévia": "Vista previa",
    "Manual": "Manual",
    "Log": "Registro",
    "Procurar atualizações": "Buscar actualizaciones",
    "Tema claro": "Tema claro",
    "Tema escuro": "Tema oscuro",
    "☀ Tema claro": "☀ Tema claro",
    "🌙 Tema escuro": "🌙 Tema oscuro",
    "Fila principal": "Cola principal",
    "Fila da aba Converter (EPUB / XTCH)": "Cola de la pestaña Convertidor (EPUB / XTCH)",
    "Versão": "Versión",
    "Atualizado em": "Actualizado el",
    "arquivo(s)": "archivo(s)",
    "item(ns)": "elemento(s)",
    "Erros": "Errores",
    "Arraste PDFs ou pastas aqui": "Arrastre PDFs o carpetas aquí",
    "Adicionar PDF(s)": "Agregar PDF(s)",
    "Adicionar arquivo(s)": "Agregar archivo(s)",
    "Adicionar pasta": "Agregar carpeta",
    "Colar caminho": "Pegar ruta",
    "Remover": "Eliminar",
    "Limpar lista": "Limpiar lista",
    "Incluir subpastas": "Incluir subcarpetas",
    "Configurações do PDF": "Configuración del PDF",
    "Saída e organização": "Salida y organización",
    "Pasta de saída": "Carpeta de salida",
    "Sufixo": "Sufijo",
    "Formato de exportação": "Formato de exportación",
    "Intervalo de páginas": "Rango de páginas",
    "Abrir resultado ao concluir": "Abrir resultado al finalizar",
    "Processar selecionados": "Procesar seleccionados",
    "Processar tudo": "Procesar todo",
    "Geral": "General",
    "PDF atual": "PDF actual",
    "Pronto": "Listo",
    "Pausado": "Pausado",
    "Processando...": "Procesando...",
    "Cancelar": "Cancelar",
    "Escolher": "Elegir",
    "Extrair páginas dos PDFs selecionados como imagens": "Extraer páginas de los PDF seleccionados como imágenes",
    "Criar PDF a partir de várias imagens": "Crear PDF a partir de varias imágenes",
    "Carregar prévia do selecionado": "Cargar vista previa del seleccionado",
    "Extrair páginas": "Extraer páginas",
    "Criar PDF de imagens": "Crear PDF de imágenes",
    "Criar PDF": "Crear PDF",
    "Abrir pasta Ferramentas": "Abrir carpeta Herramientas",
    "Nome do PDF": "Nombre del PDF",
    "Abrir pasta ao concluir": "Abrir carpeta al finalizar",
    "Arraste PDFs, EPUBs ou pastas aqui": "Arrastre PDFs, EPUBs o carpetas aquí",
    "PDF para EPUB": "PDF a EPUB",
    "PDF para XTCH": "PDF a XTCH",
    "EPUB para XTCH": "EPUB a XTCH",
    "Configurações do XTEINK": "Configuración de XTEINK",
    "Dispositivos e conversões": "Dispositivos y conversiones",
    "Dispositivo": "Dispositivo",
    "Qualidade do arquivo (%)": "Calidad del archivo (%)",
    "Aplicar perfil": "Aplicar perfil",
    "Editor de perfis": "Editor de perfiles",
    "Abrir pasta Converter": "Abrir carpeta del Convertidor",
    "Arquivo atual": "Archivo actual",
    "Total": "Total",
    "Converter pronto": "Convertidor listo",
    "XTEINK pronto": "XTEINK listo",
    "XTEINK concluído": "XTEINK concluido",
    "XTEINK cancelado": "XTEINK cancelado",
    "Aparência e interface": "Apariencia e interfaz",
    "Salvar automaticamente alterações nas configurações": "Guardar automáticamente cambios de configuración",
    "Mostrar dicas/tooltips": "Mostrar consejos/tooltips",
    "Confirmar antes de ações perigosas": "Confirmar antes de acciones peligrosas",
    "Lembrar tamanho/posição da janela": "Recordar tamaño/posición de la ventana",
    "Lembrar última aba aberta": "Recordar última pestaña abierta",
    "Densidade da interface": "Densidad de la interfaz",
    "Tamanho da fonte": "Tamaño de fuente",
    "Desempenho, CPU/GPU e cache": "Rendimiento, CPU/GPU y caché",
    "Perfil de desempenho": "Perfil de rendimiento",
    "Uso de CPU/GPU": "Uso de CPU/GPU",
    "Modo de hardware": "Modo de hardware",
    "Threads de trabalho (0 = automático)": "Hilos de trabajo (0 = automático)",
    "PDFs paralelos (0 = automático)": "PDF paralelos (0 = automático)",
    "Prioridade do processo": "Prioridad del proceso",
    "Ativar cache de páginas": "Activar caché de páginas",
    "Cache de páginas (MB)": "Caché de páginas (MB)",
    "Economia de memória": "Ahorro de memoria",
    "Usar GPU somente se for mais rápida": "Usar GPU solo si es más rápida",
    "Voltar para CPU se a GPU falhar": "Volver a CPU si falla la GPU",
    "Benchmark rápido": "Benchmark rápido",
    "Copiar diagnóstico": "Copiar diagnóstico",
    "Ver status do hardware": "Ver estado del hardware",
    "Testar aceleração": "Probar aceleración",
    "Aceleração": "Aceleración",
    "Diagnóstico": "Diagnóstico",
    "Diagnóstico copiado.": "Diagnóstico copiado.",
    "Arquivos, segurança e automação": "Archivos, seguridad y automatización",
    "Criar backup dos originais": "Crear copia de seguridad de originales",
    "Sobrescrever arquivo original": "Sobrescribir archivo original",
    "Validar saída final": "Validar salida final",
    "Salvar PDF com páginas removidas": "Guardar PDF con páginas eliminadas",
    "Senha PDF": "Contraseña PDF",
    "Detectar duplicidades": "Detectar duplicados",
    "Pular arquivos já processados": "Omitir archivos ya procesados",
    "Processar automaticamente ao adicionar": "Procesar automáticamente al agregar",
    "Continuar de onde parou quando possível": "Continuar desde donde se detuvo cuando sea posible",
    "Modo silencioso": "Modo silencioso",
    "Lembrar última pasta utilizada": "Recordar última carpeta usada",
    "Limpar cache ao sair": "Limpiar caché al salir",
    "Salvar configurações": "Guardar configuración",
    "Logs e diagnóstico": "Registros y diagnóstico",
    "Nível de log": "Nivel de registro",
    "Salvar log automaticamente": "Guardar registro automáticamente",
    "Retenção de logs (dias)": "Retención de registros (días)",
    "Abrir log": "Abrir registro",
    "Básico": "Básico",
    "Normal": "Normal",
    "Detalhado": "Detallado",
    "Debug": "Debug",
    "Prévia e visualização": "Vista previa y visualización",
    "Qualidade da prévia": "Calidad de vista previa",
    "Páginas por lote": "Páginas por lote",
    "Largura miniatura": "Ancho de miniatura",
    "Usar cache de prévia": "Usar caché de vista previa",
    "Abrir prévia maximizada": "Abrir vista previa maximizada",
    "Baixa": "Baja",
    "Média": "Media",
    "Alta": "Alta",
    "Pequena": "Pequeña",
    "Grande": "Grande",
    "Muito grande": "Muy grande",
    "Compacta": "Compacta",
    "Espaçosa": "Espaciosa",
    "Econômico": "Económico",
    "Equilibrado": "Equilibrado",
    "Rápido": "Rápido",
    "Máximo desempenho": "Máximo rendimiento",
    "Sobre o CUMA": "Acerca de CUMA",
    "Resumo rápido do que cada aba faz:": "Resumen rápido de cada pestaña:",
    "Abas do aplicativo": "Pestañas de la aplicación",
    "Abrir manual interativo": "Abrir manual interactivo",
    "Abrir manual TXT completo": "Abrir manual TXT completo",
    "Manual interativo do CUMA": "Manual interactivo de CUMA",
    "Seções": "Secciones",
    "Conteúdo": "Contenido",
    "Botões do topo": "Botones superiores",
    "Perfis de dispositivo": "Perfiles de dispositivo",
    "FAQ rápido": "FAQ rápido",
    "Abrir manual completo": "Abrir manual completo",
    "Fechar": "Cerrar",
    "Limpar PDF": "Limpiar PDF",
    "Opções": "Opciones",
    "Compactação": "Compresión",
    "Modo de detecção": "Modo de detección",
    "Perfil de limpeza": "Perfil de limpieza",
    "Preservar qualidade máxima": "Conservar calidad máxima",
    "Compactar moderadamente": "Comprimir moderadamente",
    "Compactar bastante": "Comprimir mucho",
    "Original": "Original",
    "Sempre manter primeira página": "Mantener siempre la primera página",
    "Manter últimas páginas": "Mantener últimas páginas",
    "Validar PDF final": "Validar PDF final",
    "Criar backup": "Crear copia de seguridad",
    "Processar automaticamente ao adicionar arquivos": "Procesar automáticamente al agregar archivos",
    "Lembrar última pasta aberta": "Recordar última carpeta abierta",
    "Amostra": "Amostra",
    "Texto de amostra": "Texto de amostra",
    "OK": "OK",
    "Pause": "Pause",
    "Play": "Play",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.",
    "Criar PDF dos selecionados": "Criar PDF dos selecionados",
    "Criar PDF de todos": "Criar PDF de todos",
    "Processar todos": "Processar todos",
    "Funções por tipo de arquivo": "Funções por tipo de arquivo",
    "Sobrescrever originais": "Sobrescrever originais",
    "Salvar configurações automaticamente": "Salvar configurações automaticamente",
    "Largura das miniaturas": "Largura das miniaturas",
    "Usar cache na prévia": "Usar cache na prévia",
    "Carregamento incremental": "Carregamento incremental",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.",
    "Detectar PDFs duplicados na lista": "Detectar PDFs duplicados na lista",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.",
    "Nome do dispositivo": "Nome do dispositivo",
    "Perfil carregado": "Perfil carregado",
    "Salvar perfil": "Salvar perfil",
    "Salvar no perfil atual": "Salvar no perfil atual",
    "Salvar como novo personalizado": "Salvar como novo personalizado",
    "Salvar como nome": "Salvar como nome",
    "Restaurar perfis padrão": "Restaurar perfis padrão"
  },
  "fr_FR": {
    "Configurações organizadas por categoria": "Paramètres organisés par catégorie",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.",
    "Temas e cores": "Thèmes et couleurs",
    "Qualidade e desempenho": "Qualité et performances",
    "Hardware": "Hardware",
    "Facilidades": "Fonctionnalités",
    "Segurança e logs": "Sécurité et journaux",
    "Idioma do aplicativo": "Langue de l’application",
    "Idioma": "Langue",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Elija el idioma de la aplicación. “Automático” sigue el idioma del sistema cuando sea posible. Los nombres se muestran en la forma nativa de cada idioma.",
    "Idioma do sistema detectado": "Langue système détectée",
    "Selecionado": "Sélectionné",
    "Quatro modos visuais": "Quatre modes visuels",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "Ahora hay cuatro modos: Automático, Claro, Oscuro y Personalizado. Automático intenta seguir el sistema. Personalizado combina preajustes con ajuste fino de colores.",
    "Modo visual": "Mode visuel",
    "Base do personalizado": "Base personnalisée",
    "Cor principal do botão": "Couleur principale du bouton",
    "Personalizar cor": "Personnaliser la couleur",
    "Aplicar cor": "Appliquer la couleur",
    "Cores padrão do sistema": "Couleurs par défaut du système",
    "Ajuste avançado das cores": "Réglage avancé des couleurs",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Elija si el modo personalizado parte de una base clara u oscura.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automático sigue el sistema cuando es posible. Claro y Oscuro aplican modo directo. Personalizado libera la edición completa.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Parte del flujo se simplificó con preajustes rápidos. Empiece por Manga Dark, Moderno Oscuro o Moderno Claro y refine después si quiere.",
    "Preset Manga Dark": "Preajuste Manga Dark",
    "Preset Escuro": "Preajuste oscuro",
    "Preset Claro": "Preajuste claro",
    "Primário (botão/sucesso)": "Primario (botón/éxito)",
    "Secundário": "Secundario",
    "Fundo": "Fondo",
    "Superfície": "Superficie",
    "Painel secundário": "Panel secundario",
    "Barra lateral": "Barra lateral",
    "Texto": "Texto",
    "Borda": "Borde",
    "Alerta": "Alerta",
    "Aplicar ajustes avançados": "Aplicar ajustes avanzados",
    "Restaurar tema escolhido": "Restaurar tema elegido",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Consejo: normalmente ajuste solo Primario, Secundario y Borde. El fondo y las superficies solo necesitan cambios cuando quiera un aspecto realmente diferente.",
    "Limpar": "Nettoyer",
    "Ferramentas": "Outils",
    "Converter": "Convertisseur",
    "Resultados": "Résultats",
    "Registros": "Journaux",
    "Configurações": "Paramètres",
    "Sobre": "À propos",
    "Prévia": "Aperçu",
    "Manual": "Manual",
    "Log": "Registro",
    "Procurar atualizações": "Rechercher des mises à jour",
    "Tema claro": "Tema claro",
    "Tema escuro": "Tema oscuro",
    "☀ Tema claro": "☀ Tema claro",
    "🌙 Tema escuro": "🌙 Tema oscuro",
    "Fila principal": "File principale",
    "Fila da aba Converter (EPUB / XTCH)": "File de l’onglet Convertisseur (EPUB / XTCH)",
    "Versão": "Version",
    "Atualizado em": "Mis à jour le",
    "arquivo(s)": "archivo(s)",
    "item(ns)": "elemento(s)",
    "Erros": "Erreurs",
    "Arraste PDFs ou pastas aqui": "Glissez des PDF ou dossiers ici",
    "Adicionar PDF(s)": "Ajouter PDF(s)",
    "Adicionar arquivo(s)": "Ajouter fichier(s)",
    "Adicionar pasta": "Ajouter un dossier",
    "Colar caminho": "Coller le chemin",
    "Remover": "Supprimer",
    "Limpar lista": "Vider la liste",
    "Incluir subpastas": "Inclure les sous-dossiers",
    "Configurações do PDF": "Paramètres PDF",
    "Saída e organização": "Sortie et organisation",
    "Pasta de saída": "Dossier de sortie",
    "Sufixo": "Suffixe",
    "Formato de exportação": "Format d’exportation",
    "Intervalo de páginas": "Plage de pages",
    "Abrir resultado ao concluir": "Ouvrir le résultat à la fin",
    "Processar selecionados": "Traiter la sélection",
    "Processar tudo": "Tout traiter",
    "Geral": "Général",
    "PDF atual": "PDF actuel",
    "Pronto": "Prêt",
    "Pausado": "En pause",
    "Processando...": "Traitement...",
    "Cancelar": "Annuler",
    "Escolher": "Choisir",
    "Extrair páginas dos PDFs selecionados como imagens": "Extraer páginas de los PDF seleccionados como imágenes",
    "Criar PDF a partir de várias imagens": "Crear PDF a partir de varias imágenes",
    "Carregar prévia do selecionado": "Cargar vista previa del seleccionado",
    "Extrair páginas": "Extraer páginas",
    "Criar PDF de imagens": "Crear PDF de imágenes",
    "Criar PDF": "Crear PDF",
    "Abrir pasta Ferramentas": "Abrir carpeta Herramientas",
    "Nome do PDF": "Nombre del PDF",
    "Abrir pasta ao concluir": "Abrir carpeta al finalizar",
    "Arraste PDFs, EPUBs ou pastas aqui": "Arrastre PDFs, EPUBs o carpetas aquí",
    "PDF para EPUB": "PDF a EPUB",
    "PDF para XTCH": "PDF a XTCH",
    "EPUB para XTCH": "EPUB a XTCH",
    "Configurações do XTEINK": "Configuración de XTEINK",
    "Dispositivos e conversões": "Appareils et conversions",
    "Dispositivo": "Appareil",
    "Qualidade do arquivo (%)": "Qualité du fichier (%)",
    "Aplicar perfil": "Appliquer le profil",
    "Editor de perfis": "Éditeur de profils",
    "Abrir pasta Converter": "Ouvrir le dossier Convertisseur",
    "Arquivo atual": "Fichier actuel",
    "Total": "Total",
    "Converter pronto": "Convertidor listo",
    "XTEINK pronto": "XTEINK listo",
    "XTEINK concluído": "XTEINK concluido",
    "XTEINK cancelado": "XTEINK cancelado",
    "Aparência e interface": "Apparence et interface",
    "Salvar automaticamente alterações nas configurações": "Guardar automáticamente cambios de configuración",
    "Mostrar dicas/tooltips": "Mostrar consejos/tooltips",
    "Confirmar antes de ações perigosas": "Confirmar antes de acciones peligrosas",
    "Lembrar tamanho/posição da janela": "Recordar tamaño/posición de la ventana",
    "Lembrar última aba aberta": "Recordar última pestaña abierta",
    "Densidade da interface": "Densidad de la interfaz",
    "Tamanho da fonte": "Tamaño de fuente",
    "Desempenho, CPU/GPU e cache": "Performances, CPU/GPU et cache",
    "Perfil de desempenho": "Perfil de rendimiento",
    "Uso de CPU/GPU": "Uso de CPU/GPU",
    "Modo de hardware": "Modo de hardware",
    "Threads de trabalho (0 = automático)": "Hilos de trabajo (0 = automático)",
    "PDFs paralelos (0 = automático)": "PDF paralelos (0 = automático)",
    "Prioridade do processo": "Prioridad del proceso",
    "Ativar cache de páginas": "Activar caché de páginas",
    "Cache de páginas (MB)": "Caché de páginas (MB)",
    "Economia de memória": "Ahorro de memoria",
    "Usar GPU somente se for mais rápida": "Usar GPU solo si es más rápida",
    "Voltar para CPU se a GPU falhar": "Volver a CPU si falla la GPU",
    "Benchmark rápido": "Benchmark rápido",
    "Copiar diagnóstico": "Copiar diagnóstico",
    "Ver status do hardware": "Ver estado del hardware",
    "Testar aceleração": "Probar aceleración",
    "Aceleração": "Aceleración",
    "Diagnóstico": "Diagnóstico",
    "Diagnóstico copiado.": "Diagnóstico copiado.",
    "Arquivos, segurança e automação": "Fichiers, sécurité et automatisation",
    "Criar backup dos originais": "Crear copia de seguridad de originales",
    "Sobrescrever arquivo original": "Sobrescribir archivo original",
    "Validar saída final": "Validar salida final",
    "Salvar PDF com páginas removidas": "Guardar PDF con páginas eliminadas",
    "Senha PDF": "Contraseña PDF",
    "Detectar duplicidades": "Detectar duplicados",
    "Pular arquivos já processados": "Omitir archivos ya procesados",
    "Processar automaticamente ao adicionar": "Procesar automáticamente al agregar",
    "Continuar de onde parou quando possível": "Continuar desde donde se detuvo cuando sea posible",
    "Modo silencioso": "Modo silencioso",
    "Lembrar última pasta utilizada": "Recordar última carpeta usada",
    "Limpar cache ao sair": "Limpiar caché al salir",
    "Salvar configurações": "Guardar configuración",
    "Logs e diagnóstico": "Journaux et diagnostic",
    "Nível de log": "Nivel de registro",
    "Salvar log automaticamente": "Guardar registro automáticamente",
    "Retenção de logs (dias)": "Retención de registros (días)",
    "Abrir log": "Abrir registro",
    "Básico": "Basique",
    "Normal": "Normal",
    "Detalhado": "Détaillé",
    "Debug": "Debug",
    "Prévia e visualização": "Aperçu et visualisation",
    "Qualidade da prévia": "Calidad de vista previa",
    "Páginas por lote": "Páginas por lote",
    "Largura miniatura": "Ancho de miniatura",
    "Usar cache de prévia": "Usar caché de vista previa",
    "Abrir prévia maximizada": "Abrir vista previa maximizada",
    "Baixa": "Basse",
    "Média": "Moyenne",
    "Alta": "Haute",
    "Pequena": "Petite",
    "Grande": "Grande",
    "Muito grande": "Très grande",
    "Compacta": "Compacte",
    "Espaçosa": "Spacieuse",
    "Econômico": "Économie",
    "Equilibrado": "Équilibré",
    "Rápido": "Rapide",
    "Máximo desempenho": "Performances maximales",
    "Sobre o CUMA": "Acerca de CUMA",
    "Resumo rápido do que cada aba faz:": "Resumen rápido de cada pestaña:",
    "Abas do aplicativo": "Pestañas de la aplicación",
    "Abrir manual interativo": "Abrir manual interactivo",
    "Abrir manual TXT completo": "Abrir manual TXT completo",
    "Manual interativo do CUMA": "Manual interactivo de CUMA",
    "Seções": "Secciones",
    "Conteúdo": "Contenido",
    "Botões do topo": "Botones superiores",
    "Perfis de dispositivo": "Perfiles de dispositivo",
    "FAQ rápido": "FAQ rápido",
    "Abrir manual completo": "Abrir manual completo",
    "Fechar": "Fermer",
    "Limpar PDF": "Limpiar PDF",
    "Opções": "Opciones",
    "Compactação": "Compresión",
    "Modo de detecção": "Modo de detección",
    "Perfil de limpeza": "Perfil de limpieza",
    "Preservar qualidade máxima": "Conservar calidad máxima",
    "Compactar moderadamente": "Comprimir moderadamente",
    "Compactar bastante": "Comprimir mucho",
    "Original": "Original",
    "Sempre manter primeira página": "Mantener siempre la primera página",
    "Manter últimas páginas": "Mantener últimas páginas",
    "Validar PDF final": "Validar PDF final",
    "Criar backup": "Crear copia de seguridad",
    "Processar automaticamente ao adicionar arquivos": "Procesar automáticamente al agregar archivos",
    "Lembrar última pasta aberta": "Recordar última carpeta abierta",
    "Amostra": "Amostra",
    "Texto de amostra": "Texto de amostra",
    "OK": "OK",
    "Pause": "Pause",
    "Play": "Play",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.",
    "Criar PDF dos selecionados": "Criar PDF dos selecionados",
    "Criar PDF de todos": "Criar PDF de todos",
    "Processar todos": "Processar todos",
    "Funções por tipo de arquivo": "Funções por tipo de arquivo",
    "Sobrescrever originais": "Sobrescrever originais",
    "Salvar configurações automaticamente": "Salvar configurações automaticamente",
    "Largura das miniaturas": "Largura das miniaturas",
    "Usar cache na prévia": "Usar cache na prévia",
    "Carregamento incremental": "Carregamento incremental",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.",
    "Detectar PDFs duplicados na lista": "Detectar PDFs duplicados na lista",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.",
    "Nome do dispositivo": "Nome do dispositivo",
    "Perfil carregado": "Perfil carregado",
    "Salvar perfil": "Salvar perfil",
    "Salvar no perfil atual": "Salvar no perfil atual",
    "Salvar como novo personalizado": "Salvar como novo personalizado",
    "Salvar como nome": "Salvar como nome",
    "Restaurar perfis padrão": "Restaurar perfis padrão"
  },
  "de_DE": {
    "Configurações organizadas por categoria": "Nach Kategorie organisierte Einstellungen",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.",
    "Temas e cores": "Themen und Farben",
    "Qualidade e desempenho": "Qualität und Leistung",
    "Hardware": "Hardware",
    "Facilidades": "Komfortfunktionen",
    "Segurança e logs": "Sicherheit und Protokolle",
    "Idioma do aplicativo": "App-Sprache",
    "Idioma": "Sprache",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Elija el idioma de la aplicación. “Automático” sigue el idioma del sistema cuando sea posible. Los nombres se muestran en la forma nativa de cada idioma.",
    "Idioma do sistema detectado": "Erkannte Systemsprache",
    "Selecionado": "Ausgewählt",
    "Quatro modos visuais": "Vier visuelle Modi",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "Ahora hay cuatro modos: Automático, Claro, Oscuro y Personalizado. Automático intenta seguir el sistema. Personalizado combina preajustes con ajuste fino de colores.",
    "Modo visual": "Visueller Modus",
    "Base do personalizado": "Benutzerdefinierte Basis",
    "Cor principal do botão": "Hauptfarbe der Schaltfläche",
    "Personalizar cor": "Farbe anpassen",
    "Aplicar cor": "Farbe anwenden",
    "Cores padrão do sistema": "Systemstandardfarben",
    "Ajuste avançado das cores": "Erweiterte Farbeinstellung",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Elija si el modo personalizado parte de una base clara u oscura.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automático sigue el sistema cuando es posible. Claro y Oscuro aplican modo directo. Personalizado libera la edición completa.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Parte del flujo se simplificó con preajustes rápidos. Empiece por Manga Dark, Moderno Oscuro o Moderno Claro y refine después si quiere.",
    "Preset Manga Dark": "Preajuste Manga Dark",
    "Preset Escuro": "Preajuste oscuro",
    "Preset Claro": "Preajuste claro",
    "Primário (botão/sucesso)": "Primario (botón/éxito)",
    "Secundário": "Secundario",
    "Fundo": "Fondo",
    "Superfície": "Superficie",
    "Painel secundário": "Panel secundario",
    "Barra lateral": "Barra lateral",
    "Texto": "Texto",
    "Borda": "Borde",
    "Alerta": "Alerta",
    "Aplicar ajustes avançados": "Aplicar ajustes avanzados",
    "Restaurar tema escolhido": "Restaurar tema elegido",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Consejo: normalmente ajuste solo Primario, Secundario y Borde. El fondo y las superficies solo necesitan cambios cuando quiera un aspecto realmente diferente.",
    "Limpar": "Bereinigen",
    "Ferramentas": "Werkzeuge",
    "Converter": "Konverter",
    "Resultados": "Ergebnisse",
    "Registros": "Protokolle",
    "Configurações": "Einstellungen",
    "Sobre": "Info",
    "Prévia": "Vorschau",
    "Manual": "Manual",
    "Log": "Registro",
    "Procurar atualizações": "Nach Updates suchen",
    "Tema claro": "Tema claro",
    "Tema escuro": "Tema oscuro",
    "☀ Tema claro": "☀ Tema claro",
    "🌙 Tema escuro": "🌙 Tema oscuro",
    "Fila principal": "Hauptwarteschlange",
    "Fila da aba Converter (EPUB / XTCH)": "Konverter-Warteschlange (EPUB / XTCH)",
    "Versão": "Version",
    "Atualizado em": "Aktualisiert am",
    "arquivo(s)": "archivo(s)",
    "item(ns)": "elemento(s)",
    "Erros": "Fehler",
    "Arraste PDFs ou pastas aqui": "PDFs oder Ordner hierher ziehen",
    "Adicionar PDF(s)": "PDF(s) hinzufügen",
    "Adicionar arquivo(s)": "Datei(en) hinzufügen",
    "Adicionar pasta": "Ordner hinzufügen",
    "Colar caminho": "Pfad einfügen",
    "Remover": "Entfernen",
    "Limpar lista": "Liste leeren",
    "Incluir subpastas": "Unterordner einschließen",
    "Configurações do PDF": "PDF-Einstellungen",
    "Saída e organização": "Ausgabe und Organisation",
    "Pasta de saída": "Ausgabeordner",
    "Sufixo": "Suffix",
    "Formato de exportação": "Exportformat",
    "Intervalo de páginas": "Seitenbereich",
    "Abrir resultado ao concluir": "Ergebnis nach Abschluss öffnen",
    "Processar selecionados": "Auswahl verarbeiten",
    "Processar tudo": "Alles verarbeiten",
    "Geral": "Allgemein",
    "PDF atual": "Aktuelle PDF",
    "Pronto": "Bereit",
    "Pausado": "Pausiert",
    "Processando...": "Verarbeitung...",
    "Cancelar": "Abbrechen",
    "Escolher": "Wählen",
    "Extrair páginas dos PDFs selecionados como imagens": "Extraer páginas de los PDF seleccionados como imágenes",
    "Criar PDF a partir de várias imagens": "Crear PDF a partir de varias imágenes",
    "Carregar prévia do selecionado": "Cargar vista previa del seleccionado",
    "Extrair páginas": "Extraer páginas",
    "Criar PDF de imagens": "Crear PDF de imágenes",
    "Criar PDF": "Crear PDF",
    "Abrir pasta Ferramentas": "Abrir carpeta Herramientas",
    "Nome do PDF": "Nombre del PDF",
    "Abrir pasta ao concluir": "Abrir carpeta al finalizar",
    "Arraste PDFs, EPUBs ou pastas aqui": "Arrastre PDFs, EPUBs o carpetas aquí",
    "PDF para EPUB": "PDF a EPUB",
    "PDF para XTCH": "PDF a XTCH",
    "EPUB para XTCH": "EPUB a XTCH",
    "Configurações do XTEINK": "Configuración de XTEINK",
    "Dispositivos e conversões": "Geräte und Konvertierungen",
    "Dispositivo": "Gerät",
    "Qualidade do arquivo (%)": "Dateiqualität (%)",
    "Aplicar perfil": "Profil anwenden",
    "Editor de perfis": "Profileditor",
    "Abrir pasta Converter": "Konverter-Ordner öffnen",
    "Arquivo atual": "Aktuelle Datei",
    "Total": "Total",
    "Converter pronto": "Convertidor listo",
    "XTEINK pronto": "XTEINK listo",
    "XTEINK concluído": "XTEINK concluido",
    "XTEINK cancelado": "XTEINK cancelado",
    "Aparência e interface": "Darstellung und Oberfläche",
    "Salvar automaticamente alterações nas configurações": "Guardar automáticamente cambios de configuración",
    "Mostrar dicas/tooltips": "Mostrar consejos/tooltips",
    "Confirmar antes de ações perigosas": "Confirmar antes de acciones peligrosas",
    "Lembrar tamanho/posição da janela": "Recordar tamaño/posición de la ventana",
    "Lembrar última aba aberta": "Recordar última pestaña abierta",
    "Densidade da interface": "Densidad de la interfaz",
    "Tamanho da fonte": "Tamaño de fuente",
    "Desempenho, CPU/GPU e cache": "Leistung, CPU/GPU und Cache",
    "Perfil de desempenho": "Perfil de rendimiento",
    "Uso de CPU/GPU": "Uso de CPU/GPU",
    "Modo de hardware": "Modo de hardware",
    "Threads de trabalho (0 = automático)": "Hilos de trabajo (0 = automático)",
    "PDFs paralelos (0 = automático)": "PDF paralelos (0 = automático)",
    "Prioridade do processo": "Prioridad del proceso",
    "Ativar cache de páginas": "Activar caché de páginas",
    "Cache de páginas (MB)": "Caché de páginas (MB)",
    "Economia de memória": "Ahorro de memoria",
    "Usar GPU somente se for mais rápida": "Usar GPU solo si es más rápida",
    "Voltar para CPU se a GPU falhar": "Volver a CPU si falla la GPU",
    "Benchmark rápido": "Benchmark rápido",
    "Copiar diagnóstico": "Copiar diagnóstico",
    "Ver status do hardware": "Ver estado del hardware",
    "Testar aceleração": "Probar aceleración",
    "Aceleração": "Aceleración",
    "Diagnóstico": "Diagnóstico",
    "Diagnóstico copiado.": "Diagnóstico copiado.",
    "Arquivos, segurança e automação": "Dateien, Sicherheit und Automatisierung",
    "Criar backup dos originais": "Crear copia de seguridad de originales",
    "Sobrescrever arquivo original": "Sobrescribir archivo original",
    "Validar saída final": "Validar salida final",
    "Salvar PDF com páginas removidas": "Guardar PDF con páginas eliminadas",
    "Senha PDF": "Contraseña PDF",
    "Detectar duplicidades": "Detectar duplicados",
    "Pular arquivos já processados": "Omitir archivos ya procesados",
    "Processar automaticamente ao adicionar": "Procesar automáticamente al agregar",
    "Continuar de onde parou quando possível": "Continuar desde donde se detuvo cuando sea posible",
    "Modo silencioso": "Modo silencioso",
    "Lembrar última pasta utilizada": "Recordar última carpeta usada",
    "Limpar cache ao sair": "Limpiar caché al salir",
    "Salvar configurações": "Guardar configuración",
    "Logs e diagnóstico": "Protokolle und Diagnose",
    "Nível de log": "Nivel de registro",
    "Salvar log automaticamente": "Guardar registro automáticamente",
    "Retenção de logs (dias)": "Retención de registros (días)",
    "Abrir log": "Abrir registro",
    "Básico": "Basique",
    "Normal": "Normal",
    "Detalhado": "Détaillé",
    "Debug": "Debug",
    "Prévia e visualização": "Vorschau und Anzeige",
    "Qualidade da prévia": "Calidad de vista previa",
    "Páginas por lote": "Páginas por lote",
    "Largura miniatura": "Ancho de miniatura",
    "Usar cache de prévia": "Usar caché de vista previa",
    "Abrir prévia maximizada": "Abrir vista previa maximizada",
    "Baixa": "Basse",
    "Média": "Moyenne",
    "Alta": "Haute",
    "Pequena": "Petite",
    "Grande": "Grande",
    "Muito grande": "Très grande",
    "Compacta": "Compacte",
    "Espaçosa": "Spacieuse",
    "Econômico": "Économie",
    "Equilibrado": "Équilibré",
    "Rápido": "Rapide",
    "Máximo desempenho": "Performances maximales",
    "Sobre o CUMA": "Acerca de CUMA",
    "Resumo rápido do que cada aba faz:": "Resumen rápido de cada pestaña:",
    "Abas do aplicativo": "Pestañas de la aplicación",
    "Abrir manual interativo": "Abrir manual interactivo",
    "Abrir manual TXT completo": "Abrir manual TXT completo",
    "Manual interativo do CUMA": "Manual interactivo de CUMA",
    "Seções": "Secciones",
    "Conteúdo": "Contenido",
    "Botões do topo": "Botones superiores",
    "Perfis de dispositivo": "Perfiles de dispositivo",
    "FAQ rápido": "FAQ rápido",
    "Abrir manual completo": "Abrir manual completo",
    "Fechar": "Schließen",
    "Limpar PDF": "Limpiar PDF",
    "Opções": "Opciones",
    "Compactação": "Compresión",
    "Modo de detecção": "Modo de detección",
    "Perfil de limpeza": "Perfil de limpieza",
    "Preservar qualidade máxima": "Conservar calidad máxima",
    "Compactar moderadamente": "Comprimir moderadamente",
    "Compactar bastante": "Comprimir mucho",
    "Original": "Original",
    "Sempre manter primeira página": "Mantener siempre la primera página",
    "Manter últimas páginas": "Mantener últimas páginas",
    "Validar PDF final": "Validar PDF final",
    "Criar backup": "Crear copia de seguridad",
    "Processar automaticamente ao adicionar arquivos": "Procesar automáticamente al agregar archivos",
    "Lembrar última pasta aberta": "Recordar última carpeta abierta",
    "Amostra": "Amostra",
    "Texto de amostra": "Texto de amostra",
    "OK": "OK",
    "Pause": "Pause",
    "Play": "Play",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.",
    "Criar PDF dos selecionados": "Criar PDF dos selecionados",
    "Criar PDF de todos": "Criar PDF de todos",
    "Processar todos": "Processar todos",
    "Funções por tipo de arquivo": "Funções por tipo de arquivo",
    "Sobrescrever originais": "Sobrescrever originais",
    "Salvar configurações automaticamente": "Salvar configurações automaticamente",
    "Largura das miniaturas": "Largura das miniaturas",
    "Usar cache na prévia": "Usar cache na prévia",
    "Carregamento incremental": "Carregamento incremental",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.",
    "Detectar PDFs duplicados na lista": "Detectar PDFs duplicados na lista",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.",
    "Nome do dispositivo": "Nome do dispositivo",
    "Perfil carregado": "Perfil carregado",
    "Salvar perfil": "Salvar perfil",
    "Salvar no perfil atual": "Salvar no perfil atual",
    "Salvar como novo personalizado": "Salvar como novo personalizado",
    "Salvar como nome": "Salvar como nome",
    "Restaurar perfis padrão": "Restaurar perfis padrão"
  },
  "it_IT": {
    "Configurações organizadas por categoria": "Impostazioni organizzate per categoria",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.",
    "Temas e cores": "Temi e colori",
    "Qualidade e desempenho": "Qualità e prestazioni",
    "Hardware": "Hardware",
    "Facilidades": "Funzioni pratiche",
    "Segurança e logs": "Sicurezza e log",
    "Idioma do aplicativo": "Lingua dell’applicazione",
    "Idioma": "Lingua",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Elija el idioma de la aplicación. “Automático” sigue el idioma del sistema cuando sea posible. Los nombres se muestran en la forma nativa de cada idioma.",
    "Idioma do sistema detectado": "Lingua di sistema rilevata",
    "Selecionado": "Selezionato",
    "Quatro modos visuais": "Quattro modalità visive",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "Ahora hay cuatro modos: Automático, Claro, Oscuro y Personalizado. Automático intenta seguir el sistema. Personalizado combina preajustes con ajuste fino de colores.",
    "Modo visual": "Modalità visiva",
    "Base do personalizado": "Base personalizzata",
    "Cor principal do botão": "Colore principale del pulsante",
    "Personalizar cor": "Personalizza colore",
    "Aplicar cor": "Applica colore",
    "Cores padrão do sistema": "Colori predefiniti del sistema",
    "Ajuste avançado das cores": "Regolazione avanzata dei colori",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Elija si el modo personalizado parte de una base clara u oscura.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automático sigue el sistema cuando es posible. Claro y Oscuro aplican modo directo. Personalizado libera la edición completa.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Parte del flujo se simplificó con preajustes rápidos. Empiece por Manga Dark, Moderno Oscuro o Moderno Claro y refine después si quiere.",
    "Preset Manga Dark": "Preajuste Manga Dark",
    "Preset Escuro": "Preajuste oscuro",
    "Preset Claro": "Preajuste claro",
    "Primário (botão/sucesso)": "Primario (botón/éxito)",
    "Secundário": "Secundario",
    "Fundo": "Fondo",
    "Superfície": "Superficie",
    "Painel secundário": "Panel secundario",
    "Barra lateral": "Barra lateral",
    "Texto": "Texto",
    "Borda": "Borde",
    "Alerta": "Alerta",
    "Aplicar ajustes avançados": "Aplicar ajustes avanzados",
    "Restaurar tema escolhido": "Restaurar tema elegido",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Consejo: normalmente ajuste solo Primario, Secundario y Borde. El fondo y las superficies solo necesitan cambios cuando quiera un aspecto realmente diferente.",
    "Limpar": "Pulisci",
    "Ferramentas": "Strumenti",
    "Converter": "Convertitore",
    "Resultados": "Risultati",
    "Registros": "Registri",
    "Configurações": "Impostazioni",
    "Sobre": "Informazioni",
    "Prévia": "Anteprima",
    "Manual": "Manual",
    "Log": "Registro",
    "Procurar atualizações": "Controlla aggiornamenti",
    "Tema claro": "Tema claro",
    "Tema escuro": "Tema oscuro",
    "☀ Tema claro": "☀ Tema claro",
    "🌙 Tema escuro": "🌙 Tema oscuro",
    "Fila principal": "Coda principale",
    "Fila da aba Converter (EPUB / XTCH)": "Coda della scheda Convertitore (EPUB / XTCH)",
    "Versão": "Versione",
    "Atualizado em": "Aggiornato il",
    "arquivo(s)": "archivo(s)",
    "item(ns)": "elemento(s)",
    "Erros": "Errori",
    "Arraste PDFs ou pastas aqui": "Trascina PDF o cartelle qui",
    "Adicionar PDF(s)": "Aggiungi PDF",
    "Adicionar arquivo(s)": "Aggiungi file",
    "Adicionar pasta": "Aggiungi cartella",
    "Colar caminho": "Incolla percorso",
    "Remover": "Rimuovi",
    "Limpar lista": "Svuota lista",
    "Incluir subpastas": "Includi sottocartelle",
    "Configurações do PDF": "Impostazioni PDF",
    "Saída e organização": "Output e organizzazione",
    "Pasta de saída": "Cartella di output",
    "Sufixo": "Suffisso",
    "Formato de exportação": "Formato di esportazione",
    "Intervalo de páginas": "Intervallo pagine",
    "Abrir resultado ao concluir": "Apri risultato al termine",
    "Processar selecionados": "Elabora selezionati",
    "Processar tudo": "Elabora tutto",
    "Geral": "Generale",
    "PDF atual": "PDF attuale",
    "Pronto": "Pronto",
    "Pausado": "In pausa",
    "Processando...": "Elaborazione...",
    "Cancelar": "Annulla",
    "Escolher": "Scegli",
    "Extrair páginas dos PDFs selecionados como imagens": "Extraer páginas de los PDF seleccionados como imágenes",
    "Criar PDF a partir de várias imagens": "Crear PDF a partir de varias imágenes",
    "Carregar prévia do selecionado": "Cargar vista previa del seleccionado",
    "Extrair páginas": "Extraer páginas",
    "Criar PDF de imagens": "Crear PDF de imágenes",
    "Criar PDF": "Crear PDF",
    "Abrir pasta Ferramentas": "Abrir carpeta Herramientas",
    "Nome do PDF": "Nombre del PDF",
    "Abrir pasta ao concluir": "Abrir carpeta al finalizar",
    "Arraste PDFs, EPUBs ou pastas aqui": "Arrastre PDFs, EPUBs o carpetas aquí",
    "PDF para EPUB": "PDF a EPUB",
    "PDF para XTCH": "PDF a XTCH",
    "EPUB para XTCH": "EPUB a XTCH",
    "Configurações do XTEINK": "Configuración de XTEINK",
    "Dispositivos e conversões": "Dispositivi e conversioni",
    "Dispositivo": "Dispositivo",
    "Qualidade do arquivo (%)": "Qualità file (%)",
    "Aplicar perfil": "Applica profilo",
    "Editor de perfis": "Editor profili",
    "Abrir pasta Converter": "Apri cartella Convertitore",
    "Arquivo atual": "File attuale",
    "Total": "Total",
    "Converter pronto": "Convertidor listo",
    "XTEINK pronto": "XTEINK listo",
    "XTEINK concluído": "XTEINK concluido",
    "XTEINK cancelado": "XTEINK cancelado",
    "Aparência e interface": "Aspetto e interfaccia",
    "Salvar automaticamente alterações nas configurações": "Guardar automáticamente cambios de configuración",
    "Mostrar dicas/tooltips": "Mostrar consejos/tooltips",
    "Confirmar antes de ações perigosas": "Confirmar antes de acciones peligrosas",
    "Lembrar tamanho/posição da janela": "Recordar tamaño/posición de la ventana",
    "Lembrar última aba aberta": "Recordar última pestaña abierta",
    "Densidade da interface": "Densidad de la interfaz",
    "Tamanho da fonte": "Tamaño de fuente",
    "Desempenho, CPU/GPU e cache": "Prestazioni, CPU/GPU e cache",
    "Perfil de desempenho": "Perfil de rendimiento",
    "Uso de CPU/GPU": "Uso de CPU/GPU",
    "Modo de hardware": "Modo de hardware",
    "Threads de trabalho (0 = automático)": "Hilos de trabajo (0 = automático)",
    "PDFs paralelos (0 = automático)": "PDF paralelos (0 = automático)",
    "Prioridade do processo": "Prioridad del proceso",
    "Ativar cache de páginas": "Activar caché de páginas",
    "Cache de páginas (MB)": "Caché de páginas (MB)",
    "Economia de memória": "Ahorro de memoria",
    "Usar GPU somente se for mais rápida": "Usar GPU solo si es más rápida",
    "Voltar para CPU se a GPU falhar": "Volver a CPU si falla la GPU",
    "Benchmark rápido": "Benchmark rápido",
    "Copiar diagnóstico": "Copiar diagnóstico",
    "Ver status do hardware": "Ver estado del hardware",
    "Testar aceleração": "Probar aceleración",
    "Aceleração": "Aceleración",
    "Diagnóstico": "Diagnóstico",
    "Diagnóstico copiado.": "Diagnóstico copiado.",
    "Arquivos, segurança e automação": "File, sicurezza e automazione",
    "Criar backup dos originais": "Crear copia de seguridad de originales",
    "Sobrescrever arquivo original": "Sobrescribir archivo original",
    "Validar saída final": "Validar salida final",
    "Salvar PDF com páginas removidas": "Guardar PDF con páginas eliminadas",
    "Senha PDF": "Contraseña PDF",
    "Detectar duplicidades": "Detectar duplicados",
    "Pular arquivos já processados": "Omitir archivos ya procesados",
    "Processar automaticamente ao adicionar": "Procesar automáticamente al agregar",
    "Continuar de onde parou quando possível": "Continuar desde donde se detuvo cuando sea posible",
    "Modo silencioso": "Modo silencioso",
    "Lembrar última pasta utilizada": "Recordar última carpeta usada",
    "Limpar cache ao sair": "Limpiar caché al salir",
    "Salvar configurações": "Guardar configuración",
    "Logs e diagnóstico": "Log e diagnostica",
    "Nível de log": "Nivel de registro",
    "Salvar log automaticamente": "Guardar registro automáticamente",
    "Retenção de logs (dias)": "Retención de registros (días)",
    "Abrir log": "Abrir registro",
    "Básico": "Basique",
    "Normal": "Normal",
    "Detalhado": "Détaillé",
    "Debug": "Debug",
    "Prévia e visualização": "Anteprima e visualizzazione",
    "Qualidade da prévia": "Calidad de vista previa",
    "Páginas por lote": "Páginas por lote",
    "Largura miniatura": "Ancho de miniatura",
    "Usar cache de prévia": "Usar caché de vista previa",
    "Abrir prévia maximizada": "Abrir vista previa maximizada",
    "Baixa": "Basse",
    "Média": "Moyenne",
    "Alta": "Haute",
    "Pequena": "Petite",
    "Grande": "Grande",
    "Muito grande": "Très grande",
    "Compacta": "Compacte",
    "Espaçosa": "Spacieuse",
    "Econômico": "Économie",
    "Equilibrado": "Équilibré",
    "Rápido": "Rapide",
    "Máximo desempenho": "Performances maximales",
    "Sobre o CUMA": "Acerca de CUMA",
    "Resumo rápido do que cada aba faz:": "Resumen rápido de cada pestaña:",
    "Abas do aplicativo": "Pestañas de la aplicación",
    "Abrir manual interativo": "Abrir manual interactivo",
    "Abrir manual TXT completo": "Abrir manual TXT completo",
    "Manual interativo do CUMA": "Manual interactivo de CUMA",
    "Seções": "Secciones",
    "Conteúdo": "Contenido",
    "Botões do topo": "Botones superiores",
    "Perfis de dispositivo": "Perfiles de dispositivo",
    "FAQ rápido": "FAQ rápido",
    "Abrir manual completo": "Abrir manual completo",
    "Fechar": "Chiudi",
    "Limpar PDF": "Limpiar PDF",
    "Opções": "Opciones",
    "Compactação": "Compresión",
    "Modo de detecção": "Modo de detección",
    "Perfil de limpeza": "Perfil de limpieza",
    "Preservar qualidade máxima": "Conservar calidad máxima",
    "Compactar moderadamente": "Comprimir moderadamente",
    "Compactar bastante": "Comprimir mucho",
    "Original": "Original",
    "Sempre manter primeira página": "Mantener siempre la primera página",
    "Manter últimas páginas": "Mantener últimas páginas",
    "Validar PDF final": "Validar PDF final",
    "Criar backup": "Crear copia de seguridad",
    "Processar automaticamente ao adicionar arquivos": "Procesar automáticamente al agregar archivos",
    "Lembrar última pasta aberta": "Recordar última carpeta abierta",
    "Amostra": "Amostra",
    "Texto de amostra": "Texto de amostra",
    "OK": "OK",
    "Pause": "Pause",
    "Play": "Play",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.",
    "Criar PDF dos selecionados": "Criar PDF dos selecionados",
    "Criar PDF de todos": "Criar PDF de todos",
    "Processar todos": "Processar todos",
    "Funções por tipo de arquivo": "Funções por tipo de arquivo",
    "Sobrescrever originais": "Sobrescrever originais",
    "Salvar configurações automaticamente": "Salvar configurações automaticamente",
    "Largura das miniaturas": "Largura das miniaturas",
    "Usar cache na prévia": "Usar cache na prévia",
    "Carregamento incremental": "Carregamento incremental",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.",
    "Detectar PDFs duplicados na lista": "Detectar PDFs duplicados na lista",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.",
    "Nome do dispositivo": "Nome do dispositivo",
    "Perfil carregado": "Perfil carregado",
    "Salvar perfil": "Salvar perfil",
    "Salvar no perfil atual": "Salvar no perfil atual",
    "Salvar como novo personalizado": "Salvar como novo personalizado",
    "Salvar como nome": "Salvar como nome",
    "Restaurar perfis padrão": "Restaurar perfis padrão"
  },
  "ja_JP": {
    "Configurações organizadas por categoria": "カテゴリ別に整理された設定",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "表示モードを調整しました。色を自由に編集するにはカスタムを使うか、すばやく始めるにはシステムプリセットを選択してください。",
    "Temas e cores": "テーマと色",
    "Qualidade e desempenho": "品質とパフォーマンス",
    "Hardware": "ハードウェア",
    "Facilidades": "便利機能",
    "Segurança e logs": "セキュリティとログ",
    "Idioma do aplicativo": "アプリの言語",
    "Idioma": "言語",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "アプリの言語を選択します。「自動」は可能な場合にシステム言語に従います。言語名は各言語のネイティブ表記で表示されます。",
    "Idioma do sistema detectado": "検出されたシステム言語",
    "Selecionado": "選択中",
    "Quatro modos visuais": "4つの表示モード",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "自動、ライト、ダーク、カスタムの4つのモードがあります。自動はシステムに従います。カスタムではプリセットと細かな色調整を組み合わせます。",
    "Modo visual": "表示モード",
    "Base do personalizado": "カスタムのベース",
    "Cor principal do botão": "ボタンのメイン色",
    "Personalizar cor": "色をカスタマイズ",
    "Aplicar cor": "色を適用",
    "Cores padrão do sistema": "システム標準色",
    "Ajuste avançado das cores": "高度な色調整",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "カスタムモードをライトまたはダークのどちらから始めるか選択します。",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "自動は可能な場合にシステムに従います。ライトとダークは直接適用します。カスタムは完全な編集を有効にします。",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "フローの一部はクイックプリセットで簡略化されています。Manga Dark、Moderno Escuro、Moderno Claro から始め、必要に応じて後で調整できます。",
    "Preset Manga Dark": "Manga Dark プリセット",
    "Preset Escuro": "ダークプリセット",
    "Preset Claro": "ライトプリセット",
    "Primário (botão/sucesso)": "プライマリ（ボタン/成功）",
    "Secundário": "セカンダリ",
    "Fundo": "背景",
    "Superfície": "サーフェス",
    "Painel secundário": "セカンダリパネル",
    "Barra lateral": "サイドバー",
    "Texto": "テキスト",
    "Borda": "枠線",
    "Alerta": "警告",
    "Amostra": "サンプル",
    "Texto de amostra": "サンプルテキスト",
    "Aplicar ajustes avançados": "詳細調整を適用",
    "Restaurar tema escolhido": "選択したテーマを復元",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "ヒント: 通常はプライマリ、セカンダリ、枠線だけを調整します。背景やサーフェスは見た目を大きく変えたい場合のみ変更します。",
    "Limpar": "クリーン",
    "Ferramentas": "ツール",
    "Converter": "変換",
    "Resultados": "結果",
    "Registros": "ログ",
    "Configurações": "設定",
    "Sobre": "情報",
    "Prévia": "プレビュー",
    "Manual": "マニュアル",
    "Log": "ログ",
    "Procurar atualizações": "更新を確認",
    "Tema claro": "ライトテーマ",
    "Tema escuro": "ダークテーマ",
    "☀ Tema claro": "☀ ライトテーマ",
    "🌙 Tema escuro": "🌙 ダークテーマ",
    "Fila principal": "メインキュー",
    "Fila da aba Converter (EPUB / XTCH)": "変換タブのキュー（EPUB / XTCH）",
    "Versão": "バージョン",
    "Atualizado em": "更新日",
    "arquivo(s)": "ファイル",
    "item(ns)": "項目",
    "OK": "OK",
    "Erros": "エラー",
    "Arraste PDFs ou pastas aqui": "PDFまたはフォルダーをここにドラッグ",
    "Adicionar PDF(s)": "PDFを追加",
    "Adicionar arquivo(s)": "ファイルを追加",
    "Adicionar pasta": "フォルダーを追加",
    "Colar caminho": "パスを貼り付け",
    "Remover": "削除",
    "Limpar lista": "リストをクリア",
    "Incluir subpastas": "サブフォルダーを含める",
    "Configurações do PDF": "PDF設定",
    "Saída e organização": "出力と整理",
    "Pasta de saída": "出力フォルダー",
    "Sufixo": "接尾辞",
    "Formato de exportação": "エクスポート形式",
    "Intervalo de páginas": "ページ範囲",
    "Abrir resultado ao concluir": "完了時に結果を開く",
    "Processar selecionados": "選択項目を処理",
    "Processar tudo": "すべて処理",
    "Geral": "全体",
    "PDF atual": "現在のPDF",
    "Pronto": "準備完了",
    "Pausado": "一時停止",
    "Processando...": "処理中...",
    "Cancelar": "キャンセル",
    "Pause": "Pause",
    "Play": "Play",
    "Escolher": "選択",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "The most used main-flow items stay here: output folder, name/suffix, format, page range and open result.",
    "Extrair páginas dos PDFs selecionados como imagens": "選択したPDFページを画像として抽出",
    "Criar PDF a partir de várias imagens": "複数の画像からPDFを作成",
    "Carregar prévia do selecionado": "選択項目のプレビューを読み込む",
    "Extrair páginas": "ページを抽出",
    "Criar PDF de imagens": "画像からPDFを作成",
    "Criar PDF": "PDFを作成",
    "Criar PDF dos selecionados": "Create PDF from selected",
    "Criar PDF de todos": "Create PDF from all",
    "Abrir pasta Ferramentas": "ツールフォルダーを開く",
    "Nome do PDF": "PDF名",
    "Abrir pasta ao concluir": "完了時にフォルダーを開く",
    "Arraste PDFs, EPUBs ou pastas aqui": "PDF、EPUB、フォルダーをここにドラッグ",
    "PDF para EPUB": "PDFからEPUB",
    "PDF para XTCH": "PDFからXTCH",
    "EPUB para XTCH": "EPUBからXTCH",
    "Configurações do XTEINK": "XTEINK設定",
    "Dispositivos e conversões": "デバイスと変換",
    "Dispositivo": "デバイス",
    "Qualidade do arquivo (%)": "ファイル品質 (%)",
    "Aplicar perfil": "プロファイルを適用",
    "Editor de perfis": "プロファイルエディター",
    "Abrir pasta Converter": "変換フォルダーを開く",
    "Processar todos": "Process all",
    "Arquivo atual": "現在のファイル",
    "Total": "合計",
    "Converter pronto": "変換準備完了",
    "XTEINK pronto": "XTEINK準備完了",
    "XTEINK concluído": "XTEINK完了",
    "XTEINK cancelado": "XTEINKキャンセル",
    "Funções por tipo de arquivo": "Functions by file type",
    "Aparência e interface": "外観とインターフェイス",
    "Salvar automaticamente alterações nas configurações": "設定変更を自動保存",
    "Mostrar dicas/tooltips": "ヒント/ツールチップを表示",
    "Confirmar antes de ações perigosas": "危険な操作の前に確認",
    "Lembrar tamanho/posição da janela": "ウィンドウのサイズ/位置を記憶",
    "Lembrar última aba aberta": "最後に開いたタブを記憶",
    "Densidade da interface": "インターフェイス密度",
    "Tamanho da fonte": "フォントサイズ",
    "Desempenho, CPU/GPU e cache": "パフォーマンス、CPU/GPU、キャッシュ",
    "Perfil de desempenho": "パフォーマンスプロファイル",
    "Uso de CPU/GPU": "CPU/GPU使用",
    "Modo de hardware": "ハードウェアモード",
    "Threads de trabalho (0 = automático)": "作業スレッド（0 = 自動）",
    "PDFs paralelos (0 = automático)": "並列PDF（0 = 自動）",
    "Prioridade do processo": "プロセス優先度",
    "Ativar cache de páginas": "ページキャッシュを有効化",
    "Cache de páginas (MB)": "ページキャッシュ (MB)",
    "Economia de memória": "メモリ節約",
    "Usar GPU somente se for mais rápida": "高速な場合のみGPUを使用",
    "Voltar para CPU se a GPU falhar": "GPU失敗時はCPUに戻す",
    "Benchmark rápido": "クイックベンチマーク",
    "Copiar diagnóstico": "診断をコピー",
    "Ver status do hardware": "ハードウェア状態を表示",
    "Testar aceleração": "アクセラレーションをテスト",
    "Aceleração": "アクセラレーション",
    "Diagnóstico": "診断",
    "Diagnóstico copiado.": "診断をコピーしました。",
    "Arquivos, segurança e automação": "ファイル、セキュリティ、自動化",
    "Criar backup dos originais": "元ファイルのバックアップを作成",
    "Sobrescrever arquivo original": "元ファイルを上書き",
    "Sobrescrever originais": "元ファイルを上書き",
    "Validar saída final": "最終出力を検証",
    "Salvar PDF com páginas removidas": "削除ページ付きPDFを保存",
    "Senha PDF": "PDFパスワード",
    "Detectar duplicidades": "重複を検出",
    "Pular arquivos já processados": "処理済みファイルをスキップ",
    "Processar automaticamente ao adicionar": "追加時に自動処理",
    "Continuar de onde parou quando possível": "可能な場合は中断地点から再開",
    "Modo silencioso": "サイレントモード",
    "Lembrar última pasta utilizada": "最後に使用したフォルダーを記憶",
    "Limpar cache ao sair": "終了時にキャッシュを消去",
    "Salvar configurações": "設定を保存",
    "Salvar configurações automaticamente": "Save settings automatically",
    "Logs e diagnóstico": "ログと診断",
    "Nível de log": "ログレベル",
    "Salvar log automaticamente": "ログを自動保存",
    "Retenção de logs (dias)": "ログ保持日数",
    "Abrir log": "ログを開く",
    "Básico": "基本",
    "Normal": "通常",
    "Detalhado": "詳細",
    "Debug": "デバッグ",
    "Prévia e visualização": "プレビューと表示",
    "Qualidade da prévia": "プレビュー品質",
    "Páginas por lote": "バッチあたりのページ数",
    "Largura miniatura": "サムネイル幅",
    "Largura das miniaturas": "Thumbnail width",
    "Usar cache de prévia": "プレビューキャッシュを使用",
    "Usar cache na prévia": "Use cache in preview",
    "Abrir prévia maximizada": "最大化してプレビューを開く",
    "Carregamento incremental": "Incremental loading",
    "Baixa": "低",
    "Média": "中",
    "Alta": "高",
    "Pequena": "小",
    "Grande": "大",
    "Muito grande": "非常に大きい",
    "Compacta": "コンパクト",
    "Espaçosa": "広め",
    "Econômico": "省電力",
    "Equilibrado": "バランス",
    "Rápido": "高速",
    "Máximo desempenho": "最大パフォーマンス",
    "Sobre o CUMA": "CUMAについて",
    "Resumo rápido do que cada aba faz:": "各タブの概要:",
    "Abas do aplicativo": "アプリのタブ",
    "Abrir manual interativo": "インタラクティブマニュアルを開く",
    "Abrir manual TXT completo": "完全なTXTマニュアルを開く",
    "Manual interativo do CUMA": "CUMAインタラクティブマニュアル",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Choose a section on the left to see a detailed explanation. Use the “Open full TXT” button if you want the separate system manual.",
    "Seções": "セクション",
    "Conteúdo": "内容",
    "Botões do topo": "上部ボタン",
    "Perfis de dispositivo": "デバイスプロファイル",
    "FAQ rápido": "簡易FAQ",
    "Abrir manual completo": "完全なマニュアルを開く",
    "Fechar": "閉じる",
    "Limpar PDF": "PDFをクリーン",
    "Opções": "オプション",
    "Compactação": "圧縮",
    "Modo de detecção": "検出モード",
    "Perfil de limpeza": "クリーニングプロファイル",
    "Preservar qualidade máxima": "最高品質を保持",
    "Compactar moderadamente": "中程度に圧縮",
    "Compactar bastante": "強く圧縮",
    "Original": "元のまま",
    "Sempre manter primeira página": "常に最初のページを保持",
    "Manter últimas páginas": "最後のページを保持",
    "Validar PDF final": "最終PDFを検証",
    "Criar backup": "バックアップを作成",
    "Detectar PDFs duplicados na lista": "Detect duplicate PDFs in the list",
    "Processar automaticamente ao adicionar arquivos": "ファイル追加時に自動処理",
    "Lembrar última pasta aberta": "最後に開いたフォルダーを記憶",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renders the PDF, adapts it to the device and creates an EPUB with image pages.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: generates native 2-bit grayscale XTCH directly from the PDF. It does not run xtcjs workers.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converts image-based EPUB to native XTCH.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "These options are saved per device. In Custom you can create a new name and resolution.",
    "Nome do dispositivo": "Device name",
    "Perfil carregado": "Loaded profile",
    "Salvar perfil": "Save profile",
    "Salvar no perfil atual": "Save to current profile",
    "Salvar como novo personalizado": "Save as new custom",
    "Salvar como nome": "Save as name",
    "Restaurar perfis padrão": "Restore default profiles"
  },
  "ko_KR": {
    "Configurações organizadas por categoria": "범주별로 정리된 설정",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "表示モードを調整しました。色を自由に編集するにはカスタムを使うか、すばやく始めるにはシステムプリセットを選択してください。",
    "Temas e cores": "테마 및 색상",
    "Qualidade e desempenho": "품질 및 성능",
    "Hardware": "하드웨어",
    "Facilidades": "편의 기능",
    "Segurança e logs": "보안 및 로그",
    "Idioma do aplicativo": "애플리케이션 언어",
    "Idioma": "언어",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "アプリの言語を選択します。「自動」は可能な場合にシステム言語に従います。言語名は各言語のネイティブ表記で表示されます。",
    "Idioma do sistema detectado": "감지된 시스템 언어",
    "Selecionado": "선택됨",
    "Quatro modos visuais": "네 가지 시각 모드",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "自動、ライト、ダーク、カスタムの4つのモードがあります。自動はシステムに従います。カスタムではプリセットと細かな色調整を組み合わせます。",
    "Modo visual": "시각 모드",
    "Base do personalizado": "사용자 지정 기준",
    "Cor principal do botão": "버튼 기본 색상",
    "Personalizar cor": "색상 사용자 지정",
    "Aplicar cor": "색상 적용",
    "Cores padrão do sistema": "시스템 기본 색상",
    "Ajuste avançado das cores": "고급 색상 조정",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "カスタムモードをライトまたはダークのどちらから始めるか選択します。",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "自動は可能な場合にシステムに従います。ライトとダークは直接適用します。カスタムは完全な編集を有効にします。",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "フローの一部はクイックプリセットで簡略化されています。Manga Dark、Moderno Escuro、Moderno Claro から始め、必要に応じて後で調整できます。",
    "Preset Manga Dark": "Manga Dark プリセット",
    "Preset Escuro": "ダークプリセット",
    "Preset Claro": "ライトプリセット",
    "Primário (botão/sucesso)": "プライマリ（ボタン/成功）",
    "Secundário": "セカンダリ",
    "Fundo": "背景",
    "Superfície": "サーフェス",
    "Painel secundário": "セカンダリパネル",
    "Barra lateral": "サイドバー",
    "Texto": "テキスト",
    "Borda": "枠線",
    "Alerta": "警告",
    "Amostra": "サンプル",
    "Texto de amostra": "サンプルテキスト",
    "Aplicar ajustes avançados": "詳細調整を適用",
    "Restaurar tema escolhido": "選択したテーマを復元",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "ヒント: 通常はプライマリ、セカンダリ、枠線だけを調整します。背景やサーフェスは見た目を大きく変えたい場合のみ変更します。",
    "Limpar": "정리",
    "Ferramentas": "도구",
    "Converter": "변환기",
    "Resultados": "결과",
    "Registros": "기록",
    "Configurações": "설정",
    "Sobre": "정보",
    "Prévia": "미리보기",
    "Manual": "설명서",
    "Log": "로그",
    "Procurar atualizações": "업데이트 확인",
    "Tema claro": "ライトテーマ",
    "Tema escuro": "ダークテーマ",
    "☀ Tema claro": "☀ ライトテーマ",
    "🌙 Tema escuro": "🌙 ダークテーマ",
    "Fila principal": "메인 대기열",
    "Fila da aba Converter (EPUB / XTCH)": "변환기 탭 대기열 (EPUB / XTCH)",
    "Versão": "버전",
    "Atualizado em": "업데이트 날짜",
    "arquivo(s)": "ファイル",
    "item(ns)": "項目",
    "OK": "OK",
    "Erros": "오류",
    "Arraste PDFs ou pastas aqui": "PDF 또는 폴더를 여기에 끌어다 놓으세요",
    "Adicionar PDF(s)": "PDF 추가",
    "Adicionar arquivo(s)": "파일 추가",
    "Adicionar pasta": "폴더 추가",
    "Colar caminho": "경로 붙여넣기",
    "Remover": "제거",
    "Limpar lista": "목록 지우기",
    "Incluir subpastas": "하위 폴더 포함",
    "Configurações do PDF": "PDF設定",
    "Saída e organização": "出力と整理",
    "Pasta de saída": "출력 폴더",
    "Sufixo": "接尾辞",
    "Formato de exportação": "エクスポート形式",
    "Intervalo de páginas": "ページ範囲",
    "Abrir resultado ao concluir": "完了時に結果を開く",
    "Processar selecionados": "選択項目を処理",
    "Processar tudo": "すべて処理",
    "Geral": "全体",
    "PDF atual": "現在のPDF",
    "Pronto": "준비됨",
    "Pausado": "一時停止",
    "Processando...": "処理中...",
    "Cancelar": "취소",
    "Pause": "Pause",
    "Play": "Play",
    "Escolher": "선택",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "The most used main-flow items stay here: output folder, name/suffix, format, page range and open result.",
    "Extrair páginas dos PDFs selecionados como imagens": "選択したPDFページを画像として抽出",
    "Criar PDF a partir de várias imagens": "複数の画像からPDFを作成",
    "Carregar prévia do selecionado": "選択項目のプレビューを読み込む",
    "Extrair páginas": "ページを抽出",
    "Criar PDF de imagens": "画像からPDFを作成",
    "Criar PDF": "PDFを作成",
    "Criar PDF dos selecionados": "Create PDF from selected",
    "Criar PDF de todos": "Create PDF from all",
    "Abrir pasta Ferramentas": "ツールフォルダーを開く",
    "Nome do PDF": "PDF名",
    "Abrir pasta ao concluir": "完了時にフォルダーを開く",
    "Arraste PDFs, EPUBs ou pastas aqui": "PDF、EPUB、フォルダーをここにドラッグ",
    "PDF para EPUB": "PDFからEPUB",
    "PDF para XTCH": "PDFからXTCH",
    "EPUB para XTCH": "EPUBからXTCH",
    "Configurações do XTEINK": "XTEINK設定",
    "Dispositivos e conversões": "デバイスと変換",
    "Dispositivo": "장치",
    "Qualidade do arquivo (%)": "ファイル品質 (%)",
    "Aplicar perfil": "프로필 적용",
    "Editor de perfis": "프로필 편집기",
    "Abrir pasta Converter": "변환기 폴더 열기",
    "Processar todos": "Process all",
    "Arquivo atual": "현재 파일",
    "Total": "合計",
    "Converter pronto": "変換準備完了",
    "XTEINK pronto": "XTEINK準備完了",
    "XTEINK concluído": "XTEINK完了",
    "XTEINK cancelado": "XTEINKキャンセル",
    "Funções por tipo de arquivo": "Functions by file type",
    "Aparência e interface": "外観とインターフェイス",
    "Salvar automaticamente alterações nas configurações": "設定変更を自動保存",
    "Mostrar dicas/tooltips": "ヒント/ツールチップを表示",
    "Confirmar antes de ações perigosas": "危険な操作の前に確認",
    "Lembrar tamanho/posição da janela": "ウィンドウのサイズ/位置を記憶",
    "Lembrar última aba aberta": "最後に開いたタブを記憶",
    "Densidade da interface": "インターフェイス密度",
    "Tamanho da fonte": "フォントサイズ",
    "Desempenho, CPU/GPU e cache": "パフォーマンス、CPU/GPU、キャッシュ",
    "Perfil de desempenho": "パフォーマンスプロファイル",
    "Uso de CPU/GPU": "CPU/GPU使用",
    "Modo de hardware": "ハードウェアモード",
    "Threads de trabalho (0 = automático)": "作業スレッド（0 = 自動）",
    "PDFs paralelos (0 = automático)": "並列PDF（0 = 自動）",
    "Prioridade do processo": "プロセス優先度",
    "Ativar cache de páginas": "ページキャッシュを有効化",
    "Cache de páginas (MB)": "ページキャッシュ (MB)",
    "Economia de memória": "メモリ節約",
    "Usar GPU somente se for mais rápida": "高速な場合のみGPUを使用",
    "Voltar para CPU se a GPU falhar": "GPU失敗時はCPUに戻す",
    "Benchmark rápido": "クイックベンチマーク",
    "Copiar diagnóstico": "診断をコピー",
    "Ver status do hardware": "ハードウェア状態を表示",
    "Testar aceleração": "アクセラレーションをテスト",
    "Aceleração": "アクセラレーション",
    "Diagnóstico": "診断",
    "Diagnóstico copiado.": "診断をコピーしました。",
    "Arquivos, segurança e automação": "ファイル、セキュリティ、自動化",
    "Criar backup dos originais": "元ファイルのバックアップを作成",
    "Sobrescrever arquivo original": "元ファイルを上書き",
    "Sobrescrever originais": "元ファイルを上書き",
    "Validar saída final": "最終出力を検証",
    "Salvar PDF com páginas removidas": "削除ページ付きPDFを保存",
    "Senha PDF": "PDFパスワード",
    "Detectar duplicidades": "重複を検出",
    "Pular arquivos já processados": "処理済みファイルをスキップ",
    "Processar automaticamente ao adicionar": "追加時に自動処理",
    "Continuar de onde parou quando possível": "可能な場合は中断地点から再開",
    "Modo silencioso": "サイレントモード",
    "Lembrar última pasta utilizada": "最後に使用したフォルダーを記憶",
    "Limpar cache ao sair": "終了時にキャッシュを消去",
    "Salvar configurações": "設定を保存",
    "Salvar configurações automaticamente": "Save settings automatically",
    "Logs e diagnóstico": "ログと診断",
    "Nível de log": "ログレベル",
    "Salvar log automaticamente": "ログを自動保存",
    "Retenção de logs (dias)": "ログ保持日数",
    "Abrir log": "ログを開く",
    "Básico": "基本",
    "Normal": "通常",
    "Detalhado": "詳細",
    "Debug": "デバッグ",
    "Prévia e visualização": "プレビューと表示",
    "Qualidade da prévia": "プレビュー品質",
    "Páginas por lote": "バッチあたりのページ数",
    "Largura miniatura": "サムネイル幅",
    "Largura das miniaturas": "Thumbnail width",
    "Usar cache de prévia": "プレビューキャッシュを使用",
    "Usar cache na prévia": "Use cache in preview",
    "Abrir prévia maximizada": "最大化してプレビューを開く",
    "Carregamento incremental": "Incremental loading",
    "Baixa": "低",
    "Média": "中",
    "Alta": "高",
    "Pequena": "小",
    "Grande": "大",
    "Muito grande": "非常に大きい",
    "Compacta": "コンパクト",
    "Espaçosa": "広め",
    "Econômico": "省電力",
    "Equilibrado": "バランス",
    "Rápido": "高速",
    "Máximo desempenho": "最大パフォーマンス",
    "Sobre o CUMA": "CUMAについて",
    "Resumo rápido do que cada aba faz:": "各タブの概要:",
    "Abas do aplicativo": "アプリのタブ",
    "Abrir manual interativo": "インタラクティブマニュアルを開く",
    "Abrir manual TXT completo": "完全なTXTマニュアルを開く",
    "Manual interativo do CUMA": "CUMAインタラクティブマニュアル",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Choose a section on the left to see a detailed explanation. Use the “Open full TXT” button if you want the separate system manual.",
    "Seções": "セクション",
    "Conteúdo": "内容",
    "Botões do topo": "上部ボタン",
    "Perfis de dispositivo": "デバイスプロファイル",
    "FAQ rápido": "簡易FAQ",
    "Abrir manual completo": "完全なマニュアルを開く",
    "Fechar": "닫기",
    "Limpar PDF": "PDFをクリーン",
    "Opções": "オプション",
    "Compactação": "圧縮",
    "Modo de detecção": "検出モード",
    "Perfil de limpeza": "クリーニングプロファイル",
    "Preservar qualidade máxima": "最高品質を保持",
    "Compactar moderadamente": "中程度に圧縮",
    "Compactar bastante": "強く圧縮",
    "Original": "元のまま",
    "Sempre manter primeira página": "常に最初のページを保持",
    "Manter últimas páginas": "最後のページを保持",
    "Validar PDF final": "最終PDFを検証",
    "Criar backup": "バックアップを作成",
    "Detectar PDFs duplicados na lista": "Detect duplicate PDFs in the list",
    "Processar automaticamente ao adicionar arquivos": "ファイル追加時に自動処理",
    "Lembrar última pasta aberta": "最後に開いたフォルダーを記憶",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renders the PDF, adapts it to the device and creates an EPUB with image pages.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: generates native 2-bit grayscale XTCH directly from the PDF. It does not run xtcjs workers.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converts image-based EPUB to native XTCH.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "These options are saved per device. In Custom you can create a new name and resolution.",
    "Nome do dispositivo": "Device name",
    "Perfil carregado": "Loaded profile",
    "Salvar perfil": "Save profile",
    "Salvar no perfil atual": "Save to current profile",
    "Salvar como novo personalizado": "Save as new custom",
    "Salvar como nome": "Save as name",
    "Restaurar perfis padrão": "Restore default profiles"
  },
  "zh_TW": {
    "Configurações organizadas por categoria": "依類別整理的設定",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "表示モードを調整しました。色を自由に編集するにはカスタムを使うか、すばやく始めるにはシステムプリセットを選択してください。",
    "Temas e cores": "主題與色彩",
    "Qualidade e desempenho": "品質與效能",
    "Hardware": "硬體",
    "Facilidades": "便利功能",
    "Segurança e logs": "安全與記錄",
    "Idioma do aplicativo": "應用程式語言",
    "Idioma": "語言",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "アプリの言語を選択します。「自動」は可能な場合にシステム言語に従います。言語名は各言語のネイティブ表記で表示されます。",
    "Idioma do sistema detectado": "偵測到的系統語言",
    "Selecionado": "已選取",
    "Quatro modos visuais": "四種視覺模式",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "自動、ライト、ダーク、カスタムの4つのモードがあります。自動はシステムに従います。カスタムではプリセットと細かな色調整を組み合わせます。",
    "Modo visual": "視覺模式",
    "Base do personalizado": "自訂基底",
    "Cor principal do botão": "按鈕主色",
    "Personalizar cor": "自訂色彩",
    "Aplicar cor": "套用色彩",
    "Cores padrão do sistema": "系統預設色彩",
    "Ajuste avançado das cores": "進階色彩調整",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "カスタムモードをライトまたはダークのどちらから始めるか選択します。",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "自動は可能な場合にシステムに従います。ライトとダークは直接適用します。カスタムは完全な編集を有効にします。",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "フローの一部はクイックプリセットで簡略化されています。Manga Dark、Moderno Escuro、Moderno Claro から始め、必要に応じて後で調整できます。",
    "Preset Manga Dark": "Manga Dark プリセット",
    "Preset Escuro": "ダークプリセット",
    "Preset Claro": "ライトプリセット",
    "Primário (botão/sucesso)": "プライマリ（ボタン/成功）",
    "Secundário": "セカンダリ",
    "Fundo": "背景",
    "Superfície": "サーフェス",
    "Painel secundário": "セカンダリパネル",
    "Barra lateral": "サイドバー",
    "Texto": "テキスト",
    "Borda": "枠線",
    "Alerta": "警告",
    "Amostra": "サンプル",
    "Texto de amostra": "サンプルテキスト",
    "Aplicar ajustes avançados": "詳細調整を適用",
    "Restaurar tema escolhido": "選択したテーマを復元",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "ヒント: 通常はプライマリ、セカンダリ、枠線だけを調整します。背景やサーフェスは見た目を大きく変えたい場合のみ変更します。",
    "Limpar": "清理",
    "Ferramentas": "工具",
    "Converter": "轉換器",
    "Resultados": "結果",
    "Registros": "記錄",
    "Configurações": "設定",
    "Sobre": "關於",
    "Prévia": "預覽",
    "Manual": "手冊",
    "Log": "記錄",
    "Procurar atualizações": "檢查更新",
    "Tema claro": "ライトテーマ",
    "Tema escuro": "ダークテーマ",
    "☀ Tema claro": "☀ ライトテーマ",
    "🌙 Tema escuro": "🌙 ダークテーマ",
    "Fila principal": "主要佇列",
    "Fila da aba Converter (EPUB / XTCH)": "轉換器分頁佇列 (EPUB / XTCH)",
    "Versão": "版本",
    "Atualizado em": "更新於",
    "arquivo(s)": "ファイル",
    "item(ns)": "項目",
    "OK": "OK",
    "Erros": "錯誤",
    "Arraste PDFs ou pastas aqui": "將 PDF 或資料夾拖曳到這裡",
    "Adicionar PDF(s)": "新增 PDF",
    "Adicionar arquivo(s)": "新增檔案",
    "Adicionar pasta": "新增資料夾",
    "Colar caminho": "貼上路徑",
    "Remover": "移除",
    "Limpar lista": "清除清單",
    "Incluir subpastas": "包含子資料夾",
    "Configurações do PDF": "PDF設定",
    "Saída e organização": "出力と整理",
    "Pasta de saída": "輸出資料夾",
    "Sufixo": "接尾辞",
    "Formato de exportação": "エクスポート形式",
    "Intervalo de páginas": "ページ範囲",
    "Abrir resultado ao concluir": "完了時に結果を開く",
    "Processar selecionados": "選択項目を処理",
    "Processar tudo": "すべて処理",
    "Geral": "全体",
    "PDF atual": "現在のPDF",
    "Pronto": "就緒",
    "Pausado": "一時停止",
    "Processando...": "処理中...",
    "Cancelar": "取消",
    "Pause": "Pause",
    "Play": "Play",
    "Escolher": "選擇",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "The most used main-flow items stay here: output folder, name/suffix, format, page range and open result.",
    "Extrair páginas dos PDFs selecionados como imagens": "選択したPDFページを画像として抽出",
    "Criar PDF a partir de várias imagens": "複数の画像からPDFを作成",
    "Carregar prévia do selecionado": "選択項目のプレビューを読み込む",
    "Extrair páginas": "ページを抽出",
    "Criar PDF de imagens": "画像からPDFを作成",
    "Criar PDF": "PDFを作成",
    "Criar PDF dos selecionados": "Create PDF from selected",
    "Criar PDF de todos": "Create PDF from all",
    "Abrir pasta Ferramentas": "ツールフォルダーを開く",
    "Nome do PDF": "PDF名",
    "Abrir pasta ao concluir": "完了時にフォルダーを開く",
    "Arraste PDFs, EPUBs ou pastas aqui": "PDF、EPUB、フォルダーをここにドラッグ",
    "PDF para EPUB": "PDFからEPUB",
    "PDF para XTCH": "PDFからXTCH",
    "EPUB para XTCH": "EPUBからXTCH",
    "Configurações do XTEINK": "XTEINK設定",
    "Dispositivos e conversões": "デバイスと変換",
    "Dispositivo": "裝置",
    "Qualidade do arquivo (%)": "ファイル品質 (%)",
    "Aplicar perfil": "套用設定檔",
    "Editor de perfis": "設定檔編輯器",
    "Abrir pasta Converter": "開啟轉換器資料夾",
    "Processar todos": "Process all",
    "Arquivo atual": "目前檔案",
    "Total": "合計",
    "Converter pronto": "変換準備完了",
    "XTEINK pronto": "XTEINK準備完了",
    "XTEINK concluído": "XTEINK完了",
    "XTEINK cancelado": "XTEINKキャンセル",
    "Funções por tipo de arquivo": "Functions by file type",
    "Aparência e interface": "外観とインターフェイス",
    "Salvar automaticamente alterações nas configurações": "設定変更を自動保存",
    "Mostrar dicas/tooltips": "ヒント/ツールチップを表示",
    "Confirmar antes de ações perigosas": "危険な操作の前に確認",
    "Lembrar tamanho/posição da janela": "ウィンドウのサイズ/位置を記憶",
    "Lembrar última aba aberta": "最後に開いたタブを記憶",
    "Densidade da interface": "インターフェイス密度",
    "Tamanho da fonte": "フォントサイズ",
    "Desempenho, CPU/GPU e cache": "パフォーマンス、CPU/GPU、キャッシュ",
    "Perfil de desempenho": "パフォーマンスプロファイル",
    "Uso de CPU/GPU": "CPU/GPU使用",
    "Modo de hardware": "ハードウェアモード",
    "Threads de trabalho (0 = automático)": "作業スレッド（0 = 自動）",
    "PDFs paralelos (0 = automático)": "並列PDF（0 = 自動）",
    "Prioridade do processo": "プロセス優先度",
    "Ativar cache de páginas": "ページキャッシュを有効化",
    "Cache de páginas (MB)": "ページキャッシュ (MB)",
    "Economia de memória": "メモリ節約",
    "Usar GPU somente se for mais rápida": "高速な場合のみGPUを使用",
    "Voltar para CPU se a GPU falhar": "GPU失敗時はCPUに戻す",
    "Benchmark rápido": "クイックベンチマーク",
    "Copiar diagnóstico": "診断をコピー",
    "Ver status do hardware": "ハードウェア状態を表示",
    "Testar aceleração": "アクセラレーションをテスト",
    "Aceleração": "アクセラレーション",
    "Diagnóstico": "診断",
    "Diagnóstico copiado.": "診断をコピーしました。",
    "Arquivos, segurança e automação": "ファイル、セキュリティ、自動化",
    "Criar backup dos originais": "元ファイルのバックアップを作成",
    "Sobrescrever arquivo original": "元ファイルを上書き",
    "Sobrescrever originais": "元ファイルを上書き",
    "Validar saída final": "最終出力を検証",
    "Salvar PDF com páginas removidas": "削除ページ付きPDFを保存",
    "Senha PDF": "PDFパスワード",
    "Detectar duplicidades": "重複を検出",
    "Pular arquivos já processados": "処理済みファイルをスキップ",
    "Processar automaticamente ao adicionar": "追加時に自動処理",
    "Continuar de onde parou quando possível": "可能な場合は中断地点から再開",
    "Modo silencioso": "サイレントモード",
    "Lembrar última pasta utilizada": "最後に使用したフォルダーを記憶",
    "Limpar cache ao sair": "終了時にキャッシュを消去",
    "Salvar configurações": "設定を保存",
    "Salvar configurações automaticamente": "Save settings automatically",
    "Logs e diagnóstico": "ログと診断",
    "Nível de log": "ログレベル",
    "Salvar log automaticamente": "ログを自動保存",
    "Retenção de logs (dias)": "ログ保持日数",
    "Abrir log": "ログを開く",
    "Básico": "基本",
    "Normal": "通常",
    "Detalhado": "詳細",
    "Debug": "デバッグ",
    "Prévia e visualização": "プレビューと表示",
    "Qualidade da prévia": "プレビュー品質",
    "Páginas por lote": "バッチあたりのページ数",
    "Largura miniatura": "サムネイル幅",
    "Largura das miniaturas": "Thumbnail width",
    "Usar cache de prévia": "プレビューキャッシュを使用",
    "Usar cache na prévia": "Use cache in preview",
    "Abrir prévia maximizada": "最大化してプレビューを開く",
    "Carregamento incremental": "Incremental loading",
    "Baixa": "低",
    "Média": "中",
    "Alta": "高",
    "Pequena": "小",
    "Grande": "大",
    "Muito grande": "非常に大きい",
    "Compacta": "コンパクト",
    "Espaçosa": "広め",
    "Econômico": "省電力",
    "Equilibrado": "バランス",
    "Rápido": "高速",
    "Máximo desempenho": "最大パフォーマンス",
    "Sobre o CUMA": "CUMAについて",
    "Resumo rápido do que cada aba faz:": "各タブの概要:",
    "Abas do aplicativo": "アプリのタブ",
    "Abrir manual interativo": "インタラクティブマニュアルを開く",
    "Abrir manual TXT completo": "完全なTXTマニュアルを開く",
    "Manual interativo do CUMA": "CUMAインタラクティブマニュアル",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Choose a section on the left to see a detailed explanation. Use the “Open full TXT” button if you want the separate system manual.",
    "Seções": "セクション",
    "Conteúdo": "内容",
    "Botões do topo": "上部ボタン",
    "Perfis de dispositivo": "デバイスプロファイル",
    "FAQ rápido": "簡易FAQ",
    "Abrir manual completo": "完全なマニュアルを開く",
    "Fechar": "關閉",
    "Limpar PDF": "PDFをクリーン",
    "Opções": "オプション",
    "Compactação": "圧縮",
    "Modo de detecção": "検出モード",
    "Perfil de limpeza": "クリーニングプロファイル",
    "Preservar qualidade máxima": "最高品質を保持",
    "Compactar moderadamente": "中程度に圧縮",
    "Compactar bastante": "強く圧縮",
    "Original": "元のまま",
    "Sempre manter primeira página": "常に最初のページを保持",
    "Manter últimas páginas": "最後のページを保持",
    "Validar PDF final": "最終PDFを検証",
    "Criar backup": "バックアップを作成",
    "Detectar PDFs duplicados na lista": "Detect duplicate PDFs in the list",
    "Processar automaticamente ao adicionar arquivos": "ファイル追加時に自動処理",
    "Lembrar última pasta aberta": "最後に開いたフォルダーを記憶",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renders the PDF, adapts it to the device and creates an EPUB with image pages.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: generates native 2-bit grayscale XTCH directly from the PDF. It does not run xtcjs workers.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converts image-based EPUB to native XTCH.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "These options are saved per device. In Custom you can create a new name and resolution.",
    "Nome do dispositivo": "Device name",
    "Perfil carregado": "Loaded profile",
    "Salvar perfil": "Save profile",
    "Salvar no perfil atual": "Save to current profile",
    "Salvar como novo personalizado": "Save as new custom",
    "Salvar como nome": "Save as name",
    "Restaurar perfis padrão": "Restore default profiles"
  },
  "tr_TR": {
    "Configurações organizadas por categoria": "Kategoriye göre düzenlenmiş ayarlar",
    "Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.": "Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.",
    "Temas e cores": "Temalar ve renkler",
    "Qualidade e desempenho": "Kalite ve performans",
    "Hardware": "Hardware",
    "Facilidades": "Kolaylıklar",
    "Segurança e logs": "Güvenlik ve günlükler",
    "Idioma do aplicativo": "Uygulama dili",
    "Idioma": "Dil",
    "Escolha o idioma do aplicativo. “Automático” segue o idioma do sistema quando possível. Os nomes são exibidos na forma nativa de cada idioma.": "Elija el idioma de la aplicación. “Automático” sigue el idioma del sistema cuando sea posible. Los nombres se muestran en la forma nativa de cada idioma.",
    "Idioma do sistema detectado": "Algılanan sistem dili",
    "Selecionado": "Seçili",
    "Quatro modos visuais": "Dört görsel mod",
    "Agora existem quatro modos: Automático, Claro, Escuro e Personalizado. O modo Automático tenta seguir o sistema. O Personalizado combina presets com ajuste fino das cores.": "Ahora hay cuatro modos: Automático, Claro, Oscuro y Personalizado. Automático intenta seguir el sistema. Personalizado combina preajustes con ajuste fino de colores.",
    "Modo visual": "Görsel mod",
    "Base do personalizado": "Özel temel",
    "Cor principal do botão": "Ana düğme rengi",
    "Personalizar cor": "Rengi özelleştir",
    "Aplicar cor": "Rengi uygula",
    "Cores padrão do sistema": "Sistem varsayılan renkleri",
    "Ajuste avançado das cores": "Gelişmiş renk ayarı",
    "Escolha se o modo personalizado parte de uma base clara ou escura.": "Elija si el modo personalizado parte de una base clara u oscura.",
    "Automático segue o sistema quando possível. Claro e Escuro aplicam modo direto. Personalizado libera edição completa.": "Automático sigue el sistema cuando es posible. Claro y Oscuro aplican modo directo. Personalizado libera la edición completa.",
    "Parte do fluxo foi simplificada com presets rápidos. Parta de Manga Dark, Moderno Escuro ou Moderno Claro e refine depois, se quiser.": "Parte del flujo se simplificó con preajustes rápidos. Empiece por Manga Dark, Moderno Oscuro o Moderno Claro y refine después si quiere.",
    "Preset Manga Dark": "Preajuste Manga Dark",
    "Preset Escuro": "Preajuste oscuro",
    "Preset Claro": "Preajuste claro",
    "Primário (botão/sucesso)": "Primario (botón/éxito)",
    "Secundário": "Secundario",
    "Fundo": "Fondo",
    "Superfície": "Superficie",
    "Painel secundário": "Panel secundario",
    "Barra lateral": "Barra lateral",
    "Texto": "Texto",
    "Borda": "Borde",
    "Alerta": "Alerta",
    "Aplicar ajustes avançados": "Aplicar ajustes avanzados",
    "Restaurar tema escolhido": "Restaurar tema elegido",
    "Dica: ajuste normalmente só Primário, Secundário e Borda. Fundo e superfícies só precisam ser alterados quando quiser um visual realmente diferente.": "Consejo: normalmente ajuste solo Primario, Secundario y Borde. El fondo y las superficies solo necesitan cambios cuando quiera un aspecto realmente diferente.",
    "Limpar": "Temizle",
    "Ferramentas": "Araçlar",
    "Converter": "Dönüştürücü",
    "Resultados": "Sonuçlar",
    "Registros": "Kayıtlar",
    "Configurações": "Ayarlar",
    "Sobre": "Hakkında",
    "Prévia": "Önizleme",
    "Manual": "Kılavuz",
    "Log": "Günlük",
    "Procurar atualizações": "Güncellemeleri denetle",
    "Tema claro": "Tema claro",
    "Tema escuro": "Tema oscuro",
    "☀ Tema claro": "☀ Tema claro",
    "🌙 Tema escuro": "🌙 Tema oscuro",
    "Fila principal": "Ana kuyruk",
    "Fila da aba Converter (EPUB / XTCH)": "Dönüştürücü sekmesi kuyruğu (EPUB / XTCH)",
    "Versão": "Sürüm",
    "Atualizado em": "Güncellendi",
    "arquivo(s)": "archivo(s)",
    "item(ns)": "elemento(s)",
    "Erros": "Hatalar",
    "Arraste PDFs ou pastas aqui": "PDF veya klasörleri buraya sürükleyin",
    "Adicionar PDF(s)": "PDF ekle",
    "Adicionar arquivo(s)": "Dosya ekle",
    "Adicionar pasta": "Klasör ekle",
    "Colar caminho": "Yolu yapıştır",
    "Remover": "Kaldır",
    "Limpar lista": "Listeyi temizle",
    "Incluir subpastas": "Alt klasörleri dahil et",
    "Configurações do PDF": "Configuración del PDF",
    "Saída e organização": "Salida y organización",
    "Pasta de saída": "Çıktı klasörü",
    "Sufixo": "Sufijo",
    "Formato de exportação": "Formato de exportación",
    "Intervalo de páginas": "Rango de páginas",
    "Abrir resultado ao concluir": "Abrir resultado al finalizar",
    "Processar selecionados": "Procesar seleccionados",
    "Processar tudo": "Procesar todo",
    "Geral": "General",
    "PDF atual": "PDF actual",
    "Pronto": "Hazır",
    "Pausado": "Pausado",
    "Processando...": "Procesando...",
    "Cancelar": "İptal",
    "Escolher": "Seç",
    "Extrair páginas dos PDFs selecionados como imagens": "Extraer páginas de los PDF seleccionados como imágenes",
    "Criar PDF a partir de várias imagens": "Crear PDF a partir de varias imágenes",
    "Carregar prévia do selecionado": "Cargar vista previa del seleccionado",
    "Extrair páginas": "Extraer páginas",
    "Criar PDF de imagens": "Crear PDF de imágenes",
    "Criar PDF": "Crear PDF",
    "Abrir pasta Ferramentas": "Abrir carpeta Herramientas",
    "Nome do PDF": "Nombre del PDF",
    "Abrir pasta ao concluir": "Abrir carpeta al finalizar",
    "Arraste PDFs, EPUBs ou pastas aqui": "Arrastre PDFs, EPUBs o carpetas aquí",
    "PDF para EPUB": "PDF a EPUB",
    "PDF para XTCH": "PDF a XTCH",
    "EPUB para XTCH": "EPUB a XTCH",
    "Configurações do XTEINK": "Configuración de XTEINK",
    "Dispositivos e conversões": "Dispositivos y conversiones",
    "Dispositivo": "Cihaz",
    "Qualidade do arquivo (%)": "Calidad del archivo (%)",
    "Aplicar perfil": "Profili uygula",
    "Editor de perfis": "Profil düzenleyici",
    "Abrir pasta Converter": "Dönüştürücü klasörünü aç",
    "Arquivo atual": "Geçerli dosya",
    "Total": "Total",
    "Converter pronto": "Convertidor listo",
    "XTEINK pronto": "XTEINK listo",
    "XTEINK concluído": "XTEINK concluido",
    "XTEINK cancelado": "XTEINK cancelado",
    "Aparência e interface": "Apariencia e interfaz",
    "Salvar automaticamente alterações nas configurações": "Guardar automáticamente cambios de configuración",
    "Mostrar dicas/tooltips": "Mostrar consejos/tooltips",
    "Confirmar antes de ações perigosas": "Confirmar antes de acciones peligrosas",
    "Lembrar tamanho/posição da janela": "Recordar tamaño/posición de la ventana",
    "Lembrar última aba aberta": "Recordar última pestaña abierta",
    "Densidade da interface": "Densidad de la interfaz",
    "Tamanho da fonte": "Tamaño de fuente",
    "Desempenho, CPU/GPU e cache": "Rendimiento, CPU/GPU y caché",
    "Perfil de desempenho": "Perfil de rendimiento",
    "Uso de CPU/GPU": "Uso de CPU/GPU",
    "Modo de hardware": "Modo de hardware",
    "Threads de trabalho (0 = automático)": "Hilos de trabajo (0 = automático)",
    "PDFs paralelos (0 = automático)": "PDF paralelos (0 = automático)",
    "Prioridade do processo": "Prioridad del proceso",
    "Ativar cache de páginas": "Activar caché de páginas",
    "Cache de páginas (MB)": "Caché de páginas (MB)",
    "Economia de memória": "Ahorro de memoria",
    "Usar GPU somente se for mais rápida": "Usar GPU solo si es más rápida",
    "Voltar para CPU se a GPU falhar": "Volver a CPU si falla la GPU",
    "Benchmark rápido": "Benchmark rápido",
    "Copiar diagnóstico": "Copiar diagnóstico",
    "Ver status do hardware": "Ver estado del hardware",
    "Testar aceleração": "Probar aceleración",
    "Aceleração": "Aceleración",
    "Diagnóstico": "Diagnóstico",
    "Diagnóstico copiado.": "Diagnóstico copiado.",
    "Arquivos, segurança e automação": "Archivos, seguridad y automatización",
    "Criar backup dos originais": "Crear copia de seguridad de originales",
    "Sobrescrever arquivo original": "Sobrescribir archivo original",
    "Validar saída final": "Validar salida final",
    "Salvar PDF com páginas removidas": "Guardar PDF con páginas eliminadas",
    "Senha PDF": "Contraseña PDF",
    "Detectar duplicidades": "Detectar duplicados",
    "Pular arquivos já processados": "Omitir archivos ya procesados",
    "Processar automaticamente ao adicionar": "Procesar automáticamente al agregar",
    "Continuar de onde parou quando possível": "Continuar desde donde se detuvo cuando sea posible",
    "Modo silencioso": "Modo silencioso",
    "Lembrar última pasta utilizada": "Recordar última carpeta usada",
    "Limpar cache ao sair": "Limpiar caché al salir",
    "Salvar configurações": "Guardar configuración",
    "Logs e diagnóstico": "Registros y diagnóstico",
    "Nível de log": "Nivel de registro",
    "Salvar log automaticamente": "Guardar registro automáticamente",
    "Retenção de logs (dias)": "Retención de registros (días)",
    "Abrir log": "Abrir registro",
    "Básico": "Básico",
    "Normal": "Normal",
    "Detalhado": "Detallado",
    "Debug": "Debug",
    "Prévia e visualização": "Vista previa y visualización",
    "Qualidade da prévia": "Calidad de vista previa",
    "Páginas por lote": "Páginas por lote",
    "Largura miniatura": "Ancho de miniatura",
    "Usar cache de prévia": "Usar caché de vista previa",
    "Abrir prévia maximizada": "Abrir vista previa maximizada",
    "Baixa": "Baja",
    "Média": "Media",
    "Alta": "Alta",
    "Pequena": "Pequeña",
    "Grande": "Grande",
    "Muito grande": "Muy grande",
    "Compacta": "Compacta",
    "Espaçosa": "Espaciosa",
    "Econômico": "Económico",
    "Equilibrado": "Equilibrado",
    "Rápido": "Rápido",
    "Máximo desempenho": "Máximo rendimiento",
    "Sobre o CUMA": "Acerca de CUMA",
    "Resumo rápido do que cada aba faz:": "Resumen rápido de cada pestaña:",
    "Abas do aplicativo": "Pestañas de la aplicación",
    "Abrir manual interativo": "Abrir manual interactivo",
    "Abrir manual TXT completo": "Abrir manual TXT completo",
    "Manual interativo do CUMA": "Manual interactivo de CUMA",
    "Seções": "Secciones",
    "Conteúdo": "Contenido",
    "Botões do topo": "Botones superiores",
    "Perfis de dispositivo": "Perfiles de dispositivo",
    "FAQ rápido": "FAQ rápido",
    "Abrir manual completo": "Abrir manual completo",
    "Fechar": "Kapat",
    "Limpar PDF": "Limpiar PDF",
    "Opções": "Opciones",
    "Compactação": "Compresión",
    "Modo de detecção": "Modo de detección",
    "Perfil de limpeza": "Perfil de limpieza",
    "Preservar qualidade máxima": "Conservar calidad máxima",
    "Compactar moderadamente": "Comprimir moderadamente",
    "Compactar bastante": "Comprimir mucho",
    "Original": "Original",
    "Sempre manter primeira página": "Mantener siempre la primera página",
    "Manter últimas páginas": "Mantener últimas páginas",
    "Validar PDF final": "Validar PDF final",
    "Criar backup": "Crear copia de seguridad",
    "Processar automaticamente ao adicionar arquivos": "Procesar automáticamente al agregar archivos",
    "Lembrar última pasta aberta": "Recordar última carpeta abierta",
    "Amostra": "Amostra",
    "Texto de amostra": "Texto de amostra",
    "OK": "OK",
    "Pause": "Pause",
    "Play": "Play",
    "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.": "Mantidos aqui os itens mais usados no fluxo principal: pasta de saída, nome/sufixo, formato, intervalo e abrir resultado.",
    "Criar PDF dos selecionados": "Criar PDF dos selecionados",
    "Criar PDF de todos": "Criar PDF de todos",
    "Processar todos": "Processar todos",
    "Funções por tipo de arquivo": "Funções por tipo de arquivo",
    "Sobrescrever originais": "Sobrescrever originais",
    "Salvar configurações automaticamente": "Salvar configurações automaticamente",
    "Largura das miniaturas": "Largura das miniaturas",
    "Usar cache na prévia": "Usar cache na prévia",
    "Carregamento incremental": "Carregamento incremental",
    "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.": "Escolha uma seção à esquerda para ver uma explicação detalhada. Use o botão “Abrir TXT completo” se quiser o manual separado do sistema.",
    "Detectar PDFs duplicados na lista": "Detectar PDFs duplicados na lista",
    "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.": "PDF → EPUB: renderiza o PDF, ajusta ao dispositivo e cria EPUB com páginas em imagem.",
    "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.": "PDF → XTCH: gera XTCH nativo 2-bit grayscale direto do PDF. Não executa workers do xtcjs.",
    "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.": "EPUB → XTCH: converte EPUB baseado em imagens para XTCH nativo.",
    "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.": "Essas opções são salvas por dispositivo. Em Personalizado você pode criar um novo nome e resolução própria.",
    "Nome do dispositivo": "Nome do dispositivo",
    "Perfil carregado": "Perfil carregado",
    "Salvar perfil": "Salvar perfil",
    "Salvar no perfil atual": "Salvar no perfil atual",
    "Salvar como novo personalizado": "Salvar como novo personalizado",
    "Salvar como nome": "Salvar como nome",
    "Restaurar perfis padrão": "Restaurar perfis padrão"
  }
}
V10_OPTION_DISPLAY = {
  "theme_mode": {
    "pt_BR": {
      "Automático": "Automático",
      "Claro": "Claro",
      "Escuro": "Escuro",
      "Personalizado": "Personalizado"
    },
    "en_US": {
      "Automático": "Automatic",
      "Claro": "Light",
      "Escuro": "Dark",
      "Personalizado": "Custom"
    },
    "es_ES": {
      "Automático": "Automático",
      "Claro": "Claro",
      "Escuro": "Oscuro",
      "Personalizado": "Personalizado"
    },
    "fr_FR": {
      "Automático": "Automatique",
      "Claro": "Clair",
      "Escuro": "Sombre",
      "Personalizado": "Personnalisé"
    },
    "de_DE": {
      "Automático": "Automatisch",
      "Claro": "Hell",
      "Escuro": "Dunkel",
      "Personalizado": "Benutzerdefiniert"
    },
    "it_IT": {
      "Automático": "Automatico",
      "Claro": "Chiaro",
      "Escuro": "Scuro",
      "Personalizado": "Personalizzato"
    },
    "ja_JP": {
      "Automático": "自動",
      "Claro": "ライト",
      "Escuro": "ダーク",
      "Personalizado": "カスタム"
    },
    "ko_KR": {
      "Automático": "자동",
      "Claro": "밝게",
      "Escuro": "어둡게",
      "Personalizado": "사용자 지정"
    },
    "zh_TW": {
      "Automático": "自動",
      "Claro": "淺色",
      "Escuro": "深色",
      "Personalizado": "自訂"
    },
    "tr_TR": {
      "Automático": "Otomatik",
      "Claro": "Açık",
      "Escuro": "Koyu",
      "Personalizado": "Özel"
    }
  },
  "custom_base_theme": {
    "pt_BR": {
      "Claro": "Claro",
      "Escuro": "Escuro"
    },
    "en_US": {
      "Claro": "Light",
      "Escuro": "Dark"
    },
    "es_ES": {
      "Claro": "Claro",
      "Escuro": "Oscuro"
    },
    "fr_FR": {
      "Claro": "Clair",
      "Escuro": "Sombre"
    },
    "de_DE": {
      "Claro": "Hell",
      "Escuro": "Dunkel"
    },
    "it_IT": {
      "Claro": "Chiaro",
      "Escuro": "Scuro"
    },
    "ja_JP": {
      "Claro": "ライト",
      "Escuro": "ダーク"
    },
    "ko_KR": {
      "Claro": "밝게",
      "Escuro": "어둡게"
    },
    "zh_TW": {
      "Claro": "淺色",
      "Escuro": "深色"
    },
    "tr_TR": {
      "Claro": "Açık",
      "Escuro": "Koyu"
    }
  }
}


def _cuma_v10_log(context: str, exc: Exception | None = None) -> None:
    try:
        if exc is None:
            write_log(f'[{_CUMA_TRANSLATION_TOTAL_V10_PATCH}] {context}')
        else:
            write_log(f'[{_CUMA_TRANSLATION_TOTAL_V10_PATCH}] {context}: {exc}')
            if 'write_error_log' in globals():
                write_error_log(type(exc), exc, exc.__traceback__, context)
    except Exception:
        pass


def _cuma_v10_reverse_map() -> dict:
    rev = {}
    try:
        for code, mapping in V10_UI_I18N.items():
            if isinstance(mapping, dict):
                for pt, translated in mapping.items():
                    if isinstance(pt, str) and isinstance(translated, str):
                        rev[pt] = pt
                        rev[translated] = pt
        # Preservar compatibilidade com dicionários antigos já existentes.
        for source_name in ('V8_UI_I18N', 'V6_EXTRA_TEXT', 'I18N'):
            source = globals().get(source_name, {})
            if isinstance(source, dict):
                for _code, mapping in source.items():
                    if isinstance(mapping, dict):
                        for pt, translated in mapping.items():
                            if isinstance(pt, str):
                                rev.setdefault(pt, pt)
                            if isinstance(translated, str) and isinstance(pt, str):
                                rev.setdefault(translated, pt)
    except Exception:
        pass
    return rev

V10_REVERSE_I18N = _cuma_v10_reverse_map()


def _cuma_v10_canonical(text):
    if not isinstance(text, str):
        return text
    fixed = text.strip()
    if not fixed:
        return text
    try:
        if '_cuma_fix_mojibake_text' in globals():
            fixed = _cuma_fix_mojibake_text(fixed)
    except Exception:
        pass
    if fixed in V6_LANGUAGE_DISPLAY.values():
        return fixed
    if fixed in V10_REVERSE_I18N:
        return V10_REVERSE_I18N[fixed]
    try:
        if '_cuma_v8_canonical' in globals():
            older = _cuma_v8_canonical(fixed)
            if older in V10_REVERSE_I18N:
                return V10_REVERSE_I18N[older]
            return older
    except Exception:
        pass
    return fixed


def _cuma_v10_tr(text, lang=None):
    base = _cuma_v10_canonical(text)
    if not isinstance(base, str) or not base:
        return base
    try:
        if base == APP_DISPLAY_NAME or base.startswith(APP_DISPLAY_NAME):
            return base
    except Exception:
        pass
    # A caixa de idioma deve manter nomes nativos, não traduzidos.
    try:
        if base in V6_LANGUAGE_DISPLAY.values():
            return base
    except Exception:
        pass
    lang = lang or (_cuma_detect_system_language() if '_cuma_detect_system_language' in globals() else 'pt_BR')
    if lang == 'system':
        lang = _cuma_detect_system_language()
    if lang == 'pt_BR':
        return base
    mapping = V10_UI_I18N.get(lang, {})
    if isinstance(mapping, dict) and base in mapping:
        return mapping[base]
    # Fallback seguro: se a língua não tiver chave, mantém o PT-BR canônico.
    # Isso evita a tela híbrida PT/EN vista no patch anterior.
    return base


def _cuma_v10_translate_widget_tree(widget, lang):
    try:
        # não traduzir combobox de idioma diretamente; ele é tratado pela V9/V10 role binding
        if isinstance(widget, ttk.Combobox) and getattr(widget, '_cuma_combo_role', '') == 'app_language':
            return
    except Exception:
        pass
    try:
        txt = widget.cget('text')
    except Exception:
        txt = None
    if isinstance(txt, str) and txt:
        try:
            if not hasattr(widget, '_cuma_base_text'):
                setattr(widget, '_cuma_base_text', _cuma_v10_canonical(txt))
            else:
                setattr(widget, '_cuma_base_text', _cuma_v10_canonical(getattr(widget, '_cuma_base_text')))
            base = getattr(widget, '_cuma_base_text', txt)
            widget.configure(text=_cuma_v10_tr(base, lang))
        except Exception:
            pass
    try:
        if isinstance(widget, ttk.Notebook):
            if not hasattr(widget, '_cuma_base_tabs_v10'):
                setattr(widget, '_cuma_base_tabs_v10', {tab_id: _cuma_v10_canonical(widget.tab(tab_id, 'text')) for tab_id in widget.tabs()})
            base_tabs = getattr(widget, '_cuma_base_tabs_v10', {})
            for tab_id in widget.tabs():
                base = base_tabs.get(tab_id, _cuma_v10_canonical(widget.tab(tab_id, 'text')))
                widget.tab(tab_id, text=_cuma_v10_tr(base, lang))
        if isinstance(widget, ttk.Treeview):
            if not hasattr(widget, '_cuma_base_headings_v10'):
                heading_map = {}
                for col in widget['columns']:
                    heading_map[col] = _cuma_v10_canonical(widget.heading(col, 'text'))
                setattr(widget, '_cuma_base_headings_v10', heading_map)
            for col, base in getattr(widget, '_cuma_base_headings_v10', {}).items():
                widget.heading(col, text=_cuma_v10_tr(base, lang))
    except Exception:
        pass
    try:
        for child in widget.winfo_children():
            _cuma_v10_translate_widget_tree(child, lang)
    except Exception:
        pass


def _cuma_v10_update_vars(self, lang):
    try:
        if hasattr(self, 'app_language_help'):
            sys_label = V6_LANGUAGE_DISPLAY.get(_cuma_detect_system_language(), _cuma_detect_system_language())
            sel_code = _cuma_v6_load_lang_code(self) if '_cuma_v6_load_lang_code' in globals() else 'system'
            sel_label = V6_LANGUAGE_DISPLAY.get(sel_code, sel_code)
            self.app_language_help.set(f"{_cuma_v10_tr('Idioma do sistema detectado', lang)}: {sys_label} | {_cuma_v10_tr('Selecionado', lang)}: {sel_label}")
    except Exception:
        pass
    for attr in ['xteink_status', 'tools_debug_var', 'xteink_device_note', 'xteink_counter', 'status', 'counter']:
        try:
            var = getattr(self, attr, None)
            if var is not None:
                cur = var.get()
                if not hasattr(var, '_cuma_base_value_v10'):
                    setattr(var, '_cuma_base_value_v10', _cuma_v10_canonical(cur))
                base = getattr(var, '_cuma_base_value_v10', cur)
                # Só traduz textos estáticos simples; contadores dinâmicos com números são preservados.
                if isinstance(base, str) and not any(ch.isdigit() for ch in base):
                    var.set(_cuma_v10_tr(base, lang))
        except Exception:
            pass


def _cuma_v10_option_display(raw_value, group, lang):
    mapping = V10_OPTION_DISPLAY.get(group, {})
    locale_map = mapping.get(lang) or mapping.get('en_US') or {}
    return locale_map.get(raw_value, raw_value)


def _cuma_v10_option_raw(display_value, group, lang):
    mapping = V10_OPTION_DISPLAY.get(group, {})
    locale_map = mapping.get(lang) or mapping.get('en_US') or {}
    inv = {v: k for k, v in locale_map.items()}
    # tenta todos os idiomas para permitir troca de idioma sem perder valor atual
    for lm in mapping.values():
        try:
            inv.update({v: k for k, v in lm.items()})
        except Exception:
            pass
    return inv.get(display_value, display_value)


def _cuma_v10_bind_visual_combo(self, combo, lang):
    try:
        if combo is None:
            return
        combo._cuma_combo_role = 'theme_mode'
        _cuma_v6_setup_display_option_vars(self)
        self.theme_mode_display.set(_cuma_v10_option_display(self.theme_mode.get(), 'theme_mode', lang))
        combo.configure(textvariable=self.theme_mode_display, values=list(V10_OPTION_DISPLAY['theme_mode'].get(lang, V10_OPTION_DISPLAY['theme_mode']['en_US']).values()), state='readonly')
        def on_mode_change(_event=None):
            raw = _cuma_v10_option_raw(self.theme_mode_display.get(), 'theme_mode', lang)
            self.theme_mode.set(raw)
            try:
                self._apply_theme_mode_selection(save=True)
            except Exception:
                self.save_current_config(force=True)
        combo.bind('<<ComboboxSelected>>', on_mode_change)
    except Exception as exc:
        _cuma_v10_log('Falha ao configurar combobox de modo visual V10', exc)


def _cuma_v10_bind_base_combo(self, combo, lang):
    try:
        if combo is None:
            return
        combo._cuma_combo_role = 'custom_base_theme'
        _cuma_v6_setup_display_option_vars(self)
        self.custom_base_display.set(_cuma_v10_option_display(self.custom_base_theme.get(), 'custom_base_theme', lang))
        combo.configure(textvariable=self.custom_base_display, values=list(V10_OPTION_DISPLAY['custom_base_theme'].get(lang, V10_OPTION_DISPLAY['custom_base_theme']['en_US']).values()), state='readonly')
        def on_base_change(_event=None):
            raw = _cuma_v10_option_raw(self.custom_base_display.get(), 'custom_base_theme', lang)
            self.custom_base_theme.set(raw)
            try:
                self._apply_theme_mode_selection(save=True)
            except Exception:
                self.save_current_config(force=True)
        combo.bind('<<ComboboxSelected>>', on_base_change)
    except Exception as exc:
        _cuma_v10_log('Falha ao configurar combobox de base personalizada V10', exc)


def _cuma_v10_bind_combo_translation(self, tab_theme, lang):
    try:
        _cuma_v9_bind_combo_translation(self, tab_theme, lang)
        lang_combo = getattr(self, '_cuma_language_combo', None)
        if lang_combo is not None:
            try:
                lang_combo.configure(textvariable=self.app_language_display, values=list(V6_LANGUAGE_DISPLAY.values()), state='readonly')
            except Exception:
                pass
        mode_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'theme_mode', None), getattr(self, 'theme_mode_display', None))
        base_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'custom_base_theme', None), getattr(self, 'custom_base_display', None))
        if mode_combo is not None and mode_combo is not lang_combo:
            _cuma_v10_bind_visual_combo(self, mode_combo, lang)
        if base_combo is not None and base_combo is not lang_combo:
            _cuma_v10_bind_base_combo(self, base_combo, lang)
    except Exception as exc:
        _cuma_v10_log('Falha ao vincular combos V10', exc)


def _cuma_v10_apply_language(self):
    lang = _cuma_v6_resolved_lang(self) if '_cuma_v6_resolved_lang' in globals() else _cuma_detect_system_language()
    try:
        _cuma_v10_translate_widget_tree(self.root, lang)
        _cuma_v10_update_vars(self, lang)
        try:
            if hasattr(self, 'nav_items'):
                for label, item in self.nav_items.items():
                    try:
                        item['text'].configure(text=_cuma_v10_tr(label, lang))
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if hasattr(self, 'dashboard_cards'):
                cards = self.dashboard_cards
                if 'files' in cards: cards['files']['title'].configure(text=_cuma_v10_tr('Fila principal', lang))
                if 'xteink' in cards: cards['xteink']['title'].configure(text=_cuma_v10_tr('Converter', lang))
                if 'update' in cards: cards['update']['title'].configure(text=_cuma_v10_tr('Versão', lang))
        except Exception:
            pass
        try:
            tab_theme = _cuma_v9_find_theme_tab(self)
            _cuma_v10_bind_combo_translation(self, tab_theme, lang)
        except Exception:
            pass
        try:
            self.root.title(f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}')
        except Exception:
            pass
    except Exception as exc:
        _cuma_v10_log('Falha ao aplicar tradução global V10', exc)


def _cuma_v10_install_patch():
    try:
        # substitui tradutores antigos por versão canônica V10
        globals()['_cuma_v8_tr'] = _cuma_v10_tr
        globals()['_cuma_v6_tr'] = _cuma_v10_tr
        globals()['_cuma_tr'] = _cuma_v10_tr
        globals()['_cuma_apply_language_to_widgets'] = _cuma_v10_apply_language
        globals()['_cuma_on_language_changed'] = _cuma_v10_apply_language
        globals()['_cuma_v6_option_display'] = _cuma_v10_option_display
        globals()['_cuma_v6_option_raw'] = _cuma_v10_option_raw
        globals()['_cuma_v6_bind_combo_translation'] = _cuma_v10_bind_combo_translation
        globals()['_cuma_v9_bind_combo_translation'] = _cuma_v10_bind_combo_translation
        globals()['_cuma_v9_bind_visual_combo'] = _cuma_v10_bind_visual_combo
        globals()['_cuma_v9_bind_base_combo'] = _cuma_v10_bind_base_combo
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_v10_log('Falha ao instalar patch V10', exc)


_cuma_v10_install_patch()

# =============================================================================
# CUMA - PATCH V11: tradução leve, completa nos pontos restantes e janela normal
# =============================================================================
# Objetivos:
# - Manter o título principal do aplicativo sem tradução.
# - Traduzir subtítulo, cartões do topo, contadores e textos dinâmicos restantes.
# - Remover a lentidão causada por tradução recursiva antiga/reentrante.
# - Impedir que a janela principal abra maximizada/zoomed.
# =============================================================================
_CUMA_TRANSLATION_V11_PATCH = 'v11_light_i18n_and_window_2026_06_22'

V11_EXTRA_UI_I18N = {
    'en_US': {
        APP_SUBTITLE: 'CUMA: cleaning, exporting and converting PDFs, images, EPUB and XTCH.',
        'Fila de conversão EPUB / XTCH': 'EPUB / XTCH conversion queue',
        'Arquivos': 'Files', 'Aguardando': 'Waiting', 'Concluído': 'Completed', 'Erro': 'Error',
        'Preset ativo': 'Active preset', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Visual mode adjusted. Use Custom to edit colors freely or choose a system preset to start faster.',
        'Configurações organizadas por categoria': 'Settings organized by category',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: cleaning, exporting and converting PDFs, images, EPUB and XTCH.',
        'Atualizado em {date}': 'Updated on {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'Files: {total} | OK: {ok} | Errors: {err}',
    },
    'es_ES': {
        APP_SUBTITLE: 'CUMA: limpieza, exportación y conversión de PDF, imágenes, EPUB y XTCH.',
        'Fila de conversão EPUB / XTCH': 'Cola de conversión EPUB / XTCH',
        'arquivo(s)': 'archivo(s)', 'item(ns)': 'elemento(s)', 'Arquivos': 'Archivos', 'Erros': 'Errores',
        'Aguardando': 'En espera', 'Concluído': 'Completado', 'Erro': 'Error',
        'Preset ativo': 'Preajuste activo', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Modo visual ajustado. Use Personalizado para editar colores libremente o elija un preajuste del sistema para empezar más rápido.',
        'Configurações organizadas por categoria': 'Configuración organizada por categoría',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: limpieza, exportación y conversión de PDF, imágenes, EPUB y XTCH.',
        'Atualizado em {date}': 'Actualizado el {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'Archivos: {total} | OK: {ok} | Errores: {err}',
    },
    'fr_FR': {
        APP_SUBTITLE: 'CUMA : nettoyage, exportation et conversion de PDF, images, EPUB et XTCH.',
        'Fila de conversão EPUB / XTCH': 'File de conversion EPUB / XTCH',
        'arquivo(s)': 'fichier(s)', 'item(ns)': 'élément(s)', 'Arquivos': 'Fichiers', 'Erros': 'Erreurs',
        'Aguardando': 'En attente', 'Concluído': 'Terminé', 'Erro': 'Erreur',
        'Preset ativo': 'Préréglage actif', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Mode visuel ajusté. Utilisez Personnalisé pour modifier librement les couleurs ou choisissez un préréglage système pour commencer plus vite.',
        'Configurações organizadas por categoria': 'Paramètres organisés par catégorie',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA : nettoyage, exportation et conversion de PDF, images, EPUB et XTCH.',
        'Atualizado em {date}': 'Mis à jour le {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'Fichiers : {total} | OK : {ok} | Erreurs : {err}',
    },
    'de_DE': {
        APP_SUBTITLE: 'CUMA: Bereinigung, Export und Konvertierung von PDFs, Bildern, EPUB und XTCH.',
        'Fila de conversão EPUB / XTCH': 'EPUB-/XTCH-Konvertierungswarteschlange',
        'arquivo(s)': 'Datei(en)', 'item(ns)': 'Element(e)', 'Arquivos': 'Dateien', 'Erros': 'Fehler',
        'Aguardando': 'Wartet', 'Concluído': 'Abgeschlossen', 'Erro': 'Fehler',
        'Preset ativo': 'Aktive Vorgabe', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Darstellungsmodus angepasst. Verwenden Sie Benutzerdefiniert, um Farben frei zu bearbeiten, oder wählen Sie eine Systemvorgabe für einen schnelleren Start.',
        'Configurações organizadas por categoria': 'Einstellungen nach Kategorie organisiert',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: Bereinigung, Export und Konvertierung von PDFs, Bildern, EPUB und XTCH.',
        'Atualizado em {date}': 'Aktualisiert am {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'Dateien: {total} | OK: {ok} | Fehler: {err}',
    },
    'it_IT': {
        APP_SUBTITLE: 'CUMA: pulizia, esportazione e conversione di PDF, immagini, EPUB e XTCH.',
        'Fila de conversão EPUB / XTCH': 'Coda di conversione EPUB / XTCH',
        'arquivo(s)': 'file', 'item(ns)': 'elementi', 'Arquivos': 'File', 'Erros': 'Errori',
        'Aguardando': 'In attesa', 'Concluído': 'Completato', 'Erro': 'Errore',
        'Preset ativo': 'Preset attivo', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Modalità visiva regolata. Usa Personalizzato per modificare liberamente i colori o scegli un preset di sistema per iniziare più rapidamente.',
        'Configurações organizadas por categoria': 'Impostazioni organizzate per categoria',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: pulizia, esportazione e conversione di PDF, immagini, EPUB e XTCH.',
        'Atualizado em {date}': 'Aggiornato il {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'File: {total} | OK: {ok} | Errori: {err}',
    },
    'ja_JP': {
        APP_SUBTITLE: 'CUMA：PDF、画像、EPUB、XTCH の整理・書き出し・変換。',
        'Fila de conversão EPUB / XTCH': 'EPUB / XTCH 変換キュー',
        'arquivo(s)': 'ファイル', 'item(ns)': '項目', 'Arquivos': 'ファイル', 'Erros': 'エラー',
        'Aguardando': '待機中', 'Concluído': '完了', 'Erro': 'エラー',
        'Preset ativo': '現在のプリセット', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': '表示モードを調整しました。色を自由に編集するにはカスタムを使うか、すばやく始めるにはシステムプリセットを選択してください。',
        'Configurações organizadas por categoria': 'カテゴリ別に整理された設定',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA：PDF、画像、EPUB、XTCH の整理・書き出し・変換。',
        'Atualizado em {date}': '更新日 {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'ファイル: {total} | OK: {ok} | エラー: {err}',
    },
    'ko_KR': {
        APP_SUBTITLE: 'CUMA: PDF, 이미지, EPUB 및 XTCH 정리, 내보내기와 변환.',
        'Fila de conversão EPUB / XTCH': 'EPUB / XTCH 변환 대기열',
        'arquivo(s)': '파일', 'item(ns)': '항목', 'Arquivos': '파일', 'Erros': '오류',
        'Aguardando': '대기 중', 'Concluído': '완료', 'Erro': '오류',
        'Preset ativo': '활성 프리셋', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': '시각 모드가 조정되었습니다. 색상을 자유롭게 편집하려면 사용자 지정을 사용하거나 더 빠르게 시작하려면 시스템 프리셋을 선택하세요.',
        'Configurações organizadas por categoria': '카테고리별로 정리된 설정',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: PDF, 이미지, EPUB 및 XTCH 정리, 내보내기와 변환.',
        'Atualizado em {date}': '업데이트 날짜 {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': '파일: {total} | OK: {ok} | 오류: {err}',
    },
    'zh_TW': {
        APP_SUBTITLE: 'CUMA：清理、匯出並轉換 PDF、圖片、EPUB 與 XTCH。',
        'Fila de conversão EPUB / XTCH': 'EPUB / XTCH 轉換佇列',
        'arquivo(s)': '檔案', 'item(ns)': '項目', 'Arquivos': '檔案', 'Erros': '錯誤',
        'Aguardando': '等待中', 'Concluído': '已完成', 'Erro': '錯誤',
        'Preset ativo': '目前預設', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': '視覺模式已調整。使用自訂可自由編輯顏色，或選擇系統預設以更快開始。',
        'Configurações organizadas por categoria': '依類別整理的設定',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA：清理、匯出並轉換 PDF、圖片、EPUB 與 XTCH。',
        'Atualizado em {date}': '更新於 {date}',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': '檔案: {total} | OK: {ok} | 錯誤: {err}',
    },
    'tr_TR': {
        APP_SUBTITLE: 'CUMA: PDF, görsel, EPUB ve XTCH temizleme, dışa aktarma ve dönüştürme.',
        'Fila de conversão EPUB / XTCH': 'EPUB / XTCH dönüştürme kuyruğu',
        'arquivo(s)': 'dosya', 'item(ns)': 'öğe', 'Arquivos': 'Dosyalar', 'Erros': 'Hatalar',
        'Aguardando': 'Bekliyor', 'Concluído': 'Tamamlandı', 'Erro': 'Hata',
        'Preset ativo': 'Etkin ön ayar', 'Modo visual ajustado. Use Personalizado para editar cores livremente ou escolha um preset do sistema para começar mais rápido.': 'Görsel mod ayarlandı. Renkleri serbestçe düzenlemek için Özel seçeneğini kullanın veya daha hızlı başlamak için bir sistem ön ayarı seçin.',
        'Configurações organizadas por categoria': 'Kategoriye göre düzenlenen ayarlar',
        'Conversor Ultimate de Mangás: limpeza, exportação e conversão de PDFs, imagens, EPUB e XTCH.': 'CUMA: PDF, görsel, EPUB ve XTCH temizleme, dışa aktarma ve dönüştürme.',
        'Atualizado em {date}': '{date} tarihinde güncellendi',
        'Arquivos: {total} | OK: {ok} | Erros: {err}': 'Dosyalar: {total} | OK: {ok} | Hatalar: {err}',
    },
}


def _cuma_v11_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'[{_CUMA_TRANSLATION_V11_PATCH}] {context}' if exc is None else f'[{_CUMA_TRANSLATION_V11_PATCH}] {context}: {exc}'
        write_log(msg)
    except Exception:
        pass


def _cuma_v11_language(self=None) -> str:
    try:
        lang = _cuma_v6_resolved_lang(self) if self is not None and '_cuma_v6_resolved_lang' in globals() else _cuma_detect_system_language()
    except Exception:
        lang = 'pt_BR'
    if lang == 'system':
        try:
            lang = _cuma_detect_system_language()
        except Exception:
            lang = 'pt_BR'
    return lang if lang in APP_LANGUAGE_OPTIONS else 'pt_BR'


def _cuma_v11_merged_mapping(lang: str) -> dict:
    base = {}
    try:
        if isinstance(V10_UI_I18N.get(lang), dict):
            base.update(V10_UI_I18N.get(lang, {}))
    except Exception:
        pass
    try:
        base.update(V11_EXTRA_UI_I18N.get(lang, {}))
    except Exception:
        pass
    return base


def _cuma_v11_make_reverse() -> dict:
    rev = {}
    try:
        for code in list(APP_LANGUAGE_OPTIONS.keys()) + ['pt_BR']:
            mapping = _cuma_v11_merged_mapping(code)
            for pt, translated in mapping.items():
                if isinstance(pt, str):
                    rev.setdefault(pt, pt)
                if isinstance(pt, str) and isinstance(translated, str):
                    rev.setdefault(translated, pt)
        for source_name in ('V10_REVERSE_I18N', 'V8_UI_I18N', 'V6_EXTRA_TEXT', 'I18N'):
            source = globals().get(source_name, {})
            if isinstance(source, dict):
                if source_name == 'V10_REVERSE_I18N':
                    for k, v in source.items():
                        if isinstance(k, str) and isinstance(v, str): rev.setdefault(k, v)
                else:
                    for _code, mapping in source.items():
                        if isinstance(mapping, dict):
                            for pt, translated in mapping.items():
                                if isinstance(pt, str): rev.setdefault(pt, pt)
                                if isinstance(pt, str) and isinstance(translated, str): rev.setdefault(translated, pt)
    except Exception:
        pass
    return rev

V11_REVERSE_I18N = _cuma_v11_make_reverse()
V11_TR_CACHE = {}


def _cuma_v11_canonical(text):
    if not isinstance(text, str):
        return text
    fixed = text.strip()
    if not fixed:
        return text
    try:
        if '_cuma_fix_mojibake_text' in globals():
            fixed = _cuma_fix_mojibake_text(fixed)
    except Exception:
        pass
    if fixed in V6_LANGUAGE_DISPLAY.values():
        return fixed
    return V11_REVERSE_I18N.get(fixed, fixed)


def _cuma_v11_tr(text, lang=None):
    base = _cuma_v11_canonical(text)
    if not isinstance(base, str) or not base:
        return base
    try:
        if base == APP_DISPLAY_NAME or base.startswith(APP_DISPLAY_NAME):
            return base
    except Exception:
        pass
    if base in V6_LANGUAGE_DISPLAY.values():
        return base
    lang = lang or 'pt_BR'
    if lang == 'system':
        lang = _cuma_v11_language()
    cache_key = (lang, base)
    if cache_key in V11_TR_CACHE:
        return V11_TR_CACHE[cache_key]
    if lang == 'pt_BR':
        result = base
    else:
        mapping = _cuma_v11_merged_mapping(lang)
        result = mapping.get(base, base)
    V11_TR_CACHE[cache_key] = result
    return result


def _cuma_v11_translate_widget_tree(widget, lang):
    stack = [widget]
    seen = set()
    while stack:
        w = stack.pop()
        wid = id(w)
        if wid in seen:
            continue
        seen.add(wid)
        try:
            if isinstance(w, ttk.Combobox) and getattr(w, '_cuma_combo_role', '') == 'app_language':
                pass
            else:
                try:
                    txt = w.cget('text')
                except Exception:
                    txt = None
                if isinstance(txt, str) and txt:
                    if not hasattr(w, '_cuma_base_text'):
                        setattr(w, '_cuma_base_text', _cuma_v11_canonical(txt))
                    base = _cuma_v11_canonical(getattr(w, '_cuma_base_text', txt))
                    try:
                        w.configure(text=_cuma_v11_tr(base, lang))
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if isinstance(w, ttk.Notebook):
                if not hasattr(w, '_cuma_base_tabs_v11'):
                    setattr(w, '_cuma_base_tabs_v11', {tab_id: _cuma_v11_canonical(w.tab(tab_id, 'text')) for tab_id in w.tabs()})
                for tab_id, base in getattr(w, '_cuma_base_tabs_v11', {}).items():
                    try: w.tab(tab_id, text=_cuma_v11_tr(base, lang))
                    except Exception: pass
            if isinstance(w, ttk.Treeview):
                if not hasattr(w, '_cuma_base_headings_v11'):
                    setattr(w, '_cuma_base_headings_v11', {col: _cuma_v11_canonical(w.heading(col, 'text')) for col in w['columns']})
                for col, base in getattr(w, '_cuma_base_headings_v11', {}).items():
                    try: w.heading(col, text=_cuma_v11_tr(base, lang))
                    except Exception: pass
        except Exception:
            pass
        try:
            stack.extend(w.winfo_children())
        except Exception:
            pass


def _cuma_v11_card_title_label(card):
    try:
        frame = card.get('frame') if isinstance(card, dict) else None
        lbl = getattr(frame, '_cuma_title_label', None)
        if lbl is not None:
            return lbl
        for child in frame.winfo_children():
            try:
                if str(child.cget('style')) == 'SummaryCardTitle.TLabel':
                    frame._cuma_title_label = child
                    return child
            except Exception:
                pass
    except Exception:
        pass
    return None


def _cuma_v11_create_summary_card(self, parent, title, value, subtitle):
    frame = ttk.Frame(parent, style='SummaryCard.TFrame', padding=(16, 14))
    value_var = tk.StringVar(value=value)
    subtitle_var = tk.StringVar(value=subtitle)
    title_lbl = ttk.Label(frame, text=title, style='SummaryCardTitle.TLabel')
    title_lbl._cuma_base_text = _cuma_v11_canonical(title)
    title_lbl.pack(anchor='w')
    ttk.Label(frame, textvariable=value_var, style='SummaryCardValue.TLabel').pack(anchor='w', pady=(4, 2))
    ttk.Label(frame, textvariable=subtitle_var, style='SummaryCardNote.TLabel', wraplength=260, justify='left').pack(anchor='w')
    frame._cuma_title_label = title_lbl
    return frame, value_var, subtitle_var


def _cuma_v11_refresh_dashboard(self):
    cards = getattr(self, 'dashboard_cards', {})
    if not cards:
        return
    lang = _cuma_v11_language(self)
    files_total = len(getattr(self, 'files', []))
    results = getattr(self, 'results', [])
    ok = sum(1 for r in results if getattr(r, 'status', '') == 'OK')
    err = sum(1 for r in results if getattr(r, 'status', '') == 'ERRO')
    xteink_total = len(getattr(self, 'xteink_files', []))
    try:
        lbl = _cuma_v11_card_title_label(cards.get('files'))
        if lbl: lbl.configure(text=_cuma_v11_tr('Fila principal', lang))
        cards['files']['value'].set(f"{files_total} {_cuma_v11_tr('arquivo(s)', lang)}")
        cards['files']['subtitle'].set(f"{_cuma_v11_tr('OK', lang)}: {ok}  •  {_cuma_v11_tr('Erros', lang)}: {err}")
    except Exception:
        pass
    try:
        lbl = _cuma_v11_card_title_label(cards.get('xteink'))
        if lbl: lbl.configure(text=_cuma_v11_tr('Converter', lang))
        cards['xteink']['value'].set(f"{xteink_total} {_cuma_v11_tr('item(ns)', lang)}")
        cards['xteink']['subtitle'].set(_cuma_v11_tr('Fila de conversão EPUB / XTCH', lang))
    except Exception:
        pass
    try:
        lbl = _cuma_v11_card_title_label(cards.get('update'))
        if lbl: lbl.configure(text=_cuma_v11_tr('Versão', lang))
        cards['update']['value'].set(CHANGELOG_LATEST['version'])
        cards['update']['subtitle'].set(_cuma_v11_tr('Atualizado em {date}', lang).format(date=CHANGELOG_LATEST['date']))
    except Exception:
        pass
    try:
        if hasattr(self, 'toggle_btn'):
            base = '☀ Tema claro' if self.theme.get() != 'Moderno Claro' else '🌙 Tema escuro'
            self.toggle_btn.configure(text=_cuma_v11_tr(base, lang))
    except Exception:
        pass
    try:
        if hasattr(self, 'color_choice_note'):
            kind = THEME_VISUAL_PRESETS.get(self.theme.get(), THEME_VISUAL_PRESETS['Moderno Escuro']).get('kind', '')
            self.color_choice_note.set(f"{_cuma_v11_tr('Preset ativo', lang)}: {kind}.")
    except Exception:
        pass


def _cuma_v11_update_counter(self):
    lang = _cuma_v11_language(self)
    ok = sum(1 for r in getattr(self, 'results', []) if getattr(r, 'status', '') == 'OK')
    err = sum(1 for r in getattr(self, 'results', []) if getattr(r, 'status', '') == 'ERRO')
    try:
        self.counter.set(_cuma_v11_tr('Arquivos: {total} | OK: {ok} | Erros: {err}', lang).format(total=len(getattr(self, 'files', [])), ok=ok, err=err))
    except Exception:
        pass
    try:
        self.refresh_dashboard()
    except Exception:
        pass


def _cuma_v11_update_xteink_counter(self):
    lang = _cuma_v11_language(self)
    ok = err = 0
    if hasattr(self, 'xteink_tree'):
        for iid in self.xteink_tree.get_children():
            status = str(self.xteink_tree.set(iid, 'status')).upper()
            if status == 'OK': ok += 1
            elif status in ('ERRO', 'ERROR'): err += 1
    try:
        self.xteink_counter.set(_cuma_v11_tr('Arquivos: {total} | OK: {ok} | Erros: {err}', lang).format(total=len(getattr(self, 'xteink_files', [])), ok=ok, err=err))
    except Exception:
        pass
    try:
        self.refresh_dashboard()
    except Exception:
        pass


def _cuma_v11_update_vars(self, lang):
    try:
        if hasattr(self, 'app_language_help'):
            sys_label = V6_LANGUAGE_DISPLAY.get(_cuma_detect_system_language(), _cuma_detect_system_language())
            sel_code = _cuma_v6_load_lang_code(self) if '_cuma_v6_load_lang_code' in globals() else 'system'
            sel_label = V6_LANGUAGE_DISPLAY.get(sel_code, sel_code)
            self.app_language_help.set(f"{_cuma_v11_tr('Idioma do sistema detectado', lang)}: {sys_label} | {_cuma_v11_tr('Selecionado', lang)}: {sel_label}")
    except Exception:
        pass
    try:
        if hasattr(self, 'status') and self.status.get() in ('Pronto', 'Ready', '準備完了', '준비됨'):
            self.status.set(_cuma_v11_tr('Pronto', lang))
    except Exception:
        pass


def _cuma_v11_bind_combo_translation(self, tab_theme, lang):
    try:
        lang_combo = getattr(self, '_cuma_language_combo', None)
        if lang_combo is not None:
            try:
                lang_combo._cuma_combo_role = 'app_language'
                lang_combo.configure(textvariable=self.app_language_display, values=list(V6_LANGUAGE_DISPLAY.values()), state='readonly')
            except Exception:
                pass
        try:
            mode_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'theme_mode', None), getattr(self, 'theme_mode_display', None))
            if mode_combo is not None and mode_combo is not lang_combo:
                _cuma_v10_bind_visual_combo(self, mode_combo, lang)
        except Exception:
            pass
        try:
            base_combo = _cuma_v9_find_combobox_by_textvariable(tab_theme, getattr(self, 'custom_base_theme', None), getattr(self, 'custom_base_display', None))
            if base_combo is not None and base_combo is not lang_combo:
                _cuma_v10_bind_base_combo(self, base_combo, lang)
        except Exception:
            pass
    except Exception as exc:
        _cuma_v11_log('Falha ao vincular combos V11', exc)


def _cuma_v11_apply_language(self):
    lang = _cuma_v11_language(self)
    try:
        _cuma_v11_translate_widget_tree(self.root, lang)
        _cuma_v11_update_vars(self, lang)
        try:
            if hasattr(self, 'nav_items'):
                for label, item in self.nav_items.items():
                    try: item['text'].configure(text=_cuma_v11_tr(label, lang))
                    except Exception: pass
        except Exception:
            pass
        try:
            tab_theme = _cuma_v9_find_theme_tab(self)
            _cuma_v11_bind_combo_translation(self, tab_theme, lang)
        except Exception:
            pass
        try:
            self.refresh_dashboard()
        except Exception:
            pass
        try:
            self.root.title(f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}')
        except Exception:
            pass
    except Exception as exc:
        _cuma_v11_log('Falha ao aplicar tradução V11', exc)


def _cuma_v11_fit_window_to_screen(self, top, width_ratio=0.82, height_ratio=0.82, min_width=1120, min_height=720):
    try:
        top.update_idletasks()
        sw = max(1024, int(top.winfo_screenwidth()))
        sh = max(720, int(top.winfo_screenheight()))
        width = min(max(min_width, int(sw * width_ratio)), sw - 80)
        height = min(max(min_height, int(sh * height_ratio)), sh - 100)
        x = max(20, (sw - width) // 2)
        y = max(20, (sh - height) // 2 - 10)
        try:
            top.state('normal')
        except Exception:
            pass
        top.geometry(f'{width}x{height}+{x}+{y}')
        top.minsize(min_width, min_height)
    except Exception as exc:
        _cuma_v11_log('Falha no ajuste de janela V11', exc)


def _cuma_v11_install_patch():
    try:
        App._create_summary_card = _cuma_v11_create_summary_card
        App.refresh_dashboard = _cuma_v11_refresh_dashboard
        App.update_counter = _cuma_v11_update_counter
        App.update_xteink_counter = _cuma_v11_update_xteink_counter
        App.fit_window_to_screen = _cuma_v11_fit_window_to_screen
        globals()['_cuma_v10_tr'] = _cuma_v11_tr
        globals()['_cuma_v8_tr'] = _cuma_v11_tr
        globals()['_cuma_v6_tr'] = _cuma_v11_tr
        globals()['_cuma_tr'] = _cuma_v11_tr
        globals()['_cuma_v10_apply_language'] = _cuma_v11_apply_language
        globals()['_cuma_v9_apply_language'] = _cuma_v11_apply_language
        globals()['_cuma_v8_apply_language'] = _cuma_v11_apply_language
        globals()['_cuma_v6_apply_language'] = _cuma_v11_apply_language
        globals()['_cuma_apply_language_to_widgets'] = _cuma_v11_apply_language
        globals()['_cuma_on_language_changed'] = _cuma_v11_apply_language
        globals()['_cuma_v10_bind_combo_translation'] = _cuma_v11_bind_combo_translation
        globals()['_cuma_v9_bind_combo_translation'] = _cuma_v11_bind_combo_translation
        globals()['_cuma_v6_bind_combo_translation'] = _cuma_v11_bind_combo_translation
        globals()['_cuma_v10_canonical'] = _cuma_v11_canonical
        globals()['_cuma_v10_translate_widget_tree'] = _cuma_v11_translate_widget_tree
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_v11_log('Falha ao instalar patch V11', exc)

_cuma_v11_install_patch()


# =============================================================================
# CUMA 1.080.0 - HOTFIXES REAPLICADOS + SISTEMA DE VERSÕES
# =============================================================================
# Este bloco é propositalmente instalado depois dos patches V9/V10/V11.
# A V11 permanece como base visual/tradução, e este bloco corrige estabilidade,
# saída separada do Converter, versionamento e conversões de PDF com menor RAM.

CUMA_VERSION_BASE = '1.080.0'
CUMA_VERSION_STATE_FILE = 'cuma_version_state.json'
CUMA_VERSION_HISTORY_FILE = 'cuma_version_history.json'
CUMA_VERSION_SCHEMA = {
    'grande': {
        'aliases': ('grande', 'major', 'full', 'full_rebuild'),
        'descricao': 'Atualização grande: incrementa o primeiro número e zera os demais.',
    },
    'media': {
        'aliases': ('media', 'média', 'medium', 'feature', 'recovery_partial'),
        'descricao': 'Atualização média: soma 10 no bloco central e zera correções.',
    },
    'pequena': {
        'aliases': ('pequena', 'small', 'minor', 'half_patch'),
        'descricao': 'Atualização pequena: soma 1 no bloco central e zera correções.',
    },
    'pouca': {
        'aliases': ('pouca', 'patch', 'hotfix', 'fix', 'correcao', 'correção'),
        'descricao': 'Atualização pontual/hotfix: soma 1 no terceiro número.',
    },
}


def _cuma_hotfix_log(context: str, exc: Exception | None = None) -> None:
    try:
        if exc is None:
            write_log(f'[CUMA 1.080.0] {context}')
        else:
            write_log(f'[CUMA 1.080.0] {context}: {exc}')
            try:
                write_error_log(type(exc), exc, exc.__traceback__, context)
            except Exception:
                pass
    except Exception:
        pass


def _cuma_resolve_app_path(raw: str | Path | None, default_relative: str) -> Path:
    try:
        text_value = str(raw or '').strip()
        p = Path(text_value).expanduser() if text_value else (runtime_dir() / default_relative)
        if not p.is_absolute():
            p = runtime_dir() / p
        return p
    except Exception:
        return runtime_dir() / default_relative


def _cuma_var_get_safe(var, default=''):
    try:
        return var.get()
    except Exception:
        return default


def _cuma_var_set_safe(var, value) -> None:
    try:
        var.set(value)
    except Exception:
        pass


def cuma_version_normalize_scale(scale: str) -> str:
    raw = str(scale or '').strip().lower()
    for canonical, meta in CUMA_VERSION_SCHEMA.items():
        if raw == canonical or raw in meta.get('aliases', ()):
            return canonical
    return 'pouca'


def cuma_version_parse(version: str) -> tuple[int, int, int]:
    parts = [int(x) for x in re.findall(r'\d+', str(version or CUMA_VERSION_BASE))[:3]]
    while len(parts) < 3:
        parts.append(0)
    return max(0, parts[0]), max(0, parts[1]), max(0, parts[2])


def cuma_version_format(major: int, middle: int, patch: int) -> str:
    return f'{int(major)}.{int(middle):03d}.{int(patch)}'


def cuma_version_bump(version: str, scale: str = 'pouca') -> str:
    major, middle, patch = cuma_version_parse(version)
    scale = cuma_version_normalize_scale(scale)
    if scale == 'grande':
        return cuma_version_format(major + 1, 0, 0)
    if scale == 'media':
        return cuma_version_format(major, middle + 10, 0)
    if scale == 'pequena':
        return cuma_version_format(major, middle + 1, 0)
    return cuma_version_format(major, middle, patch + 1)


def cuma_version_load_state() -> dict:
    path = runtime_dir() / CUMA_VERSION_STATE_FILE
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        _cuma_hotfix_log('Falha ao ler estado de versão', exc)
    return {
        'current_version': CUMA_VERSION_BASE,
        'base_version': CUMA_VERSION_BASE,
        'schema': CUMA_VERSION_SCHEMA,
        'events': [],
    }


def cuma_version_save_state(state: dict) -> None:
    state.setdefault('current_version', CUMA_VERSION_BASE)
    state.setdefault('base_version', CUMA_VERSION_BASE)
    state['schema'] = CUMA_VERSION_SCHEMA
    try:
        target = runtime_dir() / CUMA_VERSION_STATE_FILE
        payload = json.dumps(state, ensure_ascii=False, indent=2, default=str)
        try:
            if target.exists() and target.read_text(encoding='utf-8') == payload:
                return
        except Exception:
            pass
        target.write_text(payload, encoding='utf-8')
    except Exception as exc:
        _cuma_hotfix_log('Falha ao salvar estado de versão', exc)


def _cuma_version_write_public_files(state: dict) -> None:
    version = str(state.get('current_version') or CUMA_VERSION_BASE)
    events = list(state.get('events', [])) if isinstance(state.get('events', []), list) else []
    latest_event = next((e for e in reversed(events) if isinstance(e, dict) and str(e.get('version', '')) == version), None)
    updated_at = str((latest_event or {}).get('timestamp', '')).split('T')[0] or '2026-06-22'
    try:
        version_payload = {
            'name': APP_DISPLAY_NAME if 'APP_DISPLAY_NAME' in globals() else 'CUMA - Conversor Ultimate de Mangás',
            'version': version,
            'base_version': CUMA_VERSION_BASE,
            'build': 'release_stability_manual_debug_1_081_1' if version == '1.081.1' else 'base_1_080_0_hotfixes_v11_merged',
            'notes': 'Release consolidado: V11, hotfixes reaplicados, temas 1.081.0, manual completo, relatórios condensados e melhorias de estabilidade.' if version == '1.081.1' else 'V11 de tradução/interface com hotfixes reaplicados e sistema de versionamento sistemático.',
            'versioning': {
                'grande': 'incrementa o primeiro número: 1.080.0 -> 2.000.0',
                'media': 'soma 10 no bloco central: 1.080.0 -> 1.090.0',
                'pequena': 'soma 1 no bloco central: 1.080.0 -> 1.081.0',
                'pouca': 'soma 1 no terceiro número: 1.080.0 -> 1.080.1',
            },
            'updated_at': updated_at,
        }
        target = runtime_dir() / 'version.json'
        payload = json.dumps(version_payload, ensure_ascii=False, indent=2)
        try:
            if target.exists() and target.read_text(encoding='utf-8') == payload:
                pass
            else:
                target.write_text(payload, encoding='utf-8')
        except Exception:
            target.write_text(payload, encoding='utf-8')
    except Exception as exc:
        _cuma_hotfix_log('Falha ao atualizar version.json', exc)
    try:
        # Histórico público enxuto, deduplicado por update_id.
        public = {'base_version': CUMA_VERSION_BASE, 'current_version': version, 'events': events[-80:]}
        target = runtime_dir() / CUMA_VERSION_HISTORY_FILE
        payload = json.dumps(public, ensure_ascii=False, indent=2, default=str)
        try:
            if target.exists() and target.read_text(encoding='utf-8') == payload:
                return
        except Exception:
            pass
        target.write_text(payload, encoding='utf-8')
    except Exception as exc:
        _cuma_hotfix_log('Falha ao atualizar histórico de versão', exc)


def cuma_version_apply_globals(version: str) -> None:
    globals()['APP_DISPLAY_VERSION'] = version
    globals()['APP_VERSION'] = f'{version} CUMA'
    globals()['APP_NAME'] = 'CUMA'
    globals()['CUMA_CONVERTER_DEVICE_UPDATE_VERSION'] = version
    try:
        if isinstance(CHANGELOG_LATEST, dict):
            CHANGELOG_LATEST['version'] = version
            CHANGELOG_LATEST['date'] = datetime.now().date().isoformat()
            items = CHANGELOG_LATEST.setdefault('items', [])
            marker = 'Sistema de versões 1.080.0 com hotfixes reaplicados à V11.'
            if marker not in items:
                items.insert(0, marker)
    except Exception:
        pass


def cuma_register_code_update(update_id: str, scale: str = 'pouca', description: str = '', apply_increment: bool = True) -> str:
    # Registra atualização de código sem duplicar eventos a cada abertura.
    # Escalas:
    # - grande: 1.080.0 -> 2.000.0
    # - media/média: 1.080.0 -> 1.090.0
    # - pequena: 1.080.0 -> 1.081.0
    # - pouca/hotfix: 1.080.0 -> 1.080.1
    state = cuma_version_load_state()
    events = state.get('events', [])
    if not isinstance(events, list):
        events = []
    existing_ids = {str(e.get('update_id')) for e in events if isinstance(e, dict)}
    current = str(state.get('current_version') or CUMA_VERSION_BASE)
    normalized = cuma_version_normalize_scale(scale)
    if update_id and str(update_id) in existing_ids:
        cuma_version_apply_globals(current)
        _cuma_version_write_public_files(state)
        return current
    next_version = cuma_version_bump(current, normalized) if apply_increment else CUMA_VERSION_BASE
    event = {
        'update_id': str(update_id or f'update_{len(events)+1}'),
        'version': next_version,
        'base_version': CUMA_VERSION_BASE,
        'scale': normalized,
        'description': description,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
    }
    events.append(event)
    state['events'] = events[-80:]
    state['current_version'] = next_version
    state['base_version'] = CUMA_VERSION_BASE
    cuma_version_save_state(state)
    _cuma_version_write_public_files(state)
    cuma_version_apply_globals(next_version)
    return next_version


def cuma_initialize_version_system() -> str:
    state = cuma_version_load_state()
    # Esta versão é o novo marco zero solicitado pelo usuário; não incrementa sozinha.
    if not state.get('events'):
        state['current_version'] = CUMA_VERSION_BASE
        state['base_version'] = CUMA_VERSION_BASE
        state['events'] = [{
            'update_id': 'base_1_080_0',
            'version': CUMA_VERSION_BASE,
            'base_version': CUMA_VERSION_BASE,
            'scale': 'base',
            'description': 'Marco base definido pelo usuário após V11 e reaplicação dos hotfixes.',
            'timestamp': datetime.now().isoformat(timespec='seconds'),
        }]
        cuma_version_save_state(state)
    else:
        state['current_version'] = str(state.get('current_version') or CUMA_VERSION_BASE)
        state['base_version'] = CUMA_VERSION_BASE
        cuma_version_save_state(state)
    _cuma_version_write_public_files(state)
    cuma_version_apply_globals(str(state.get('current_version') or CUMA_VERSION_BASE))
    return str(state.get('current_version') or CUMA_VERSION_BASE)


def cuma_version_debug_snapshot() -> dict:
    state = cuma_version_load_state()
    return {
        'current_version': str(state.get('current_version') or CUMA_VERSION_BASE),
        'base_version': CUMA_VERSION_BASE,
        'schema': CUMA_VERSION_SCHEMA,
        'events_count': len(state.get('events', [])) if isinstance(state.get('events', []), list) else 0,
        'state_file': str(runtime_dir() / CUMA_VERSION_STATE_FILE),
        'history_file': str(runtime_dir() / CUMA_VERSION_HISTORY_FILE),
    }


def _cuma_config_get_xteink_output(cfg) -> str:
    try:
        return str(getattr(cfg, 'xteink_output_dir', '') or '')
    except Exception:
        return ''


def _cuma_converter_output_dir_hotfix(self, preferred: str = '') -> Path:
    clean_raw = str(_cuma_var_get_safe(getattr(self, 'output_dir', None), '') or '').strip()
    cfg_raw = _cuma_config_get_xteink_output(getattr(self, 'cfg', None))
    current_raw = str(_cuma_var_get_safe(getattr(self, 'xteink_output_dir', None), '') or '').strip()
    raw = str(preferred or '').strip()
    if not raw:
        # Na V11, build_xteink_tab inicializava xteink_output_dir com output_dir.
        # Se os dois estão iguais, prioriza o valor separado salvo em cfg.xteink_output_dir.
        if cfg_raw and (not current_raw or current_raw == clean_raw):
            raw = cfg_raw
        else:
            raw = current_raw or cfg_raw
    p = _cuma_resolve_app_path(raw, 'limpos/Converter')
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cuma_sync_converter_model_hotfix(self, preferred_output: str = '') -> Path:
    if not hasattr(self, 'xteink_device'):
        self.xteink_device = tk.StringVar(value='XTEINK X4')
    if not hasattr(self, 'xteink_quality'):
        self.xteink_quality = tk.IntVar(value=100)
    try:
        self.xteink_quality.set(100)
    except Exception:
        pass
    out_dir = _cuma_converter_output_dir_hotfix(self, preferred_output)
    if not hasattr(self, 'xteink_output_dir'):
        self.xteink_output_dir = tk.StringVar(value=str(out_dir))
    else:
        _cuma_var_set_safe(self.xteink_output_dir, str(out_dir))
    try:
        self.cfg.xteink_output_dir = str(out_dir)
    except Exception:
        pass
    # Importante: nunca tocar self.output_dir nem self.cfg.output_dir aqui.
    return out_dir


def _cuma_choose_xteink_output_hotfix(self) -> None:
    try:
        folder = filedialog.askdirectory(title='Escolher pasta de saída do Converter')
        if folder:
            _cuma_sync_converter_model_hotfix(self, folder)
            try:
                self.save_current_config(force=True)
            except TypeError:
                self.save_current_config()
    except Exception as exc:
        _cuma_hotfix_log('Escolha de pasta do Converter', exc)
        messagebox.showerror('Pasta de saída', friendly_error(exc))


def _cuma_xteink_paths_hotfix(self) -> tuple[Path, Path, tuple[int, int], int]:
    src = Path(str(_cuma_var_get_safe(getattr(self, 'xteink_input', None), '')).strip())
    if not src.exists():
        raise RuntimeError('Arquivo XTEINK não encontrado.')
    out_dir = _cuma_sync_converter_model_hotfix(self)
    return src, out_dir, self.xteink_target(), 100


def iter_pdf_pages_as_images(pdf_path: Path, target: Optional[tuple[int, int]] = None, quality_zoom: float = 2.0):
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            if target:
                zoom = max(target[0] / max(page.rect.width, 1), target[1] / max(page.rect.height, 1)) * 1.25
            else:
                zoom = quality_zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            try:
                fitted = fit_to_target(im, target)
                if fitted is im:
                    yield im
                    im = None
                else:
                    yield fitted
            finally:
                try:
                    if im is not None:
                        im.close()
                except Exception:
                    pass
    finally:
        doc.close()


def create_image_epub_from_pdf(pdf_path: Path, output_epub: Path, title: str, target: Optional[tuple[int, int]] = None, quality: int = 88) -> None:
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    uid = str(uuid.uuid4())
    manifest = []
    spine = []
    nav = []
    with zipfile.ZipFile(output_epub, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
        count = 0
        for count, im in enumerate(iter_pdf_pages_as_images(pdf_path, target=target), 1):
            try:
                img_name = f'images/page_{count:04d}.jpg'
                html_name = f'page_{count:04d}.xhtml'
                bio = BytesIO()
                im.save(bio, format='JPEG', quality=int(quality or 88), optimize=True)
                z.writestr('OEBPS/' + img_name, bio.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
                z.writestr('OEBPS/' + html_name, f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Página {count}</title><style>html,body{{margin:0;padding:0;background:white;}} img{{width:100%;height:100%;object-fit:contain;display:block;}}</style></head><body><img src="{img_name}" alt="Página {count}"/></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
                manifest.append(f'<item id="p{count}" href="{html_name}" media-type="application/xhtml+xml"/>')
                manifest.append(f'<item id="img{count}" href="{img_name}" media-type="image/jpeg"/>')
                spine.append(f'<itemref idref="p{count}"/>')
                nav.append(f'<li><a href="{html_name}">Página {count}</a></li>')
            finally:
                try:
                    im.close()
                except Exception:
                    pass
        if count <= 0:
            raise RuntimeError('Nenhuma imagem para criar EPUB.')
        z.writestr('OEBPS/nav.xhtml', f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Sumário</title></head><body><nav epub:type="toc"><ol>{''.join(nav)}</ol></nav></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/content.opf', f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:language>pt-BR</dc:language></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>''', compress_type=zipfile.ZIP_DEFLATED)


def create_xtch_from_pdf(pdf_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    output_xtch.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        page_count = len(doc)
    finally:
        doc.close()
    if page_count <= 0:
        raise RuntimeError('Nenhuma imagem para criar XTCH.')
    if page_count > 65535:
        raise RuntimeError('XTCH suporta no máximo 65535 páginas por arquivo.')
    header_size = 56
    table_offset = header_size
    data_offset = header_size + page_count * 16
    w, h = target
    header = struct.pack('<IBBHBBBBIQQQQII', 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0)
    table_rows = []
    with output_xtch.open('wb') as f:
        f.write(header)
        f.write(b'\x00' * (page_count * 16))
        for im in iter_pdf_pages_as_images(pdf_path, target=target):
            try:
                blob = xth_page_bytes(im, target)
                off = f.tell()
                f.write(blob)
                table_rows.append((off, len(blob), w, h))
            finally:
                try:
                    im.close()
                except Exception:
                    pass
        f.seek(table_offset)
        for off, size, tw, th in table_rows:
            f.write(struct.pack('<QIHH', off, size, tw, th))


def _cuma_run_xteink_job_hotfix(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    suffix = src.suffix.lower()
    if suffix == '.pdf' and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            create_image_epub_from_pdf(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            create_xtch_from_pdf(src, out, src.stem, target)
            outputs.append(out)
    elif suffix == '.epub' and flags.get('epub_xtch'):
        images = extract_epub_images(src, target)
        out = unique_path(out_dir / f'{src.stem}.xtch')
        try:
            create_xtch_from_images(images, out, src.stem, target)
        finally:
            for im in images:
                try:
                    im.close()
                except Exception:
                    pass
        outputs.append(out)
    else:
        raise RuntimeError('Formato/combinação de conversão não suportado para este arquivo.')
    return outputs


def _cuma_xteink_pdf_to_epub_hotfix(self) -> Path:
    src, out_dir, target, quality = _cuma_xteink_paths_hotfix(self)
    if src.suffix.lower() != '.pdf':
        raise RuntimeError('Selecione um PDF.')
    output = unique_path(out_dir / f'{src.stem}_xteink.epub')
    create_image_epub_from_pdf(src, output, src.stem, target=target, quality=quality)
    self._xteink_last_out_dir = out_dir
    if not getattr(self, '_xteink_batch_mode', False) and self.open_after.get():
        open_folder(output)
    return output


def _cuma_xteink_pdf_to_xtch_hotfix(self) -> Path:
    src, out_dir, target, _quality = _cuma_xteink_paths_hotfix(self)
    if src.suffix.lower() != '.pdf':
        raise RuntimeError('Selecione um PDF.')
    output = unique_path(out_dir / f'{src.stem}.xtch')
    create_xtch_from_pdf(src, output, src.stem, target)
    self._xteink_last_out_dir = out_dir
    if not getattr(self, '_xteink_batch_mode', False) and self.open_after.get():
        open_folder(output)
    return output


_CUMA_1080_RUNTIME = {
    'setup_vars': App.setup_vars,
    'setup_window': App.setup_window,
    'save_current_config': App.save_current_config,
    'build_about_tab': getattr(App, 'build_about_tab', None),
}


def _cuma_setup_vars_1080(self):
    _CUMA_1080_RUNTIME['setup_vars'](self)
    try:
        clean_dir = _cuma_resolve_app_path(_cuma_var_get_safe(getattr(self, 'output_dir', None), ''), 'limpos')
        _cuma_var_set_safe(self.output_dir, str(clean_dir))
        conv = _cuma_resolve_app_path(_cuma_config_get_xteink_output(getattr(self, 'cfg', None)), 'limpos/Converter')
        if hasattr(self, 'xteink_output_dir'):
            _cuma_var_set_safe(self.xteink_output_dir, str(conv))
        else:
            self.xteink_output_dir = tk.StringVar(value=str(conv))
        try:
            self.cfg.output_dir = str(clean_dir)
            self.cfg.xteink_output_dir = str(conv)
        except Exception:
            pass
    except Exception as exc:
        _cuma_hotfix_log('setup_vars 1.080.0', exc)


def _cuma_setup_window_1080(self):
    result = _CUMA_1080_RUNTIME['setup_window'](self)
    try:
        # Fallback para Linux/macOS quando .ico não é aceito pelo Tk.
        if not sys.platform.startswith('win'):
            logo = resource_path('cuma_logo.png')
            if logo.exists():
                img = tk.PhotoImage(file=str(logo))
                self.root.iconphoto(True, img)
                self._cuma_iconphoto_ref = img
    except Exception as exc:
        _cuma_hotfix_log('Fallback de ícone', exc)
    try:
        self.root.title(f'{APP_DISPLAY_NAME} {APP_DISPLAY_VERSION}')
    except Exception:
        pass
    return result


def _cuma_save_current_config_1080(self, force: bool = False) -> None:
    clean_before = str(_cuma_var_get_safe(getattr(self, 'output_dir', None), '') or '').strip()
    conv_before = str(_cuma_var_get_safe(getattr(self, 'xteink_output_dir', None), '') or '').strip()
    try:
        _CUMA_1080_RUNTIME['save_current_config'](self, force)
    except TypeError:
        _CUMA_1080_RUNTIME['save_current_config'](self)
    except Exception as exc:
        _cuma_hotfix_log('save_current_config legado', exc)
        if force:
            raise
    try:
        clean_path = _cuma_resolve_app_path(clean_before or getattr(self.cfg, 'output_dir', ''), 'limpos')
        conv_path = _cuma_resolve_app_path(conv_before or _cuma_config_get_xteink_output(self.cfg), 'limpos/Converter')
        if hasattr(self, 'output_dir'):
            _cuma_var_set_safe(self.output_dir, str(clean_path))
        if hasattr(self, 'xteink_output_dir'):
            _cuma_var_set_safe(self.xteink_output_dir, str(conv_path))
        self.cfg.output_dir = str(clean_path)
        self.cfg.xteink_output_dir = str(conv_path)
        save_config(self.cfg)
    except Exception as exc:
        _cuma_hotfix_log('Persistência separada Limpar/Converter', exc)
        if force:
            raise


def _cuma_build_about_tab_1080(self):
    old = _CUMA_1080_RUNTIME.get('build_about_tab')
    if old is not None:
        old(self)
    try:
        lang = _cuma_v11_language(self) if '_cuma_v11_language' in globals() else 'pt_BR'
        wrap = self.tab_about.winfo_children()[0] if self.tab_about.winfo_children() else self.tab_about
        box = ttk.LabelFrame(wrap, text=_cuma_v11_tr('Sistema de versões', lang) if '_cuma_v11_tr' in globals() else 'Sistema de versões', padding=12, style='Card.TLabelframe')
        box.pack(fill='x', pady=(12, 0))
        snapshot = cuma_version_debug_snapshot()
        ttk.Label(box, text=f"Versão atual: {snapshot['current_version']} | Base: {snapshot['base_version']}", style='Muted.TLabel').pack(anchor='w')
        ttk.Label(box, text='Escalas: grande = 2.000.0; média = +10 no bloco central; pequena = +1 no bloco central; pouca/hotfix = +1 no terceiro número.', style='Muted.TLabel', wraplength=1020, justify='left').pack(anchor='w', pady=(4, 0))
        ttk.Label(box, text=f"Eventos registrados: {snapshot['events_count']}", style='Muted.TLabel').pack(anchor='w', pady=(4, 0))
    except Exception as exc:
        _cuma_hotfix_log('Seção de versão no Sobre', exc)



def _cuma_1080_extend_translations() -> None:
    try:
        extra_en = {
            'Adicionar PDF(s)': 'Add PDF(s)',
            'Adicionar arquivo(s)': 'Add file(s)',
            'Adicionar pasta': 'Add folder',
            'Arquivo': 'File',
            'Arquivos': 'Files',
            'Arquivos: 0': 'Files: 0',
            '0 arquivo(s)': '0 file(s)',
            'Saída': 'Output',
            'Limpar cache ao sair': 'Clear cache on exit',
            'Arraste arquivos ou pastas aqui — Extrair páginas': 'Drag files or folders here — Extract pages',
            'Arraste arquivos ou pastas aqui — Criar PDF de imagens': 'Drag files or folders here — Create PDF from images',
            'Ferramentas 1.0.6.0.2 carregadas; seleção visual das abas corrigida.': 'Tools 1.0.6.0.2 loaded; tab visual selection fixed.',
            'Sistema de versões': 'Version system',
            'Versão atual': 'Current version',
            'Base': 'Base',
            'Eventos registrados': 'Registered events',
            'Escolher pasta de saída do Converter': 'Choose Converter output folder',
            'Pasta de saída do Converter': 'Converter output folder',
            'Abrir pasta Converter': 'Open Converter folder',
            'Dispositivos e conversões': 'Devices and conversions',
            'Qualidade do arquivo (%)': 'File quality (%)',
            'Editor de perfis': 'Profile editor',
            'Aplicar perfil': 'Apply profile',
        }
        if 'V10_UI_I18N' in globals():
            V10_UI_I18N.setdefault('en_US', {}).update(extra_en)
        if 'V8_UI_I18N' in globals():
            V8_UI_I18N.setdefault('en_US', {}).update(extra_en)
    except Exception as exc:
        _cuma_hotfix_log('Extensão de traduções 1.080.0', exc)




# =============================================================================
# CUMA 1.081.3 - ARMAZENAMENTO LIMPO E CONFIGURAÇÕES CONSOLIDADAS
# =============================================================================
# Este bloco prepara a versão de lançamento para uma pasta mais limpa:
# - dados graváveis do usuário em uma pasta própria;
# - configurações consolidadas em um único cuma_settings.json;
# - migração automática dos JSONs antigos;
# - logs/erros fora da pasta do executável quando compilado;
# - versionamento público salvo dentro do arquivo consolidado.

CUMA_SETTINGS_FILE = 'cuma_settings.json'
CUMA_SETTINGS_TEMPLATE_FILE = 'cuma_settings_template.json'
CUMA_1081_2_UPDATE_ID = 'storage_consolidation_user_data_1081_2'
CUMA_LEGACY_JSON_FILES = (
    'config_cuma.json',
    'cuma_interface_colors.json',
    'cuma_device_profiles.json',
    'version.json',
    'cuma_version_state.json',
    'cuma_version_history.json',
)
_CUMA_SETTINGS_CACHE = None


def _cuma_json_clone(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return value


def _cuma_deep_merge(base, extra):
    result = dict(base or {})
    if not isinstance(extra, dict):
        return result
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _cuma_deep_merge(result.get(key), value)
        else:
            result[key] = value
    return result


def cuma_user_data_dir() -> Path:
    forced = os.environ.get('CUMA_USER_DATA_DIR', '').strip()
    if forced:
        root = Path(forced).expanduser()
    elif getattr(sys, 'frozen', False):
        if sys.platform.startswith('win'):
            base = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Roaming')
            root = Path(base) / 'CUMA'
        elif sys.platform == 'darwin':
            root = Path.home() / 'Library' / 'Application Support' / 'CUMA'
        else:
            base = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
            root = Path(base) / 'CUMA'
    else:
        root = app_dir() / '.cuma_user_data'
    try:
        root.mkdir(parents=True, exist_ok=True)
    except Exception:
        try:
            fallback = Path.cwd() / '.cuma_user_data'
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
        except Exception:
            return app_dir()
    return root


def cuma_settings_path() -> Path:
    return cuma_user_data_dir() / CUMA_SETTINGS_FILE


def _cuma_settings_template_candidates() -> list[Path]:
    candidates = []
    for candidate in (
        resource_path(CUMA_SETTINGS_TEMPLATE_FILE),
        app_dir() / '_internal' / CUMA_SETTINGS_TEMPLATE_FILE,
        app_dir() / CUMA_SETTINGS_TEMPLATE_FILE,
        Path(__file__).resolve().parent / CUMA_SETTINGS_TEMPLATE_FILE if '__file__' in globals() else app_dir() / CUMA_SETTINGS_TEMPLATE_FILE,
    ):
        try:
            if candidate not in candidates:
                candidates.append(candidate)
        except Exception:
            candidates.append(candidate)
    return candidates


def _cuma_load_json_path(path: Path):
    try:
        if path and path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            return data
    except Exception:
        return None
    return None


def _cuma_load_first_legacy_json(name: str):
    candidates = [
        cuma_user_data_dir() / name,
        app_dir() / name,
        app_dir() / '_internal' / name,
        resource_path(name),
        Path(__file__).resolve().parent / name if '__file__' in globals() else app_dir() / name,
    ]
    seen = set()
    for path in candidates:
        try:
            key = str(Path(path).resolve())
            if key in seen:
                continue
            seen.add(key)
        except Exception:
            pass
        data = _cuma_load_json_path(Path(path))
        if data is not None:
            return data
    return None


def _cuma_default_interface_settings() -> dict:
    try:
        accent = THEME_VISUAL_PRESETS.get('Moderno Escuro', {}).get('accent', '#3B82F6')
    except Exception:
        accent = '#3B82F6'
    return {
        'theme_name': 'Moderno Escuro',
        'roles': {},
        'theme_mode': 'Automático',
        'custom_base': 'Escuro',
        'custom_accent': accent,
        'app_language': 'system',
    }


def _cuma_default_device_profiles_settings() -> dict:
    try:
        if isinstance(DEFAULT_DEVICE_PROFILE_CATALOG, dict) and DEFAULT_DEVICE_PROFILE_CATALOG:
            return {str(k): dict(v) for k, v in DEFAULT_DEVICE_PROFILE_CATALOG.items()}
    except Exception:
        pass
    return {
        'XTEINK X4': {'width': 480, 'height': 800, 'dpi': 212, 'jpeg_quality': 100},
        'XTEINK X3': {'width': 528, 'height': 792, 'dpi': 212, 'jpeg_quality': 100},
        'Personalizado': {'width': 600, 'height': 800, 'dpi': 200, 'jpeg_quality': 100},
    }


def _cuma_default_version_payload(version: str = '') -> dict:
    current = version or globals().get('APP_DISPLAY_VERSION') or CUMA_VERSION_BASE
    return {
        'name': globals().get('APP_DISPLAY_NAME', 'CUMA - Conversor Ultimate de Mangás'),
        'version': current,
        'base_version': CUMA_VERSION_BASE,
        'build': 'storage_consolidation_1_081_2',
        'notes': 'Release com configurações consolidadas, dados do usuário fora da pasta do executável e pacote mais limpo.',
        'versioning': {
            'grande': 'incrementa o primeiro número: 1.080.0 -> 2.000.0',
            'media': 'soma 10 no bloco central: 1.080.0 -> 1.090.0',
            'pequena': 'soma 1 no bloco central: 1.080.0 -> 1.081.0',
            'pouca': 'soma 1 no terceiro número: 1.080.0 -> 1.080.1',
        },
        'updated_at': datetime.now().date().isoformat(),
    }


def _cuma_default_settings_payload() -> dict:
    cfg = {}
    try:
        cfg = asdict(CleanerConfig())
    except Exception:
        cfg = {}
    state = {
        'current_version': globals().get('APP_DISPLAY_VERSION', CUMA_VERSION_BASE),
        'base_version': CUMA_VERSION_BASE,
        'schema': CUMA_VERSION_SCHEMA,
        'events': [],
    }
    return {
        'format': 'CUMA_SETTINGS',
        'schema_version': 1,
        'created_by': 'CUMA',
        'storage': {
            'mode': 'single_user_settings_file',
            'user_data_dir': str(cuma_user_data_dir()),
            'manual_visible_next_to_exe': True,
        },
        'config': cfg,
        'interface_colors': _cuma_default_interface_settings(),
        'device_profiles': _cuma_default_device_profiles_settings(),
        'version_state': state,
        'version_history': {
            'base_version': CUMA_VERSION_BASE,
            'current_version': state['current_version'],
            'events': [],
        },
        'version': _cuma_default_version_payload(state['current_version']),
        'runtime': {},
    }


def _cuma_load_template_settings() -> dict:
    for candidate in _cuma_settings_template_candidates():
        data = _cuma_load_json_path(candidate)
        if isinstance(data, dict):
            return data
    return {}


def _cuma_migrate_legacy_sections(payload: dict) -> dict:
    migrated = dict(payload or {})
    legacy_map = {
        'config': CONFIG_FILE,
        'interface_colors': INTERFACE_COLOR_FILE,
        'device_profiles': 'cuma_device_profiles.json',
        'version': 'version.json',
        'version_state': CUMA_VERSION_STATE_FILE,
        'version_history': CUMA_VERSION_HISTORY_FILE,
    }
    for section, filename in legacy_map.items():
        legacy = _cuma_load_first_legacy_json(filename)
        if isinstance(legacy, dict):
            current = migrated.get(section)
            if isinstance(current, dict):
                migrated[section] = _cuma_deep_merge(current, legacy)
            else:
                migrated[section] = legacy
    migrated.setdefault('format', 'CUMA_SETTINGS')
    migrated.setdefault('schema_version', 1)
    migrated.setdefault('storage', {})
    migrated['storage']['user_data_dir'] = str(cuma_user_data_dir())
    migrated['storage']['manual_visible_next_to_exe'] = True
    return migrated


def cuma_settings_load(force: bool = False) -> dict:
    global _CUMA_SETTINGS_CACHE
    if _CUMA_SETTINGS_CACHE is not None and not force:
        return _cuma_json_clone(_CUMA_SETTINGS_CACHE)
    default = _cuma_default_settings_payload()
    path = cuma_settings_path()
    data = _cuma_load_json_path(path)
    if isinstance(data, dict):
        payload = _cuma_deep_merge(default, data)
    else:
        try:
            if path.exists():
                backup = path.with_name(path.stem + '_corrompido_' + datetime.now().strftime('%Y%m%d_%H%M%S') + path.suffix)
                shutil.copy2(path, backup)
        except Exception:
            pass
        template = _cuma_load_template_settings()
        payload = _cuma_deep_merge(default, template if isinstance(template, dict) else {})
        payload = _cuma_migrate_legacy_sections(payload)
        try:
            cuma_settings_save(payload)
        except Exception:
            pass
    _CUMA_SETTINGS_CACHE = _cuma_json_clone(payload)
    return payload


def cuma_settings_save(payload: dict) -> None:
    global _CUMA_SETTINGS_CACHE
    data = _cuma_deep_merge(_cuma_default_settings_payload(), payload if isinstance(payload, dict) else {})
    data.setdefault('format', 'CUMA_SETTINGS')
    data.setdefault('schema_version', 1)
    data.setdefault('storage', {})
    data['storage']['user_data_dir'] = str(cuma_user_data_dir())
    path = cuma_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    try:
        if path.exists() and path.read_text(encoding='utf-8') == raw:
            _CUMA_SETTINGS_CACHE = _cuma_json_clone(data)
            return
    except Exception:
        pass
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(raw, encoding='utf-8')
    os.replace(str(tmp), str(path))
    _CUMA_SETTINGS_CACHE = _cuma_json_clone(data)


def cuma_settings_section(section: str, default=None):
    data = cuma_settings_load()
    value = data.get(section)
    if value is None:
        return _cuma_json_clone(default)
    return _cuma_json_clone(value)


def cuma_settings_set_section(section: str, value) -> None:
    data = cuma_settings_load()
    data[section] = _cuma_json_clone(value)
    cuma_settings_save(data)


def log_path() -> Path:
    return cuma_user_data_dir() / LOG_FILE


def error_log_path() -> Path:
    return cuma_user_data_dir() / ERROR_FILE_NAME


def load_config() -> CleanerConfig:
    cfg = CleanerConfig()
    try:
        data = cuma_settings_section('config', {})
        if not isinstance(data, dict):
            data = {}
        # Mantém compatibilidade com usuários que ainda tenham config_cuma.json.
        legacy = _cuma_load_first_legacy_json(CONFIG_FILE)
        if isinstance(legacy, dict) and not (cuma_settings_path().exists() and data):
            data = _cuma_deep_merge(data, legacy)
        base = asdict(cfg)
        base.update({k: v for k, v in data.items() if k in base})
        return CleanerConfig(**base)
    except Exception as exc:
        write_log(f'Config consolidada inválida: {exc}')
        return cfg


def save_config(cfg: CleanerConfig) -> None:
    try:
        cuma_settings_set_section('config', asdict(cfg))
    except Exception as exc:
        write_log(f'Falha ao salvar configuração consolidada: {exc}')


def load_interface_colors_file() -> dict[str, object]:
    default = _cuma_default_interface_settings()
    try:
        data = cuma_settings_section('interface_colors', default)
        if not isinstance(data, dict):
            return default
        merged = _cuma_deep_merge(default, data)
        theme_name = merged.get('theme_name', default['theme_name'])
        if 'THEME_VISUAL_PRESETS' in globals() and theme_name not in THEME_VISUAL_PRESETS:
            theme_name = default['theme_name']
        roles_in = merged.get('roles', {})
        roles = roles_in if isinstance(roles_in, dict) else {}
        normalized_roles = {str(k): normalize_hex(v, '#FFFFFF') for k, v in roles.items()}
        theme_mode = merged.get('theme_mode', default['theme_mode'])
        if theme_mode not in THEME_SETTING_MODES:
            theme_mode = default['theme_mode']
        custom_base = merged.get('custom_base', default['custom_base'])
        if custom_base not in CUSTOM_THEME_BASES:
            custom_base = default['custom_base']
        try:
            accent_fallback = THEME_VISUAL_PRESETS.get(theme_name, THEME_VISUAL_PRESETS.get('Moderno Escuro', {})).get('accent', default['custom_accent'])
        except Exception:
            accent_fallback = default['custom_accent']
        return {
            'theme_name': theme_name,
            'roles': normalized_roles,
            'theme_mode': theme_mode,
            'custom_base': custom_base,
            'custom_accent': normalize_hex(merged.get('custom_accent', accent_fallback), accent_fallback),
            'app_language': str(merged.get('app_language', default.get('app_language', 'system')) or 'system'),
        }
    except Exception:
        return default


def save_interface_colors_file(theme_name: str, roles: dict[str, str], metadata: Optional[dict[str, object]] = None) -> None:
    try:
        current = load_interface_colors_file()
        safe_theme = theme_name if ('THEME_VISUAL_PRESETS' in globals() and theme_name in THEME_VISUAL_PRESETS) else current.get('theme_name', 'Moderno Escuro')
        safe_roles = {str(k): normalize_hex(v, '#FFFFFF') for k, v in (roles or {}).items()}
        payload = dict(current)
        payload.update({'theme_name': safe_theme, 'roles': safe_roles})
        if isinstance(metadata, dict):
            if metadata.get('theme_mode') in THEME_SETTING_MODES:
                payload['theme_mode'] = metadata.get('theme_mode')
            if metadata.get('custom_base') in CUSTOM_THEME_BASES:
                payload['custom_base'] = metadata.get('custom_base')
            if metadata.get('custom_accent') is not None:
                try:
                    fallback = THEME_VISUAL_PRESETS[safe_theme]['accent']
                except Exception:
                    fallback = '#3B82F6'
                payload['custom_accent'] = normalize_hex(str(metadata.get('custom_accent')), fallback)
            if metadata.get('app_language') is not None:
                payload['app_language'] = str(metadata.get('app_language') or 'system')
        cuma_settings_set_section('interface_colors', payload)
    except Exception as exc:
        write_log(f'Falha ao salvar cores/idioma no arquivo consolidado: {exc}')


def _cuma_save_app_language(lang: str) -> None:
    try:
        data = load_interface_colors_file()
        data['app_language'] = lang if lang in ('system', 'pt_BR', 'en_US', 'es_ES', 'fr_FR', 'de_DE', 'it_IT', 'ja_JP', 'ko_KR', 'zh_TW', 'tr_TR') else 'system'
        cuma_settings_set_section('interface_colors', data)
    except Exception as exc:
        write_log(f'Falha ao salvar idioma: {exc}')


def _cuma_v6_save_lang_code(code):
    try:
        data = load_interface_colors_file()
        data['app_language'] = code if code else 'system'
        cuma_settings_set_section('interface_colors', data)
    except Exception as exc:
        write_log(f'Falha ao salvar idioma V6: {exc}')


def _cuma_runtime_json(name: str, default):
    try:
        if name == 'cuma_device_profiles.json':
            return cuma_settings_section('device_profiles', default)
        runtime = cuma_settings_section('runtime', {})
        if isinstance(runtime, dict) and name in runtime:
            return _cuma_json_clone(runtime.get(name))
    except Exception:
        pass
    return default


def _cuma_write_runtime_json(name: str, data) -> None:
    try:
        if name == 'cuma_device_profiles.json':
            cuma_settings_set_section('device_profiles', data)
            return
        runtime = cuma_settings_section('runtime', {})
        if not isinstance(runtime, dict):
            runtime = {}
        runtime[name] = _cuma_json_clone(data)
        cuma_settings_set_section('runtime', runtime)
    except Exception as exc:
        try:
            write_log(f'Falha ao salvar {name} no arquivo consolidado: {exc}')
        except Exception:
            pass


def _cuma_device_profiles() -> dict:
    data = cuma_settings_section('device_profiles', {})
    if not isinstance(data, dict):
        data = {}
    defaults = _cuma_default_device_profiles_settings()
    for k, v in defaults.items():
        data.setdefault(k, dict(v))
    return data


def _cuma_save_all_device_profiles(data: dict) -> None:
    try:
        merged = _cuma_default_device_profiles_settings()
        if isinstance(data, dict):
            for k, v in data.items():
                merged[str(k)] = dict(v) if isinstance(v, dict) else v
        cuma_settings_set_section('device_profiles', merged)
    except Exception as exc:
        try:
            _cuma_final_log('Falha ao salvar catálogo de dispositivos no arquivo consolidado', exc)
        except Exception:
            write_log(f'Falha ao salvar catálogo de dispositivos: {exc}')


def _cuma_save_device_profile(device: str, profile: dict) -> None:
    data = _cuma_device_profiles()
    merged = dict(_cuma_default_device_profiles_settings().get('Personalizado', {}))
    if isinstance(profile, dict):
        merged.update(profile)
    data[str(device)] = merged
    _cuma_save_all_device_profiles(data)
    try:
        globals()['XTEINK_DEVICE_PROFILES'][str(device)] = (int(merged.get('width', 600)), int(merged.get('height', 800)))
        globals()['XTEINK_DEVICES'] = tuple(sorted(data.keys(), key=lambda x: (0 if x.startswith('XTEINK') else 1 if x.startswith('Kindle') else 2 if x.startswith('Kobo') else 3 if x.startswith('BOOX') else 4 if x.startswith('PocketBook') else 5 if x.startswith('Smartphone') else 9, x.lower())))
    except Exception:
        pass


def cuma_version_load_state() -> dict:
    try:
        state = cuma_settings_section('version_state', {})
        if isinstance(state, dict) and state:
            state.setdefault('current_version', CUMA_VERSION_BASE)
            state.setdefault('base_version', CUMA_VERSION_BASE)
            state.setdefault('schema', CUMA_VERSION_SCHEMA)
            state.setdefault('events', [])
            return state
    except Exception as exc:
        try:
            write_log(f'Falha ao ler estado de versão consolidado: {exc}')
        except Exception:
            pass
    return {
        'current_version': CUMA_VERSION_BASE,
        'base_version': CUMA_VERSION_BASE,
        'schema': CUMA_VERSION_SCHEMA,
        'events': [],
    }


def cuma_version_save_state(state: dict) -> None:
    try:
        if not isinstance(state, dict):
            state = {}
        state.setdefault('current_version', CUMA_VERSION_BASE)
        state.setdefault('base_version', CUMA_VERSION_BASE)
        state['schema'] = CUMA_VERSION_SCHEMA
        cuma_settings_set_section('version_state', state)
    except Exception as exc:
        try:
            write_log(f'Falha ao salvar estado de versão consolidado: {exc}')
        except Exception:
            pass


def _cuma_version_write_public_files(state: dict) -> None:
    version = str((state or {}).get('current_version') or CUMA_VERSION_BASE)
    events = list((state or {}).get('events', [])) if isinstance((state or {}).get('events', []), list) else []
    latest_event = next((e for e in reversed(events) if isinstance(e, dict) and str(e.get('version', '')) == version), None)
    updated_at = str((latest_event or {}).get('timestamp', '')).split('T')[0] or datetime.now().date().isoformat()
    version_payload = _cuma_default_version_payload(version)
    version_payload.update({
        'version': version,
        'updated_at': updated_at,
        'build': 'storage_consolidation_1_081_2' if version == '1.081.3' else version_payload.get('build', 'cuma_release'),
    })
    history_payload = {'base_version': CUMA_VERSION_BASE, 'current_version': version, 'events': events[-80:]}
    try:
        data = cuma_settings_load()
        data['version'] = version_payload
        data['version_history'] = history_payload
        data['version_state'] = state
        cuma_settings_save(data)
    except Exception as exc:
        try:
            write_log(f'Falha ao atualizar metadados consolidados: {exc}')
        except Exception:
            pass


def cuma_version_debug_snapshot() -> dict:
    state = cuma_version_load_state()
    return {
        'current_version': str(state.get('current_version') or CUMA_VERSION_BASE),
        'base_version': CUMA_VERSION_BASE,
        'schema': CUMA_VERSION_SCHEMA,
        'events_count': len(state.get('events', [])) if isinstance(state.get('events', []), list) else 0,
        'settings_file': str(cuma_settings_path()),
        'user_data_dir': str(cuma_user_data_dir()),
    }


def _cuma_update_manifest_url_from_settings() -> str:
    try:
        cfg = cuma_settings_section('config', {})
        if isinstance(cfg, dict):
            return str(cfg.get('update_manifest_url', '') or '').strip()
    except Exception:
        pass
    return ''


def _cuma_check_updates_button_async(self):
    if getattr(self, '_update_manifest_check_running', False):
        return
    self._update_manifest_check_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None:
            btn.configure(state='disabled')
    except Exception:
        pass

    def finish(kind: str, title: str, message: str) -> None:
        self._update_manifest_check_running = False
        try:
            if btn is not None:
                btn.configure(state='normal')
        except Exception:
            pass
        (messagebox.showerror if kind == 'error' else messagebox.showinfo)(title, _cuma_fix_mojibake_text(message) if '_cuma_fix_mojibake_text' in globals() else message)

    def worker():
        try:
            url = _cuma_update_manifest_url_from_settings()
            if not url:
                self.root.after(0, lambda: finish('info', 'Procurar atualizações', 'Nenhum repositório configurado. Defina update_manifest_url no arquivo cuma_settings.json, seção config.'))
                return
            import urllib.request
            with urllib.request.urlopen(url, timeout=8) as resp:
                remote = json.loads(resp.read().decode('utf-8'))
            latest = str(remote.get('version', ''))
            msg = f'Versão disponível: {latest}\nBaixe em: {remote.get("download_url", "sem link informado")}' if latest and latest != APP_DISPLAY_VERSION else 'Você já está usando a versão mais recente informada no repositório.'
            self.root.after(0, lambda: finish('info', 'Procurar atualizações', msg))
        except Exception as exc:
            try:
                _cuma_patch_log_exception('Verificação de atualizações', exc)
            except Exception:
                write_log(f'Verificação de atualizações: {exc}')
            self.root.after(0, lambda: finish('error', 'Procurar atualizações', friendly_error(exc)))

    threading.Thread(target=worker, daemon=True, name='CUMA-Update-Checker').start()


def write_full_debug_report() -> Path:
    path = cuma_user_data_dir() / 'debug_completo_cuma.txt'
    root = _cuma_default_output_root() if '_cuma_default_output_root' in globals() else app_dir() / 'limpos'
    payload = {
        'app': {
            'name': globals().get('APP_DISPLAY_NAME', 'CUMA'),
            'version': globals().get('APP_DISPLAY_VERSION', APP_VERSION),
            'install_dir': str(app_dir()),
            'user_data_dir': str(cuma_user_data_dir()),
            'settings_file': str(cuma_settings_path()),
            'frozen': bool(getattr(sys, 'frozen', False)),
        },
        'environment': environment_diagnostics() if 'environment_diagnostics' in globals() else {},
        'output': {
            'root': str(root),
            'limpar': str(root / 'Limpar'),
            'converter': str(root / 'Converter'),
            'ferramentas': str(root / 'Ferramentas'),
        },
        'settings_snapshot': cuma_settings_load(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return path


def _cuma_cleanup_legacy_runtime_files() -> None:
    # Remove arquivos antigos que agora ficam dentro do cuma_settings.json. A migração
    # acontece antes; a remoção é silenciosa para não atrapalhar pastas sem permissão.
    try:
        if not cuma_settings_path().exists():
            return
        for name in CUMA_LEGACY_JSON_FILES:
            for candidate in (app_dir() / name, cuma_user_data_dir() / name):
                try:
                    if candidate.exists() and candidate.resolve() != cuma_settings_path().resolve():
                        candidate.unlink()
                except Exception:
                    pass
        for old in ('debug_patch_mesclado.json', 'debug_patch_final_devices_languages.json', 'RELATORIO_RELEASE_1_081_1.txt'):
            try:
                p = app_dir() / old
                if p.exists():
                    p.unlink()
            except Exception:
                pass
    except Exception:
        pass


def _cuma_install_storage_core_1081_2() -> None:
    try:
        # Força criação/migração do arquivo único antes dos patches de versão.
        cuma_settings_load(force=True)
        globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_async
        try:
            _cuma_refresh_device_globals()
        except Exception:
            pass
        _cuma_cleanup_legacy_runtime_files()
    except Exception as exc:
        try:
            write_log(f'Instalação storage 1.081.3: {exc}')
        except Exception:
            pass


_cuma_install_storage_core_1081_2()


def _cuma_install_1080_hotfixes():
    try:
        _cuma_1080_extend_translations()
        globals()['APP_DISPLAY_VERSION'] = CUMA_VERSION_BASE
        globals()['APP_VERSION'] = f'{CUMA_VERSION_BASE} CUMA'
        globals()['APP_NAME'] = 'CUMA'
        globals()['_cuma_converter_output_dir'] = _cuma_converter_output_dir_hotfix
        globals()['_cuma_sync_converter_model'] = _cuma_sync_converter_model_hotfix
        globals()['_cuma_run_xteink_job'] = _cuma_run_xteink_job_hotfix
        App.setup_vars = _cuma_setup_vars_1080
        App.setup_window = _cuma_setup_window_1080
        App.save_current_config = _cuma_save_current_config_1080
        App.xteink_paths = _cuma_xteink_paths_hotfix
        App.choose_xteink_output = _cuma_choose_xteink_output_hotfix
        App.xteink_pdf_to_epub = _cuma_xteink_pdf_to_epub_hotfix
        App.xteink_pdf_to_xtch = _cuma_xteink_pdf_to_xtch_hotfix
        if _CUMA_1080_RUNTIME.get('build_about_tab') is not None:
            App.build_about_tab = _cuma_build_about_tab_1080
        version = cuma_initialize_version_system()
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_hotfix_log('Instalação dos hotfixes 1.080.0', exc)


_cuma_install_1080_hotfixes()




# =============================================================================
# CUMA 1.081.0 - TEMAS DO ÍCONE + HARMONIZAÇÃO VISUAL DA INTERFACE
# =============================================================================
# Este bloco fica depois dos hotfixes 1.080.0. Ele adiciona temas baseados no
# ícone do CUMA, mantém Automático como padrão visual e harmoniza sidebar, abas,
# caixas e scrollbars sem remover os patches V9/V10/V11.

CUMA_1081_UPDATE_ID = 'ui_icon_themes_sidebar_scrollbar_1081'

CUMA_ICON_THEME_PRESETS = {
    'CUMA Neon': {
        'accent': '#8B5CF6', 'accent_hover': '#7C3AED', 'secondary': '#38BDF8',
        'bg': '#050713', 'surface': '#121827', 'surface2': '#1B2240',
        'sidebar_bg': '#080B1A', 'sidebar_item': '#11172A', 'sidebar_item_active': '#231B4D',
        'field': '#0D1328', 'fg': '#F5F3FF', 'muted': '#B5B4D8', 'border': '#332B6B',
        'selection': '#4C1D95', 'drop': '#10142A', 'danger': '#FB7185',
        'scrollbar': '#252C4A', 'scrollbar_hover': '#3A446C', 'tab_bg': '#141A31',
        'tab_active': '#231B4D', 'hover': '#202747', 'kind': 'cuma-neon-violeta', 'is_light': False,
    },
    'CUMA Eclipse': {
        'accent': '#C026FF', 'accent_hover': '#A21CAF', 'secondary': '#60A5FA',
        'bg': '#000008', 'surface': '#0E1022', 'surface2': '#19132F',
        'sidebar_bg': '#070817', 'sidebar_item': '#111426', 'sidebar_item_active': '#2B1455',
        'field': '#090B1B', 'fg': '#F8F7FF', 'muted': '#A7A6C8', 'border': '#2D245D',
        'selection': '#3B0764', 'drop': '#101122', 'danger': '#F43F5E',
        'scrollbar': '#211B3A', 'scrollbar_hover': '#3B2A67', 'tab_bg': '#15142B',
        'tab_active': '#2B1455', 'hover': '#211A3D', 'kind': 'cuma-eclipse-roxo', 'is_light': False,
    },
    'CUMA Invertido': {
        'accent': '#6D28D9', 'accent_hover': '#5B21B6', 'secondary': '#2563EB',
        'bg': '#F6F2FF', 'surface': '#FFFFFF', 'surface2': '#EDE7FF',
        'sidebar_bg': '#E5DDFB', 'sidebar_item': '#F9F7FF', 'sidebar_item_active': '#DDD6FE',
        'field': '#FFFFFF', 'fg': '#1E1B4B', 'muted': '#6B638E', 'border': '#CEC3F2',
        'selection': '#DDD6FE', 'drop': '#F1ECFF', 'danger': '#DC2626',
        'scrollbar': '#CFC6EA', 'scrollbar_hover': '#B9A9E7', 'tab_bg': '#ECE6FF',
        'tab_active': '#DDD6FE', 'hover': '#E4DCFF', 'kind': 'cuma-invertido-claro', 'is_light': True,
    },
}


def _cuma_1081_unique_tuple(*values):
    out = []
    for value in values:
        if isinstance(value, (list, tuple)):
            for item in value:
                if item not in out:
                    out.append(item)
        elif value not in out:
            out.append(value)
    return tuple(out)


def _cuma_1081_hex_to_rgb(hx: str) -> tuple[int, int, int]:
    hx = normalize_hex(hx, '#000000').lstrip('#')
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))


def _cuma_1081_rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(v))) for v in rgb)


def _cuma_1081_blend(c1: str, c2: str, ratio: float = 0.5) -> str:
    try:
        r1, g1, b1 = _cuma_1081_hex_to_rgb(c1)
        r2, g2, b2 = _cuma_1081_hex_to_rgb(c2)
        ratio = max(0.0, min(1.0, float(ratio)))
        return _cuma_1081_rgb_to_hex((
            r1 * (1.0 - ratio) + r2 * ratio,
            g1 * (1.0 - ratio) + g2 * ratio,
            b1 * (1.0 - ratio) + b2 * ratio,
        ))
    except Exception:
        return normalize_hex(c1, '#20262F')


def _cuma_1081_is_light_preset(theme_name: str) -> bool:
    try:
        preset = THEME_VISUAL_PRESETS.get(theme_name, {})
        if 'is_light' in preset:
            return bool(preset.get('is_light'))
        kind = str(preset.get('kind', '')).lower()
        return theme_name == 'Moderno Claro' or 'claro' in kind or 'light' in kind
    except Exception:
        return False


def _cuma_1081_install_icon_themes() -> None:
    global THEMES, SYSTEM_COLOR_PRESETS, ACCENT_PRESETS
    try:
        for name, preset in CUMA_ICON_THEME_PRESETS.items():
            THEME_VISUAL_PRESETS[name] = dict(preset)
            try:
                PALETTES[name] = {
                    'bg': preset['bg'], 'surface': preset['surface'], 'surface2': preset['surface2'],
                    'field': preset['field'], 'fg': preset['fg'], 'muted': preset['muted'],
                    'border': preset['border'], 'accent': preset['accent'],
                    'accent_hover': preset['accent_hover'], 'success': preset['accent'],
                    'danger': preset['danger'], 'selection': preset['selection'], 'drop': preset['drop'],
                }
            except Exception:
                pass
        THEMES = _cuma_1081_unique_tuple(THEMES, tuple(CUMA_ICON_THEME_PRESETS.keys()))
        SYSTEM_COLOR_PRESETS = _cuma_1081_unique_tuple(SYSTEM_COLOR_PRESETS, tuple(CUMA_ICON_THEME_PRESETS.keys()))
        ACCENT_PRESETS = _cuma_1081_unique_tuple(ACCENT_PRESETS, ('#8B5CF6', '#C026FF', '#60A5FA', '#6D28D9'))
    except Exception as exc:
        _cuma_hotfix_log('Instalação dos temas do ícone 1.081.0', exc)


def _cuma_1081_extend_translations() -> None:
    try:
        extra_en = {
            'Preset CUMA Neon': 'CUMA Neon preset',
            'Preset CUMA Eclipse': 'CUMA Eclipse preset',
            'Preset CUMA Invertido': 'CUMA Inverted preset',
            'Temas do ícone CUMA': 'CUMA icon themes',
            'Presets baseados nas cores violeta, azul e roxo do ícone. Eles seguem a mesma linguagem visual da barra lateral, abas e caixas.': 'Presets based on the icon violet, blue and purple colors. They follow the same visual language as the sidebar, tabs and boxes.',
            'Temas e interface 1.081.0': 'Themes and interface 1.081.0',
            'Adicionados temas do ícone CUMA e ajustes visuais na sidebar, abas, caixas e barras de rolagem.': 'Added CUMA icon themes and visual adjustments to the sidebar, tabs, boxes and scrollbars.',
        }
        for mapping_name in ('V10_UI_I18N', 'V8_UI_I18N', 'V11_EXTRA_UI_I18N'):
            mapping = globals().get(mapping_name)
            if isinstance(mapping, dict):
                mapping.setdefault('en_US', {}).update(extra_en)
        try:
            globals()['V11_REVERSE_I18N'] = _cuma_v11_make_reverse()
            if isinstance(globals().get('V11_TR_CACHE'), dict):
                V11_TR_CACHE.clear()
        except Exception:
            pass
    except Exception as exc:
        _cuma_hotfix_log('Traduções dos temas 1.081.0', exc)


def _cuma_1081_apply_icon_theme_preset(self, theme_name: str) -> None:
    try:
        if theme_name not in THEME_VISUAL_PRESETS:
            theme_name = 'CUMA Neon'
        self.theme.set(theme_name)
        defaults = self.default_role_colors(theme_name)
        self.ensure_color_role_vars()
        for key, var in self.color_role_vars.items():
            var.set(defaults.get(key, '#FFFFFF'))
        self.custom_accent.set(defaults.get('primary', '#8B5CF6'))
        self.custom_base_theme.set('Claro' if _cuma_1081_is_light_preset(theme_name) else 'Escuro')
        self.theme_mode.set('Personalizado')
        self.sync_picker_states_from_roles()
        self.save_role_colors()
        self.apply_theme()
        self.save_current_config(force=True)
        if hasattr(self, 'config_help_text'):
            self.config_help_text.set('Tema do ícone CUMA aplicado. Você ainda pode ajustar as cores em Personalizado.')
        try:
            if '_cuma_v11_apply_language' in globals():
                _cuma_v11_apply_language(self)
        except Exception:
            pass
    except Exception as exc:
        _cuma_hotfix_log('Aplicar tema do ícone 1.081.0', exc)


def _cuma_1081_find_widgets_by_text(root_widget, text_value: str):
    found = []
    stack = [root_widget]
    while stack:
        widget = stack.pop()
        try:
            if str(widget.cget('text')) == text_value:
                found.append(widget)
        except Exception:
            pass
        try:
            stack.extend(widget.winfo_children())
        except Exception:
            pass
    return found


def _cuma_1081_add_icon_theme_buttons(self) -> None:
    try:
        if getattr(self, '_cuma_1081_icon_theme_buttons_added', False):
            return
        boxes = _cuma_1081_find_widgets_by_text(self.tab_config, 'Cores padrão do sistema')
        parent = boxes[0] if boxes else self.tab_config
        block = ttk.Frame(parent, style='Card.TFrame')
        block.pack(fill='x', pady=(8, 0))
        ttk.Label(block, text='Temas do ícone CUMA', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 4))
        ttk.Label(block, text='Presets baseados nas cores violeta, azul e roxo do ícone. Eles seguem a mesma linguagem visual da barra lateral, abas e caixas.', style='Muted.TLabel', wraplength=980, justify='left').pack(anchor='w', pady=(0, 8))
        row = ttk.Frame(block, style='Card.TFrame')
        row.pack(fill='x')
        for theme_name, label in (
            ('CUMA Neon', 'Preset CUMA Neon'),
            ('CUMA Eclipse', 'Preset CUMA Eclipse'),
            ('CUMA Invertido', 'Preset CUMA Invertido'),
        ):
            ttk.Button(row, text=label, command=lambda n=theme_name: self._cuma_apply_icon_theme_preset(n), style='Ghost.TButton').pack(side='left', padx=(0, 8), pady=(0, 2))
        self._cuma_1081_icon_theme_buttons_added = True
        try:
            if '_cuma_v11_apply_language' in globals():
                _cuma_v11_apply_language(self)
        except Exception:
            pass
    except Exception as exc:
        _cuma_hotfix_log('Botões de temas do ícone 1.081.0', exc)


def _cuma_1081_bind_sidebar_hover(self) -> None:
    try:
        if getattr(self, '_cuma_1081_sidebar_hover_bound', False):
            return

        def pointer_inside(widget):
            try:
                px, py = self.root.winfo_pointerxy()
                x, y = widget.winfo_rootx(), widget.winfo_rooty()
                return x <= px <= x + widget.winfo_width() and y <= py <= y + widget.winfo_height()
            except Exception:
                return False

        for label, item in getattr(self, 'nav_items', {}).items():
            body = item.get('body')
            if body is None:
                continue
            body._cuma_hover = False

            def enter(_event=None, b=body):
                try:
                    b._cuma_hover = True
                    self.update_sidebar_selection()
                except Exception:
                    pass

            def leave(_event=None, b=body):
                def later():
                    try:
                        b._cuma_hover = pointer_inside(b)
                        self.update_sidebar_selection()
                    except Exception:
                        pass
                try:
                    self.root.after(45, later)
                except Exception:
                    later()

            for widget in (item.get('container'), item.get('body'), item.get('icon'), item.get('text'), item.get('indicator')):
                if widget is not None:
                    try:
                        widget.bind('<Enter>', enter, add='+')
                        widget.bind('<Leave>', leave, add='+')
                    except Exception:
                        pass
        self._cuma_1081_sidebar_hover_bound = True
    except Exception as exc:
        _cuma_hotfix_log('Hover da sidebar 1.081.0', exc)


def _cuma_1081_visual_refinements(self) -> None:
    try:
        self.ensure_color_role_vars()
        roles = self.current_role_colors()
        base = THEME_VISUAL_PRESETS.get(self.theme.get(), THEME_VISUAL_PRESETS['Moderno Escuro'])
        light = _cuma_1081_is_light_preset(self.theme.get())
        bg = roles.get('background', base.get('bg', '#0F1318'))
        surface = roles.get('surface', base.get('surface', '#20262F'))
        surface2 = roles.get('surface2', base.get('surface2', '#2B3340'))
        sidebar_bg = roles.get('sidebar_bg', base.get('sidebar_bg', '#161A20'))
        fg = roles.get('text', base.get('fg', '#E5E7EB'))
        muted = base.get('muted', '#9CA3AF')
        border = roles.get('border', base.get('border', '#38414E'))
        accent = roles.get('primary', base.get('accent', '#2563EB'))
        accent_hover = base.get('accent_hover', accent)
        field = base.get('field', surface)
        tab_bg = base.get('tab_bg', _cuma_1081_blend(surface2, sidebar_bg, 0.35))
        tab_active = base.get('tab_active', base.get('sidebar_item_active', surface))
        hover = base.get('hover', _cuma_1081_blend(surface2, accent, 0.10 if light else 0.18))
        scrollbar = base.get('scrollbar', _cuma_1081_blend(surface2, bg, 0.45))
        scrollbar_hover = base.get('scrollbar_hover', _cuma_1081_blend(scrollbar, accent, 0.22))
        scrollbar_pressed = _cuma_1081_blend(scrollbar_hover, accent_hover, 0.30)
        selected_fg = fg if light else '#FFFFFF'

        self._sidebar_colors = {
            'sidebar_bg': sidebar_bg,
            'item_bg': base.get('sidebar_item', _cuma_1081_blend(sidebar_bg, surface, 0.42)),
            'item_hover_bg': hover,
            'active_bg': tab_active,
            'item_fg': muted,
            'hover_fg': fg,
            'active_fg': fg,
            'accent': accent,
            'muted': muted,
            'border': border,
        }
        self._theme_palette = {
            **getattr(self, '_theme_palette', {}),
            'accent': accent, 'bg': bg, 'surface': surface, 'surface2': surface2,
            'sidebar_bg': sidebar_bg, 'fg': fg, 'muted': muted, 'border': border,
            'drop': base.get('drop', surface2), 'selection': base.get('selection', tab_active),
            'danger': roles.get('danger', base.get('danger', '#FF6B6B')),
            'accent_hover': accent_hover,
        }

        s = self.style
        s.configure('Card.TFrame', background=surface, relief='flat', borderwidth=0)
        s.configure('Card.TLabelframe', background=surface, bordercolor=border, relief='solid', borderwidth=1)
        s.configure('Card.TLabelframe.Label', background=surface, foreground=fg, padding=(7, 2))
        s.configure('TNotebook', background=surface, borderwidth=0, tabmargins=(0, 2, 0, 0))
        s.configure('TNotebook.Tab', background=tab_bg, foreground=muted, bordercolor=border,
                    lightcolor=tab_bg, darkcolor=tab_bg, focuscolor=tab_bg,
                    relief='flat', borderwidth=1, padding=(18, 10), font=('Segoe UI', 9))
        s.map('TNotebook.Tab',
              background=[('selected', tab_active), ('active', hover), ('!selected', tab_bg)],
              foreground=[('selected', selected_fg), ('active', fg), ('!selected', muted)],
              bordercolor=[('selected', accent), ('active', border), ('!selected', border)],
              lightcolor=[('selected', tab_active), ('active', hover), ('!selected', tab_bg)],
              darkcolor=[('selected', tab_active), ('active', hover), ('!selected', tab_bg)])
        for style_name in ('TEntry', 'TCombobox', 'TSpinbox'):
            try:
                s.configure(style_name, fieldbackground=field, background=surface2, foreground=fg,
                            bordercolor=border, lightcolor=border, darkcolor=border,
                            insertcolor=fg, relief='flat', borderwidth=1)
                s.map(style_name,
                      bordercolor=[('focus', accent), ('active', _cuma_1081_blend(border, accent, 0.35)), ('!disabled', border)],
                      lightcolor=[('focus', accent), ('active', _cuma_1081_blend(border, accent, 0.35)), ('!disabled', border)],
                      darkcolor=[('focus', accent), ('active', _cuma_1081_blend(border, accent, 0.35)), ('!disabled', border)])
            except Exception:
                pass
        for style_name in ('Vertical.TScrollbar', 'Horizontal.TScrollbar', 'TScrollbar'):
            try:
                s.configure(style_name, background=scrollbar, troughcolor=bg, bordercolor=bg,
                            arrowcolor=muted, relief='flat', borderwidth=0, gripcount=0)
                s.map(style_name,
                      background=[('pressed', scrollbar_pressed), ('active', scrollbar_hover), ('!disabled', scrollbar)],
                      arrowcolor=[('pressed', fg), ('active', fg), ('!disabled', muted)],
                      troughcolor=[('pressed', bg), ('active', bg), ('!disabled', bg)],
                      bordercolor=[('pressed', bg), ('active', bg), ('!disabled', bg)])
            except Exception:
                pass
        try:
            self.root.option_add('*TCombobox*Listbox*Background', field)
            self.root.option_add('*TCombobox*Listbox*Foreground', fg)
            self.root.option_add('*TCombobox*Listbox*selectBackground', tab_active)
            self.root.option_add('*TCombobox*Listbox*selectForeground', selected_fg)
        except Exception:
            pass
        try:
            for child in self.tab_config.winfo_children():
                if isinstance(child, tk.Canvas):
                    self.config_canvas = child
                    child.configure(bg=surface, highlightbackground=surface, highlightcolor=surface)
        except Exception:
            pass
        try:
            self.update_sidebar_selection()
        except Exception:
            pass
    except Exception as exc:
        _cuma_hotfix_log('Refinamento visual 1.081.0', exc)


_CUMA_1081_RUNTIME = {
    'build': App.build,
    'build_config_tab': App.build_config_tab,
    'apply_theme': App.apply_theme,
    'update_sidebar_selection': App.update_sidebar_selection,
    '_apply_system_preset': App._apply_system_preset,
    'on_theme_choice_change': App.on_theme_choice_change,
}


def _cuma_1081_build(self):
    result = _CUMA_1081_RUNTIME['build'](self)
    try:
        # Ao abrir o aplicativo, a primeira tela da sessão é sempre Limpar.
        # Depois disso, a navegação normal continua gravando onde o usuário parou.
        if getattr(self, '_cuma_1081_start_page_done', False) is False:
            self.show_page('Limpar', save_state=False)
            self._cuma_1081_start_page_done = True
    except Exception as exc:
        _cuma_hotfix_log('Página inicial Limpar 1.081.0', exc)
    try:
        _cuma_1081_bind_sidebar_hover(self)
        _cuma_1081_visual_refinements(self)
    except Exception as exc:
        _cuma_hotfix_log('Pós-build visual 1.081.0', exc)
    return result


def _cuma_1081_build_config_tab(self):
    result = _CUMA_1081_RUNTIME['build_config_tab'](self)
    try:
        _cuma_1081_add_icon_theme_buttons(self)
    except Exception as exc:
        _cuma_hotfix_log('Configuração dos temas 1.081.0', exc)
    return result


def _cuma_1081_apply_theme(self):
    result = _CUMA_1081_RUNTIME['apply_theme'](self)
    try:
        _cuma_1081_visual_refinements(self)
    except Exception as exc:
        _cuma_hotfix_log('Aplicação visual 1.081.0', exc)
    return result


def _cuma_1081_update_sidebar_selection(self):
    try:
        colors = getattr(self, '_sidebar_colors', {})
        palette = getattr(self, '_theme_palette', {})
        outer_bg = colors.get('sidebar_bg', palette.get('sidebar_bg', '#161A20'))
        item_bg = colors.get('item_bg', '#1D232C')
        hover_bg = colors.get('item_hover_bg', '#242C38')
        active_bg = colors.get('active_bg', '#2C3139')
        item_fg = colors.get('item_fg', '#9CA3AF')
        hover_fg = colors.get('hover_fg', palette.get('fg', '#E5E7EB'))
        active_fg = colors.get('active_fg', palette.get('fg', '#E5E7EB'))
        accent = colors.get('accent', palette.get('accent', '#2563EB'))
        border = colors.get('border', palette.get('border', '#38414E'))
        if hasattr(self, 'sidebar'):
            self.sidebar.configure(bg=outer_bg)
        if hasattr(self, 'sidebar_top'):
            self.sidebar_top.configure(bg=outer_bg)
        for label, item in getattr(self, 'nav_items', {}).items():
            active = label == getattr(self, '_current_tab_label', 'Limpar')
            hover = False
            try:
                hover = bool(getattr(item.get('body'), '_cuma_hover', False))
            except Exception:
                hover = False
            body_bg = active_bg if active else (hover_bg if hover else item_bg)
            text_fg = active_fg if active else (hover_fg if hover else item_fg)
            indicator_bg = accent if active else (_cuma_1081_blend(border, outer_bg, 0.55) if hover else outer_bg)
            for key in ('container',):
                try:
                    item[key].configure(bg=outer_bg, highlightthickness=0, bd=0)
                except Exception:
                    pass
            try:
                item['indicator'].configure(bg=indicator_bg)
            except Exception:
                pass
            for key in ('body', 'icon', 'text'):
                try:
                    item[key].configure(bg=body_bg, fg=text_fg)
                except Exception:
                    try:
                        item[key].configure(bg=body_bg)
                    except Exception:
                        pass
            try:
                item['body'].configure(highlightthickness=1 if (active or hover) else 0,
                                       highlightbackground=_cuma_1081_blend(border, accent, 0.20 if active else 0.05),
                                       highlightcolor=_cuma_1081_blend(border, accent, 0.20 if active else 0.05))
            except Exception:
                pass
    except Exception as exc:
        _cuma_hotfix_log('Seleção da sidebar 1.081.0', exc)


def _cuma_1081_apply_system_preset(self, preset_name, force_custom=False):
    try:
        preset_name = preset_name if preset_name in THEME_VISUAL_PRESETS else 'Moderno Escuro'
        self.theme.set(preset_name)
        defaults = self.default_role_colors(preset_name)
        self.ensure_color_role_vars()
        for key, var in self.color_role_vars.items():
            var.set(defaults.get(key, '#FFFFFF'))
        self.custom_accent.set(defaults.get('primary', '#2563EB'))
        self.custom_base_theme.set('Claro' if _cuma_1081_is_light_preset(preset_name) else 'Escuro')
        if force_custom:
            self.theme_mode.set('Personalizado')
        self.sync_picker_states_from_roles()
        self.save_role_colors()
        self.apply_theme()
        self.save_current_config(force=True)
    except Exception as exc:
        _cuma_hotfix_log('Preset visual 1.081.0', exc)


def _cuma_1081_on_theme_choice_change(self, _event=None):
    try:
        selected = self.theme.get()
        if _cuma_1081_is_light_preset(selected):
            self.theme_mode.set('Claro' if selected == 'Moderno Claro' else 'Personalizado')
            self.custom_base_theme.set('Claro')
        elif selected == 'Manga Dark' or selected in CUMA_ICON_THEME_PRESETS:
            self.theme_mode.set('Personalizado')
            self.custom_base_theme.set('Escuro')
        else:
            self.theme_mode.set('Escuro')
            self.custom_base_theme.set('Escuro')
        self._apply_theme_mode_selection(save=True)
    except Exception as exc:
        _cuma_hotfix_log('Mudança de tema 1.081.0', exc)


def _cuma_install_1081_visual_update():
    try:
        _cuma_1081_install_icon_themes()
        _cuma_1081_extend_translations()
        App._cuma_apply_icon_theme_preset = _cuma_1081_apply_icon_theme_preset
        App.build = _cuma_1081_build
        App.build_config_tab = _cuma_1081_build_config_tab
        App.apply_theme = _cuma_1081_apply_theme
        App.update_sidebar_selection = _cuma_1081_update_sidebar_selection
        App._apply_system_preset = _cuma_1081_apply_system_preset
        App.on_theme_choice_change = _cuma_1081_on_theme_choice_change
        version = cuma_register_code_update(
            CUMA_1081_UPDATE_ID,
            'pequena',
            'Temas baseados no ícone do CUMA, tela inicial Limpar por sessão e refinamento visual de sidebar, abas, caixas e barras de rolagem.',
            apply_increment=True,
        )
        try:
            if isinstance(CHANGELOG_LATEST, dict):
                CHANGELOG_LATEST['version'] = version
                CHANGELOG_LATEST['date'] = datetime.now().date().isoformat()
                items = CHANGELOG_LATEST.setdefault('items', [])
                marker = 'Temas do ícone CUMA e harmonia visual de abas, caixas e scrollbars.'
                if marker not in items:
                    items.insert(0, marker)
        except Exception:
            pass
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_hotfix_log('Instalação da atualização visual 1.081.0', exc)


_cuma_install_1081_visual_update()


def _cuma_1081_rewrite_version_metadata() -> None:
    try:
        state = cuma_version_load_state()
        version = str(state.get('current_version') or globals().get('APP_DISPLAY_VERSION') or '1.081.0')
        # Não sobrescreve metadados de releases posteriores.
        if cuma_version_parse(version) > cuma_version_parse('1.081.0'):
            return
        events = list(state.get('events', [])) if isinstance(state.get('events', []), list) else []
        latest_event = next((e for e in reversed(events) if isinstance(e, dict) and str(e.get('version', '')) == version), None)
        updated_at = str((latest_event or {}).get('timestamp', '')).split('T')[0] or '2026-06-22'
        payload = {
            'name': APP_DISPLAY_NAME if 'APP_DISPLAY_NAME' in globals() else 'CUMA - Conversor Ultimate de Mangás',
            'version': version,
            'base_version': CUMA_VERSION_BASE,
            'build': 'ui_theme_harmonization_1_081_0',
            'notes': 'V11 com hotfixes 1.080.0, temas baseados no ícone CUMA, tela inicial Limpar por sessão e refinamento visual de sidebar, abas, caixas e scrollbars.',
            'versioning': {
                'grande': 'incrementa o primeiro número: 1.080.0 -> 2.000.0',
                'media': 'soma 10 no bloco central: 1.080.0 -> 1.090.0',
                'pequena': 'soma 1 no bloco central: 1.080.0 -> 1.081.0',
                'pouca': 'soma 1 no terceiro número: 1.080.0 -> 1.080.1',
            },
            'updated_at': updated_at,
        }
        target = runtime_dir() / 'version.json'
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        try:
            if target.exists() and target.read_text(encoding='utf-8') == payload_text:
                return
        except Exception:
            pass
        target.write_text(payload_text, encoding='utf-8')
    except Exception as exc:
        _cuma_hotfix_log('Metadados de versão 1.081.0', exc)


_cuma_1081_rewrite_version_metadata()


# =============================================================================
# CUMA 1.081.1 - ESTABILIDADE DE LANÇAMENTO, MANUAL COMPLETO E DEBUG CONDENSADO
# =============================================================================
# Este bloco é pequeno e proposital: mantém a V11 e a atualização visual 1.081.0,
# mas consolida a versão de lançamento, evita reescritas desnecessárias de
# metadados e reforça rotinas que podiam consumir memória demais.

CUMA_1081_1_UPDATE_ID = 'release_stability_manual_debug_1081_1'


def _cuma_1081_1_manual_text() -> str:
    version = globals().get('APP_DISPLAY_VERSION', '1.081.1')
    return f"""MANUAL COMPLETO DO CUMA - Conversor Ultimate de Mangás
Versão: {version}
Base de versionamento: {CUMA_VERSION_BASE}

===============================================================================
1. VISÃO GERAL
===============================================================================

O CUMA é um aplicativo desktop para organizar fluxos de mangás e PDFs. Ele
concentra quatro trabalhos principais:

1. Limpar PDFs, removendo páginas vazias ou pouco úteis.
2. Exportar o resultado como PDF, PDF + CBZ, CBZ ou imagens.
3. Usar ferramentas auxiliares para extrair páginas e montar PDFs de imagens.
4. Converter PDFs/EPUBs para formatos voltados a leitura em e-readers e
   dispositivos compactos, incluindo EPUB baseado em imagens e XTCH nativo.

A interface é dividida em sete áreas laterais:

• Limpar: fluxo principal de limpeza e exportação de PDFs.
• Ferramentas: utilidades auxiliares fora da fila principal.
• Converter: conversões PDF → EPUB, PDF → XTCH e EPUB → XTCH.
• Resultados: lista os processos concluídos e os arquivos gerados.
• Registros: mostra mensagens internas, logs e diagnósticos.
• Configurações: aparência, idioma, desempenho, hardware, segurança e logs.
• Sobre: resumo do aplicativo, versão e acesso aos manuais.

O botão Manual no topo abre o manual interativo simplificado. Este arquivo TXT é
a referência completa para lançamento, suporte e uso avançado.

===============================================================================
2. BOTÕES DO TOPO
===============================================================================

Manual
Abre o manual interativo do CUMA. Ele é propositalmente mais curto que este TXT e
serve para orientar rapidamente o usuário dentro do aplicativo.

Log
Abre o arquivo de log do aplicativo quando existir. Use para investigar falhas,
conferir mensagens internas ou enviar diagnóstico.

Procurar atualizações
Verifica os metadados de versão configurados no aplicativo. Quando uma fonte de
atualização estiver configurada, compara a versão atual com a versão disponível.

Botão de tema rápido, normalmente “☀ Tema claro” ou equivalente
Alterna rapidamente o modo visual entre aparência clara e escura. As opções
completas ficam em Configurações > Temas e cores.

===============================================================================
3. ABA LIMPAR
===============================================================================

A aba Limpar é o fluxo principal do programa.

Área “Arraste PDFs ou pastas aqui”
Permite soltar PDFs ou pastas diretamente na fila. Quando tkinterdnd2 não estiver
instalado, o aplicativo continua funcionando, mas o arrastar-e-soltar pode ficar
indisponível. Nesse caso, use os botões de seleção de arquivos/pastas.

Incluir subpastas
Quando marcado, ao adicionar uma pasta o CUMA também procura PDFs dentro das
subpastas. Útil para coleções grandes organizadas por capítulos.

Pasta de saída
Define onde os arquivos limpos serão gravados. Esta pasta é independente da pasta
do Converter. A partir dos hotfixes, mudar a saída do Converter não altera a
saída da aba Limpar.

Botão Escolher, ao lado de Pasta de saída
Abre o seletor de pasta para escolher a saída da limpeza.

Sufixo
Texto adicionado ao nome do arquivo de saída. Exemplo: se o PDF original for
capitulo01.pdf e o sufixo for _limpo, o resultado será capitulo01_limpo.pdf.

Formato de exportação
Define o tipo de saída:
• PDF: cria apenas o PDF limpo.
• PDF + CBZ: cria o PDF limpo e um CBZ com as páginas mantidas.
• CBZ: cria apenas o CBZ.
• Imagens JPG: exporta as páginas mantidas como JPG.
• Imagens PNG: exporta as páginas mantidas como PNG.

Intervalo de páginas
Permite limitar o processamento a páginas específicas. Exemplos:
• 1-10: processa da página 1 até a 10.
• 1-5, 8, 12-15: processa blocos separados.
• vazio: processa todas as páginas.

Abrir resultado ao concluir
Quando marcado, o CUMA tenta abrir a pasta ou o arquivo final ao terminar.

Carregar prévia do selecionado
Renderiza uma prévia do PDF selecionado na fila. Use para conferir visualmente
antes de processar.

Processar selecionados
Processa apenas os itens selecionados na fila.

Processar tudo
Processa todos os itens da fila.

Cancelar
Solicita cancelamento do processamento atual. O cancelamento ocorre de forma
segura entre etapas/páginas.

Pause
Pausa o processamento em lote. O item atual pode terminar a etapa em andamento
antes de parar.

Play
Retoma um processamento pausado.

Como o CUMA decide o que remover
O CUMA avalia densidade visual, presença de imagens grandes e perfil escolhido.
Páginas com baixa densidade podem ser tratadas como vazias. Em mangás, páginas
com imagem principal são preservadas. Em PDFs mistos, o modo visual preserva a
página renderizada.

Perfis de limpeza
• Conservador: remove menos páginas; indicado quando você quer evitar perdas.
• Normal: equilíbrio entre segurança e limpeza.
• Agressivo: remove mais páginas; use depois de testar em uma cópia.

Opção “Manter primeira página”
Mantém a primeira página quando aplicável, mas o algoritmo evita preservar uma
primeira página completamente vazia.

Opção “Manter últimas páginas”
Força a preservação das últimas páginas informadas. Útil quando o final tem
créditos, capa extra ou informações importantes.

Salvar páginas removidas
Cria um PDF separado com as páginas descartadas. Recomendado para auditoria antes
de apagar originais.

Criar backup
Cria cópia de segurança quando a operação puder substituir ou interferir em
arquivos existentes.

Sobrescrever original
Deve ser usado com cuidado. Para lançamento e uso comum, prefira manter desligado
e gerar arquivo novo com sufixo.

===============================================================================
4. ABA FERRAMENTAS
===============================================================================

A aba Ferramentas reúne funções auxiliares.

Extrair páginas dos PDFs selecionados como imagens
Transforma páginas dos PDFs selecionados em arquivos de imagem. Use quando você
quer editar páginas fora do CUMA ou criar uma sequência de imagens.

Criar PDF a partir de várias imagens
Monta um PDF usando imagens selecionadas. A rotina de lançamento processa imagens
uma a uma para reduzir consumo de memória em coleções grandes.

Salvar como PNG; desligado salva JPG
Define o formato das imagens extraídas. PNG preserva mais, mas costuma gerar
arquivos maiores. JPG é menor e geralmente suficiente para mangás.

Abrir pasta ao concluir
Abre a pasta final depois que a ferramenta terminar.

Zoom/renderização
Controla a escala usada ao renderizar páginas de PDF como imagem. Valores mais
altos melhoram definição, mas aumentam tempo e tamanho.

Nome do PDF
Nome usado ao criar PDF a partir de imagens.

Processar selecionados
Executa a ferramenta escolhida apenas nos arquivos selecionados.

Processar todos
Executa a ferramenta em todos os arquivos adicionados.

Criar PDF dos selecionados
Monta PDF usando somente as imagens selecionadas.

Criar PDF de todos
Monta PDF usando todas as imagens adicionadas à ferramenta.

Cancelar, Pause e Play
Têm o mesmo papel da aba Limpar: cancelar, pausar ou retomar tarefas em lote.

===============================================================================
5. ABA CONVERTER
===============================================================================

A aba Converter prepara arquivos para leitura em e-readers, celulares e
dispositivos compatíveis.

Área “Arraste PDFs, EPUBs ou pastas aqui”
Recebe PDFs, EPUBs e pastas. Se o recurso de arrastar-e-soltar estiver
indisponível, use os botões de adição.

Dispositivo
Escolhe o perfil de destino. O perfil define largura, altura, DPI, qualidade,
margem e ajustes de imagem. Exemplos incluídos: XTEINK X4, XTEINK X3, Kindle,
Kobo, BOOX, PocketBook, reMarkable e smartphones.

Aplicar perfil
Aplica o perfil selecionado ao fluxo de conversão.

Editor de perfis
Abre a janela para ajustar ou criar perfis de dispositivo.

Abrir pasta Converter
Abre a pasta de saída própria do Converter.

Pasta de saída
Define onde EPUBs e XTCHs serão gravados. Esta pasta é separada da pasta da aba
Limpar.

Botão Escolher, ao lado da pasta do Converter
Abre o seletor de pasta para a saída do Converter.

Qualidade do arquivo (%)
Controla a qualidade usada principalmente em EPUBs baseados em imagem. Valores
altos preservam mais detalhes e aumentam o tamanho final.

PDF para EPUB
Gera um EPUB de imagens a partir do PDF. É indicado para leitores que aceitam EPUB
e para casos em que você quer navegação mais comum de e-book.

PDF para XTCH
Gera XTCH nativo diretamente do PDF. A rotina atual processa página por página,
reduzindo RAM em PDFs grandes.

EPUB para XTCH
Converte EPUBs baseados em imagens para XTCH. EPUBs puramente textuais não são
renderizados nativamente nesta versão.

Processar selecionados
Converte apenas os itens selecionados na fila.

Processar tudo
Converte todos os itens adicionados.

Cancelar, Pause e Play
Cancelam, pausam e retomam a conversão em lote.

Detalhes do XTCH
O XTCH é gerado nativamente em Python. O CUMA monta páginas XTH em grayscale
2-bit e empacota o contêiner XTCH sem depender de Node, npm, bun ou workers
externos.

===============================================================================
6. EDITOR DE PERFIS DE DISPOSITIVO
===============================================================================

Perfil carregado
Mostra o perfil atualmente aberto para edição.

Salvar como nome
Define o nome usado ao salvar um perfil personalizado.

Largura e altura
Resolução final em pixels.

DPI
Densidade de referência do dispositivo. Ajuda a documentar e ajustar perfis.

Qualidade/JPEG
Qualidade de compressão para saídas que usam JPEG.

Gamma, contraste e nitidez
Ajustes finos de imagem. Use com moderação:
• Gamma altera brilho médio.
• Contraste destaca diferença entre tons.
• Nitidez reforça bordas.

Margem
Adiciona ou remove espaço em torno da página, dependendo do fluxo de conversão.

Salvar no perfil atual
Atualiza o perfil selecionado com os valores da janela.

Salvar como novo personalizado
Cria um perfil novo usando o nome informado em “Salvar como nome”.

Restaurar perfis padrão
Recria os perfis originais distribuídos com o CUMA. Use se um perfil foi
alterado incorretamente.

Fechar
Fecha o editor.

===============================================================================
7. ABA RESULTADOS
===============================================================================

A aba Resultados mostra o resumo das tarefas.

Colunas comuns
• Arquivo: arquivo original.
• Status: OK, ERRO, CANCELADO ou informação equivalente.
• Modo: estratégia usada na limpeza/conversão.
• Páginas: quantidade original e final quando aplicável.
• Removidas: páginas descartadas.
• Saída: caminho final gerado.
• Extras: CBZ, PDF de removidas ou outros arquivos relacionados.
• Erro: mensagem amigável quando algo falha.

Use esta aba para conferir se tudo saiu corretamente antes de mover ou apagar
arquivos originais.

===============================================================================
8. ABA REGISTROS
===============================================================================

A aba Registros centraliza logs.

Abrir log
Abre o arquivo CUMA.log.

Copiar diagnóstico
Copia um diagnóstico textual para a área de transferência. Use ao pedir suporte.

Salvar log automaticamente
Mantém registro em arquivo. Recomendado para builds de lançamento.

Nível de log
Controla o detalhamento:
• Básico: menos mensagens.
• Normal: equilíbrio recomendado.
• Detalhado: mais contexto.
• Debug: máximo detalhe, indicado para testes.

Retenção de logs
Define por quantos dias logs antigos devem ser mantidos.

erro.txt
Quando ocorre uma exceção crítica, o aplicativo pode gravar detalhes em erro.txt.

debug_completo_cuma.txt
Não precisa vir pronto dentro do pacote. Ele é gerado quando o aplicativo é
executado com --debug-env e serve para suporte técnico.

===============================================================================
9. ABA CONFIGURAÇÕES
===============================================================================

A aba Configurações é dividida em categorias.

Temas e cores
Controla idioma, modo visual, base personalizada, cor principal e presets.

Idioma do aplicativo
Permite escolher Automático ou um idioma disponível. Automático tenta seguir o
sistema operacional.

Modo visual
• Automático: tenta seguir o sistema; é o padrão recomendado.
• Claro: força tema claro.
• Escuro: força tema escuro.
• Personalizado: libera ajuste fino com base clara ou escura.

Base do personalizado
Define se o modo personalizado começa de uma base clara ou escura.

Cor principal do botão
Define a cor de destaque principal.

Personalizar cor
Abre o seletor visual de cor.

Aplicar cor
Aplica o valor hexadecimal digitado.

Preset Manga Dark
Aplica uma base escura com aparência inspirada em mangá.

Preset Escuro
Aplica a base moderna escura.

Preset Claro
Aplica a base moderna clara.

Temas do ícone CUMA
Presets visuais derivados das cores do ícone:
• CUMA Neon
• CUMA Eclipse
• CUMA Invertido

Ajuste avançado das cores
Permite alterar papéis visuais como fundo, superfície, texto, borda, primário,
secundário e perigo. Use quando quiser refinar a identidade visual.

Aplicar ajustes avançados
Salva e aplica as cores avançadas.

Restaurar tema escolhido
Volta o tema atual para seus valores originais.

Qualidade e desempenho
Reúne perfil de desempenho, cache, paralelismo, qualidade de prévia e opções de
memória.

Hardware
Permite escolher Automático, CPU, NVIDIA CUDA, AMD OpenCL, Intel OpenCL, OpenCL
genérico ou CPU + GPU. O modo automático tenta detectar o melhor caminho, com
fallback seguro para CPU.

Testar aceleração
Mostra se CUDA/OpenCL parecem disponíveis.

Benchmark rápido / Benchmark CPU/GPU
Executa teste simples de desempenho para comparar caminhos de processamento.

Facilidades
Opções de conveniência:
• salvar configurações automaticamente;
• mostrar dicas/tooltips;
• confirmar ações perigosas;
• lembrar tamanho/posição da janela;
• lembrar última aba aberta;
• lembrar última pasta;
• abrir pasta ao concluir;
• detectar duplicados;
• pular existentes;
• retomar processamento, quando disponível.

Segurança e logs
Opções para cache, logs, diagnóstico, confirmações e limpeza ao fechar.

Salvar configurações
Grava a configuração atual imediatamente.

Fechar
Fecha janelas auxiliares de configuração.

===============================================================================
10. ABA SOBRE
===============================================================================

A aba Sobre mostra nome do app, versão atual, resumo das abas e informações do
sistema de versionamento.

Abrir manual interativo
Abre uma versão curta, feita para orientação rápida.

Abrir manual TXT completo
Abre este arquivo, com explicação detalhada de funções e botões.

Sistema de versões
Mostra a versão atual, a base e o número de eventos registrados.

===============================================================================
11. SISTEMA DE VERSÕES
===============================================================================

A base definida para o projeto é 1.080.0.

Escalas:
• grande: incrementa o primeiro número e zera os demais.
  Exemplo: 1.080.0 → 2.000.0
• média: soma 10 ao bloco central e zera o patch.
  Exemplo: 1.080.0 → 1.090.0
• pequena: soma 1 ao bloco central e zera o patch.
  Exemplo: 1.080.0 → 1.081.0
• pouca/hotfix: soma 1 ao terceiro número.
  Exemplo: 1.081.0 → 1.081.1

Arquivos relacionados:
• version.json: metadados públicos da versão.
• cuma_version_state.json: estado interno do versionamento.
• cuma_version_history.json: histórico público enxuto.

A função interna cuma_register_code_update(update_id, scale, description) registra
atualizações sem duplicar eventos quando o aplicativo é aberto várias vezes.

===============================================================================
12. ARQUIVOS DO PACOTE
===============================================================================

cuma.py
Código principal do aplicativo.

config_cuma.json
Configuração inicial do app.

cuma_interface_colors.json
Cores, tema visual e idioma.

cuma_device_profiles.json
Perfis de dispositivos.

version.json
Metadados da versão atual.

cuma_version_state.json
Estado do versionamento.

cuma_version_history.json
Histórico resumido de versões.

manual_do_programa.txt
Este manual completo.

RELATORIO_RELEASE_1_081_1.txt
Relatório único de debug, limpeza de pacote e validação de lançamento.

requirements.txt
Dependências Python.

rodar_cuma.bat
Cria/usa ambiente virtual e abre o aplicativo no Windows.

criar_exe_windows_e_zip.bat
Compila o executável com PyInstaller e compacta a pasta final.

cuma.spec
Receita de build do PyInstaller.

app_icon.ico e cuma_logo.png
Ícone e logo do aplicativo.

===============================================================================
13. LIMITAÇÕES CONHECIDAS
===============================================================================

• EPUB textual puro não é renderizado para XTCH nesta versão. O conversor EPUB →
  XTCH espera EPUB baseado em imagens.
• tkinterdnd2 é opcional. Sem ele, arrastar-e-soltar pode não funcionar, mas o
  aplicativo abre normalmente.
• Aceleração CUDA/OpenCL depende de drivers, OpenCV e hardware disponíveis. O
  fallback seguro é CPU.
• Arquivos muito grandes podem demorar. Prefira testar primeiro com poucos
  capítulos.
• A detecção de páginas vazias é visual/heurística. Em materiais raros, revise o
  PDF de páginas removidas antes de apagar originais.

===============================================================================
14. FLUXOS RECOMENDADOS
===============================================================================

Fluxo seguro para lançamento/produção:
1. Abra o CUMA.
2. Use a aba Limpar.
3. Ative salvar páginas removidas.
4. Use perfil Normal ou Conservador.
5. Processe um arquivo de teste.
6. Confira Resultado e PDF de removidas.
7. Só depois processe lotes grandes.

Fluxo para e-reader:
1. Abra Converter.
2. Escolha o perfil do dispositivo.
3. Defina a pasta do Converter.
4. Marque PDF para EPUB ou PDF para XTCH.
5. Processe um arquivo.
6. Teste no dispositivo real.
7. Ajuste perfil se necessário.

Fluxo para diagnóstico:
1. Abra Registros.
2. Copie diagnóstico.
3. Verifique CUMA.log e erro.txt se existirem.
4. Execute python cuma.py --debug-env quando precisar gerar debug completo.
"""


def _cuma_1081_1_simple_manual_sections(lang):
    pt = {
        'Visão geral': 'O CUMA limpa PDFs, exporta PDF/CBZ/imagens e converte PDF/EPUB para formatos de leitura como EPUB de imagens e XTCH. Use as abas laterais para navegar.',
        'Limpar': 'Fluxo principal: adicione PDFs, escolha a saída, ajuste formato/sufixo/intervalo e processe. Use o PDF de páginas removidas para conferência.',
        'Ferramentas': 'Utilidades rápidas: extrair páginas como imagens e criar PDF a partir de imagens.',
        'Converter': 'Conversões para leitura: PDF → EPUB, PDF → XTCH e EPUB → XTCH. A pasta do Converter é separada da pasta da limpeza.',
        'Resultados': 'Mostra status, arquivos gerados, páginas removidas e erros.',
        'Registros': 'Centraliza logs e diagnóstico. Use “Copiar diagnóstico” ou abra o log para suporte.',
        'Configurações': 'Ajuste idioma, modo visual, temas, desempenho, hardware, facilidades, segurança e logs.',
        'Sobre': 'Mostra versão, resumo do app, sistema de versões e acesso aos manuais.',
        'Botões do topo': 'Manual abre esta ajuda interativa curta. Log abre o log. O botão de tema alterna visual rapidamente.',
        'Perfis de dispositivo': 'Perfis definem resolução, DPI, qualidade e ajustes para e-readers, celulares e dispositivos XTEINK.',
        'FAQ rápido': 'Para segurança, teste um arquivo antes do lote. Para suporte, consulte Registros, CUMA.log, erro.txt e o manual TXT completo.',
    }
    en = {
        'Visão geral': 'CUMA cleans PDFs, exports PDF/CBZ/images and converts PDF/EPUB to reading formats such as image EPUB and XTCH. Use the side tabs to navigate.',
        'Limpar': 'Main workflow: add PDFs, choose output, adjust format/suffix/range and process. Review the removed-pages PDF when needed.',
        'Ferramentas': 'Quick tools: extract pages as images and create a PDF from images.',
        'Converter': 'Reading conversions: PDF → EPUB, PDF → XTCH and EPUB → XTCH. Converter output is separate from Clean output.',
        'Resultados': 'Shows status, generated files, removed pages and errors.',
        'Registros': 'Centralizes logs and diagnostics. Use Copy diagnostics or open the log for support.',
        'Configurações': 'Adjust language, visual mode, themes, performance, hardware, convenience, security and logs.',
        'Sobre': 'Shows version, app summary, version system and manual access.',
        'Botões do topo': 'Manual opens this short interactive help. Log opens the log. The theme button switches appearance quickly.',
        'Perfis de dispositivo': 'Profiles define resolution, DPI, quality and adjustments for e-readers, phones and XTEINK devices.',
        'FAQ rápido': 'For safety, test one file before batches. For support, check Logs, CUMA.log, erro.txt and the full TXT manual.',
    }
    return pt if str(lang).lower().startswith('pt') else en


def ensure_manual() -> Path:
    try:
        manual_path().write_text(_cuma_1081_1_manual_text(), encoding='utf-8')
    except Exception as exc:
        try:
            _cuma_hotfix_log('Manual completo 1.081.1', exc)
        except Exception:
            pass
    return manual_path()


def xth_page_bytes(img: Image.Image, target: tuple[int, int]) -> bytes:
    """Converte imagem para XTH 2-bit grayscale sem manter cópias extras."""
    w, h = target
    temp = Image.new('RGB', (w, h), 'white')
    copy = img.convert('RGB')
    try:
        copy.thumbnail((w, h), Image.Resampling.LANCZOS)
        temp.paste(copy, ((w - copy.width) // 2, (h - copy.height) // 2))
        gray = temp.convert('L')
        px = gray.load()
        col_bytes = (h + 7) // 8
        plane_size = w * col_bytes
        plane1 = bytearray(plane_size)
        plane2 = bytearray(plane_size)
        for x in range(w - 1, -1, -1):
            col_index = w - 1 - x
            base = col_index * col_bytes
            for y in range(h):
                g = px[x, y]
                if g >= 224:
                    val = 0
                elif g >= 160:
                    val = 2
                elif g >= 80:
                    val = 1
                else:
                    val = 3
                byte_i = base + (y // 8)
                bit = 7 - (y % 8)
                if val & 0b10:
                    plane1[byte_i] |= 1 << bit
                if val & 0b01:
                    plane2[byte_i] |= 1 << bit
        data = bytes(plane1) + bytes(plane2)
        digest8 = hashlib.md5(data).digest()[:8]
        return struct.pack('<IHHBBI8s', 0x00485458, w, h, 0, 0, len(data), digest8) + data
    finally:
        try:
            copy.close()
        except Exception:
            pass
        try:
            temp.close()
        except Exception:
            pass


def create_xtch_from_images(images: list[Image.Image], output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    """Cria XTCH escrevendo páginas em fluxo para reduzir picos de RAM."""
    if not images:
        raise RuntimeError('Nenhuma imagem para criar XTCH.')
    page_count = len(images)
    if page_count > 65535:
        raise RuntimeError('XTCH suporta no máximo 65535 páginas por arquivo.')
    output_xtch.parent.mkdir(parents=True, exist_ok=True)
    header_size = 56
    table_offset = header_size
    data_offset = header_size + page_count * 16
    w, h = target
    header = struct.pack('<IBBHBBBBIQQQQII', 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0)
    rows = []
    with output_xtch.open('wb') as f:
        f.write(header)
        f.write(b'\x00' * (page_count * 16))
        for im in images:
            blob = xth_page_bytes(im, target)
            off = f.tell()
            f.write(blob)
            rows.append((off, len(blob), w, h))
        f.seek(table_offset)
        for off, size, tw, th in rows:
            f.write(struct.pack('<QIHH', off, size, tw, th))


def iter_epub_images(epub_path: Path, target: tuple[int, int]):
    if not epub_path.exists():
        raise RuntimeError('EPUB não encontrado.')
    with zipfile.ZipFile(epub_path, 'r') as z:
        names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_natural_key)
        for name in names:
            try:
                with z.open(name) as f:
                    data = BytesIO(f.read())
                im = Image.open(data).convert('RGB')
                try:
                    if im.width < 80 or im.height < 80:
                        continue
                    fitted = fit_to_target(im, target)
                    yield fitted
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
            except Exception as exc:
                try:
                    _cuma_hotfix_log(f'Imagem ignorada no EPUB: {name}', exc)
                except Exception:
                    pass


def create_xtch_from_epub(epub_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    """Converte EPUB baseado em imagens para XTCH sem manter todas as páginas em RAM."""
    if not epub_path.exists():
        raise RuntimeError('EPUB não encontrado.')
    with zipfile.ZipFile(epub_path, 'r') as z:
        page_count = len([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT])
    if page_count <= 0:
        raise RuntimeError('Não encontrei imagens úteis dentro do EPUB. EPUB textual puro ainda não é renderizado nativamente.')
    if page_count > 65535:
        raise RuntimeError('XTCH suporta no máximo 65535 páginas por arquivo.')
    output_xtch.parent.mkdir(parents=True, exist_ok=True)
    header_size = 56
    table_offset = header_size
    data_offset = header_size + page_count * 16
    w, h = target
    header = struct.pack('<IBBHBBBBIQQQQII', 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0)
    rows = []
    written = 0
    with output_xtch.open('wb') as f:
        f.write(header)
        f.write(b'\x00' * (page_count * 16))
        for im in iter_epub_images(epub_path, target):
            try:
                blob = xth_page_bytes(im, target)
                off = f.tell()
                f.write(blob)
                rows.append((off, len(blob), w, h))
                written += 1
            finally:
                try:
                    im.close()
                except Exception:
                    pass
        if written <= 0:
            raise RuntimeError('Não encontrei imagens úteis dentro do EPUB. EPUB textual puro ainda não é renderizado nativamente.')
        if written != page_count:
            # Reescreve header/tabela com contagem real quando entradas inválidas foram ignoradas.
            # O início real dos dados continua no primeiro offset já gravado.
            page_count = written
            data_offset = rows[0][0] if rows else (header_size + page_count * 16)
            f.seek(0)
            f.write(struct.pack('<IBBHBBBBIQQQQII', 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0))
            f.write(b'\x00' * (page_count * 16))
        f.seek(table_offset)
        for off, size, tw, th in rows:
            f.write(struct.pack('<QIHH', off, size, tw, th))


def save_images_to_pdf(image_paths: list[Path], output_pdf: Path) -> None:
    """Cria PDF de imagens em fluxo, sem carregar todas as imagens simultaneamente."""
    if not image_paths:
        raise RuntimeError('Nenhuma imagem selecionada.')
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    try:
        for raw in image_paths:
            p = Path(raw)
            if not p.exists():
                continue
            with Image.open(p) as im:
                rgb = im.convert('RGB')
                try:
                    bio = BytesIO()
                    rgb.save(bio, format='JPEG', quality=95, optimize=True)
                    w, h = rgb.size
                finally:
                    try:
                        rgb.close()
                    except Exception:
                        pass
            page = doc.new_page(width=w, height=h)
            page.insert_image(fitz.Rect(0, 0, w, h), stream=bio.getvalue(), keep_proportion=False)
        if len(doc) <= 0:
            raise RuntimeError('Nenhuma imagem válida para criar PDF.')
        doc.save(str(output_pdf), garbage=4, deflate=True)
    finally:
        doc.close()


def _cuma_xteink_epub_to_xtch_1081_1(self) -> Path:
    src, out_dir, target, _quality = self.xteink_paths()
    if src.suffix.lower() != '.epub':
        raise RuntimeError('Selecione um EPUB.')
    output = unique_path(out_dir / f'{src.stem}.xtch')
    create_xtch_from_epub(src, output, src.stem, target)
    self._xteink_last_out_dir = out_dir
    if not getattr(self, '_xteink_batch_mode', False) and self.open_after.get():
        open_folder(output)
    return output


def _cuma_run_xteink_job_1081_1(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    suffix = src.suffix.lower()
    if suffix == '.pdf' and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            create_image_epub_from_pdf(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            create_xtch_from_pdf(src, out, src.stem, target)
            outputs.append(out)
    elif suffix == '.epub' and flags.get('epub_xtch'):
        out = unique_path(out_dir / f'{src.stem}.xtch')
        create_xtch_from_epub(src, out, src.stem, target)
        outputs.append(out)
    else:
        raise RuntimeError('Formato/combinação de conversão não suportado para este arquivo.')
    return outputs


def _cuma_1081_1_rewrite_release_metadata(version: str) -> None:
    try:
        state = cuma_version_load_state()
        events = list(state.get('events', [])) if isinstance(state.get('events', []), list) else []
        latest_event = next((e for e in reversed(events) if isinstance(e, dict) and str(e.get('version', '')) == version), None)
        updated_at = str((latest_event or {}).get('timestamp', '')).split('T')[0] or '2026-06-22'
        payload = {
            'name': APP_DISPLAY_NAME if 'APP_DISPLAY_NAME' in globals() else 'CUMA - Conversor Ultimate de Mangás',
            'version': version,
            'base_version': CUMA_VERSION_BASE,
            'build': 'release_stability_manual_debug_1_081_1',
            'notes': 'Release consolidado: V11, hotfixes reaplicados, temas 1.081.0, manual completo, relatórios condensados e melhorias de estabilidade.',
            'versioning': {
                'grande': 'incrementa o primeiro número: 1.080.0 -> 2.000.0',
                'media': 'soma 10 no bloco central: 1.080.0 -> 1.090.0',
                'pequena': 'soma 1 no bloco central: 1.080.0 -> 1.081.0',
                'pouca': 'soma 1 no terceiro número: 1.080.0 -> 1.080.1',
            },
            'updated_at': updated_at,
        }
        target = runtime_dir() / 'version.json'
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2)
        try:
            if target.exists() and target.read_text(encoding='utf-8') == payload_text:
                return
        except Exception:
            pass
        target.write_text(payload_text, encoding='utf-8')
    except Exception as exc:
        _cuma_hotfix_log('Metadados release 1.081.1', exc)


def _cuma_install_1081_1_release_patch() -> None:
    try:
        version = cuma_register_code_update(
            CUMA_1081_1_UPDATE_ID,
            'pouca',
            'Consolidação de lançamento: relatório único, manual TXT completo, manual interativo curto, escrita de metadados idempotente e melhorias de memória em PDF/XTCH.',
            apply_increment=True,
        )
        globals()['_cuma_run_xteink_job'] = _cuma_run_xteink_job_1081_1
        try:
            App.xteink_epub_to_xtch = _cuma_xteink_epub_to_xtch_1081_1
        except Exception:
            pass
        try:
            globals()['_cuma_v6_manual_sections'] = _cuma_1081_1_simple_manual_sections
        except Exception:
            pass
        _cuma_1081_1_rewrite_release_metadata(version)
        try:
            ensure_manual()
        except Exception:
            pass
        # Instalação normal sem log em runtime; falhas continuam registradas.
    except Exception as exc:
        _cuma_hotfix_log('Instalação release patch 1.081.1', exc)


_cuma_install_1081_1_release_patch()


# =============================================================================
# CUMA 1.081.3 - PACOTE LIMPO PARA RELEASE
# =============================================================================

def _cuma_1081_2_manual_text() -> str:
    try:
        base = _cuma_1081_1_manual_text()
    except Exception:
        base = f"""MANUAL COMPLETO DO CUMA - Conversor Ultimate de Mangás
Versão: {globals().get('APP_DISPLAY_VERSION', '1.081.3')}

O CUMA limpa PDFs, exporta páginas/imagens e converte PDFs/EPUBs para formatos de leitura como EPUB e XTCH.
"""
    version = globals().get('APP_DISPLAY_VERSION', '1.081.3')
    base = re.sub(r'Versão:\s*[0-9]+\.[0-9]+\.[0-9]+', f'Versão: {version}', base, count=1)
    old_files = """cuma.py
Código principal do aplicativo.

config_cuma.json
Configuração inicial do app.

cuma_interface_colors.json
Cores, tema visual e idioma.

cuma_device_profiles.json
Perfis de dispositivos.

version.json
Metadados da versão atual.

cuma_version_state.json
Estado interno do versionamento.

cuma_version_history.json
Histórico público enxuto.

CUMA.log
Log de execução. Pode ser gerado automaticamente quando houver mensagens ou erros.

erro.txt
Quando ocorre uma exceção crítica, o aplicativo pode gravar detalhes em erro.txt.

debug_completo_cuma.txt
Não precisa vir pronto dentro do pacote. Ele é gerado quando o aplicativo é executado com --debug-env e serve para suporte técnico.
"""
    new_files = """cuma.exe
Executável compilado do aplicativo. Na distribuição one-folder, ele deve ficar junto da pasta _internal.

_internal/
Pasta interna criada pelo PyInstaller. Contém bibliotecas, DLLs, imagens, ícone, template de configurações e recursos necessários. O usuário não precisa editar esta pasta.

manual_do_programa.txt
Manual completo visível ao lado do executável. Pode ser aberto fora do aplicativo.

LEIA-ME.txt
Resumo rápido de instalação/uso para o usuário final.

cuma_settings.json
Arquivo único de configurações do usuário. Ele NÃO precisa ficar ao lado do executável. Quando o app está compilado no Windows, fica em:
%APPDATA%\\CUMA\\cuma_settings.json

Dentro dele ficam:
- configuração geral da aba Limpar;
- pasta separada do Converter;
- temas, cores e idioma;
- perfis de dispositivos;
- estado e histórico de versão;
- metadados públicos de versão;
- pequenas preferências de runtime.

CUMA.log
Log de execução. Quando necessário, é criado em:
%APPDATA%\\CUMA\\CUMA.log

erro.txt
Relatório de exceções críticas. Quando necessário, é criado em:
%APPDATA%\\CUMA\\erro.txt

debug_completo_cuma.txt
Gerado somente ao executar com --debug-env. Também fica na pasta de dados do usuário.

limpos/
Pasta de saída criada somente quando o usuário processa arquivos. Não deve vir pronta no pacote final.
"""
    section12 = (
        "=" * 79 + "\n"
        "12. ARQUIVOS E DADOS DO USUÁRIO\n"
        + "=" * 79 + "\n\n"
        + new_files
        + "\n"
    )
    if old_files in base:
        base = base.replace(old_files, new_files)
    else:
        base_new = re.sub(
            r"={20,}\n12\. ARQUIVOS DO PACOTE\n={20,}\n.*?(?=\n={20,}\n13\. LIMITAÇÕES CONHECIDAS)",
            lambda _m: section12.rstrip(),
            base,
            flags=re.S,
        )
        if base_new == base:
            base += "\n\n" + section12
        else:
            base = base_new
    base += f"""

===============================================================================
ADENDO DA VERSÃO 1.081.3 - PACOTE MAIS LIMPO
===============================================================================

Esta versão consolida os arquivos JSON editáveis em um único arquivo de usuário:
{cuma_settings_path()}

Na versão compilada para Windows, isso evita que a pasta do programa fique cheia de
config_cuma.json, cuma_interface_colors.json, version.json e arquivos similares.

Para lançamento, a pasta distribuída deve ficar idealmente assim:

CUMA/
  cuma.exe
  manual_do_programa.txt
  LEIA-ME.txt
  _internal/

Não distribua a pasta limpos/, logs, PDFs convertidos, arquivos de teste ou builds
antigas. Esses itens devem ser criados somente no computador do usuário.
"""
    return base


def ensure_manual() -> Path:
    try:
        manual_path().write_text(_cuma_1081_2_manual_text(), encoding='utf-8')
    except Exception as exc:
        try:
            _cuma_hotfix_log('Manual completo 1.081.3', exc)
        except Exception:
            pass
    return manual_path()


def _cuma_1081_2_write_readme() -> None:
    try:
        readme = f"""CUMA - Conversor Ultimate de Mangás
Versão: {globals().get('APP_DISPLAY_VERSION', '1.081.3')}

COMO USAR
1. Extraia o ZIP inteiro.
2. Abra cuma.exe.
3. Não apague a pasta _internal.
4. O manual completo está em manual_do_programa.txt.

ESTRUTURA RECOMENDADA
CUMA/
  cuma.exe
  manual_do_programa.txt
  LEIA-ME.txt
  _internal/

DADOS DO USUÁRIO
As configurações ficam em um único arquivo:
%APPDATA%\\CUMA\\cuma_settings.json

Logs e relatórios de erro também ficam em %APPDATA%\\CUMA quando forem necessários.

OBSERVAÇÃO
Não distribua a pasta limpos/, arquivos convertidos, CUMA.log, erro.txt ou arquivos de debug.
"""
        target = app_dir() / 'LEIA-ME.txt'
        try:
            if target.exists() and target.read_text(encoding='utf-8') == readme:
                return
        except Exception:
            pass
        target.write_text(readme, encoding='utf-8')
    except Exception:
        pass


def _cuma_1081_2_update_metadata(version: str) -> None:
    try:
        state = cuma_version_load_state()
        events = list(state.get('events', [])) if isinstance(state.get('events', []), list) else []
        updated_at = datetime.now().date().isoformat()
        for event in reversed(events):
            if isinstance(event, dict) and event.get('update_id') == CUMA_1081_2_UPDATE_ID:
                updated_at = str(event.get('timestamp', '')).split('T')[0] or updated_at
                break
        payload = _cuma_default_version_payload(version)
        payload.update({
            'version': version,
            'build': 'storage_consolidation_1_081_2',
            'notes': 'Configurações consolidadas em cuma_settings.json, dados graváveis movidos para a pasta do usuário e pacote de distribuição mais limpo.',
            'updated_at': updated_at,
        })
        data = cuma_settings_load()
        data['version'] = payload
        data['version_history'] = {'base_version': CUMA_VERSION_BASE, 'current_version': version, 'events': events[-80:]}
        data['version_state'] = state
        cuma_settings_save(data)
    except Exception as exc:
        try:
            write_log(f'Metadados 1.081.3: {exc}')
        except Exception:
            pass


def _cuma_install_1081_2_release_cleanup() -> None:
    try:
        version = cuma_register_code_update(
            CUMA_1081_2_UPDATE_ID,
            'pouca',
            'Consolidação dos JSONs em cuma_settings.json, dados graváveis em pasta de usuário, limpeza de pacote e manual atualizado.',
            apply_increment=True,
        )
        _cuma_1081_2_update_metadata(version)
        try:
            ensure_manual()
        except Exception:
            pass
        try:
            _cuma_1081_2_write_readme()
        except Exception:
            pass
        try:
            _cuma_cleanup_legacy_runtime_files()
        except Exception:
            pass
        try:
            if isinstance(CHANGELOG_LATEST, dict):
                CHANGELOG_LATEST['version'] = version
                CHANGELOG_LATEST['date'] = datetime.now().date().isoformat()
                marker = 'Pacote limpo: configurações em cuma_settings.json e dados do usuário fora da pasta do executável.'
                items = CHANGELOG_LATEST.setdefault('items', [])
                if marker not in items:
                    items.insert(0, marker)
        except Exception:
            pass
    except Exception as exc:
        try:
            write_log(f'Instalação release cleanup 1.081.3: {exc}')
        except Exception:
            pass


_cuma_install_1081_2_release_cleanup()




# =============================================================================
# CUMA 1.081.3 - ENDPOINT OFICIAL DE ATUALIZAÇÃO VIA GITHUB
# =============================================================================
# Este bloco mantém a versão 1.081.3 e apenas configura o botão "Procurar
# atualizações" para consultar o manifesto oficial do repositório soldieg/CUMA.

CUMA_DEFAULT_UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/soldieg/CUMA/main/updates/stable.json"
CUMA_DEFAULT_UPDATE_DOWNLOAD_URL = "https://github.com/soldieg/CUMA/releases/download/Stable/CUMA_windows.zip"
CUMA_DEFAULT_UPDATE_SHA256 = ""
CUMA_DEFAULT_UPDATE_SIZE_BYTES = 0


def _cuma_update_version_tuple(value: str) -> tuple:
    try:
        parts = re.findall(r'\d+', str(value or ''))[:3]
        nums = [int(x) for x in parts]
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums[:3])
    except Exception:
        return (0, 0, 0)


def _cuma_update_manifest_url_from_settings() -> str:
    try:
        settings = cuma_settings_load()
        if isinstance(settings, dict):
            cfg = settings.get('config', {})
            if isinstance(cfg, dict):
                url = str(cfg.get('update_manifest_url', '') or '').strip()
                if url:
                    return url
            updates = settings.get('updates', {})
            if isinstance(updates, dict):
                url = str(updates.get('manifest_url', '') or '').strip()
                if url:
                    return url
    except Exception:
        pass
    return CUMA_DEFAULT_UPDATE_MANIFEST_URL


def _cuma_ensure_update_settings_defaults() -> None:
    try:
        settings = cuma_settings_load()
        if not isinstance(settings, dict):
            settings = {}
        cfg = settings.setdefault('config', {})
        if isinstance(cfg, dict) and not str(cfg.get('update_manifest_url', '') or '').strip():
            cfg['update_manifest_url'] = CUMA_DEFAULT_UPDATE_MANIFEST_URL
        updates = settings.setdefault('updates', {})
        if isinstance(updates, dict):
            updates.setdefault('channel', 'stable')
            updates.setdefault('manifest_url', CUMA_DEFAULT_UPDATE_MANIFEST_URL)
            updates.setdefault('auto_download', False)
            updates.setdefault('verify_sha256', True)
            updates.setdefault('last_checked_at', '')
            updates.setdefault('last_available_version', '')
        cuma_settings_save(settings)
    except Exception as exc:
        try:
            write_log(f'Configuração padrão de atualização GitHub: {exc}')
        except Exception:
            pass


def _cuma_check_updates_button_async(self):
    if getattr(self, '_update_manifest_check_running', False):
        return
    self._update_manifest_check_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None:
            btn.configure(state='disabled')
    except Exception:
        pass

    def finish(kind: str, title: str, message: str) -> None:
        self._update_manifest_check_running = False
        try:
            if btn is not None:
                btn.configure(state='normal')
        except Exception:
            pass
        try:
            text = _cuma_fix_mojibake_text(message) if '_cuma_fix_mojibake_text' in globals() else message
        except Exception:
            text = message
        (messagebox.showerror if kind == 'error' else messagebox.showinfo)(title, text)

    def worker():
        try:
            _cuma_ensure_update_settings_defaults()
            manifest_url = _cuma_update_manifest_url_from_settings()
            import urllib.request
            req = urllib.request.Request(
                manifest_url,
                headers={'User-Agent': 'CUMA-Update-Checker/1.100.0'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                remote = json.loads(resp.read().decode('utf-8'))

            if str(remote.get('app_id', 'cuma')).lower() != 'cuma':
                raise ValueError('O manifesto remoto não parece ser do CUMA.')

            latest = str(remote.get('version', '') or '').strip()
            current = str(globals().get('APP_DISPLAY_VERSION', '1.081.3') or '1.081.3').strip()
            download_url = str(remote.get('download_url', '') or CUMA_DEFAULT_UPDATE_DOWNLOAD_URL)
            remote_sha = str(remote.get('sha256', '') or '').strip()
            remote_size = int(remote.get('size_bytes', 0) or 0)
            notes = remote.get('release_notes', [])
            if isinstance(notes, list):
                notes_text = '\n'.join(f'• {str(item)}' for item in notes[:8])
            else:
                notes_text = str(notes or '')

            try:
                settings = cuma_settings_load()
                settings.setdefault('updates', {})
                if isinstance(settings.get('updates'), dict):
                    settings['updates']['last_checked_at'] = datetime.now().isoformat(timespec='seconds')
                    settings['updates']['last_available_version'] = latest
                cuma_settings_save(settings)
            except Exception:
                pass

            latest_tuple = _cuma_update_version_tuple(latest)
            current_tuple = _cuma_update_version_tuple(current)

            if latest and latest_tuple > current_tuple:
                msg = (
                    f'Atualização encontrada: {latest}\n'
                    f'Versão instalada: {current}\n\n'
                    f'Baixe em:\n{download_url}\n\n'
                    f'SHA256:\n{remote_sha or "não informado"}\n\n'
                    f'Tamanho: {remote_size or "não informado"} bytes'
                )
                if notes_text:
                    msg += f'\n\nNovidades:\n{notes_text}'
            elif latest and latest_tuple == current_tuple:
                msg = (
                    f'Você já está usando a versão mais recente informada no repositório.\n\n'
                    f'Versão instalada: {current}\n'
                    f'Versão no GitHub: {latest}'
                )
            else:
                msg = (
                    f'O manifesto do GitHub está em uma versão anterior à instalada.\n\n'
                    f'Versão instalada: {current}\n'
                    f'Versão no GitHub: {latest or "não informada"}'
                )

            self.root.after(0, lambda: finish('info', 'Procurar atualizações', msg))
        except Exception as exc:
            try:
                _cuma_patch_log_exception('Verificação de atualizações GitHub', exc)
            except Exception:
                try:
                    write_log(f'Verificação de atualizações GitHub: {exc}')
                except Exception:
                    pass
            self.root.after(0, lambda: finish('error', 'Procurar atualizações', friendly_error(exc)))

    threading.Thread(target=worker, daemon=True, name='CUMA-Update-Checker').start()


def _cuma_install_github_update_endpoint_1081_2() -> None:
    try:
        _cuma_ensure_update_settings_defaults()
        globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_async
    except Exception as exc:
        try:
            write_log(f'Instalação do endpoint GitHub de atualização: {exc}')
        except Exception:
            pass


_cuma_install_github_update_endpoint_1081_2()



# =============================================================================
# CUMA 1.081.3 - POP-UP DE ATUALIZAÇÕES INTEGRADO AO TEMA
# =============================================================================
# Substitui os messagebox nativos do Tk no botão "Procurar atualizações".
# O objetivo é evitar janelas brancas/fora do visual do aplicativo e impedir
# mensagens vazias como "None" quando algum erro não traz texto amigável.

def _cuma_update_dialog_palette(app) -> dict:
    try:
        roles = app.current_role_colors() if hasattr(app, 'current_role_colors') else {}
    except Exception:
        roles = {}
    try:
        palette = getattr(app, '_theme_palette', {}) or {}
    except Exception:
        palette = {}
    bg = roles.get('background') or palette.get('bg') or '#0B1020'
    surface = roles.get('surface') or palette.get('surface') or '#111827'
    surface2 = roles.get('surface2') or palette.get('surface2') or '#172033'
    fg = roles.get('text') or palette.get('fg') or '#E5E7EB'
    muted = palette.get('muted') or '#9CA3AF'
    border = roles.get('border') or palette.get('border') or '#263244'
    accent = roles.get('primary') or palette.get('accent') or '#3B82F6'
    danger = roles.get('danger') or palette.get('danger') or '#EF4444'
    success = palette.get('success') or '#22C55E'
    drop = palette.get('drop') or surface2
    return {
        'bg': bg, 'surface': surface, 'surface2': surface2, 'fg': fg, 'muted': muted,
        'border': border, 'accent': accent, 'danger': danger, 'success': success,
        'drop': drop, 'button_fg': '#FFFFFF'
    }


def _cuma_update_safe_text(value, fallback='Não foi possível obter detalhes.') -> str:
    try:
        text_value = str(value or '').strip()
    except Exception:
        text_value = ''
    if not text_value or text_value.lower() == 'none':
        return fallback
    try:
        if '_cuma_fix_mojibake_text' in globals():
            text_value = _cuma_fix_mojibake_text(text_value)
    except Exception:
        pass
    return text_value


def _cuma_update_human_size(size_bytes) -> str:
    try:
        n = int(size_bytes or 0)
    except Exception:
        n = 0
    if n <= 0:
        return 'não informado'
    units = ['bytes', 'KB', 'MB', 'GB']
    value = float(n)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == 'bytes':
        return f'{int(value)} bytes'
    return f'{value:.1f} {unit} ({n} bytes)'


def _cuma_copy_to_clipboard(root, text_value: str) -> None:
    try:
        root.clipboard_clear()
        root.clipboard_append(str(text_value or ''))
        root.update_idletasks()
    except Exception as exc:
        try:
            write_log(f'Falha ao copiar para área de transferência: {exc}')
        except Exception:
            pass


def _cuma_show_themed_update_dialog(app, state='none', title='Procurar atualizações',
                                    heading=None, message=None, details=None,
                                    download_url='', sha256='', size_bytes=0,
                                    release_notes='') -> None:
    try:
        pal = _cuma_update_dialog_palette(app)
        root = app.root
        top = tk.Toplevel(root)
        top.title(title)
        top.configure(bg=pal['bg'])
        top.resizable(False, False)
        try:
            top.transient(root)
            top.grab_set()
        except Exception:
            pass

        width, height = 620, 460
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            x = rx + max(0, (rw - width) // 2)
            y = ry + max(0, (rh - height) // 2)
            top.geometry(f'{width}x{height}+{x}+{y}')
        except Exception:
            top.geometry(f'{width}x{height}')

        container = tk.Frame(top, bg=pal['surface'], bd=0, highlightthickness=1, highlightbackground=pal['border'])
        container.pack(fill='both', expand=True, padx=1, pady=1)

        accent_color = pal['accent']
        icon_text = 'i'
        if state == 'available':
            accent_color = pal['accent']; icon_text = '↓'
            heading = heading or 'Atualização disponível'
        elif state == 'error':
            accent_color = pal['danger']; icon_text = '!'
            heading = heading or 'Não foi possível verificar atualizações'
        else:
            accent_color = pal['success']; icon_text = '✓'
            heading = heading or 'Não há atualizações. Aguarde...'

        top_bar = tk.Frame(container, bg=accent_color, height=4)
        top_bar.pack(fill='x', side='top')
        header = tk.Frame(container, bg=pal['surface'], padx=24, pady=22)
        header.pack(fill='x')

        icon = tk.Canvas(header, width=54, height=54, bg=pal['surface'], highlightthickness=0)
        icon.pack(side='left', padx=(0, 16))
        icon.create_oval(4, 4, 50, 50, fill=accent_color, outline=accent_color)
        icon.create_text(27, 27, text=icon_text, fill=pal['button_fg'], font=('Segoe UI', 22, 'bold'))

        title_box = tk.Frame(header, bg=pal['surface'])
        title_box.pack(side='left', fill='x', expand=True)
        tk.Label(title_box, text=_cuma_update_safe_text(heading, 'Procurar atualizações'),
                 bg=pal['surface'], fg=pal['fg'], font=('Segoe UI', 14, 'bold'),
                 anchor='w', justify='left').pack(fill='x', anchor='w')
        sub = 'Verificação concluída pelo GitHub Releases.'
        if state == 'available':
            sub = 'Existe um pacote novo publicado para baixar.'
        elif state == 'error':
            sub = 'Confira sua conexão ou o manifesto de atualização.'
        tk.Label(title_box, text=sub, bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 9), anchor='w', justify='left').pack(fill='x', anchor='w', pady=(4, 0))

        body = tk.Frame(container, bg=pal['surface'], padx=24, pady=0)
        body.pack(side='top', fill='both', expand=True)

        msg = _cuma_update_safe_text(message, 'Nenhuma informação adicional foi recebida.')
        msg_label = tk.Label(body, text=msg, bg=pal['surface'], fg=pal['fg'],
                             font=('Segoe UI', 10), anchor='nw', justify='left',
                             wraplength=560)
        msg_label.pack(fill='x', anchor='w', pady=(0, 12))

        info_box = tk.Frame(body, bg=pal['surface2'], highlightthickness=1, highlightbackground=pal['border'])
        info_box.pack(fill='both', expand=True)

        text_box = tk.Text(info_box, height=9, wrap='word', bg=pal['surface2'], fg=pal['fg'],
                           insertbackground=pal['fg'], relief='flat', bd=0,
                           font=('Segoe UI', 9), padx=12, pady=10)
        text_box.pack(side='left', fill='both', expand=True)

        scroll = tk.Scrollbar(info_box, orient='vertical', command=text_box.yview,
                              bg=pal['surface2'], activebackground=pal['drop'],
                              troughcolor=pal['bg'], relief='flat', bd=0)
        scroll.pack(side='right', fill='y')
        text_box.configure(yscrollcommand=scroll.set)

        lines = []
        if details:
            lines.append(_cuma_update_safe_text(details, ''))
        if download_url:
            lines.append('')
            lines.append('Link de download:')
            lines.append(str(download_url))
        if sha256:
            lines.append('')
            lines.append('SHA256:')
            lines.append(str(sha256))
        if size_bytes:
            lines.append('')
            lines.append('Tamanho:')
            lines.append(_cuma_update_human_size(size_bytes))
        if release_notes:
            lines.append('')
            lines.append('Novidades:')
            lines.append(_cuma_update_safe_text(release_notes, ''))
        text_box.insert('1.0', '\n'.join(lines).strip() or 'Sem detalhes extras.')
        text_box.configure(state='disabled')

        actions = tk.Frame(container, bg=pal['surface'], padx=24, pady=(16, 20))
        # Mantém os botões sempre visíveis no rodapé da janela,
        # mesmo quando as notas da atualização ocupam muito espaço.
        actions.pack(side='bottom', fill='x')
        try:
            actions.lift()
        except Exception:
            pass

        def make_button(text_label, command, primary=False):
            bg = accent_color if primary else pal['surface2']
            fg = pal['button_fg'] if primary else pal['fg']
            active = pal['drop'] if not primary else pal['accent']
            btn = tk.Button(actions, text=text_label, command=command, bg=bg, fg=fg,
                            activebackground=active, activeforeground=fg,
                            relief='flat', bd=0, padx=16, pady=9,
                            font=('Segoe UI', 9, 'bold' if primary else 'normal'),
                            cursor='hand2')
            btn.pack(side='right', padx=(8, 0))
            return btn

        make_button('Fechar', top.destroy, primary=False)

        if download_url:
            def open_download():
                try:
                    import webbrowser
                    webbrowser.open(download_url)
                except Exception as exc:
                    try:
                        write_log(f'Falha ao abrir download: {exc}')
                    except Exception:
                        pass

            make_button('Copiar link', lambda: _cuma_copy_to_clipboard(root, download_url), primary=False)
            make_button('Abrir download', open_download, primary=True)
        elif sha256:
            make_button('Copiar SHA256', lambda: _cuma_copy_to_clipboard(root, sha256), primary=False)

        try:
            top.bind('<Escape>', lambda _e: top.destroy())
            top.focus_force()
        except Exception:
            pass
    except Exception as exc:
        # Última defesa: nunca mostrar "None".
        fallback = _cuma_update_safe_text(message or exc, 'Não foi possível verificar atualizações.')
        try:
            messagebox.showinfo(title or 'Procurar atualizações', fallback)
        except Exception:
            pass


def _cuma_check_updates_button_async_1081_3(self):
    if getattr(self, '_update_manifest_check_running', False):
        return
    self._update_manifest_check_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None:
            btn.configure(state='disabled', text='Verificando...')
    except Exception:
        pass

    def finish(payload: dict) -> None:
        self._update_manifest_check_running = False
        try:
            if btn is not None:
                btn.configure(state='normal', text='Procurar atualizações')
        except Exception:
            pass
        try:
            _cuma_show_themed_update_dialog(self, **payload)
        except Exception as exc:
            safe_message = _cuma_update_safe_text(payload.get('message') or exc, 'Não foi possível verificar atualizações.')
            try:
                messagebox.showinfo(payload.get('title', 'Procurar atualizações'), safe_message)
            except Exception:
                pass

    def worker():
        try:
            _cuma_ensure_update_settings_defaults()
            manifest_url = _cuma_update_manifest_url_from_settings()
            import urllib.request
            req = urllib.request.Request(
                manifest_url,
                headers={'User-Agent': 'CUMA-Update-Checker/1.100.0'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                remote = json.loads(resp.read().decode('utf-8'))

            if str(remote.get('app_id', 'cuma')).lower() != 'cuma':
                raise ValueError('O manifesto remoto não parece ser do CUMA.')

            latest = str(remote.get('version', '') or '').strip()
            current = str(globals().get('APP_DISPLAY_VERSION', '1.081.3') or '1.081.3').strip()
            download_url = str(remote.get('download_url', '') or '').strip()
            remote_sha = str(remote.get('sha256', '') or '').strip()
            try:
                remote_size = int(remote.get('size_bytes', 0) or 0)
            except Exception:
                remote_size = 0
            notes = remote.get('release_notes', [])
            if isinstance(notes, list):
                notes_text = '\n'.join(f'• {str(item)}' for item in notes[:10])
            else:
                notes_text = str(notes or '')

            try:
                settings = cuma_settings_load()
                settings.setdefault('updates', {})
                if isinstance(settings.get('updates'), dict):
                    settings['updates']['last_checked_at'] = datetime.now().isoformat(timespec='seconds')
                    settings['updates']['last_available_version'] = latest
                    settings['updates']['last_manifest_url'] = manifest_url
                cuma_settings_save(settings)
            except Exception:
                pass

            latest_tuple = _cuma_update_version_tuple(latest)
            current_tuple = _cuma_update_version_tuple(current)

            if latest and latest_tuple > current_tuple:
                payload = {
                    'state': 'available',
                    'title': 'Atualização disponível',
                    'heading': f'CUMA {latest} está disponível',
                    'message': f'Você está usando a versão {current}. Baixe a nova versão pelo botão abaixo.',
                    'details': f'Versão instalada: {current}\nVersão no GitHub: {latest}\nCanal: {remote.get("channel", "stable")}',
                    'download_url': download_url or CUMA_DEFAULT_UPDATE_DOWNLOAD_URL,
                    'sha256': remote_sha,
                    'size_bytes': remote_size,
                    'release_notes': notes_text,
                }
            else:
                # Quando o manifesto está igual OU anterior à versão instalada, não assustar o usuário.
                # Isso evita mensagens técnicas durante testes de builds locais mais novas que o stable.json.
                payload = {
                    'state': 'none',
                    'title': 'Procurar atualizações',
                    'heading': 'Não há atualizações. Aguarde...',
                    'message': f'Você já está usando a versão mais recente disponível para este canal.',
                    'details': f'Versão instalada: {current}\nVersão no GitHub: {latest or "não informada"}\nCanal: {remote.get("channel", "stable")}\nManifesto: {manifest_url}',
                    'download_url': '',
                    'sha256': remote_sha,
                    'size_bytes': remote_size,
                    'release_notes': notes_text,
                }

            self.root.after(0, lambda payload=payload: finish(payload))
        except Exception as exc:
            try:
                _cuma_patch_log_exception('Verificação de atualizações GitHub', exc)
            except Exception:
                try:
                    write_log(f'Verificação de atualizações GitHub: {exc}')
                except Exception:
                    pass
            payload = {
                'state': 'error',
                'title': 'Procurar atualizações',
                'heading': 'Não foi possível verificar atualizações',
                'message': _cuma_update_safe_text(friendly_error(exc), 'Não foi possível verificar atualizações.'),
                'details': f'Erro técnico: {type(exc).__name__}: {exc}',
            }
            self.root.after(0, lambda payload=payload: finish(payload))

    threading.Thread(target=worker, daemon=True, name='CUMA-Update-Checker').start()


def _cuma_install_themed_update_dialog_1081_3() -> None:
    try:
        globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_async_1081_3
    except Exception as exc:
        try:
            write_log(f'Instalação do pop-up de atualização 1.081.3: {exc}')
        except Exception:
            pass


_cuma_install_themed_update_dialog_1081_3()


# =============================================================================
# CUMA 1.100.0 - PERFIS, LEITURA, OTIMIZAÇÃO E-INK E EXPERIÊNCIA AVANÇADA
# =============================================================================
# Consolida o roadmap planejado:
# - 1.082.0: perfis reais de dispositivos, ordenação natural, leitura mangá/ocidental.
# - 1.090.0: otimização E-ink, corte de margens, páginas duplas e presets de imagem.
# - 1.100.0: preview antes/depois, metadados, arquivos compactados e webtoon básico.
#
# Observação de licença/referência: os perfis Kindle/Kobo/reMarkable abaixo foram
# adaptados a partir da referência técnica do Kindle Comic Converter (KCC),
# repositório https://github.com/ciromattia/kcc, licença ISC.

CUMA_11000_UPDATE_ID = 'roadmap_kcc_full_consolidation_11000'
CUMA_11000_VERSION = '1.100.0'

CUMA_11000_KCC_DEVICE_PROFILES = {
    'Kindle 1 (KCC)': {'width': 600, 'height': 670, 'dpi': 167, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle 2 (KCC)': {'width': 600, 'height': 670, 'dpi': 167, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle DX/DXG (KCC)': {'width': 824, 'height': 1000, 'dpi': 150, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Keyboard/Touch (KCC)': {'width': 600, 'height': 800, 'dpi': 167, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle 5/7/8/10 (KCC)': {'width': 600, 'height': 800, 'dpi': 167, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Paperwhite 1/2 (KCC)': {'width': 758, 'height': 1024, 'dpi': 212, 'jpeg_quality': 94, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Voyage (KCC)': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Paperwhite 3/4/Oasis (KCC)': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Oasis 2/3 (KCC)': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle 11 (KCC)': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Paperwhite 5/Signature (KCC)': {'width': 1236, 'height': 1648, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Paperwhite 6 (KCC)': {'width': 1272, 'height': 1696, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Scribe 1/2 (KCC)': {'width': 1860, 'height': 2480, 'dpi': 300, 'jpeg_quality': 96, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.06, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Colorsoft (KCC)': {'width': 1272, 'height': 1696, 'dpi': 300, 'jpeg_quality': 96, 'gamma': 1.0, 'contrast': 1.04, 'sharpen': 0.06, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kindle Scribe 3/Colorsoft (KCC)': {'width': 1986, 'height': 2648, 'dpi': 300, 'jpeg_quality': 96, 'gamma': 1.0, 'contrast': 1.05, 'sharpen': 0.06, 'margin': 0, 'category': 'Kindle', 'source': 'KCC/ISC'},
    'Kobo Mini/Touch (KCC)': {'width': 600, 'height': 800, 'dpi': 167, 'jpeg_quality': 92, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.08, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Glo/Aura/Nia (KCC)': {'width': 758, 'height': 1024, 'dpi': 212, 'jpeg_quality': 94, 'gamma': 1.0, 'contrast': 1.07, 'sharpen': 0.09, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Glo HD/Clara/Clara 2E (KCC)': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Clara Colour (KCC)': {'width': 1072, 'height': 1448, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.04, 'sharpen': 0.06, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Libra/Libra 2 (KCC)': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.08, 'sharpen': 0.10, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Libra Colour (KCC)': {'width': 1264, 'height': 1680, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.04, 'sharpen': 0.06, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Aura ONE/Elipsa (KCC)': {'width': 1404, 'height': 1872, 'dpi': 227, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.06, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'Kobo Forma/Sage (KCC)': {'width': 1440, 'height': 1920, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.06, 'sharpen': 0.06, 'margin': 0, 'category': 'Kobo', 'source': 'KCC/ISC'},
    'reMarkable 1/2 (KCC)': {'width': 1404, 'height': 1872, 'dpi': 226, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.05, 'sharpen': 0.04, 'margin': 0, 'category': 'reMarkable', 'source': 'KCC/ISC'},
    'reMarkable Paper Pro (KCC)': {'width': 1620, 'height': 2160, 'dpi': 229, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.05, 'sharpen': 0.04, 'margin': 0, 'category': 'reMarkable', 'source': 'KCC/ISC'},
    'reMarkable Paper Pro Move (KCC)': {'width': 954, 'height': 1696, 'dpi': 264, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.05, 'sharpen': 0.04, 'margin': 0, 'category': 'reMarkable', 'source': 'KCC/ISC'},
}

CUMA_11000_PROCESSING_DEFAULTS = {
    'reading_order': 'Ocidental',
    'auto_crop': False,
    'auto_crop_strength': 'Normal',
    'remove_page_numbers': False,
    'split_double_pages': False,
    'split_keep_original': False,
    'webtoon_split': False,
    'webtoon_max_ratio': 2.8,
    'image_preset': 'Original',
    'cbz_zip_input': True,
    'rar_7z_input': True,
    'metadata': {'title': '', 'creator': '', 'series': '', 'volume': '', 'language': 'pt-BR', 'description': ''},
}
CUMA_11000_IMAGE_PRESETS = ('Original', 'Mangá preto e branco', 'E-reader contraste alto', 'E-reader cinza suave', 'Colorido preservado', 'Arquivo menor', 'Alta qualidade')
CUMA_11000_READING_ORDERS = ('Ocidental', 'Mangá')
CUMA_11000_CROP_STRENGTHS = ('Suave', 'Normal', 'Forte')
CUMA_11000_ARCHIVE_EXTS = ('.cbz', '.zip', '.cbr', '.rar', '.7z')


def _cuma_11000_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = str(context)
        if exc is not None:
            msg += f': {type(exc).__name__}: {exc}'
        write_log(msg)
    except Exception:
        pass


def _cuma_11000_deep_merge(base, overlay):
    if isinstance(base, dict) and isinstance(overlay, dict):
        out = dict(base)
        for k, v in overlay.items():
            out[k] = _cuma_11000_deep_merge(out.get(k), v) if k in out else v
        return out
    return overlay if overlay is not None else base


def _cuma_11000_processing_settings() -> dict:
    try:
        data = cuma_settings_section('advanced_processing', {})
        if not isinstance(data, dict):
            data = {}
        return _cuma_11000_deep_merge(CUMA_11000_PROCESSING_DEFAULTS, data)
    except Exception:
        return dict(CUMA_11000_PROCESSING_DEFAULTS)


def _cuma_11000_save_processing_settings(data: dict) -> None:
    try:
        cuma_settings_set_section('advanced_processing', _cuma_11000_deep_merge(CUMA_11000_PROCESSING_DEFAULTS, data if isinstance(data, dict) else {}))
    except Exception as exc:
        _cuma_11000_log('Falha ao salvar configurações avançadas 1.100.0', exc)


def _cuma_11000_natural_key(value) -> list:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(value))]


def _cuma_11000_profile_sort_key(name: str) -> tuple:
    text = str(name)
    order = ('XTEINK', 'Kindle', 'Kobo', 'reMarkable', 'BOOX', 'PocketBook', 'Smartphone', 'Tablet', 'Personalizado')
    idx = 99
    for i, prefix in enumerate(order):
        if text.startswith(prefix):
            idx = i
            break
    return (idx, text.lower())


def _cuma_11000_default_device_profiles() -> dict:
    try:
        prev_defaults = _CUMA_11000_RUNTIME.get('default_profiles')
        data = prev_defaults() if callable(prev_defaults) else {}
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    for k, v in CUMA_11000_KCC_DEVICE_PROFILES.items():
        data.setdefault(k, dict(v))
    data.setdefault('Tablet 8" genérico', {'width': 1200, 'height': 1920, 'dpi': 280, 'jpeg_quality': 94, 'gamma': 1.0, 'contrast': 1.03, 'sharpen': 0.04, 'margin': 0, 'category': 'Tablet'})
    data.setdefault('Tablet 10" genérico', {'width': 1600, 'height': 2560, 'dpi': 300, 'jpeg_quality': 95, 'gamma': 1.0, 'contrast': 1.02, 'sharpen': 0.03, 'margin': 0, 'category': 'Tablet'})
    return data


def _cuma_11000_device_profiles() -> dict:
    try:
        data = _CUMA_11000_RUNTIME.get('device_profiles')()
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    for k, v in _cuma_11000_default_device_profiles().items():
        data.setdefault(k, dict(v))
    return data


def _cuma_11000_refresh_device_globals() -> None:
    try:
        data = _cuma_11000_device_profiles()
        globals()['XTEINK_DEVICE_PROFILES'] = {k: (int(v.get('width', 600)), int(v.get('height', 800))) for k, v in data.items() if isinstance(v, dict)}
        globals()['XTEINK_DEVICES'] = tuple(sorted(globals()['XTEINK_DEVICE_PROFILES'].keys(), key=_cuma_11000_profile_sort_key))
    except Exception as exc:
        _cuma_11000_log('Falha ao atualizar perfis 1.100.0', exc)


def _cuma_11000_safe_bool_var(var, default=False) -> bool:
    try:
        return bool(var.get())
    except Exception:
        return bool(default)


def _cuma_11000_safe_str_var(var, default='') -> str:
    try:
        return str(var.get())
    except Exception:
        return str(default)


def _cuma_11000_app_processing_settings(self=None) -> dict:
    data = _cuma_11000_processing_settings()
    if self is not None:
        try:
            data['reading_order'] = _cuma_11000_safe_str_var(getattr(self, 'cuma_reading_order', None), data.get('reading_order', 'Ocidental'))
            data['auto_crop'] = _cuma_11000_safe_bool_var(getattr(self, 'cuma_auto_crop', None), data.get('auto_crop', False))
            data['auto_crop_strength'] = _cuma_11000_safe_str_var(getattr(self, 'cuma_auto_crop_strength', None), data.get('auto_crop_strength', 'Normal'))
            data['remove_page_numbers'] = _cuma_11000_safe_bool_var(getattr(self, 'cuma_remove_page_numbers', None), data.get('remove_page_numbers', False))
            data['split_double_pages'] = _cuma_11000_safe_bool_var(getattr(self, 'cuma_split_double_pages', None), data.get('split_double_pages', False))
            data['split_keep_original'] = _cuma_11000_safe_bool_var(getattr(self, 'cuma_split_keep_original', None), data.get('split_keep_original', False))
            data['webtoon_split'] = _cuma_11000_safe_bool_var(getattr(self, 'cuma_webtoon_split', None), data.get('webtoon_split', False))
            data['image_preset'] = _cuma_11000_safe_str_var(getattr(self, 'cuma_image_preset', None), data.get('image_preset', 'Original'))
        except Exception:
            pass
    return data


def _cuma_11000_set_processing_from_app(self) -> None:
    _cuma_11000_save_processing_settings(_cuma_11000_app_processing_settings(self))


def _cuma_11000_find_content_bbox(img: Image.Image, strength='Normal'):
    try:
        arr = np.asarray(img.convert('L'))
        if arr.size == 0:
            return None
        if strength == 'Suave':
            white_delta, black_delta, min_ratio = 18, 18, 0.003
        elif strength == 'Forte':
            white_delta, black_delta, min_ratio = 8, 8, 0.001
        else:
            white_delta, black_delta, min_ratio = 12, 12, 0.002
        edges = np.concatenate([arr[:5, :].ravel(), arr[-5:, :].ravel(), arr[:, :5].ravel(), arr[:, -5:].ravel()])
        bg = float(np.median(edges)) if edges.size else 255.0
        mask = arr < max(0, bg - white_delta) if bg >= 128 else arr > min(255, bg + black_delta)
        if float(mask.mean()) < min_ratio:
            return None
        ys, xs = np.where(mask)
        if len(xs) == 0 or len(ys) == 0:
            return None
        left, right = int(xs.min()), int(xs.max()) + 1
        top, bottom = int(ys.min()), int(ys.max()) + 1
        if (right - left) < img.width * 0.30 or (bottom - top) < img.height * 0.30:
            return None
        pad = 6 if strength == 'Forte' else 12 if strength == 'Normal' else 20
        left = max(0, left - pad); top = max(0, top - pad)
        right = min(img.width, right + pad); bottom = min(img.height, bottom + pad)
        if (right - left) >= img.width * 0.985 and (bottom - top) >= img.height * 0.985:
            return None
        return (left, top, right, bottom)
    except Exception as exc:
        _cuma_11000_log('Corte automático ignorado', exc)
        return None


def _cuma_11000_crop_margins(img: Image.Image, settings: dict) -> Image.Image:
    if not settings.get('auto_crop'):
        return img
    bbox = _cuma_11000_find_content_bbox(img, settings.get('auto_crop_strength', 'Normal'))
    if not bbox:
        return img
    try:
        return img.crop(bbox)
    except Exception:
        return img


def _cuma_11000_remove_page_number_area(img: Image.Image, settings: dict) -> Image.Image:
    if not settings.get('remove_page_numbers'):
        return img
    try:
        cut = int(img.height * 0.965)
        if cut > img.height * 0.80:
            return img.crop((0, 0, img.width, cut))
    except Exception:
        pass
    return img


def _cuma_11000_split_double_page(img: Image.Image, settings: dict) -> list[Image.Image]:
    if not settings.get('split_double_pages'):
        return [img]
    try:
        ratio = img.width / max(1, img.height)
        if ratio < 1.22:
            return [img]
        mid = img.width // 2
        left = img.crop((0, 0, mid, img.height))
        right = img.crop((mid, 0, img.width, img.height))
        pages = [right, left] if str(settings.get('reading_order', 'Ocidental')).lower().startswith('mang') else [left, right]
        if settings.get('split_keep_original'):
            return [img] + pages
        try:
            img.close()
        except Exception:
            pass
        return pages
    except Exception as exc:
        _cuma_11000_log('Divisão de página dupla ignorada', exc)
        return [img]


def _cuma_11000_split_webtoon(img: Image.Image, settings: dict) -> list[Image.Image]:
    if not settings.get('webtoon_split'):
        return [img]
    try:
        max_ratio = float(settings.get('webtoon_max_ratio', 2.8) or 2.8)
        if img.height / max(1, img.width) <= max_ratio:
            return [img]
        segment_h = int(max(400, min(img.width * 2, img.height)))
        out = []
        y = 0
        while y < img.height:
            bottom = min(img.height, y + segment_h)
            out.append(img.crop((0, y, img.width, bottom)))
            y = bottom
        try:
            img.close()
        except Exception:
            pass
        return out or [img]
    except Exception as exc:
        _cuma_11000_log('Divisão webtoon ignorada', exc)
        return [img]


def _cuma_11000_apply_image_preset(img: Image.Image, settings: dict) -> Image.Image:
    preset = str(settings.get('image_preset') or 'Original')
    try:
        from PIL import ImageEnhance, ImageOps
        im = img.convert('RGB')
        if preset == 'Original':
            return im
        if preset == 'Colorido preservado':
            im = ImageEnhance.Contrast(im).enhance(1.04)
            im = ImageEnhance.Sharpness(im).enhance(1.05)
            return im
        if preset == 'Arquivo menor':
            im = im.convert('L')
            im = ImageEnhance.Contrast(im).enhance(1.08)
            return im.convert('RGB')
        if preset == 'Alta qualidade':
            im = ImageEnhance.Contrast(im).enhance(1.06)
            im = ImageEnhance.Sharpness(im).enhance(1.18)
            return im
        gray = im.convert('L')
        if preset == 'Mangá preto e branco':
            gray = ImageOps.autocontrast(gray, cutoff=1)
            gray = ImageEnhance.Contrast(gray).enhance(1.35)
            gray = gray.point(lambda p: 255 if p > 205 else 0 if p < 65 else p)
            return gray.convert('RGB')
        if preset == 'E-reader contraste alto':
            gray = ImageOps.autocontrast(gray, cutoff=1)
            gray = ImageEnhance.Contrast(gray).enhance(1.28)
            gray = ImageEnhance.Sharpness(gray).enhance(1.15)
            return gray.convert('RGB')
        if preset == 'E-reader cinza suave':
            gray = ImageOps.autocontrast(gray, cutoff=0.5)
            gray = ImageEnhance.Contrast(gray).enhance(1.10)
            return gray.convert('RGB')
        return im
    except Exception as exc:
        _cuma_11000_log('Preset de imagem ignorado', exc)
        return img.convert('RGB')


def _cuma_11000_process_source_image(img: Image.Image, target: Optional[tuple[int, int]], settings: dict):
    try:
        base = img.convert('RGB')
    except Exception:
        base = img
    base = _cuma_11000_crop_margins(base, settings)
    base = _cuma_11000_remove_page_number_area(base, settings)
    base = _cuma_11000_crop_margins(base, settings)
    pages = []
    for part in _cuma_11000_split_double_page(base, settings):
        for segment in _cuma_11000_split_webtoon(part, settings):
            processed = _cuma_11000_apply_image_preset(segment, settings)
            fitted = fit_to_target(processed, target) if target else processed
            pages.append(fitted)
            try:
                if processed is not fitted:
                    processed.close()
            except Exception:
                pass
            try:
                if segment is not processed and segment is not fitted:
                    segment.close()
            except Exception:
                pass
    return pages


def _cuma_11000_iter_pdf_pages_as_images(pdf_path: Path, target: Optional[tuple[int, int]] = None, quality_zoom: float = 2.0):
    settings = _cuma_11000_processing_settings()
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            if target:
                zoom = max(target[0] / max(page.rect.width, 1), target[1] / max(page.rect.height, 1)) * 1.35
            else:
                zoom = quality_zoom
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            im = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            try:
                for processed in _cuma_11000_process_source_image(im, target, settings):
                    yield processed
            finally:
                try:
                    im.close()
                except Exception:
                    pass
    finally:
        doc.close()


def _cuma_11000_archive_image_names(zf: zipfile.ZipFile) -> list[str]:
    names = []
    for n in zf.namelist():
        suffix = Path(n).suffix.lower()
        if suffix in SUPPORTED_IMAGE_EXT and not n.endswith('/'):
            names.append(n)
    return sorted(names, key=_cuma_11000_natural_key)


def _cuma_11000_extract_with_7z(archive_path: Path, tmp_dir: Path) -> list[Path]:
    exe = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
    if not exe:
        raise RuntimeError('Arquivos CBR/RAR/7Z precisam do 7-Zip instalado e disponível no PATH. CBZ/ZIP funciona nativamente.')
    cmd = [exe, 'x', '-y', f'-o{str(tmp_dir)}', str(archive_path)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'Falha ao extrair arquivo compactado com 7-Zip.').strip())
    files = [p for p in tmp_dir.rglob('*') if p.suffix.lower() in SUPPORTED_IMAGE_EXT and p.is_file()]
    return sorted(files, key=lambda p: _cuma_11000_natural_key(p.as_posix()))


def _cuma_11000_iter_archive_images(archive_path: Path, target: Optional[tuple[int, int]] = None):
    settings = _cuma_11000_processing_settings()
    suffix = archive_path.suffix.lower()
    if suffix in ('.zip', '.cbz'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            for name in _cuma_11000_archive_image_names(z):
                try:
                    with z.open(name) as f:
                        data = BytesIO(f.read())
                    im = Image.open(data).convert('RGB')
                    try:
                        if im.width < 80 or im.height < 80:
                            continue
                        for processed in _cuma_11000_process_source_image(im, target, settings):
                            yield processed
                    finally:
                        try:
                            im.close()
                        except Exception:
                            pass
                except Exception as exc:
                    _cuma_11000_log(f'Imagem ignorada no compactado: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='cuma_archive_') as td:
            files = _cuma_11000_extract_with_7z(archive_path, Path(td))
            for p in files:
                try:
                    with Image.open(p) as im:
                        im = im.convert('RGB')
                        if im.width < 80 or im.height < 80:
                            continue
                        for processed in _cuma_11000_process_source_image(im, target, settings):
                            yield processed
                except Exception as exc:
                    _cuma_11000_log(f'Imagem ignorada no compactado: {p.name}', exc)
    else:
        raise RuntimeError('Arquivo compactado não suportado. Use CBZ, ZIP, CBR, RAR ou 7Z.')


def _cuma_11000_iter_epub_images(epub_path: Path, target: tuple[int, int]):
    if not epub_path.exists():
        raise RuntimeError('EPUB não encontrado.')
    settings = _cuma_11000_processing_settings()
    with zipfile.ZipFile(epub_path, 'r') as z:
        names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_cuma_11000_natural_key)
        for name in names:
            try:
                with z.open(name) as f:
                    data = BytesIO(f.read())
                im = Image.open(data).convert('RGB')
                try:
                    if im.width < 80 or im.height < 80:
                        continue
                    for processed in _cuma_11000_process_source_image(im, target, settings):
                        yield processed
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
            except Exception as exc:
                _cuma_11000_log(f'Imagem ignorada no EPUB: {name}', exc)


def _cuma_11000_extract_epub_images(epub_path: Path, target: tuple[int, int]) -> list[Image.Image]:
    images = list(_cuma_11000_iter_epub_images(epub_path, target))
    if not images:
        raise RuntimeError('Não encontrei imagens úteis dentro do EPUB. EPUB textual puro ainda não é renderizado nativamente.')
    return images


def _cuma_11000_epub_metadata(title: str) -> dict:
    settings = _cuma_11000_processing_settings()
    meta = settings.get('metadata', {}) if isinstance(settings.get('metadata'), dict) else {}
    return {
        'title': str(meta.get('title') or title or 'CUMA'),
        'creator': str(meta.get('creator') or ''),
        'series': str(meta.get('series') or ''),
        'volume': str(meta.get('volume') or ''),
        'language': str(meta.get('language') or 'pt-BR'),
        'description': str(meta.get('description') or ''),
    }


def _cuma_11000_epub_opf_metadata(meta: dict, uid: str) -> str:
    title = html.escape(meta.get('title') or 'CUMA')
    lang = html.escape(meta.get('language') or 'pt-BR')
    creator = html.escape(meta.get('creator') or '')
    desc = html.escape(meta.get('description') or '')
    series = html.escape(meta.get('series') or '')
    volume = html.escape(meta.get('volume') or '')
    extra = ''
    if creator:
        extra += f'<dc:creator>{creator}</dc:creator>'
    if desc:
        extra += f'<dc:description>{desc}</dc:description>'
    if series:
        extra += f'<meta property="belongs-to-collection">{series}</meta><meta property="collection-type">series</meta>'
    if volume:
        extra += f'<meta property="group-position">{volume}</meta>'
    return f'<dc:identifier id="uid">{uid}</dc:identifier><dc:title>{title}</dc:title><dc:language>{lang}</dc:language>{extra}'


def _cuma_11000_create_image_epub_from_iter(image_iter, output_epub: Path, title: str, quality: int = 92) -> None:
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    uid = str(uuid.uuid4())
    manifest = []
    spine = []
    nav = []
    meta = _cuma_11000_epub_metadata(title)
    with zipfile.ZipFile(output_epub, 'w') as z:
        z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
        count = 0
        for count, im in enumerate(image_iter, 1):
            try:
                img_name = f'images/page_{count:04d}.jpg'
                html_name = f'page_{count:04d}.xhtml'
                bio = BytesIO()
                q = int(max(50, min(100, quality or 92)))
                im.convert('RGB').save(bio, format='JPEG', quality=q, optimize=True)
                z.writestr('OEBPS/' + img_name, bio.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
                z.writestr('OEBPS/' + html_name, f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Página {count}</title><style>html,body{{margin:0;padding:0;background:white;}} img{{width:100%;height:100%;object-fit:contain;display:block;}}</style></head><body><img src="{img_name}" alt="Página {count}"/></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
                manifest.append(f'<item id="p{count}" href="{html_name}" media-type="application/xhtml+xml"/>')
                manifest.append(f'<item id="img{count}" href="{img_name}" media-type="image/jpeg"/>')
                spine.append(f'<itemref idref="p{count}"/>')
                nav.append(f'<li><a href="{html_name}">Página {count}</a></li>')
            finally:
                try:
                    im.close()
                except Exception:
                    pass
        if count <= 0:
            raise RuntimeError('Nenhuma imagem para criar EPUB.')
        z.writestr('OEBPS/nav.xhtml', f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Sumário</title></head><body><nav epub:type="toc"><ol>{''.join(nav)}</ol></nav></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/content.opf', f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{_cuma_11000_epub_opf_metadata(meta, uid)}</metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>''', compress_type=zipfile.ZIP_DEFLATED)


def _cuma_11000_create_image_epub(images: list[Image.Image], output_epub: Path, title: str, quality: int = 92) -> None:
    if not images:
        raise RuntimeError('Nenhuma imagem para criar EPUB.')
    return _cuma_11000_create_image_epub_from_iter(iter(images), output_epub, title, quality)


def _cuma_11000_create_image_epub_from_pdf(pdf_path: Path, output_epub: Path, title: str, target: Optional[tuple[int, int]] = None, quality: int = 92) -> None:
    return _cuma_11000_create_image_epub_from_iter(_cuma_11000_iter_pdf_pages_as_images(pdf_path, target=target), output_epub, title, quality)


def _cuma_11000_create_epub_from_archive(archive_path: Path, output_epub: Path, title: str, target: Optional[tuple[int, int]] = None, quality: int = 92) -> None:
    return _cuma_11000_create_image_epub_from_iter(_cuma_11000_iter_archive_images(archive_path, target=target), output_epub, title, quality)


def _cuma_11000_create_xtch_from_archive(archive_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    images = list(_cuma_11000_iter_archive_images(archive_path, target=target))
    try:
        return create_xtch_from_images(images, output_xtch, title, target)
    finally:
        for im in images:
            try:
                im.close()
            except Exception:
                pass


def _cuma_11000_run_xteink_job(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    src = Path(src)
    suffix = src.suffix.lower()
    if suffix == '.pdf' and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_image_epub_from_pdf(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            create_xtch_from_pdf(src, out, src.stem, target)
            outputs.append(out)
    elif suffix == '.epub' and flags.get('epub_xtch'):
        out = unique_path(out_dir / f'{src.stem}.xtch')
        create_xtch_from_epub(src, out, src.stem, target)
        outputs.append(out)
    elif suffix in CUMA_11000_ARCHIVE_EXTS and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_epub_from_archive(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_archive(src, out, src.stem, target)
            outputs.append(out)
    else:
        raise RuntimeError('Formato/combinação de conversão não suportado. Use PDF, EPUB, CBZ/ZIP ou CBR/RAR/7Z com 7-Zip instalado.')
    return outputs


def _cuma_11000_first_source_image(path: Path, target: Optional[tuple[int, int]] = None):
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        doc = fitz.open(str(path))
        try:
            if len(doc) <= 0:
                return None
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        finally:
            doc.close()
    if suffix == '.epub':
        with zipfile.ZipFile(path, 'r') as z:
            names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_cuma_11000_natural_key)
            if not names:
                return None
            with z.open(names[0]) as f:
                return Image.open(BytesIO(f.read())).convert('RGB')
    if suffix in CUMA_11000_ARCHIVE_EXTS:
        it = _cuma_11000_iter_archive_images(path, target=None)
        try:
            return next(it)
        except StopIteration:
            return None
    if suffix in SUPPORTED_IMAGE_EXT:
        return Image.open(path).convert('RGB')
    return None


def _cuma_11000_photo_for_preview(img: Image.Image, max_w=420, max_h=520):
    copy = img.copy().convert('RGB')
    copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(copy)


def _cuma_11000_open_before_after_preview(self) -> None:
    try:
        selected = []
        try:
            if hasattr(self, 'xteink_tree') and self.xteink_tree.selection():
                selected = [p for p in getattr(self, 'xteink_files', []) if _cuma_11008_path_key(p) in set(self.xteink_tree.selection())]
        except Exception:
            pass
        if not selected:
            try:
                selected = self.xteink_selected_paths()
            except Exception:
                selected = []
        if not selected:
            messagebox.showinfo('Prévia antes/depois', 'Selecione um item na aba Converter.')
            return
        src = Path(selected[0])
        original = _cuma_11000_first_source_image(src, target=None)
        if original is None:
            messagebox.showwarning('Prévia antes/depois', 'Não consegui abrir uma imagem de prévia para este arquivo.')
            return
        settings = _cuma_11000_app_processing_settings(self)
        target = self.xteink_target() if hasattr(self, 'xteink_target') else None
        processed_pages = _cuma_11000_process_source_image(original.copy(), target, settings)
        processed = processed_pages[0] if processed_pages else original.copy()
        top = tk.Toplevel(self.root)
        top.title('Prévia antes/depois - CUMA 1.100.0')
        top.geometry('980x680')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass
        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Prévia antes/depois', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 6))
        ttk.Label(wrap, text=f'{src.name}  •  Preset: {settings.get("image_preset")}  •  Leitura: {settings.get("reading_order")}', style='Muted.TLabel').pack(anchor='w', pady=(0, 12))
        grid = ttk.Frame(wrap, style='Card.TFrame')
        grid.pack(fill='both', expand=True)
        left = ttk.Frame(grid, style='Card.TFrame'); right = ttk.Frame(grid, style='Card.TFrame')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8)); right.pack(side='left', fill='both', expand=True, padx=(8, 0))
        ttk.Label(left, text='Original', style='Strong.TLabel').pack(anchor='center')
        ttk.Label(right, text='Processado', style='Strong.TLabel').pack(anchor='center')
        photo1 = _cuma_11000_photo_for_preview(original); photo2 = _cuma_11000_photo_for_preview(processed)
        lbl1 = ttk.Label(left, image=photo1); lbl2 = ttk.Label(right, image=photo2)
        lbl1.image = photo1; lbl2.image = photo2
        lbl1.pack(expand=True, pady=8); lbl2.pack(expand=True, pady=8)
        ttk.Label(wrap, text='Ative/desative corte, páginas duplas, webtoon e presets para comparar antes de converter o arquivo inteiro.', style='Muted.TLabel', wraplength=900, justify='left').pack(anchor='w', pady=(10, 0))
        ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(12, 0))
    except Exception as exc:
        _cuma_11000_log('Falha na prévia antes/depois', exc)
        messagebox.showerror('Prévia antes/depois', friendly_error(exc))


def _cuma_11000_open_metadata_editor(self) -> None:
    try:
        data = _cuma_11000_app_processing_settings(self)
        meta = data.get('metadata', {}) if isinstance(data.get('metadata'), dict) else {}
        top = tk.Toplevel(self.root)
        top.title('Metadados do livro - CUMA 1.100.0')
        top.geometry('680x520')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass
        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Metadados para EPUB/saídas', style='TitleSmall.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))
        vars_ = {k: tk.StringVar(value=str(meta.get(k, 'pt-BR' if k == 'language' else ''))) for k in ('title', 'creator', 'series', 'volume', 'language')}
        labels = [('title','Título'),('creator','Autor/criador'),('series','Série'),('volume','Volume'),('language','Idioma')]
        for r, (key, label) in enumerate(labels, start=1):
            ttk.Label(wrap, text=label, style='Muted.TLabel').grid(row=r, column=0, sticky='w', pady=5, padx=(0, 10))
            ttk.Entry(wrap, textvariable=vars_[key], width=56).grid(row=r, column=1, sticky='ew', pady=5)
        ttk.Label(wrap, text='Descrição', style='Muted.TLabel').grid(row=6, column=0, sticky='nw', pady=5, padx=(0, 10))
        txt = tk.Text(wrap, height=8, wrap='word')
        txt.grid(row=6, column=1, sticky='nsew', pady=5)
        txt.insert('1.0', str(meta.get('description', '')))
        wrap.columnconfigure(1, weight=1); wrap.rowconfigure(6, weight=1)
        def save_meta():
            data2 = _cuma_11000_app_processing_settings(self)
            data2['metadata'] = {k: v.get() for k, v in vars_.items()}
            data2['metadata']['description'] = txt.get('1.0', 'end').strip()
            _cuma_11000_save_processing_settings(data2)
            messagebox.showinfo('Metadados', 'Metadados salvos para as próximas conversões EPUB.')
            top.destroy()
        btns = ttk.Frame(wrap, style='Card.TFrame')
        btns.grid(row=7, column=0, columnspan=2, sticky='ew', pady=(12, 0))
        ttk.Button(btns, text='Salvar', command=save_meta, style='Accent.TButton').pack(side='right', padx=(8, 0))
        ttk.Button(btns, text='Cancelar', command=top.destroy, style='Ghost.TButton').pack(side='right')
    except Exception as exc:
        _cuma_11000_log('Falha no editor de metadados', exc)
        messagebox.showerror('Metadados', friendly_error(exc))


def _cuma_11000_add_advanced_converter_panel(self) -> None:
    try:
        container = getattr(self, 'tab_xteink', None)
        if container is None or getattr(self, '_cuma_11000_panel_added', False):
            return
        self._cuma_11000_panel_added = True
        settings = _cuma_11000_app_processing_settings(self)
        if not hasattr(self, 'cuma_reading_order'):
            self.cuma_reading_order = tk.StringVar(value=settings.get('reading_order', 'Ocidental'))
        if not hasattr(self, 'cuma_image_preset'):
            self.cuma_image_preset = tk.StringVar(value=settings.get('image_preset', 'Original'))
        if not hasattr(self, 'cuma_auto_crop'):
            self.cuma_auto_crop = tk.BooleanVar(value=bool(settings.get('auto_crop', False)))
        if not hasattr(self, 'cuma_auto_crop_strength'):
            self.cuma_auto_crop_strength = tk.StringVar(value=settings.get('auto_crop_strength', 'Normal'))
        if not hasattr(self, 'cuma_remove_page_numbers'):
            self.cuma_remove_page_numbers = tk.BooleanVar(value=bool(settings.get('remove_page_numbers', False)))
        if not hasattr(self, 'cuma_split_double_pages'):
            self.cuma_split_double_pages = tk.BooleanVar(value=bool(settings.get('split_double_pages', False)))
        if not hasattr(self, 'cuma_split_keep_original'):
            self.cuma_split_keep_original = tk.BooleanVar(value=bool(settings.get('split_keep_original', False)))
        if not hasattr(self, 'cuma_webtoon_split'):
            self.cuma_webtoon_split = tk.BooleanVar(value=bool(settings.get('webtoon_split', False)))
        kwargs = {'fill': 'x', 'pady': (0, 10)}
        children = list(container.winfo_children())
        if children:
            kwargs['before'] = children[0]
        panel = ttk.LabelFrame(container, text='Otimização de leitura e E-ink - 1.100.0', padding=12, style='Card.TLabelframe')
        panel.pack(**kwargs)
        ttk.Label(panel, text='Leitura', style='Muted.TLabel').grid(row=0, column=0, sticky='w', padx=(0, 8), pady=4)
        cb_order = ttk.Combobox(panel, textvariable=self.cuma_reading_order, values=CUMA_11000_READING_ORDERS, state='readonly', width=14)
        cb_order.grid(row=0, column=1, sticky='w', pady=4)
        ttk.Label(panel, text='Preset de imagem', style='Muted.TLabel').grid(row=0, column=2, sticky='w', padx=(18, 8), pady=4)
        cb_preset = ttk.Combobox(panel, textvariable=self.cuma_image_preset, values=CUMA_11000_IMAGE_PRESETS, state='readonly', width=24)
        cb_preset.grid(row=0, column=3, sticky='w', pady=4)
        ttk.Label(panel, text='Corte', style='Muted.TLabel').grid(row=0, column=4, sticky='w', padx=(18, 8), pady=4)
        cb_crop = ttk.Combobox(panel, textvariable=self.cuma_auto_crop_strength, values=CUMA_11000_CROP_STRENGTHS, state='readonly', width=10)
        cb_crop.grid(row=0, column=5, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Remover margens', variable=self.cuma_auto_crop, command=lambda: _cuma_11000_set_processing_from_app(self)).grid(row=1, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Remover número/rodapé', variable=self.cuma_remove_page_numbers, command=lambda: _cuma_11000_set_processing_from_app(self)).grid(row=1, column=2, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Dividir páginas duplas', variable=self.cuma_split_double_pages, command=lambda: _cuma_11000_set_processing_from_app(self)).grid(row=1, column=4, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Manter original ao dividir', variable=self.cuma_split_keep_original, command=lambda: _cuma_11000_set_processing_from_app(self)).grid(row=2, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Webtoon/imagens longas', variable=self.cuma_webtoon_split, command=lambda: _cuma_11000_set_processing_from_app(self)).grid(row=2, column=2, columnspan=2, sticky='w', pady=4)
        ttk.Button(panel, text='Prévia antes/depois', command=lambda: _cuma_11000_open_before_after_preview(self), style='Accent.TButton').grid(row=2, column=4, sticky='w', padx=(18, 6), pady=4)
        ttk.Button(panel, text='Metadados', command=lambda: _cuma_11000_open_metadata_editor(self), style='Ghost.TButton').grid(row=2, column=5, sticky='w', pady=4)
        for cb in (cb_order, cb_preset, cb_crop):
            cb.bind('<<ComboboxSelected>>', lambda _e: _cuma_11000_set_processing_from_app(self))
        ttk.Label(panel, text='CBZ/ZIP funcionam nativamente. CBR/RAR/7Z usam 7-Zip se estiver instalado no Windows.', style='Muted.TLabel', wraplength=950, justify='left').grid(row=3, column=0, columnspan=6, sticky='w', pady=(8, 0))
    except Exception as exc:
        _cuma_11000_log('Falha ao adicionar painel 1.100.0', exc)


def _cuma_11000_setup_vars(self):
    _CUMA_11000_RUNTIME['setup_vars'](self)
    try:
        settings = _cuma_11000_processing_settings()
        self.cuma_reading_order = tk.StringVar(value=settings.get('reading_order', 'Ocidental'))
        self.cuma_auto_crop = tk.BooleanVar(value=bool(settings.get('auto_crop', False)))
        self.cuma_auto_crop_strength = tk.StringVar(value=settings.get('auto_crop_strength', 'Normal'))
        self.cuma_remove_page_numbers = tk.BooleanVar(value=bool(settings.get('remove_page_numbers', False)))
        self.cuma_split_double_pages = tk.BooleanVar(value=bool(settings.get('split_double_pages', False)))
        self.cuma_split_keep_original = tk.BooleanVar(value=bool(settings.get('split_keep_original', False)))
        self.cuma_webtoon_split = tk.BooleanVar(value=bool(settings.get('webtoon_split', False)))
        self.cuma_image_preset = tk.StringVar(value=settings.get('image_preset', 'Original'))
    except Exception as exc:
        _cuma_11000_log('setup_vars 1.100.0', exc)


def _cuma_11000_save_current_config(self, force: bool = False):
    result = _CUMA_11000_RUNTIME['save_current_config'](self, force)
    try:
        if force or not hasattr(self, 'auto_save_config') or self.auto_save_config.get():
            _cuma_11000_set_processing_from_app(self)
    except Exception as exc:
        _cuma_11000_log('Salvar opções 1.100.0', exc)
    return result


def _cuma_11000_build(self):
    result = _CUMA_11000_RUNTIME['build'](self)
    try:
        _cuma_11000_add_advanced_converter_panel(self)
        _cuma_11000_refresh_device_globals()
    except Exception as exc:
        _cuma_11000_log('build 1.100.0', exc)
    return result


def _cuma_11000_add_xteink_path(self, path: Path) -> bool:
    path = Path(path)
    if path.is_dir():
        added = False
        for f in sorted(path.rglob('*'), key=lambda p: _cuma_11000_natural_key(p.as_posix())):
            if f.suffix.lower() in ('.pdf', '.epub') + CUMA_11000_ARCHIVE_EXTS:
                added = _cuma_11000_add_xteink_path(self, f) or added
        return added
    if path.suffix.lower() not in ('.pdf', '.epub') + CUMA_11000_ARCHIVE_EXTS or not path.exists() or path in getattr(self, 'xteink_files', []):
        return False
    self.xteink_files.append(path)
    iid = _cuma_11008_path_key(path)
    if not self.xteink_tree.exists(iid):
        self.xteink_tree.insert('', 'end', iid=iid, values=(path.name, 'Aguardando', path.suffix[1:].upper(), '', ''))
    self.xteink_input.set(str(path))
    self.update_xteink_counter()
    return True


def _cuma_11000_add_xteink_files(self) -> None:
    files = filedialog.askopenfilenames(title='Adicionar PDF/EPUB/CBZ/ZIP/CBR/RAR/7Z', filetypes=[('Compatíveis', '*.pdf *.epub *.cbz *.zip *.cbr *.rar *.7z'), ('PDF', '*.pdf'), ('EPUB', '*.epub'), ('Compactados', '*.cbz *.zip *.cbr *.rar *.7z'), ('Todos', '*.*')])
    for f in sorted(files, key=_cuma_11000_natural_key):
        self.add_xteink_path(Path(f))


def _cuma_11000_xteink_status_for_src(src: Path, flags: dict) -> str:
    suffix = Path(src).suffix.lower()
    if suffix == '.pdf':
        parts = []
        if flags.get('pdf_epub'): parts.append('PDF→EPUB')
        if flags.get('pdf_xtch'): parts.append('PDF→XTCH')
        return ' + '.join(parts) or 'PDF'
    if suffix == '.epub':
        return 'EPUB→XTCH' if flags.get('epub_xtch') else 'EPUB'
    if suffix in CUMA_11000_ARCHIVE_EXTS:
        parts = []
        if flags.get('pdf_epub'): parts.append('IMG→EPUB')
        if flags.get('pdf_xtch'): parts.append('IMG→XTCH')
        return ' + '.join(parts) or suffix.upper().lstrip('.')
    return suffix.upper().lstrip('.')


def _cuma_11000_open_xteink_settings_window(self) -> None:
    try:
        return _CUMA_11000_RUNTIME['open_xteink_settings_window'](self)
    finally:
        try:
            _cuma_11000_set_processing_from_app(self)
        except Exception:
            pass


def _cuma_11000_create_pdf_from_images_dialog(self) -> None:
    files = filedialog.askopenfilenames(title='Selecione imagens', filetypes=[('Imagens', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'), ('Todos', '*.*')])
    if not files:
        return
    out = filedialog.asksaveasfilename(title='Salvar PDF como', defaultextension='.pdf', filetypes=[('PDF', '*.pdf')])
    if not out:
        return
    try:
        image_paths = sorted([Path(f) for f in files if Path(f).suffix.lower() in SUPPORTED_IMAGE_EXT], key=lambda p: _cuma_11000_natural_key(p.name))
        save_images_to_pdf(image_paths, Path(out))
        self.log(f'PDF criado a partir de imagens: {out}')
        messagebox.showinfo('Concluído', f'PDF criado:\n{out}')
    except Exception as exc:
        messagebox.showerror('Erro', friendly_error(exc))


def _cuma_11000_save_images_to_pdf(image_paths: list[Path], output_pdf: Path) -> None:
    image_paths = sorted([Path(p) for p in image_paths], key=lambda p: _cuma_11000_natural_key(p.name))
    return _CUMA_11000_RUNTIME['save_images_to_pdf'](image_paths, output_pdf)


def _cuma_11000_force_version_files() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11000_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11000_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {'version': CUMA_11000_VERSION, 'date': datetime.now().strftime('%Y-%m-%d'), 'notes': 'Roadmap KCC consolidado: perfis, leitura, E-ink, preview, metadados e compactados.'}
    except Exception:
        pass
    try:
        state = cuma_version_load_state()
        events = state.get('events', [])
        if not isinstance(events, list):
            events = []
        if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11000_UPDATE_ID for e in events):
            events.append({'update_id': CUMA_11000_UPDATE_ID, 'version': CUMA_11000_VERSION, 'base_version': CUMA_VERSION_BASE, 'scale': 'grande', 'description': 'Consolidação das versões 1.082.0, 1.090.0 e 1.100.0: perfis reais, leitura mangá, otimização E-ink, páginas duplas, metadados, preview e compactados.', 'timestamp': datetime.now().isoformat(timespec='seconds')})
        state['events'] = events[-80:]
        state['current_version'] = CUMA_11000_VERSION
        state['base_version'] = CUMA_VERSION_BASE
        cuma_version_save_state(state)
        _cuma_version_write_public_files(state)
        cuma_version_apply_globals(CUMA_11000_VERSION)
    except Exception as exc:
        _cuma_11000_log('Versionamento 1.100.0', exc)


_CUMA_11000_RUNTIME = {
    'setup_vars': App.setup_vars,
    'save_current_config': App.save_current_config,
    'build': App.build,
    'add_xteink_path': getattr(App, 'add_xteink_path', None),
    'add_xteink_files': getattr(App, 'add_xteink_files', None),
    'open_xteink_settings_window': getattr(App, 'open_xteink_settings_window', None),
    'create_pdf_from_images_dialog': getattr(App, 'create_pdf_from_images_dialog', None),
    'default_profiles': globals().get('_cuma_default_device_profiles_settings'),
    'device_profiles': globals().get('_cuma_device_profiles'),
    'save_images_to_pdf': globals().get('save_images_to_pdf'),
}


def _cuma_install_11000_full_roadmap() -> None:
    try:
        _cuma_11000_force_version_files()
        globals()['_cuma_default_device_profiles_settings'] = _cuma_11000_default_device_profiles
        globals()['_cuma_device_profiles'] = _cuma_11000_device_profiles
        _cuma_11000_refresh_device_globals()
        globals()['iter_pdf_pages_as_images'] = _cuma_11000_iter_pdf_pages_as_images
        globals()['iter_epub_images'] = _cuma_11000_iter_epub_images
        globals()['extract_epub_images'] = _cuma_11000_extract_epub_images
        globals()['create_image_epub'] = _cuma_11000_create_image_epub
        globals()['create_image_epub_from_pdf'] = _cuma_11000_create_image_epub_from_pdf
        globals()['_cuma_run_xteink_job'] = _cuma_11000_run_xteink_job
        globals()['_cuma_xteink_status_for_src'] = _cuma_11000_xteink_status_for_src
        globals()['save_images_to_pdf'] = _cuma_11000_save_images_to_pdf
        App.setup_vars = _cuma_11000_setup_vars
        App.save_current_config = _cuma_11000_save_current_config
        App.build = _cuma_11000_build
        App.add_xteink_path = _cuma_11000_add_xteink_path
        App.add_xteink_files = _cuma_11000_add_xteink_files
        App.open_xteink_settings_window = _cuma_11000_open_xteink_settings_window
        if _CUMA_11000_RUNTIME.get('create_pdf_from_images_dialog') is not None:
            App.create_pdf_from_images_dialog = _cuma_11000_create_pdf_from_images_dialog
        App.open_cuma_before_after_preview = _cuma_11000_open_before_after_preview
        App.open_cuma_metadata_editor = _cuma_11000_open_metadata_editor
        try:
            ensure_manual()
        except Exception:
            pass
    except Exception as exc:
        _cuma_11000_log('Instalação do roadmap completo 1.100.0', exc)


_cuma_install_11000_full_roadmap()


# Ajuste técnico 1.100.0: XTCH com contagem real após cortes/divisões.
def _cuma_11000_create_xtch_from_iter_stream(image_iter, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    import tempfile
    output_xtch.parent.mkdir(parents=True, exist_ok=True)
    w, h = target
    sizes = []
    with tempfile.NamedTemporaryFile(prefix='cuma_xtch_pages_', suffix='.bin', delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            for im in image_iter:
                try:
                    blob = xth_page_bytes(im, target)
                    tmp.write(blob)
                    sizes.append(len(blob))
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
        finally:
            pass
    try:
        page_count = len(sizes)
        if page_count <= 0:
            raise RuntimeError('Nenhuma imagem para criar XTCH.')
        if page_count > 65535:
            raise RuntimeError('XTCH suporta no máximo 65535 páginas por arquivo.')
        header_size = 56
        table_offset = header_size
        data_offset = header_size + page_count * 16
        header = struct.pack('<IBBHBBBBIQQQQII', 0x48435458, 1, 0, page_count, 0, 0, 0, 0, 1, 0, table_offset, data_offset, 0, 0, 0)
        with output_xtch.open('wb') as out:
            out.write(header)
            cursor = data_offset
            for size in sizes:
                out.write(struct.pack('<QIHH', cursor, size, w, h))
                cursor += size
            with tmp_path.open('rb') as inp:
                shutil.copyfileobj(inp, out, length=1024 * 1024)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _cuma_11000_create_xtch_from_pdf(pdf_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    return _cuma_11000_create_xtch_from_iter_stream(_cuma_11000_iter_pdf_pages_as_images(pdf_path, target=target), output_xtch, title, target)


def _cuma_11000_create_xtch_from_epub_stream(epub_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    return _cuma_11000_create_xtch_from_iter_stream(_cuma_11000_iter_epub_images(epub_path, target), output_xtch, title, target)


def _cuma_11000_create_xtch_from_archive_stream(archive_path: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    return _cuma_11000_create_xtch_from_iter_stream(_cuma_11000_iter_archive_images(archive_path, target=target), output_xtch, title, target)


def _cuma_11000_run_xteink_job_stream_safe(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    src = Path(src)
    suffix = src.suffix.lower()
    if suffix == '.pdf' and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_image_epub_from_pdf(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_pdf(src, out, src.stem, target)
            outputs.append(out)
    elif suffix == '.epub' and flags.get('epub_xtch'):
        out = unique_path(out_dir / f'{src.stem}.xtch')
        _cuma_11000_create_xtch_from_epub_stream(src, out, src.stem, target)
        outputs.append(out)
    elif suffix in CUMA_11000_ARCHIVE_EXTS and (flags.get('pdf_epub') or flags.get('pdf_xtch')):
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_epub_from_archive(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_archive_stream(src, out, src.stem, target)
            outputs.append(out)
    else:
        raise RuntimeError('Formato/combinação de conversão não suportado. Use PDF, EPUB, CBZ/ZIP ou CBR/RAR/7Z com 7-Zip instalado.')
    return outputs


globals()['create_xtch_from_pdf'] = _cuma_11000_create_xtch_from_pdf
globals()['create_xtch_from_epub'] = _cuma_11000_create_xtch_from_epub_stream
globals()['_cuma_run_xteink_job'] = _cuma_11000_run_xteink_job_stream_safe

def main() -> None:
    install_global_error_handlers()
    if any(arg in ('--debug-env', '/debug-env') for arg in sys.argv[1:]):
        print_environment_diagnostics(); print('Debug completo:', write_full_debug_report()); return
    ensure_manual(); root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk(); install_global_error_handlers(root)
    try:
        App(root)
        root.mainloop()
    except Exception as exc:
        write_error_log(type(exc), exc, exc.__traceback__, 'Falha ao iniciar ou executar o aplicativo')
        raise

# Chamada main movida para o fim por patches finais do CUMA.

# =============================================================================
# CUMA 1.100.0 - CORREÇÃO OFICIAL DE CONEXÕES GITHUB SOLDIEG
# =============================================================================
# Mantém a versão 1.100.0 e corrige as conexões de atualização para o repositório
# oficial informado pelo autor: https://github.com/soldieg/CUMA.
# Também migra configurações antigas salvas com o usuário/repositório anterior,
# evitando que instalações antigas continuem tentando baixar manifesto em URL 404.

CUMA_OFFICIAL_GITHUB_OWNER = "soldieg"
CUMA_OFFICIAL_GITHUB_REPO = "CUMA"
CUMA_OFFICIAL_RELEASE_TAG = "Stable"
CUMA_OFFICIAL_REPO_URL = "https://github.com/soldieg/CUMA"
CUMA_DEFAULT_UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/soldieg/CUMA/main/updates/stable.json"
CUMA_DEFAULT_UPDATE_DOWNLOAD_URL = "https://github.com/soldieg/CUMA/releases/download/Stable/CUMA_windows.zip"
CUMA_DEFAULT_UPDATE_SHA256 = ""
CUMA_DEFAULT_UPDATE_SIZE_BYTES = 0


def _cuma_github_normalize_manifest_url(url_value: str = "") -> str:
    """Normaliza URLs antigas/erradas do manifesto para o endpoint oficial."""
    url = str(url_value or "").strip()
    if not url:
        return CUMA_DEFAULT_UPDATE_MANIFEST_URL

    lowered = url.lower()

    legacy_or_wrong = (
        "soldiego/cuma" in lowered or
        "github.com/soldiego" in lowered or
        "raw.githubusercontent.com/soldiego" in lowered
    )
    official_cuma_manifest_variant = (
        "raw.githubusercontent.com" in lowered and
        "/cuma/" in lowered and
        lowered.endswith("/updates/stable.json")
    )

    # Se é uma URL antiga conhecida ou uma variação do próprio manifesto do CUMA,
    # força o endpoint oficial atual. URLs personalizadas externas são preservadas.
    if legacy_or_wrong or official_cuma_manifest_variant:
        return CUMA_DEFAULT_UPDATE_MANIFEST_URL

    return url


def _cuma_update_manifest_url_from_settings() -> str:
    try:
        settings = cuma_settings_load()
        changed = False
        if not isinstance(settings, dict):
            settings = {}
            changed = True

        cfg = settings.setdefault('config', {})
        updates = settings.setdefault('updates', {})

        candidate = ''
        if isinstance(cfg, dict):
            candidate = str(cfg.get('update_manifest_url', '') or '').strip()
        if not candidate and isinstance(updates, dict):
            candidate = str(updates.get('manifest_url', '') or '').strip()

        normalized = _cuma_github_normalize_manifest_url(candidate)

        if isinstance(cfg, dict) and cfg.get('update_manifest_url') != normalized:
            cfg['update_manifest_url'] = normalized
            cfg['update_channel'] = 'stable'
            changed = True

        if isinstance(updates, dict):
            if updates.get('manifest_url') != normalized:
                updates['manifest_url'] = normalized
                changed = True
            updates.setdefault('channel', 'stable')
            updates.setdefault('release_tag', CUMA_OFFICIAL_RELEASE_TAG)
            updates.setdefault('download_url', CUMA_DEFAULT_UPDATE_DOWNLOAD_URL)
            updates.setdefault('auto_download', False)
            updates.setdefault('verify_sha256', True)

        if changed:
            cuma_settings_save(settings)

        return normalized
    except Exception as exc:
        try:
            write_log(f'Normalização de URL de atualização GitHub: {exc}')
        except Exception:
            pass
        return CUMA_DEFAULT_UPDATE_MANIFEST_URL


def _cuma_ensure_update_settings_defaults() -> None:
    try:
        settings = cuma_settings_load()
        if not isinstance(settings, dict):
            settings = {}

        cfg = settings.setdefault('config', {})
        updates = settings.setdefault('updates', {})

        old_cfg_url = ''
        if isinstance(cfg, dict):
            old_cfg_url = str(cfg.get('update_manifest_url', '') or '').strip()
        old_updates_url = ''
        if isinstance(updates, dict):
            old_updates_url = str(updates.get('manifest_url', '') or '').strip()

        chosen = old_cfg_url or old_updates_url
        normalized = _cuma_github_normalize_manifest_url(chosen)

        if isinstance(cfg, dict):
            cfg['update_manifest_url'] = normalized
            cfg['update_channel'] = 'stable'

        if isinstance(updates, dict):
            updates['manifest_url'] = normalized
            updates['channel'] = 'stable'
            updates['release_tag'] = CUMA_OFFICIAL_RELEASE_TAG
            updates['download_url'] = CUMA_DEFAULT_UPDATE_DOWNLOAD_URL
            updates.setdefault('auto_download', False)
            updates.setdefault('verify_sha256', True)
            updates.setdefault('last_checked_at', '')
            updates.setdefault('last_available_version', '')

        cuma_settings_save(settings)
    except Exception as exc:
        try:
            write_log(f'Configuração padrão de atualização GitHub oficial: {exc}')
        except Exception:
            pass



# =============================================================================
# CUMA 1.100.1 - REORGANIZAÇÃO LIMPAR/CONVERTER + CONVERSÕES DINÂMICAS
# =============================================================================
# Esta camada mantém o roadmap 1.100.0, mas corrige a separação conceitual:
# - Limpar: preparação/otimização visual do conteúdo.
# - Converter: escolha de dispositivo, metadados, prévia e conversões por tipo.
# Também amplia as conversões disponíveis por detecção automática de extensão.

CUMA_11001_VERSION = '1.100.1'
CUMA_11001_UPDATE_ID = 'reorganizacao_limpar_converter_conversoes_dinamicas_11001'
CUMA_11001_ARCHIVE_EXTS = tuple(globals().get('CUMA_11000_ARCHIVE_EXTS', ('.cbz', '.zip', '.cbr', '.rar', '.7z')))
CUMA_11001_IMAGE_EXTS = tuple(globals().get('SUPPORTED_IMAGE_EXT', ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')))

CUMA_11001_CONVERSION_LABELS = {
    'pdf_epub': 'PDF → EPUB',
    'pdf_xtch': 'PDF → XTCH',
    'pdf_cbz': 'PDF → CBZ',
    'pdf_images': 'PDF → imagens',
    'epub_xtch': 'EPUB → XTCH',
    'epub_pdf': 'EPUB → PDF',
    'archive_epub': 'CBZ/ZIP/CBR/RAR/7Z → EPUB',
    'archive_xtch': 'CBZ/ZIP/CBR/RAR/7Z → XTCH',
    'archive_pdf': 'CBZ/ZIP/CBR/RAR/7Z → PDF',
    'images_pdf': 'Imagem → PDF',
    'images_epub': 'Imagem → EPUB',
    'images_xtch': 'Imagem → XTCH',
}

CUMA_11001_CONVERSIONS_BY_KIND = {
    'pdf': ('pdf_epub', 'pdf_xtch', 'pdf_cbz', 'pdf_images'),
    'epub': ('epub_xtch', 'epub_pdf'),
    'archive': ('archive_epub', 'archive_xtch', 'archive_pdf'),
    'image': ('images_pdf', 'images_epub', 'images_xtch'),
}


def _cuma_11001_log(context: str, exc: Exception | None = None) -> None:
    try:
        if exc is None:
            write_log(f'[CUMA 1.100.1] {context}')
        else:
            write_log(f'[CUMA 1.100.1] {context}: {exc}')
    except Exception:
        pass


def _cuma_11001_boolvar(self, name: str, default: bool = False) -> tk.BooleanVar:
    var = getattr(self, name, None)
    if isinstance(var, tk.BooleanVar):
        return var
    try:
        var = tk.BooleanVar(value=default)
    except Exception:
        var = tk.BooleanVar(value=default)
    try:
        setattr(self, name, var)
    except Exception:
        pass
    return var


def _cuma_11001_setup_conversion_vars(self) -> None:
    # Mantém compatibilidade com as opções antigas e adiciona as novas.
    _cuma_11001_boolvar(self, 'xteink_pdf_epub', False)
    _cuma_11001_boolvar(self, 'xteink_pdf_xtch', True)
    _cuma_11001_boolvar(self, 'xteink_epub_xtch', True)
    _cuma_11001_boolvar(self, 'xteink_pdf_cbz', False)
    _cuma_11001_boolvar(self, 'xteink_pdf_images', False)
    _cuma_11001_boolvar(self, 'xteink_epub_pdf', False)
    _cuma_11001_boolvar(self, 'xteink_archive_epub', False)
    _cuma_11001_boolvar(self, 'xteink_archive_xtch', True)
    _cuma_11001_boolvar(self, 'xteink_archive_pdf', False)
    _cuma_11001_boolvar(self, 'xteink_images_pdf', True)
    _cuma_11001_boolvar(self, 'xteink_images_epub', False)
    _cuma_11001_boolvar(self, 'xteink_images_xtch', False)


def _cuma_11001_var_for_key(self, key: str) -> tk.BooleanVar:
    mapping = {
        'pdf_epub': ('xteink_pdf_epub', False),
        'pdf_xtch': ('xteink_pdf_xtch', True),
        'pdf_cbz': ('xteink_pdf_cbz', False),
        'pdf_images': ('xteink_pdf_images', False),
        'epub_xtch': ('xteink_epub_xtch', True),
        'epub_pdf': ('xteink_epub_pdf', False),
        'archive_epub': ('xteink_archive_epub', False),
        'archive_xtch': ('xteink_archive_xtch', True),
        'archive_pdf': ('xteink_archive_pdf', False),
        'images_pdf': ('xteink_images_pdf', True),
        'images_epub': ('xteink_images_epub', False),
        'images_xtch': ('xteink_images_xtch', False),
    }
    name, default = mapping[key]
    return _cuma_11001_boolvar(self, name, default)


def _cuma_11001_kind_for_path(path: Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        return 'pdf'
    if suffix == '.epub':
        return 'epub'
    if suffix in CUMA_11001_ARCHIVE_EXTS:
        return 'archive'
    if suffix in CUMA_11001_IMAGE_EXTS:
        return 'image'
    return 'unknown'


def _cuma_11001_active_converter_path(self) -> Path | None:
    try:
        selected = set(getattr(self, 'xteink_tree').selection())
        if selected:
            for p in getattr(self, 'xteink_files', []):
                if _cuma_11008_path_key(Path(p)) in selected:
                    return Path(p)
    except Exception:
        pass
    try:
        value = str(getattr(self, 'xteink_input').get() or '').strip()
        if value:
            p = Path(value)
            if p.exists():
                return p
    except Exception:
        pass
    try:
        files = list(getattr(self, 'xteink_files', []) or [])
        if files:
            return Path(files[0])
    except Exception:
        pass
    return None


def _cuma_11001_flags(self) -> dict:
    _cuma_11001_setup_conversion_vars(self)
    return {key: bool(_cuma_11001_var_for_key(self, key).get()) for key in CUMA_11001_CONVERSION_LABELS}


def _cuma_11001_status_for_src(src: Path, flags: dict) -> str:
    kind = _cuma_11001_kind_for_path(src)
    keys = CUMA_11001_CONVERSIONS_BY_KIND.get(kind, ())
    chosen = [CUMA_11001_CONVERSION_LABELS[k] for k in keys if flags.get(k)]
    return ' + '.join(chosen) if chosen else ('Aguardando opção' if kind != 'unknown' else 'Formato não suportado')


def _cuma_11001_refresh_conversion_options(self) -> None:
    try:
        path = _cuma_11001_active_converter_path(self)
        kind = _cuma_11001_kind_for_path(path) if path else 'unknown'
        active_keys = set(CUMA_11001_CONVERSIONS_BY_KIND.get(kind, ()))
        label = getattr(self, 'cuma_conversion_hint', None)
        if label is not None:
            if path:
                if kind == 'archive' and Path(path).suffix.lower() in ('.cbr', '.rar', '.7z'):
                    label.set(f'Arquivo detectado: {Path(path).suffix.upper().lstrip(".")} • opções de compactado. CBR/RAR/7Z exigem 7-Zip no PATH.')
                else:
                    label.set(f'Arquivo detectado: {Path(path).suffix.upper().lstrip(".")} • escolha as conversões disponíveis abaixo.')
            else:
                label.set('Adicione ou selecione um arquivo para liberar as conversões compatíveis.')
        widgets = getattr(self, '_cuma_11001_conversion_widgets', {})
        for key, widget in widgets.items():
            try:
                if key in active_keys:
                    widget.grid()
                    widget.configure(state='normal')
                else:
                    widget.grid_remove()
                    widget.configure(state='disabled')
            except Exception:
                pass
    except Exception as exc:
        _cuma_11001_log('Atualização das opções dinâmicas de conversão', exc)


def _cuma_11001_destroy_legacy_converter_optimization_panel(self) -> None:
    try:
        container = getattr(self, 'tab_xteink', None)
        if container is None:
            return
        stack = [container]
        while stack:
            widget = stack.pop()
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            try:
                txt = str(widget.cget('text') or '')
            except Exception:
                txt = ''
            normalized = txt.lower()
            if isinstance(widget, ttk.LabelFrame) and ('otimização de leitura' in normalized or 'e-ink - 1.100.0' in normalized):
                try:
                    widget.destroy()
                except Exception:
                    pass
            # Remove checkboxes antigos de conversão fixa criados no painel legado.
            if isinstance(widget, ttk.Checkbutton) and txt in ('PDF para EPUB', 'PDF para XTCH', 'EPUB para XTCH'):
                try:
                    widget.destroy()
                except Exception:
                    pass
    except Exception as exc:
        _cuma_11001_log('Remoção do painel legado do Converter', exc)


def _cuma_11001_find_tree_frame(tab) -> object | None:
    try:
        for child in tab.winfo_children():
            try:
                descendants = list(child.winfo_children())
            except Exception:
                descendants = []
            if any(isinstance(d, ttk.Treeview) for d in descendants):
                return child
    except Exception:
        pass
    return None


def _cuma_11001_add_clean_optimization_panel(self) -> None:
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        # Remove versão anterior do painel para evitar duplicação ao reconstruir interface.
        for child in list(tab.winfo_children()):
            try:
                if isinstance(child, ttk.LabelFrame) and 'Limpeza e otimização de leitura' in str(child.cget('text')):
                    child.destroy()
            except Exception:
                pass

        _cuma_11001_setup_conversion_vars(self)
        settings = _cuma_11000_app_processing_settings(self) if '_cuma_11000_app_processing_settings' in globals() else {}

        if not hasattr(self, 'cuma_reading_order'):
            self.cuma_reading_order = tk.StringVar(value=settings.get('reading_order', 'Ocidental'))
        if not hasattr(self, 'cuma_image_preset'):
            self.cuma_image_preset = tk.StringVar(value=settings.get('image_preset', 'Original'))
        if not hasattr(self, 'cuma_auto_crop'):
            self.cuma_auto_crop = tk.BooleanVar(value=bool(settings.get('auto_crop', False)))
        if not hasattr(self, 'cuma_auto_crop_strength'):
            self.cuma_auto_crop_strength = tk.StringVar(value=settings.get('auto_crop_strength', 'Normal'))
        if not hasattr(self, 'cuma_remove_page_numbers'):
            self.cuma_remove_page_numbers = tk.BooleanVar(value=bool(settings.get('remove_page_numbers', False)))
        if not hasattr(self, 'cuma_split_double_pages'):
            self.cuma_split_double_pages = tk.BooleanVar(value=bool(settings.get('split_double_pages', False)))
        if not hasattr(self, 'cuma_split_keep_original'):
            self.cuma_split_keep_original = tk.BooleanVar(value=bool(settings.get('split_keep_original', False)))
        if not hasattr(self, 'cuma_webtoon_split'):
            self.cuma_webtoon_split = tk.BooleanVar(value=bool(settings.get('webtoon_split', False)))

        before = _cuma_11001_find_tree_frame(tab)
        kwargs = {'fill': 'x', 'pady': (0, 10)}
        if before is not None:
            kwargs['before'] = before

        panel = ttk.LabelFrame(tab, text='Limpeza e otimização de leitura / E-ink', padding=12, style='Card.TLabelframe')
        panel.pack(**kwargs)

        ttk.Label(panel, text='Estas opções modificam/preparam as páginas antes da exportação ou conversão.', style='Muted.TLabel', wraplength=1050, justify='left').grid(row=0, column=0, columnspan=6, sticky='w', pady=(0, 8))

        ttk.Label(panel, text='Ordem de leitura', style='Muted.TLabel').grid(row=1, column=0, sticky='w', padx=(0, 8), pady=4)
        cb_order = ttk.Combobox(panel, textvariable=self.cuma_reading_order, values=globals().get('CUMA_11000_READING_ORDERS', ('Ocidental', 'Mangá')), state='readonly', width=14)
        cb_order.grid(row=1, column=1, sticky='w', pady=4)

        ttk.Label(panel, text='Preset E-ink', style='Muted.TLabel').grid(row=1, column=2, sticky='w', padx=(18, 8), pady=4)
        cb_preset = ttk.Combobox(panel, textvariable=self.cuma_image_preset, values=globals().get('CUMA_11000_IMAGE_PRESETS', ('Original',)), state='readonly', width=26)
        cb_preset.grid(row=1, column=3, sticky='w', pady=4)

        ttk.Label(panel, text='Força do corte', style='Muted.TLabel').grid(row=1, column=4, sticky='w', padx=(18, 8), pady=4)
        cb_crop = ttk.Combobox(panel, textvariable=self.cuma_auto_crop_strength, values=globals().get('CUMA_11000_CROP_STRENGTHS', ('Suave', 'Normal', 'Forte')), state='readonly', width=10)
        cb_crop.grid(row=1, column=5, sticky='w', pady=4)

        def save_processing():
            try:
                _cuma_11000_set_processing_from_app(self)
            except Exception as exc:
                _cuma_11001_log('Salvar otimização de leitura', exc)
            try:
                self.save_current_config()
            except Exception:
                pass

        ttk.Checkbutton(panel, text='Remover margens', variable=self.cuma_auto_crop, command=save_processing).grid(row=2, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Remover número/rodapé', variable=self.cuma_remove_page_numbers, command=save_processing).grid(row=2, column=2, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Dividir páginas duplas', variable=self.cuma_split_double_pages, command=save_processing).grid(row=2, column=4, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Manter original ao dividir', variable=self.cuma_split_keep_original, command=save_processing).grid(row=3, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Webtoon/imagens longas', variable=self.cuma_webtoon_split, command=save_processing).grid(row=3, column=2, columnspan=2, sticky='w', pady=4)

        for cb in (cb_order, cb_preset, cb_crop):
            cb.bind('<<ComboboxSelected>>', lambda _e: save_processing())

        ttk.Label(panel, text='Fluxo sugerido: use Limpar para preparar/cortar/dividir páginas; use Converter apenas para transformar o arquivo final em EPUB, XTCH, PDF, CBZ ou imagens.', style='Muted.TLabel', wraplength=1050, justify='left').grid(row=4, column=0, columnspan=6, sticky='w', pady=(8, 0))
        panel.columnconfigure(3, weight=1)
    except Exception as exc:
        _cuma_11001_log('Adicionar painel Limpar/otimização', exc)


def _cuma_11001_add_converter_dynamic_panel(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        _cuma_11001_setup_conversion_vars(self)

        for child in list(tab.winfo_children()):
            try:
                if isinstance(child, ttk.LabelFrame) and str(child.cget('text')) in ('Conversões disponíveis', 'Prévia, metadados e conversões'):
                    child.destroy()
            except Exception:
                pass

        children = list(tab.winfo_children())
        kwargs = {'fill': 'x', 'pady': (0, 10)}
        if children:
            # Depois de dispositivos/conversões, antes da área de arquivos quando possível.
            kwargs['before'] = children[1] if len(children) > 1 else children[0]

        panel = ttk.LabelFrame(tab, text='Prévia, metadados e conversões', padding=12, style='Card.TLabelframe')
        panel.pack(**kwargs)

        top = ttk.Frame(panel, style='Card.TFrame')
        top.grid(row=0, column=0, columnspan=4, sticky='ew')
        ttk.Button(top, text='Prévia antes/depois', command=lambda: _cuma_11000_open_before_after_preview(self), style='Accent.TButton').pack(side='left', padx=(0, 8))
        ttk.Button(top, text='Metadados EPUB', command=lambda: _cuma_11000_open_metadata_editor(self), style='Ghost.TButton').pack(side='left', padx=(0, 8))
        ttk.Label(top, text='O Converter agora mostra apenas as opções compatíveis com o arquivo selecionado.', style='Muted.TLabel').pack(side='left', padx=(10, 0))

        self.cuma_conversion_hint = tk.StringVar(value='Adicione ou selecione um arquivo para liberar as conversões compatíveis.')
        ttk.Label(panel, textvariable=self.cuma_conversion_hint, style='Muted.TLabel', wraplength=1050, justify='left').grid(row=1, column=0, columnspan=4, sticky='w', pady=(10, 6))

        grid = ttk.Frame(panel, style='Card.TFrame')
        grid.grid(row=2, column=0, columnspan=4, sticky='ew')
        self._cuma_11001_conversion_widgets = {}
        ordered = (
            'pdf_epub', 'pdf_xtch', 'pdf_cbz', 'pdf_images',
            'epub_xtch', 'epub_pdf',
            'archive_epub', 'archive_xtch', 'archive_pdf',
            'images_pdf', 'images_epub', 'images_xtch'
        )
        for idx, key in enumerate(ordered):
            var = _cuma_11001_var_for_key(self, key)
            cb = ttk.Checkbutton(grid, text=CUMA_11001_CONVERSION_LABELS[key], variable=var)
            cb.grid(row=idx // 4, column=idx % 4, sticky='w', padx=(0, 18), pady=4)
            self._cuma_11001_conversion_widgets[key] = cb

        try:
            self.xteink_tree.bind('<<TreeviewSelect>>', lambda _e: _cuma_11001_refresh_conversion_options(self), add='+')
        except Exception:
            pass
        try:
            self.xteink_input.trace_add('write', lambda *_: _cuma_11001_refresh_conversion_options(self))
        except Exception:
            pass
        _cuma_11001_refresh_conversion_options(self)
    except Exception as exc:
        _cuma_11001_log('Adicionar painel dinâmico do Converter', exc)


def _cuma_11001_reorganize_ui(self) -> None:
    _cuma_11001_destroy_legacy_converter_optimization_panel(self)
    _cuma_11001_add_clean_optimization_panel(self)
    _cuma_11001_add_converter_dynamic_panel(self)
    try:
        if hasattr(self, 'xteink_drop'):
            self.xteink_drop.configure(text='Arraste PDF, EPUB, CBZ/ZIP, CBR/RAR/7Z, imagens ou pastas aqui')
    except Exception:
        pass


def _cuma_11001_iter_image_file(path: Path, target: tuple[int, int] | None = None):
    settings = _cuma_11000_processing_settings() if '_cuma_11000_processing_settings' in globals() else {}
    with Image.open(path) as im:
        im = im.convert('RGB')
        for processed in _cuma_11000_process_source_image(im, target, settings):
            yield processed


def _cuma_11001_iter_source_images(src: Path, target: tuple[int, int] | None = None):
    src = Path(src)
    suffix = src.suffix.lower()
    if suffix == '.pdf':
        yield from _cuma_11000_iter_pdf_pages_as_images(src, target=target)
    elif suffix == '.epub':
        yield from _cuma_11000_iter_epub_images(src, target or (1200, 1600))
    elif suffix in CUMA_11001_ARCHIVE_EXTS:
        yield from _cuma_11000_iter_archive_images(src, target=target)
    elif suffix in CUMA_11001_IMAGE_EXTS:
        yield from _cuma_11001_iter_image_file(src, target=target)
    else:
        raise RuntimeError('Formato não suportado para gerar imagens.')


def _cuma_11001_create_pdf_from_image_iter(image_iter, output_pdf: Path) -> None:
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    count = 0
    try:
        for im in image_iter:
            count += 1
            try:
                rgb = im.convert('RGB')
                bio = BytesIO()
                rgb.save(bio, format='JPEG', quality=92, optimize=True)
                page = doc.new_page(width=max(1, rgb.width), height=max(1, rgb.height))
                page.insert_image(page.rect, stream=bio.getvalue())
            finally:
                try:
                    im.close()
                except Exception:
                    pass
        if count <= 0:
            raise RuntimeError('Nenhuma imagem para criar PDF.')
        doc.save(str(output_pdf))
    finally:
        doc.close()


def _cuma_11001_create_cbz_from_image_iter(image_iter, output_cbz: Path, quality: int = 92) -> None:
    output_cbz = Path(output_cbz)
    output_cbz.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output_cbz, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for im in image_iter:
            count += 1
            try:
                bio = BytesIO()
                im.convert('RGB').save(bio, format='JPEG', quality=int(max(50, min(100, quality or 92))), optimize=True)
                z.writestr(f'page_{count:04d}.jpg', bio.getvalue())
            finally:
                try:
                    im.close()
                except Exception:
                    pass
    if count <= 0:
        raise RuntimeError('Nenhuma imagem para criar CBZ.')


def _cuma_11001_export_images_from_iter(image_iter, output_folder: Path, stem: str, quality: int = 92) -> Path:
    output_folder = Path(output_folder) / f'{stem}_imagens'
    output_folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for im in image_iter:
        count += 1
        try:
            out = unique_path(output_folder / f'page_{count:04d}.jpg')
            im.convert('RGB').save(out, format='JPEG', quality=int(max(50, min(100, quality or 92))), optimize=True)
        finally:
            try:
                im.close()
            except Exception:
                pass
    if count <= 0:
        raise RuntimeError('Nenhuma imagem exportada.')
    return output_folder


def _cuma_11001_run_xteink_job(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    outputs = []
    src = Path(src)
    out_dir = Path(out_dir)
    suffix = src.suffix.lower()
    kind = _cuma_11001_kind_for_path(src)

    if kind == 'pdf':
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_image_epub_from_pdf(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_pdf(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('pdf_cbz'):
            out = unique_path(out_dir / f'{src.stem}.cbz')
            _cuma_11001_create_cbz_from_image_iter(_cuma_11000_iter_pdf_pages_as_images(src, target=target), out, quality)
            outputs.append(out)
        if flags.get('pdf_images'):
            out_folder = _cuma_11001_export_images_from_iter(_cuma_11000_iter_pdf_pages_as_images(src, target=target), out_dir, src.stem, quality)
            outputs.append(out_folder)

    elif kind == 'epub':
        if flags.get('epub_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_epub_stream(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('epub_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11000_iter_epub_images(src, target), out)
            outputs.append(out)

    elif kind == 'archive':
        if flags.get('archive_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_epub_from_archive(src, out, src.stem, target=target, quality=quality)
            outputs.append(out)
        if flags.get('archive_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_archive_stream(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('archive_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11000_iter_archive_images(src, target=target), out)
            outputs.append(out)

    elif kind == 'image':
        if flags.get('images_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11001_iter_image_file(src, target=None), out)
            outputs.append(out)
        if flags.get('images_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11000_create_image_epub_from_iter(_cuma_11001_iter_image_file(src, target=target), out, src.stem, quality)
            outputs.append(out)
        if flags.get('images_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11000_create_xtch_from_iter_stream(_cuma_11001_iter_image_file(src, target=target), out, src.stem, target)
            outputs.append(out)

    else:
        raise RuntimeError('Formato não suportado. Use PDF, EPUB, CBZ/ZIP, CBR/RAR/7Z ou imagens.')

    return outputs


def _cuma_11001_add_xteink_path(self, path: Path) -> bool:
    path = Path(path)
    if path.is_dir():
        added = False
        exts = ('.pdf', '.epub') + CUMA_11001_ARCHIVE_EXTS + CUMA_11001_IMAGE_EXTS
        for f in sorted(path.rglob('*'), key=lambda p: _cuma_11000_natural_key(p.as_posix())):
            if f.is_file() and f.suffix.lower() in exts:
                added = _cuma_11001_add_xteink_path(self, f) or added
        _cuma_11001_refresh_conversion_options(self)
        return added

    if path.suffix.lower() not in ('.pdf', '.epub') + CUMA_11001_ARCHIVE_EXTS + CUMA_11001_IMAGE_EXTS:
        return False
    if not path.exists() or path in getattr(self, 'xteink_files', []):
        return False

    self.xteink_files.append(path)
    iid = _cuma_11008_path_key(path)
    kind = _cuma_11001_kind_for_path(path)
    tipo = {'pdf': 'PDF', 'epub': 'EPUB', 'archive': path.suffix.upper().lstrip('.'), 'image': 'IMG'}.get(kind, path.suffix.upper().lstrip('.'))
    if not self.xteink_tree.exists(iid):
        self.xteink_tree.insert('', 'end', iid=iid, values=(path.name, 'Aguardando', tipo, '', ''))
    self.xteink_input.set(str(path))
    try:
        self.xteink_tree.selection_set(iid)
        self.xteink_tree.focus(iid)
    except Exception:
        pass
    try:
        self.update_xteink_counter()
    except Exception:
        pass
    _cuma_11001_refresh_conversion_options(self)
    return True


def _cuma_11001_add_xteink_files(self) -> None:
    files = filedialog.askopenfilenames(
        title='Adicionar arquivos para conversão',
        filetypes=[
            ('Compatíveis', '*.pdf *.epub *.cbz *.zip *.cbr *.rar *.7z *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'),
            ('PDF', '*.pdf'),
            ('EPUB', '*.epub'),
            ('Compactados', '*.cbz *.zip *.cbr *.rar *.7z'),
            ('Imagens', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'),
            ('Todos', '*.*'),
        ],
    )
    for f in sorted(files, key=_cuma_11000_natural_key):
        self.add_xteink_path(Path(f))
    _cuma_11001_refresh_conversion_options(self)


def _cuma_11001_process_xteink_paths_async(self, paths: list[Path]) -> None:
    if not paths:
        messagebox.showwarning('Converter', 'Adicione ou selecione arquivos compatíveis.')
        return
    if getattr(self, '_xteink_async_queue', None) is not None or getattr(self, 'processing', False):
        return

    base = _cuma_sync_converter_model(self)
    flags = _cuma_11001_flags(self)
    self.pause_event.set()
    self.cancel_requested = False
    self.processing = True
    self._xteink_batch_mode = True
    self._xteink_last_out_dir = str(base)
    self._xteink_async_queue = queue.Queue()

    try:
        self.xteink_total_prog['maximum'] = len(paths)
        self.xteink_total_prog['value'] = 0
        self.xteink_current_prog['value'] = 0
        self.xteink_cancel_btn.configure(state='normal')
        self.xteink_pause_btn.configure(state='normal')
        self.xteink_play_btn.configure(state='normal')
    except Exception as exc:
        _cuma_11001_log('Preparação visual do lote Converter', exc)

    src_list = [Path(p) for p in paths]
    target = self.xteink_target()
    try:
        quality = int(getattr(self, 'xteink_quality').get())
    except Exception:
        quality = 92

    def worker():
        last_out_dir = str(base)
        try:
            for idx, src in enumerate(src_list, 1):
                if self.cancel_requested:
                    break
                while not self.pause_event.is_set() and not self.cancel_requested:
                    time.sleep(0.10)
                self._xteink_async_queue.put({'kind': 'item_start', 'src': str(src), 'index': idx, 'total': len(src_list), 'status': _cuma_11001_status_for_src(src, flags)})
                try:
                    outputs = _cuma_11001_run_xteink_job(src, base, target, quality, flags)
                    resumo = ', '.join(('PASTA' if p.is_dir() else p.suffix.upper().lstrip('.')) for p in outputs) if outputs else 'Nenhuma opção marcada compatível'
                    status = 'OK' if outputs else 'IGNORADO'
                    saida = str(outputs[-1].parent if outputs and not outputs[-1].is_dir() else outputs[-1] if outputs else base)
                    last_out_dir = saida or last_out_dir
                    self._xteink_async_queue.put({'kind': 'item_done', 'src': str(src), 'index': idx, 'status': status, 'saida': saida, 'resumo': resumo})
                except Exception as exc:
                    _cuma_11001_log(f'Processamento Converter de {src.name}', exc)
                    self._xteink_async_queue.put({'kind': 'item_done', 'src': str(src), 'index': idx, 'status': 'ERRO', 'saida': str(base), 'resumo': friendly_error(exc)})
            self._xteink_async_queue.put({'kind': 'batch_done', 'last_out_dir': last_out_dir})
        except Exception as exc:
            _cuma_11001_log('Lote Converter/worker', exc)
            self._xteink_async_queue.put({'kind': 'batch_error', 'last_out_dir': last_out_dir, 'error': friendly_error(exc)})

    threading.Thread(target=worker, daemon=True, name='CUMA-Converter-Worker').start()
    _cuma_poll_xteink_queue(self)


_CUMA_11001_RUNTIME = {
    'build': App.build,
    'setup_vars': App.setup_vars,
    'save_current_config': App.save_current_config,
}


def _cuma_11001_build(self):
    result = _CUMA_11001_RUNTIME['build'](self)
    try:
        _cuma_11001_reorganize_ui(self)
    except Exception as exc:
        _cuma_11001_log('build/reorganização UI', exc)
    return result


def _cuma_11001_setup_vars(self):
    result = _CUMA_11001_RUNTIME['setup_vars'](self)
    try:
        _cuma_11001_setup_conversion_vars(self)
    except Exception as exc:
        _cuma_11001_log('setup vars conversões dinâmicas', exc)
    return result


def _cuma_11001_save_current_config(self, force: bool = False):
    result = _CUMA_11001_RUNTIME['save_current_config'](self, force)
    try:
        if '_cuma_11000_set_processing_from_app' in globals():
            _cuma_11000_set_processing_from_app(self)
    except Exception as exc:
        _cuma_11001_log('Salvar otimização 1.100.1', exc)
    return result


def _cuma_11001_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11001_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11001_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11001_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'Reorganização Limpar/Converter e conversões dinâmicas por tipo de arquivo.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11001_VERSION)
    except Exception:
        pass
    try:
        state = cuma_version_load_state()
        events = state.get('events', [])
        if not isinstance(events, list):
            events = []
        if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11001_UPDATE_ID for e in events):
            events.append({
                'update_id': CUMA_11001_UPDATE_ID,
                'version': CUMA_11001_VERSION,
                'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                'scale': 'pouca',
                'description': 'Move otimização de leitura/E-ink para Limpar, mantém perfis/metadados/prévia no Converter e adiciona conversões dinâmicas por tipo.',
                'timestamp': datetime.now().isoformat(timespec='seconds')
            })
        state['events'] = events[-100:]
        state['current_version'] = CUMA_11001_VERSION
        state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
        cuma_version_save_state(state)
        if '_cuma_version_write_public_files' in globals():
            _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11001_log('Versionamento 1.100.1', exc)


def _cuma_install_11001_reorg() -> None:
    try:
        _cuma_11001_force_version()
        App.setup_vars = _cuma_11001_setup_vars
        App.build = _cuma_11001_build
        App.save_current_config = _cuma_11001_save_current_config
        App.add_xteink_path = _cuma_11001_add_xteink_path
        App.add_xteink_files = _cuma_11001_add_xteink_files
        App.process_xteink_paths = _cuma_11001_process_xteink_paths_async
        globals()['_cuma_converter_flags'] = _cuma_11001_flags
        globals()['_cuma_xteink_status_for_src'] = _cuma_11001_status_for_src
        globals()['_cuma_run_xteink_job'] = _cuma_11001_run_xteink_job
    except Exception as exc:
        _cuma_11001_log('Instalação patch 1.100.1', exc)


_cuma_install_11001_reorg()


# Chamada main movida para o fim por subpatch 1.100.1b.


# -----------------------------------------------------------------------------
# CUMA 1.100.1b - ajuste visual: remover checkboxes legados e posicionar Limpar.
# -----------------------------------------------------------------------------

def _cuma_11001_widget_text(widget) -> str:
    try:
        return str(widget.cget('text') or '')
    except Exception:
        return ''


def _cuma_11001_is_treeview(widget) -> bool:
    try:
        return widget.winfo_class() == 'Treeview'
    except Exception:
        return isinstance(widget, ttk.Treeview)


def _cuma_11001_contains_treeview(widget) -> bool:
    try:
        for child in widget.winfo_children():
            if _cuma_11001_is_treeview(child) or _cuma_11001_contains_treeview(child):
                return True
    except Exception:
        pass
    return False


def _cuma_11001_find_tree_frame(tab) -> object | None:
    try:
        for child in tab.winfo_children():
            if _cuma_11001_contains_treeview(child):
                return child
    except Exception:
        pass
    return None


def _cuma_11001_remove_legacy_converter_checkbuttons(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        legacy = {'PDF para EPUB', 'PDF para XTCH', 'EPUB para XTCH'}
        stack = [tab]
        while stack:
            widget = stack.pop()
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            txt = _cuma_11001_widget_text(widget)
            try:
                klass = widget.winfo_class()
            except Exception:
                klass = ''
            if txt in legacy and (klass == 'TCheckbutton' or isinstance(widget, ttk.Checkbutton)):
                try:
                    widget.destroy()
                except Exception:
                    pass
    except Exception as exc:
        _cuma_11001_log('Remoção robusta dos checkboxes legados', exc)


_CUMA_11001B_RUNTIME = {
    'reorganize': _cuma_11001_reorganize_ui,
}


def _cuma_11001_reorganize_ui(self) -> None:
    _cuma_11001_destroy_legacy_converter_optimization_panel(self)
    _cuma_11001_remove_legacy_converter_checkbuttons(self)
    _cuma_11001_add_clean_optimization_panel(self)
    _cuma_11001_add_converter_dynamic_panel(self)
    _cuma_11001_remove_legacy_converter_checkbuttons(self)
    try:
        if hasattr(self, 'xteink_drop'):
            self.xteink_drop.configure(text='Arraste PDF, EPUB, CBZ/ZIP, CBR/RAR/7Z, imagens ou pastas aqui')
    except Exception:
        pass


# Chamada main movida para o fim por subpatch 1.100.1c.


# -----------------------------------------------------------------------------
# CUMA 1.100.1c - remove também os switches compactos legados por seus rótulos.
# -----------------------------------------------------------------------------

def _cuma_11001_remove_legacy_converter_checkbuttons(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        legacy = {'PDF para EPUB', 'PDF para XTCH', 'EPUB para XTCH'}
        stack = [tab]
        targets = []
        while stack:
            widget = stack.pop()
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            txt = _cuma_11001_widget_text(widget)
            if txt in legacy:
                targets.append(widget)
        for widget in targets:
            try:
                klass = widget.winfo_class()
            except Exception:
                klass = ''
            try:
                if klass == 'TCheckbutton' or isinstance(widget, ttk.Checkbutton):
                    widget.destroy()
                else:
                    # No tema novo, alguns switches são frames compostos: label dentro do frame.
                    parent = getattr(widget, 'master', None)
                    if parent is not None and parent is not tab:
                        parent.destroy()
                    else:
                        widget.destroy()
            except Exception:
                pass
    except Exception as exc:
        _cuma_11001_log('Remoção robusta dos switches legados', exc)


# Chamada main movida para o fim por subpatch 1.100.1d.


# -----------------------------------------------------------------------------
# CUMA 1.100.1d - reposiciona painel Limpar imediatamente antes da lista.
# -----------------------------------------------------------------------------

_CUMA_11001D_ADD_CLEAN = _cuma_11001_add_clean_optimization_panel

def _cuma_11001_add_clean_optimization_panel(self) -> None:
    _CUMA_11001D_ADD_CLEAN(self)
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        panel = None
        for child in tab.winfo_children():
            try:
                if isinstance(child, ttk.LabelFrame) and 'Limpeza e otimização de leitura' in str(child.cget('text')):
                    panel = child
                    break
            except Exception:
                pass
        before = _cuma_11001_find_tree_frame(tab)
        if panel is not None and before is not None:
            try:
                panel.pack_forget()
                panel.pack(fill='x', pady=(0, 10), before=before)
            except Exception as exc:
                _cuma_11001_log('Reposicionamento do painel Limpar', exc)
    except Exception as exc:
        _cuma_11001_log('Reposicionamento final do painel Limpar', exc)


# Chamada main movida para o fim por subpatch 1.100.1e.


# -----------------------------------------------------------------------------
# CUMA 1.100.1e - reordenação via Tcl pack para garantir posição visual.
# -----------------------------------------------------------------------------

_CUMA_11001E_ADD_CLEAN = _cuma_11001_add_clean_optimization_panel

def _cuma_11001_add_clean_optimization_panel(self) -> None:
    _CUMA_11001E_ADD_CLEAN(self)
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        panel = None
        for child in tab.winfo_children():
            try:
                if isinstance(child, ttk.LabelFrame) and 'Limpeza e otimização de leitura' in str(child.cget('text')):
                    panel = child
                    break
            except Exception:
                pass
        before = _cuma_11001_find_tree_frame(tab)
        if panel is not None and before is not None:
            try:
                panel.tk.call('pack', 'forget', panel._w)
                panel.tk.call('pack', 'configure', panel._w, '-fill', 'x', '-pady', '0 10', '-before', before._w)
            except Exception as exc:
                _cuma_11001_log('Reordenação Tcl do painel Limpar', exc)
    except Exception as exc:
        _cuma_11001_log('Reordenação final Tcl do painel Limpar', exc)



# -----------------------------------------------------------------------------
# CUMA 1.100.2 - Converter em modo puro: sem nova limpeza/otimização visual.
# -----------------------------------------------------------------------------
# Motivo:
# A aba Limpar é a única responsável por modificar conteúdo visual: corte,
# margens, páginas duplas, webtoon e presets E-ink. A aba Converter deve apenas
# transformar formato. Este patch impede que o Converter reaplique os filtros
# do bloco KCC/E-ink e impede que a prévia adicione canvas branco por perfil de
# dispositivo quando o usuário só quer comparar a entrada real.

CUMA_11002_VERSION = '1.100.2'
CUMA_11002_UPDATE_ID = 'converter_puro_sem_relimpeza_11002'


def _cuma_11002_log(msg: str, exc: Exception | None = None) -> None:
    try:
        if '_cuma_11001_log' in globals():
            _cuma_11001_log(msg, exc)
        elif '_cuma_11000_log' in globals():
            _cuma_11000_log(msg, exc)
    except Exception:
        pass


def _cuma_11002_iter_pdf_pages_raw(pdf_path: Path, quality_zoom: float = 2.0):
    """Renderiza PDF para imagens sem corte, sem preset, sem página dupla e sem fit_to_target."""
    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(quality_zoom, quality_zoom), alpha=False)
            yield Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    finally:
        doc.close()


def _cuma_11002_iter_epub_images_raw(epub_path: Path):
    """Extrai imagens do EPUB preservando proporção e dimensões da imagem interna."""
    if not Path(epub_path).exists():
        raise RuntimeError('EPUB não encontrado.')
    with zipfile.ZipFile(epub_path, 'r') as z:
        names = sorted(
            [n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT],
            key=_cuma_11000_natural_key if '_cuma_11000_natural_key' in globals() else _natural_key
        )
        for name in names:
            try:
                with z.open(name) as f:
                    data = BytesIO(f.read())
                im = Image.open(data).convert('RGB')
                if im.width < 80 or im.height < 80:
                    try:
                        im.close()
                    except Exception:
                        pass
                    continue
                yield im
            except Exception as exc:
                _cuma_11002_log(f'Imagem ignorada no EPUB: {name}', exc)


def _cuma_11002_iter_archive_images_raw(archive_path: Path):
    """Extrai imagens de CBZ/ZIP/CBR/RAR/7Z sem aplicar otimizações da aba Limpar."""
    archive_path = Path(archive_path)
    suffix = archive_path.suffix.lower()
    if suffix in ('.zip', '.cbz'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            names = _cuma_11000_archive_image_names(z) if '_cuma_11000_archive_image_names' in globals() else sorted(
                [n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT],
                key=_natural_key
            )
            for name in names:
                try:
                    with z.open(name) as f:
                        data = BytesIO(f.read())
                    im = Image.open(data).convert('RGB')
                    if im.width < 80 or im.height < 80:
                        try:
                            im.close()
                        except Exception:
                            pass
                        continue
                    yield im
                except Exception as exc:
                    _cuma_11002_log(f'Imagem ignorada no compactado: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        with tempfile.TemporaryDirectory(prefix='cuma_archive_raw_') as td:
            files = _cuma_11000_extract_with_7z(archive_path, Path(td))
            for p in files:
                try:
                    with Image.open(p) as im:
                        rgb = im.convert('RGB')
                    if rgb.width < 80 or rgb.height < 80:
                        try:
                            rgb.close()
                        except Exception:
                            pass
                        continue
                    yield rgb
                except Exception as exc:
                    _cuma_11002_log(f'Imagem ignorada no compactado: {p.name}', exc)
    else:
        raise RuntimeError('Arquivo compactado não suportado. Use CBZ, ZIP, CBR, RAR ou 7Z.')


def _cuma_11002_iter_image_file_raw(path: Path):
    """Abre imagem individual sem aplicar filtros da aba Limpar."""
    with Image.open(path) as im:
        yield im.convert('RGB')


def _cuma_11002_iter_source_images_raw(src: Path):
    """Iterador central do Converter: fonte sempre pura, sem reprocessamento visual."""
    src = Path(src)
    suffix = src.suffix.lower()
    kind = _cuma_11001_kind_for_path(src) if '_cuma_11001_kind_for_path' in globals() else ''
    if kind == 'pdf' or suffix == '.pdf':
        yield from _cuma_11002_iter_pdf_pages_raw(src)
    elif kind == 'epub' or suffix == '.epub':
        yield from _cuma_11002_iter_epub_images_raw(src)
    elif kind == 'archive' or suffix in ('.cbz', '.zip', '.cbr', '.rar', '.7z'):
        yield from _cuma_11002_iter_archive_images_raw(src)
    elif kind == 'image' or suffix in SUPPORTED_IMAGE_EXT:
        yield from _cuma_11002_iter_image_file_raw(src)
    else:
        raise RuntimeError('Formato não suportado para gerar imagens.')


def _cuma_11002_create_epub_from_raw_iter(src: Path, output_epub: Path, title: str, quality: int = 92) -> None:
    return _cuma_11000_create_image_epub_from_iter(_cuma_11002_iter_source_images_raw(src), output_epub, title, quality)


def _cuma_11002_create_xtch_from_raw_iter(src: Path, output_xtch: Path, title: str, target: tuple[int, int]) -> None:
    # XTCH/XTH exige dimensões fixas do dispositivo no contêiner. Aqui a única
    # adaptação é a etapa obrigatória do formato; corte/preset/divisão não são aplicados.
    return _cuma_11000_create_xtch_from_iter_stream(_cuma_11002_iter_source_images_raw(src), output_xtch, title, target)


def _cuma_11002_run_xteink_job(src: Path, out_dir: Path, target: tuple[int, int], quality: int, flags: dict) -> list[Path]:
    """Conversão pura: não chama _cuma_11000_process_source_image nem fit_to_target antes da saída."""
    outputs = []
    src = Path(src)
    out_dir = Path(out_dir)
    kind = _cuma_11001_kind_for_path(src) if '_cuma_11001_kind_for_path' in globals() else src.suffix.lower().lstrip('.')

    if kind == 'pdf':
        if flags.get('pdf_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11002_create_epub_from_raw_iter(src, out, src.stem, quality)
            outputs.append(out)
        if flags.get('pdf_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11002_create_xtch_from_raw_iter(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('pdf_cbz'):
            out = unique_path(out_dir / f'{src.stem}.cbz')
            _cuma_11001_create_cbz_from_image_iter(_cuma_11002_iter_pdf_pages_raw(src), out, quality)
            outputs.append(out)
        if flags.get('pdf_images'):
            out_folder = _cuma_11001_export_images_from_iter(_cuma_11002_iter_pdf_pages_raw(src), out_dir, src.stem, quality)
            outputs.append(out_folder)

    elif kind == 'epub':
        if flags.get('epub_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11002_create_xtch_from_raw_iter(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('epub_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11002_iter_epub_images_raw(src), out)
            outputs.append(out)

    elif kind == 'archive':
        if flags.get('archive_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11002_create_epub_from_raw_iter(src, out, src.stem, quality)
            outputs.append(out)
        if flags.get('archive_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11002_create_xtch_from_raw_iter(src, out, src.stem, target)
            outputs.append(out)
        if flags.get('archive_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11002_iter_archive_images_raw(src), out)
            outputs.append(out)

    elif kind == 'image':
        if flags.get('images_pdf'):
            out = unique_path(out_dir / f'{src.stem}.pdf')
            _cuma_11001_create_pdf_from_image_iter(_cuma_11002_iter_image_file_raw(src), out)
            outputs.append(out)
        if flags.get('images_epub'):
            out = unique_path(out_dir / f'{src.stem}_xteink.epub')
            _cuma_11002_create_epub_from_raw_iter(src, out, src.stem, quality)
            outputs.append(out)
        if flags.get('images_xtch'):
            out = unique_path(out_dir / f'{src.stem}.xtch')
            _cuma_11002_create_xtch_from_raw_iter(src, out, src.stem, target)
            outputs.append(out)

    else:
        raise RuntimeError('Formato não suportado. Use PDF, EPUB, CBZ/ZIP, CBR/RAR/7Z ou imagens.')

    return outputs


def _cuma_11002_selected_converter_path(self) -> Path | None:
    try:
        if hasattr(self, 'xteink_tree') and self.xteink_tree.selection():
            selected = set(self.xteink_tree.selection())
            for p in getattr(self, 'xteink_files', []):
                if _cuma_11008_path_key(p) in selected:
                    return Path(p)
    except Exception:
        pass
    try:
        paths = self.xteink_selected_paths()
        if paths:
            return Path(paths[0])
    except Exception:
        pass
    files = getattr(self, 'xteink_files', [])
    return Path(files[0]) if files else None


def _cuma_11002_first_source_image_raw(path: Path):
    try:
        return next(_cuma_11002_iter_source_images_raw(path))
    except StopIteration:
        return None


def _cuma_11002_open_before_after_preview(self) -> None:
    """Prévia temática sem aplicar fit do dispositivo. Mostra o efeito real das opções da aba Limpar."""
    try:
        src = _cuma_11002_selected_converter_path(self)
        if not src:
            messagebox.showinfo('Prévia antes/depois', 'Selecione um item para pré-visualizar.')
            return

        original = _cuma_11002_first_source_image_raw(src)
        if original is None:
            messagebox.showwarning('Prévia antes/depois', 'Não consegui abrir uma imagem de prévia para este arquivo.')
            return

        # A prévia da aba Limpar mostra apenas filtros visuais. Nada de target/dispositivo aqui.
        settings = _cuma_11000_app_processing_settings(self) if '_cuma_11000_app_processing_settings' in globals() else {}
        processed_pages = _cuma_11000_process_source_image(original.copy(), None, settings) if '_cuma_11000_process_source_image' in globals() else [original.copy()]
        processed = processed_pages[0] if processed_pages else original.copy()

        top = tk.Toplevel(self.root)
        top.title('Prévia antes/depois - CUMA 1.100.2')
        top.geometry('980x680')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass

        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Prévia antes/depois', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 6))
        ttk.Label(
            wrap,
            text=f'{src.name}  •  Preset: {settings.get("image_preset", "Original")}  •  Leitura: {settings.get("reading_order", "Ocidental")}  •  Sem encaixe de dispositivo',
            style='Muted.TLabel'
        ).pack(anchor='w', pady=(0, 12))

        grid = ttk.Frame(wrap, style='Card.TFrame')
        grid.pack(fill='both', expand=True)
        left = ttk.Frame(grid, style='Card.TFrame')
        right = ttk.Frame(grid, style='Card.TFrame')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        right.pack(side='left', fill='both', expand=True, padx=(8, 0))
        ttk.Label(left, text='Original', style='Strong.TLabel').pack(anchor='center')
        ttk.Label(right, text='Processado pela aba Limpar', style='Strong.TLabel').pack(anchor='center')

        photo1 = _cuma_11000_photo_for_preview(original)
        photo2 = _cuma_11000_photo_for_preview(processed)
        lbl1 = ttk.Label(left, image=photo1)
        lbl2 = ttk.Label(right, image=photo2)
        lbl1.image = photo1
        lbl2.image = photo2
        lbl1.pack(expand=True, pady=8)
        lbl2.pack(expand=True, pady=8)

        ttk.Label(
            wrap,
            text='Esta prévia não usa perfil de dispositivo e não adiciona canvas branco. O Converter trabalha com o arquivo já preparado; ajustes visuais ficam na aba Limpar.',
            style='Muted.TLabel',
            wraplength=900,
            justify='left'
        ).pack(anchor='w', pady=(10, 0))
        ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(12, 0))
    except Exception as exc:
        _cuma_11002_log('Falha na prévia antes/depois 1.100.2', exc)
        messagebox.showerror('Prévia antes/depois', friendly_error(exc))


def _cuma_11002_open_converter_preview(self) -> None:
    """Prévia da aba Converter: conversão pura, sem reprocessar a página."""
    try:
        src = _cuma_11002_selected_converter_path(self)
        if not src:
            messagebox.showwarning('Prévia', 'Selecione ou adicione um arquivo compatível.')
            return
        original = _cuma_11002_first_source_image_raw(src)
        if original is None:
            messagebox.showwarning('Prévia', 'Não consegui abrir uma imagem de prévia para este arquivo.')
            return
        processed = original.copy()

        top = tk.Toplevel(self.root)
        top.title('Prévia do Converter - CUMA 1.100.2')
        top.geometry('980x680')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass

        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Prévia do Converter', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 6))
        ttk.Label(
            wrap,
            text=f'{src.name}  •  Conversão pura: sem corte, sem divisão, sem webtoon e sem preset E-ink.',
            style='Muted.TLabel',
            wraplength=900,
            justify='left'
        ).pack(anchor='w', pady=(0, 12))

        grid = ttk.Frame(wrap, style='Card.TFrame')
        grid.pack(fill='both', expand=True)
        left = ttk.Frame(grid, style='Card.TFrame')
        right = ttk.Frame(grid, style='Card.TFrame')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))
        right.pack(side='left', fill='both', expand=True, padx=(8, 0))
        ttk.Label(left, text='Entrada selecionada', style='Strong.TLabel').pack(anchor='center')
        ttk.Label(right, text='Como será enviado ao conversor', style='Strong.TLabel').pack(anchor='center')

        photo1 = _cuma_11000_photo_for_preview(original)
        photo2 = _cuma_11000_photo_for_preview(processed)
        lbl1 = ttk.Label(left, image=photo1)
        lbl2 = ttk.Label(right, image=photo2)
        lbl1.image = photo1
        lbl2.image = photo2
        lbl1.pack(expand=True, pady=8)
        lbl2.pack(expand=True, pady=8)

        ttk.Label(
            wrap,
            text='Se precisar remover margem, dividir página dupla, tratar webtoon ou aplicar E-ink, faça isso antes na aba Limpar. A aba Converter não altera estruturalmente o arquivo.',
            style='Muted.TLabel',
            wraplength=900,
            justify='left'
        ).pack(anchor='w', pady=(10, 0))
        ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(12, 0))
    except Exception as exc:
        _cuma_11002_log('Falha na prévia do Converter 1.100.2', exc)
        messagebox.showerror('Prévia', friendly_error(exc))


def _cuma_11002_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11002_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11002_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11002_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'Converter agora trabalha em modo puro: não reaplica limpeza, presets, páginas duplas, webtoon nem encaixe de dispositivo em EPUB/CBZ/imagens/PDF.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11002_VERSION)
    except Exception:
        pass
    try:
        state = cuma_version_load_state()
        events = state.get('events', [])
        if not isinstance(events, list):
            events = []
        if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11002_UPDATE_ID for e in events):
            events.append({
                'update_id': CUMA_11002_UPDATE_ID,
                'version': CUMA_11002_VERSION,
                'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                'scale': 'pouca',
                'description': 'Garante separação total: Limpar modifica conteúdo; Converter apenas troca formato sem reprocessar visualmente.',
                'timestamp': datetime.now().isoformat(timespec='seconds')
            })
        state['events'] = events[-100:]
        state['current_version'] = CUMA_11002_VERSION
        state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
        cuma_version_save_state(state)
        if '_cuma_version_write_public_files' in globals():
            _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11002_log('Versionamento 1.100.2', exc)


def _cuma_install_11002_converter_puro() -> None:
    try:
        _cuma_11002_force_version()
        # O worker 1.100.1 chama este nome global; trocar o alvo corrige o lote inteiro.
        globals()['_cuma_11001_run_xteink_job'] = _cuma_11002_run_xteink_job
        globals()['_cuma_run_xteink_job'] = _cuma_11002_run_xteink_job
        globals()['_cuma_11000_open_before_after_preview'] = _cuma_11002_open_before_after_preview
        App.open_xteink_preview = _cuma_11002_open_converter_preview
    except Exception as exc:
        _cuma_11002_log('Instalação patch 1.100.2', exc)


_cuma_install_11002_converter_puro()




# ---------------------------------------------------------------------------
# CUMA 1.100.3 - Integração real da otimização na aba Limpar + Converter mais limpo
# ---------------------------------------------------------------------------
CUMA_11003_VERSION = '1.100.3'
CUMA_11003_UPDATE_ID = 'limpar_kcc_real_converter_preview_unificada_11003'


def _cuma_11003_log(msg: str, exc: Exception | None = None) -> None:
    try:
        if '_cuma_11002_log' in globals():
            _cuma_11002_log(msg, exc)
        elif '_cuma_11001_log' in globals():
            _cuma_11001_log(msg, exc)
        else:
            write_log(f'{msg}: {exc}' if exc else msg)
    except Exception:
        pass


def _cuma_11003_processing_active(settings: dict | None = None) -> bool:
    """Retorna True somente quando a aba Limpar tem alguma transformação visual ativa."""
    try:
        data = settings if isinstance(settings, dict) else (
            _cuma_11000_processing_settings() if '_cuma_11000_processing_settings' in globals() else {}
        )
        preset = str(data.get('image_preset') or 'Original')
        return bool(
            data.get('auto_crop')
            or data.get('remove_page_numbers')
            or data.get('split_double_pages')
            or data.get('webtoon_split')
            or preset != 'Original'
        )
    except Exception:
        return False


def _cuma_11003_page_to_image(page: fitz.Page) -> Image.Image:
    """Extrai a imagem principal da página limpa quando possível; fallback renderiza a página."""
    try:
        blocks = [b for b in page.get_text('dict').get('blocks', []) if b.get('type') == 1 and b.get('image')]
        if blocks:
            block = max(blocks, key=lambda b: int(b.get('width', 0)) * int(b.get('height', 0)))
            raw = block.get('image')
            if raw:
                return Image.open(BytesIO(raw)).convert('RGB')
    except Exception as exc:
        _cuma_11003_log('Extração direta da imagem da página limpa ignorada', exc)
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
        return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
    except Exception:
        pix = page.get_pixmap(alpha=False)
        return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)


def _cuma_11003_insert_image_page(doc: fitz.Document, im: Image.Image, quality: int = 94) -> None:
    rgb = im.convert('RGB')
    bio = BytesIO()
    rgb.save(bio, format='JPEG', quality=int(max(50, min(100, quality or 94))), optimize=True)
    page = doc.new_page(width=max(1, rgb.width), height=max(1, rgb.height))
    page.insert_image(page.rect, stream=bio.getvalue(), keep_proportion=False)


def _cuma_11003_process_clean_pdf_in_place(pdf_path: Path, settings: dict | None = None, cancel=None) -> dict:
    """Aplica as opções da aba Limpar no PDF já limpo.

    Esta etapa é propositalmente exclusiva da aba Limpar. O Converter permanece em
    conversão pura e não chama este fluxo.
    """
    pdf_path = Path(pdf_path)
    data = settings if isinstance(settings, dict) else (
        _cuma_11000_processing_settings() if '_cuma_11000_processing_settings' in globals() else {}
    )
    stats = {
        'input_pages': 0,
        'output_pages': 0,
        'double_pages_split': 0,
        'webtoon_segments': 0,
        'active': _cuma_11003_processing_active(data),
    }
    if not stats['active'] or not pdf_path.exists() or pdf_path.suffix.lower() != '.pdf':
        return stats

    src = out = None
    tmp = pdf_path.with_suffix('.cuma_opt.tmp.pdf')
    try:
        src = fitz.open(str(pdf_path))
        out = fitz.open()
        stats['input_pages'] = len(src)
        for idx, page in enumerate(src, 1):
            if cancel and cancel():
                raise RuntimeError('Processamento cancelado pelo usuário.')
            original = _cuma_11003_page_to_image(page)
            ow, oh = original.size
            produced = []
            try:
                if '_cuma_11000_process_source_image' in globals():
                    produced = _cuma_11000_process_source_image(original, None, data)
                else:
                    produced = [original]
            except Exception as exc:
                _cuma_11003_log(f'Otimização Limpar ignorada na página {idx}', exc)
                produced = [original]
            if not produced:
                produced = [original]
            if len(produced) > 1 and data.get('split_double_pages') and ow / max(1, oh) >= 1.22:
                stats['double_pages_split'] += 1
            if len(produced) > 1 and data.get('webtoon_split') and oh / max(1, ow) > float(data.get('webtoon_max_ratio', 2.8) or 2.8):
                stats['webtoon_segments'] += max(0, len(produced) - 1)
            for im in produced:
                try:
                    _cuma_11003_insert_image_page(out, im, quality=94)
                    stats['output_pages'] += 1
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
            try:
                if original not in produced:
                    original.close()
            except Exception:
                pass

        if stats['output_pages'] <= 0:
            raise RuntimeError('A otimização da aba Limpar não gerou páginas.')
        tmp.unlink(missing_ok=True)
        out.save(str(tmp), garbage=4, deflate=True, clean=True)
        src.close(); src = None
        out.close(); out = None
        pdf_path.unlink(missing_ok=True)
        tmp.replace(pdf_path)
        return stats
    finally:
        for doc in (src, out):
            try:
                if doc is not None:
                    doc.close()
            except Exception:
                pass
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


_CUMA_11003_ORIGINAL_PDF_CLEAN = getattr(PDFCleaner, 'clean', None)


def _cuma_11003_pdf_clean(self, source: Path, output_pdf: Path, progress=None, cancel=None) -> Result:
    result = _CUMA_11003_ORIGINAL_PDF_CLEAN(self, source, output_pdf, progress=progress, cancel=cancel)
    try:
        settings = _cuma_11000_processing_settings() if '_cuma_11000_processing_settings' in globals() else {}
        out_path = Path(getattr(result, 'output', '') or '')
        if out_path.exists() and out_path.suffix.lower() == '.pdf' and _cuma_11003_processing_active(settings):
            before_pages = int(getattr(result, 'final_pages', 0) or 0)
            stats = _cuma_11003_process_clean_pdf_in_place(out_path, settings=settings, cancel=cancel)
            if stats.get('output_pages'):
                result.final_pages = int(stats.get('output_pages') or result.final_pages)
                try:
                    result.final_size = out_path.stat().st_size
                except Exception:
                    pass
                try:
                    result.saved_bytes = max(0, int(result.original_size or 0) - int(result.final_size or 0))
                except Exception:
                    pass
                extras = []
                if str(getattr(result, 'extra_outputs', '') or '').strip():
                    extras.append(str(result.extra_outputs))
                if stats.get('double_pages_split'):
                    extras.append(f"páginas duplas divididas: {stats.get('double_pages_split')}")
                if stats.get('webtoon_segments'):
                    extras.append(f"segmentos webtoon: {stats.get('webtoon_segments')}")
                result.extra_outputs = ' | '.join(extras)
                mode = str(getattr(result, 'mode', '') or '')
                suffix = ' + otimização Limpar'
                if suffix not in mode:
                    result.mode = mode + suffix
                if before_pages and result.final_pages != before_pages:
                    result.mode = str(result.mode) + f' ({before_pages}→{result.final_pages} págs.)'
    except Exception as exc:
        _cuma_11003_log('Otimização pós-Limpar ignorada', exc)
    return result


def _cuma_11003_selected_clean_source(self) -> Path | None:
    try:
        selected = self.selected_paths()
        if selected:
            return Path(selected[0])
    except Exception:
        pass
    try:
        files = list(getattr(self, 'files', []) or [])
        if files:
            return Path(files[0])
    except Exception:
        pass
    return None


def _cuma_11003_open_clean_preview(self) -> None:
    """Prévia da aba Limpar: mostra o efeito real dos controles KCC/E-ink antes de processar."""
    try:
        src = _cuma_11003_selected_clean_source(self)
        if not src:
            messagebox.showwarning('Prévia Limpar', 'Adicione ou selecione um PDF na aba Limpar.')
            return
        if src.suffix.lower() != '.pdf':
            messagebox.showwarning('Prévia Limpar', 'A prévia da aba Limpar usa arquivos PDF.')
            return
        doc = fitz.open(str(src))
        try:
            if len(doc) <= 0:
                messagebox.showwarning('Prévia Limpar', 'PDF sem páginas.')
                return
            original = _cuma_11003_page_to_image(doc[0])
        finally:
            doc.close()
        settings = _cuma_11000_app_processing_settings(self) if '_cuma_11000_app_processing_settings' in globals() else {}
        processed_pages = _cuma_11000_process_source_image(original.copy(), None, settings) if '_cuma_11000_process_source_image' in globals() else [original.copy()]
        processed = processed_pages[0] if processed_pages else original.copy()
        top = tk.Toplevel(self.root)
        top.title('Prévia Limpar - CUMA 1.100.3')
        top.geometry('980x680')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            top.configure(bg=pal.get('bg', '#0F1318'))
        except Exception:
            pass
        wrap = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrap.pack(fill='both', expand=True)
        ttk.Label(wrap, text='Prévia da aba Limpar', style='TitleSmall.TLabel').pack(anchor='w', pady=(0, 6))
        info = f'{src.name}  •  Preset: {settings.get("image_preset")}  •  Leitura: {settings.get("reading_order")}'
        if len(processed_pages) > 1:
            info += f'  •  Saída desta página: {len(processed_pages)} páginas'
        ttk.Label(wrap, text=info, style='Muted.TLabel').pack(anchor='w', pady=(0, 12))
        grid = ttk.Frame(wrap, style='Card.TFrame')
        grid.pack(fill='both', expand=True)
        left = ttk.Frame(grid, style='Card.TFrame'); right = ttk.Frame(grid, style='Card.TFrame')
        left.pack(side='left', fill='both', expand=True, padx=(0, 8)); right.pack(side='left', fill='both', expand=True, padx=(8, 0))
        ttk.Label(left, text='Original', style='Strong.TLabel').pack(anchor='center')
        ttk.Label(right, text='Processado pela aba Limpar', style='Strong.TLabel').pack(anchor='center')
        photo1 = _cuma_11000_photo_for_preview(original) if '_cuma_11000_photo_for_preview' in globals() else ImageTk.PhotoImage(original)
        photo2 = _cuma_11000_photo_for_preview(processed) if '_cuma_11000_photo_for_preview' in globals() else ImageTk.PhotoImage(processed)
        lbl1 = ttk.Label(left, image=photo1); lbl2 = ttk.Label(right, image=photo2)
        lbl1.image = photo1; lbl2.image = photo2
        lbl1.pack(expand=True, pady=8); lbl2.pack(expand=True, pady=8)
        ttk.Label(wrap, text='Esta prévia representa as opções da aba Limpar. O Converter não reaplica estas alterações.', style='Muted.TLabel', wraplength=900, justify='left').pack(anchor='w', pady=(10, 0))
        ttk.Button(wrap, text='Fechar', command=top.destroy, style='Accent.TButton').pack(anchor='e', pady=(12, 0))
        try:
            original.close()
            for im in processed_pages:
                im.close()
        except Exception:
            pass
    except Exception as exc:
        _cuma_11003_log('Falha na prévia da aba Limpar', exc)
        messagebox.showerror('Prévia Limpar', friendly_error(exc))


def _cuma_11003_add_clean_optimization_panel(self) -> None:
    """Recria o painel da aba Limpar com opções que realmente entram no fluxo de limpeza."""
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        for child in list(tab.winfo_children()):
            try:
                text = str(child.cget('text')) if isinstance(child, ttk.LabelFrame) else ''
                if 'Limpeza e otimização' in text or 'Otimização de leitura' in text or 'Limpar: preparação' in text:
                    child.destroy()
            except Exception:
                pass

        settings = _cuma_11000_app_processing_settings(self) if '_cuma_11000_app_processing_settings' in globals() else {}

        if not hasattr(self, 'cuma_reading_order'):
            self.cuma_reading_order = tk.StringVar(value=settings.get('reading_order', 'Ocidental'))
        if not hasattr(self, 'cuma_image_preset'):
            self.cuma_image_preset = tk.StringVar(value=settings.get('image_preset', 'Original'))
        if not hasattr(self, 'cuma_auto_crop'):
            self.cuma_auto_crop = tk.BooleanVar(value=bool(settings.get('auto_crop', False)))
        if not hasattr(self, 'cuma_auto_crop_strength'):
            self.cuma_auto_crop_strength = tk.StringVar(value=settings.get('auto_crop_strength', 'Normal'))
        if not hasattr(self, 'cuma_remove_page_numbers'):
            self.cuma_remove_page_numbers = tk.BooleanVar(value=bool(settings.get('remove_page_numbers', False)))
        if not hasattr(self, 'cuma_split_double_pages'):
            self.cuma_split_double_pages = tk.BooleanVar(value=bool(settings.get('split_double_pages', False)))
        if not hasattr(self, 'cuma_split_keep_original'):
            self.cuma_split_keep_original = tk.BooleanVar(value=bool(settings.get('split_keep_original', False)))
        if not hasattr(self, 'cuma_webtoon_split'):
            self.cuma_webtoon_split = tk.BooleanVar(value=bool(settings.get('webtoon_split', False)))

        before = _cuma_11001_find_tree_frame(tab) if '_cuma_11001_find_tree_frame' in globals() else None
        kwargs = {'fill': 'x', 'pady': (0, 10)}
        if before is not None:
            kwargs['before'] = before

        panel = ttk.LabelFrame(tab, text='Limpar: preparação visual das páginas', padding=12, style='Card.TLabelframe')
        panel.pack(**kwargs)

        ttk.Label(panel, text='Estas opções são aplicadas ao clicar em Processar na aba Limpar. O Converter apenas usa o arquivo já limpo.', style='Muted.TLabel', wraplength=1050, justify='left').grid(row=0, column=0, columnspan=7, sticky='w', pady=(0, 8))

        ttk.Label(panel, text='Ordem', style='Muted.TLabel').grid(row=1, column=0, sticky='w', padx=(0, 8), pady=4)
        cb_order = ttk.Combobox(panel, textvariable=self.cuma_reading_order, values=globals().get('CUMA_11000_READING_ORDERS', ('Ocidental', 'Mangá')), state='readonly', width=12)
        cb_order.grid(row=1, column=1, sticky='w', pady=4)

        ttk.Label(panel, text='Preset E-ink', style='Muted.TLabel').grid(row=1, column=2, sticky='w', padx=(18, 8), pady=4)
        cb_preset = ttk.Combobox(panel, textvariable=self.cuma_image_preset, values=globals().get('CUMA_11000_IMAGE_PRESETS', ('Original',)), state='readonly', width=24)
        cb_preset.grid(row=1, column=3, sticky='w', pady=4)

        ttk.Label(panel, text='Corte', style='Muted.TLabel').grid(row=1, column=4, sticky='w', padx=(18, 8), pady=4)
        cb_crop = ttk.Combobox(panel, textvariable=self.cuma_auto_crop_strength, values=globals().get('CUMA_11000_CROP_STRENGTHS', ('Suave', 'Normal', 'Forte')), state='readonly', width=10)
        cb_crop.grid(row=1, column=5, sticky='w', pady=4)

        def save_processing():
            try:
                _cuma_11000_set_processing_from_app(self)
            except Exception as exc:
                _cuma_11003_log('Salvar opções da aba Limpar', exc)
            try:
                self.save_current_config()
            except Exception:
                pass

        ttk.Checkbutton(panel, text='Remover margens', variable=self.cuma_auto_crop, command=save_processing).grid(row=2, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Remover número/rodapé', variable=self.cuma_remove_page_numbers, command=save_processing).grid(row=2, column=2, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Dividir páginas duplas', variable=self.cuma_split_double_pages, command=save_processing).grid(row=2, column=4, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Manter original ao dividir', variable=self.cuma_split_keep_original, command=save_processing).grid(row=3, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(panel, text='Webtoon/imagens longas', variable=self.cuma_webtoon_split, command=save_processing).grid(row=3, column=2, columnspan=2, sticky='w', pady=4)
        ttk.Button(panel, text='Prévia Limpar', command=lambda: _cuma_11003_open_clean_preview(self), style='Accent.TButton').grid(row=3, column=4, sticky='w', padx=(0, 8), pady=4)

        for cb in (cb_order, cb_preset, cb_crop):
            cb.bind('<<ComboboxSelected>>', lambda _e: save_processing())

        ttk.Label(panel, text='Exemplo: se uma página estiver muito larga, ative "Dividir páginas duplas". Em leitura Mangá, a metade direita sai antes da esquerda.', style='Muted.TLabel', wraplength=1050, justify='left').grid(row=4, column=0, columnspan=7, sticky='w', pady=(8, 0))
        panel.columnconfigure(6, weight=1)
    except Exception as exc:
        _cuma_11003_log('Adicionar painel Limpar 1.100.3', exc)


def _cuma_11003_add_converter_dynamic_panel(self) -> None:
    """Painel de conversão sem prévia duplicada; a prévia fica no botão superior do Converter."""
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        if '_cuma_11001_setup_conversion_vars' in globals():
            _cuma_11001_setup_conversion_vars(self)

        for child in list(tab.winfo_children()):
            try:
                if isinstance(child, ttk.LabelFrame) and str(child.cget('text')) in (
                    'Conversões disponíveis', 'Prévia, metadados e conversões', 'Conversões compatíveis'
                ):
                    child.destroy()
            except Exception:
                pass

        children = list(tab.winfo_children())
        kwargs = {'fill': 'x', 'pady': (0, 10)}
        if children:
            kwargs['before'] = children[1] if len(children) > 1 else children[0]

        panel = ttk.LabelFrame(tab, text='Conversões compatíveis', padding=12, style='Card.TLabelframe')
        panel.pack(**kwargs)

        top = ttk.Frame(panel, style='Card.TFrame')
        top.grid(row=0, column=0, columnspan=4, sticky='ew')
        ttk.Button(top, text='Metadados EPUB', command=lambda: _cuma_11000_open_metadata_editor(self), style='Ghost.TButton').pack(side='left', padx=(0, 8))
        ttk.Label(top, text='Selecione/adicione um arquivo. O CUMA libera apenas as conversões compatíveis com o tipo detectado.', style='Muted.TLabel').pack(side='left', padx=(10, 0))

        self.cuma_conversion_hint = tk.StringVar(value='Adicione ou selecione um arquivo para liberar as conversões compatíveis.')
        ttk.Label(panel, textvariable=self.cuma_conversion_hint, style='Muted.TLabel', wraplength=1050, justify='left').grid(row=1, column=0, columnspan=4, sticky='w', pady=(10, 6))

        grid = ttk.Frame(panel, style='Card.TFrame')
        grid.grid(row=2, column=0, columnspan=4, sticky='ew')
        self._cuma_11001_conversion_widgets = {}
        ordered = (
            'pdf_epub', 'pdf_xtch', 'pdf_cbz', 'pdf_images',
            'epub_xtch', 'epub_pdf',
            'archive_epub', 'archive_xtch', 'archive_pdf',
            'images_pdf', 'images_epub', 'images_xtch'
        )
        for idx, key in enumerate(ordered):
            var = _cuma_11001_var_for_key(self, key)
            cb = ttk.Checkbutton(grid, text=CUMA_11001_CONVERSION_LABELS[key], variable=var)
            cb.grid(row=idx // 4, column=idx % 4, sticky='w', padx=(0, 18), pady=4)
            self._cuma_11001_conversion_widgets[key] = cb

        try:
            self.xteink_tree.bind('<<TreeviewSelect>>', lambda _e: _cuma_11001_refresh_conversion_options(self), add='+')
        except Exception:
            pass
        try:
            self.xteink_input.trace_add('write', lambda *_: _cuma_11001_refresh_conversion_options(self))
        except Exception:
            pass
        _cuma_11001_refresh_conversion_options(self)
    except Exception as exc:
        _cuma_11003_log('Adicionar painel Converter 1.100.3', exc)


def _cuma_11003_unify_converter_preview_button(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        for child in tab.winfo_children():
            try:
                for btn in child.winfo_children():
                    try:
                        if isinstance(btn, ttk.Button) and str(btn.cget('text')).strip() == 'Prévia':
                            btn.configure(text='Prévia', command=self.open_xteink_preview, style='Accent.TButton')
                            return
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception as exc:
        _cuma_11003_log('Unificar botão de prévia do Converter', exc)


def _cuma_11003_reorganize_ui(self) -> None:
    try:
        if '_cuma_11001_destroy_legacy_converter_optimization_panel' in globals():
            _cuma_11001_destroy_legacy_converter_optimization_panel(self)
    except Exception:
        pass
    try:
        if '_cuma_11001_remove_legacy_converter_checkbuttons' in globals():
            _cuma_11001_remove_legacy_converter_checkbuttons(self)
    except Exception:
        pass
    _cuma_11003_add_clean_optimization_panel(self)
    _cuma_11003_add_converter_dynamic_panel(self)
    _cuma_11003_unify_converter_preview_button(self)
    try:
        if '_cuma_11001_remove_legacy_converter_checkbuttons' in globals():
            _cuma_11001_remove_legacy_converter_checkbuttons(self)
    except Exception:
        pass


_CUMA_11003_RUNTIME = {
    'build': getattr(App, 'build', None),
    'save_current_config': getattr(App, 'save_current_config', None),
}


def _cuma_11003_build(self):
    result = _CUMA_11003_RUNTIME['build'](self)
    try:
        _cuma_11003_reorganize_ui(self)
    except Exception as exc:
        _cuma_11003_log('Reorganização UI 1.100.3', exc)
    return result


def _cuma_11003_save_current_config(self, force: bool = False):
    result = _CUMA_11003_RUNTIME['save_current_config'](self, force)
    try:
        if '_cuma_11000_set_processing_from_app' in globals():
            _cuma_11000_set_processing_from_app(self)
    except Exception as exc:
        _cuma_11003_log('Salvar opções Limpar 1.100.3', exc)
    return result


def _cuma_11003_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11003_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11003_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11003_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'Integração real das opções KCC/E-ink na aba Limpar, divisão de páginas duplas no processamento e prévia do Converter sem duplicação.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11003_VERSION)
    except Exception:
        pass
    try:
        state = cuma_version_load_state()
        events = state.get('events', [])
        if not isinstance(events, list):
            events = []
        if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11003_UPDATE_ID for e in events):
            events.append({
                'update_id': CUMA_11003_UPDATE_ID,
                'version': CUMA_11003_VERSION,
                'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                'scale': 'pouca',
                'description': 'Aplica páginas duplas/webtoon/presets na aba Limpar de verdade e remove a prévia duplicada do Converter.',
                'timestamp': datetime.now().isoformat(timespec='seconds')
            })
        state['events'] = events[-100:]
        state['current_version'] = CUMA_11003_VERSION
        state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
        cuma_version_save_state(state)
        if '_cuma_version_write_public_files' in globals():
            _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11003_log('Versionamento 1.100.3', exc)


def _cuma_install_11003_clean_kcc_and_preview() -> None:
    try:
        _cuma_11003_force_version()
        if _CUMA_11003_ORIGINAL_PDF_CLEAN is not None:
            PDFCleaner.clean = _cuma_11003_pdf_clean
        App.build = _cuma_11003_build
        App.save_current_config = _cuma_11003_save_current_config
        App.open_cuma_clean_preview = _cuma_11003_open_clean_preview
        # Reaproveita a prévia mais nova no botão antigo da barra superior.
        App.open_xteink_preview = _cuma_11002_open_converter_preview if '_cuma_11002_open_converter_preview' in globals() else App.open_xteink_preview
        globals()['_cuma_11001_add_clean_optimization_panel'] = _cuma_11003_add_clean_optimization_panel
        globals()['_cuma_11001_add_converter_dynamic_panel'] = _cuma_11003_add_converter_dynamic_panel
        globals()['_cuma_11001_reorganize_ui'] = _cuma_11003_reorganize_ui
    except Exception as exc:
        _cuma_11003_log('Instalação patch 1.100.3', exc)


_cuma_install_11003_clean_kcc_and_preview()



# -----------------------------------------------------------------------------
# CUMA 1.100.4 - acabamento visual Limpar/Converter, metadados contextuais e limpeza de UI.
# -----------------------------------------------------------------------------

CUMA_11004_VERSION = '1.100.4'
CUMA_11004_UPDATE_ID = 'converter_clean_ui_metadata_context_11004'


def _cuma_11004_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'[CUMA 1.100.4] {context}' if exc is None else f'[CUMA 1.100.4] {context}: {exc}'
        write_log(msg)
    except Exception:
        pass


def _cuma_11004_ensure_clean_vars(self) -> dict:
    settings = _cuma_11000_app_processing_settings(self) if '_cuma_11000_app_processing_settings' in globals() else {}
    try:
        if not hasattr(self, 'cuma_reading_order'):
            self.cuma_reading_order = tk.StringVar(value=settings.get('reading_order', 'Ocidental'))
        if not hasattr(self, 'cuma_image_preset'):
            self.cuma_image_preset = tk.StringVar(value=settings.get('image_preset', 'Original'))
        if not hasattr(self, 'cuma_auto_crop'):
            self.cuma_auto_crop = tk.BooleanVar(value=bool(settings.get('auto_crop', False)))
        if not hasattr(self, 'cuma_auto_crop_strength'):
            self.cuma_auto_crop_strength = tk.StringVar(value=settings.get('auto_crop_strength', 'Normal'))
        if not hasattr(self, 'cuma_remove_page_numbers'):
            self.cuma_remove_page_numbers = tk.BooleanVar(value=bool(settings.get('remove_page_numbers', False)))
        if not hasattr(self, 'cuma_split_double_pages'):
            self.cuma_split_double_pages = tk.BooleanVar(value=bool(settings.get('split_double_pages', False)))
        if not hasattr(self, 'cuma_split_keep_original'):
            self.cuma_split_keep_original = tk.BooleanVar(value=bool(settings.get('split_keep_original', False)))
        if not hasattr(self, 'cuma_webtoon_split'):
            self.cuma_webtoon_split = tk.BooleanVar(value=bool(settings.get('webtoon_split', False)))
    except Exception as exc:
        _cuma_11004_log('Garantia de variáveis da aba Limpar', exc)
    return settings


def _cuma_11004_save_clean_settings(self) -> None:
    try:
        if '_cuma_11000_set_processing_from_app' in globals():
            _cuma_11000_set_processing_from_app(self)
    except Exception as exc:
        _cuma_11004_log('Salvar opções de preparação visual', exc)
    try:
        self.save_current_config(force=True)
    except Exception:
        pass


def _cuma_11004_remove_clean_optimization_panel(self) -> None:
    """Remove o bloco grande da aba Limpar. As opções passam a ficar em Configurações do PDF."""
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        targets = []
        stack = [tab]
        while stack:
            widget = stack.pop()
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            try:
                txt = str(widget.cget('text') or '').lower()
            except Exception:
                txt = ''
            try:
                klass = widget.winfo_class()
            except Exception:
                klass = ''
            if klass in ('TLabelframe', 'Labelframe') or isinstance(widget, ttk.LabelFrame):
                if (
                    'limpar: preparação' in txt
                    or 'preparação visual' in txt
                    or 'otimização de leitura' in txt
                    or 'limpeza e otimização' in txt
                ):
                    targets.append(widget)
        for widget in targets:
            try:
                widget.destroy()
            except Exception:
                pass
    except Exception as exc:
        _cuma_11004_log('Remover painel grande da aba Limpar', exc)


def _cuma_11004_replace_clean_preview_button(self) -> None:
    """Substitui a prévia antiga da aba Limpar pela prévia real das opções de limpeza."""
    try:
        tab = getattr(self, 'tab_files', None)
        if tab is None:
            return
        stack = [tab]
        while stack:
            widget = stack.pop()
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            try:
                txt = str(widget.cget('text') or '').strip()
            except Exception:
                txt = ''
            try:
                klass = widget.winfo_class()
            except Exception:
                klass = ''
            if (klass == 'TButton' or isinstance(widget, ttk.Button)) and txt == 'Prévia':
                try:
                    widget.configure(text='Prévia Limpar', command=lambda: _cuma_11003_open_clean_preview(self), style='Accent.TButton')
                except Exception:
                    widget.configure(command=lambda: _cuma_11003_open_clean_preview(self))
                return
    except Exception as exc:
        _cuma_11004_log('Trocar botão de prévia da aba Limpar', exc)


def _cuma_11004_open_pdf_settings_window(self) -> None:
    """Janela de Configurações do PDF com as opções KCC/E-ink que modificam páginas."""
    try:
        _cuma_11004_ensure_clean_vars(self)
        top = tk.Toplevel(self.root)
        top.title('Configurações do PDF')
        try:
            pal = getattr(self, '_theme_palette', {}) or {}
            if pal.get('bg'):
                top.configure(bg=pal.get('bg'))
        except Exception:
            pass

        wrapper = ttk.Frame(top, style='Card.TFrame', padding=14)
        wrapper.pack(fill='both', expand=True, padx=12, pady=12)
        ttk.Label(wrapper, text='Configurações do PDF', style='TitleSmall.TLabel').grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 8))
        ttk.Label(
            wrapper,
            text='A aba Limpar mantém o fluxo principal enxuto. Opções avançadas de preparação visual ficam aqui e são aplicadas somente ao processar/limpar o PDF.',
            style='Muted.TLabel',
            wraplength=820,
            justify='left'
        ).grid(row=1, column=0, columnspan=4, sticky='w', pady=(0, 12))

        rows = [
            ('Modo', ttk.Combobox(wrapper, textvariable=self.mode, values=MODES, state='readonly', width=28)),
            ('Perfil', ttk.Combobox(wrapper, textvariable=self.profile, values=PROFILES, state='readonly', width=28)),
            ('Compactação', ttk.Combobox(wrapper, textvariable=self.compression, values=COMPRESSION_OPTIONS, state='readonly', width=36)),
            ('Senha PDF', ttk.Entry(wrapper, textvariable=self.password, show='*', width=38)),
        ]
        for offset, (label, widget) in enumerate(rows, start=2):
            ttk.Label(wrapper, text=label, style='Muted.TLabel').grid(row=offset, column=0, sticky='w', pady=5, padx=(0, 12))
            widget.grid(row=offset, column=1, sticky='w', pady=5)
            try:
                if isinstance(widget, ttk.Combobox):
                    widget.bind('<<ComboboxSelected>>', lambda _e: self.save_current_config(force=True))
                else:
                    widget.bind('<FocusOut>', lambda _e: self.save_current_config(force=True))
            except Exception:
                pass

        row = 6
        ttk.Separator(wrapper, orient='horizontal').grid(row=row, column=0, columnspan=4, sticky='ew', pady=(10, 12))
        row += 1
        ttk.Label(wrapper, text='Preparação visual de páginas', style='TitleSmall.TLabel').grid(row=row, column=0, columnspan=4, sticky='w', pady=(0, 6))
        row += 1
        ttk.Label(
            wrapper,
            text='Essas opções vêm da integração inspirada no KCC. Elas mudam o conteúdo do PDF limpo; o Converter apenas transforma formato.',
            style='Muted.TLabel',
            wraplength=820,
            justify='left'
        ).grid(row=row, column=0, columnspan=4, sticky='w', pady=(0, 8))
        row += 1

        def save_processing(*_):
            _cuma_11004_save_clean_settings(self)

        ttk.Label(wrapper, text='Ordem de leitura', style='Muted.TLabel').grid(row=row, column=0, sticky='w', pady=5)
        cb_order = ttk.Combobox(wrapper, textvariable=self.cuma_reading_order, values=globals().get('CUMA_11000_READING_ORDERS', ('Ocidental', 'Mangá')), state='readonly', width=16)
        cb_order.grid(row=row, column=1, sticky='w', pady=5)
        ttk.Label(wrapper, text='Preset E-ink', style='Muted.TLabel').grid(row=row, column=2, sticky='w', padx=(18, 8), pady=5)
        cb_preset = ttk.Combobox(wrapper, textvariable=self.cuma_image_preset, values=globals().get('CUMA_11000_IMAGE_PRESETS', ('Original',)), state='readonly', width=26)
        cb_preset.grid(row=row, column=3, sticky='w', pady=5)
        row += 1

        ttk.Checkbutton(wrapper, text='Remover margens automaticamente', variable=self.cuma_auto_crop, command=save_processing).grid(row=row, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Label(wrapper, text='Força do corte', style='Muted.TLabel').grid(row=row, column=2, sticky='w', padx=(18, 8), pady=5)
        cb_crop = ttk.Combobox(wrapper, textvariable=self.cuma_auto_crop_strength, values=('Suave', 'Normal', 'Forte'), state='readonly', width=12)
        cb_crop.grid(row=row, column=3, sticky='w', pady=5)
        row += 1

        ttk.Checkbutton(wrapper, text='Remover rodapé/número de página', variable=self.cuma_remove_page_numbers, command=save_processing).grid(row=row, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(wrapper, text='Dividir páginas duplas', variable=self.cuma_split_double_pages, command=save_processing).grid(row=row, column=2, columnspan=2, sticky='w', pady=4)
        row += 1

        ttk.Checkbutton(wrapper, text='Manter original ao dividir', variable=self.cuma_split_keep_original, command=save_processing).grid(row=row, column=0, columnspan=2, sticky='w', pady=4)
        ttk.Checkbutton(wrapper, text='Webtoon/imagens longas', variable=self.cuma_webtoon_split, command=save_processing).grid(row=row, column=2, columnspan=2, sticky='w', pady=4)
        row += 1

        ttk.Button(wrapper, text='Prévia Limpar', command=lambda: _cuma_11003_open_clean_preview(self), style='Accent.TButton').grid(row=row, column=0, sticky='w', pady=(8, 10))
        ttk.Label(
            wrapper,
            text='Dica: para páginas muito largas, ative “Dividir páginas duplas”. Em leitura Mangá, a metade direita sai antes da esquerda.',
            style='Muted.TLabel',
            wraplength=690,
            justify='left'
        ).grid(row=row, column=1, columnspan=3, sticky='w', pady=(8, 10))
        row += 1

        ttk.Separator(wrapper, orient='horizontal').grid(row=row, column=0, columnspan=4, sticky='ew', pady=(4, 12))
        row += 1
        for txt, var in (
            ('Sobrescrever originais', self.overwrite_original),
            ('Criar backup', self.create_backup),
            ('Sempre manter primeira página', self.keep_first),
            ('Salvar PDF com páginas removidas', self.save_removed_pdf),
            ('Validar PDF final', self.validate_output),
            ('Pular arquivos já processados', self.skip_existing),
            ('Detectar duplicidades', self.detect_duplicates),
            ('Processar automaticamente ao adicionar', self.auto_process_added),
        ):
            ttk.Checkbutton(wrapper, text=txt, variable=var, command=self.save_current_config).grid(row=row, column=0, columnspan=2, sticky='w', pady=3)
            row += 1

        ttk.Label(wrapper, text='Manter últimas páginas', style='Muted.TLabel').grid(row=row, column=0, sticky='w', pady=5)
        ttk.Spinbox(wrapper, from_=0, to=20, textvariable=self.keep_last, width=8, command=self.save_current_config).grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        for cb in (cb_order, cb_preset, cb_crop):
            try:
                cb.bind('<<ComboboxSelected>>', save_processing)
            except Exception:
                pass

        buttons = ttk.Frame(wrapper, style='Card.TFrame')
        buttons.grid(row=row, column=0, columnspan=4, sticky='ew', pady=(12, 0))
        ttk.Button(buttons, text='Salvar configurações', command=lambda: self.save_current_config(force=True), style='Accent.TButton').pack(side='left')
        ttk.Button(buttons, text='Fechar', command=top.destroy, style='Ghost.TButton').pack(side='left', padx=8)
        wrapper.columnconfigure(1, weight=1)
        wrapper.columnconfigure(3, weight=1)

        try:
            self.place_window_near_widget(top, getattr(self, 'pdf_settings_btn', None), width=920, height=800, min_width=840, min_height=640)
        except Exception:
            top.geometry('920x800')
    except Exception as exc:
        _cuma_11004_log('Abrir Configurações do PDF 1.100.4', exc)
        try:
            messagebox.showerror('Configurações do PDF', friendly_error(exc))
        except Exception:
            pass


def _cuma_11004_find_converter_device_panel(self):
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return None
        stack = [tab]
        while stack:
            widget = stack.pop(0)
            try:
                stack.extend(list(widget.winfo_children()))
            except Exception:
                pass
            try:
                txt = str(widget.cget('text') or '')
            except Exception:
                txt = ''
            if (isinstance(widget, ttk.LabelFrame) or getattr(widget, 'winfo_class', lambda: '')() in ('TLabelframe', 'Labelframe')) and txt == 'Dispositivos e conversões':
                return widget
    except Exception as exc:
        _cuma_11004_log('Localizar painel Dispositivos e conversões', exc)
    return None


def _cuma_11004_destroy_converter_floating_panels(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        targets = []
        for child in list(tab.winfo_children()):
            try:
                txt = str(child.cget('text') or '')
            except Exception:
                txt = ''
            if isinstance(child, ttk.LabelFrame) and txt in ('Conversões disponíveis', 'Prévia, metadados e conversões', 'Conversões compatíveis'):
                targets.append(child)
            else:
                # normalmente o LabelFrame está dentro do frame principal; remova também em descendentes de primeiro nível
                try:
                    for grand in list(child.winfo_children()):
                        gtxt = str(grand.cget('text') or '') if isinstance(grand, ttk.LabelFrame) else ''
                        if gtxt in ('Conversões disponíveis', 'Prévia, metadados e conversões', 'Conversões compatíveis'):
                            targets.append(grand)
                except Exception:
                    pass
        for widget in targets:
            try:
                widget.destroy()
            except Exception:
                pass
    except Exception as exc:
        _cuma_11004_log('Remover painéis flutuantes do Converter', exc)


def _cuma_11004_update_metadata_button(self) -> None:
    try:
        btn = getattr(self, '_cuma_11004_metadata_btn', None)
        if btn is None:
            return
        path = _cuma_11001_active_converter_path(self) if '_cuma_11001_active_converter_path' in globals() else None
        kind = _cuma_11001_kind_for_path(path) if path and '_cuma_11001_kind_for_path' in globals() else 'unknown'
        to_epub = any(bool(_cuma_11001_var_for_key(self, key).get()) for key in ('pdf_epub', 'archive_epub', 'images_epub') if '_cuma_11001_var_for_key' in globals())
        show = (kind == 'epub') or to_epub
        if show:
            try:
                btn.grid()
            except Exception:
                pass
        else:
            try:
                btn.grid_remove()
            except Exception:
                pass
    except Exception as exc:
        _cuma_11004_log('Atualizar visibilidade dos metadados EPUB', exc)


_CUMA_11004_OLD_REFRESH = globals().get('_cuma_11001_refresh_conversion_options')


def _cuma_11001_refresh_conversion_options(self) -> None:
    try:
        if _CUMA_11004_OLD_REFRESH is not None:
            _CUMA_11004_OLD_REFRESH(self)
    finally:
        _cuma_11004_update_metadata_button(self)


def _cuma_11004_add_converter_dynamic_panel(self) -> None:
    """Integra as conversões compatíveis dentro de Dispositivos e conversões."""
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        if '_cuma_11001_setup_conversion_vars' in globals():
            _cuma_11001_setup_conversion_vars(self)

        _cuma_11004_destroy_converter_floating_panels(self)
        top = _cuma_11004_find_converter_device_panel(self)
        if top is None:
            return

        for child in list(top.winfo_children()):
            try:
                if child.winfo_name() == 'cuma11004_conversions':
                    child.destroy()
            except Exception:
                pass

        panel = ttk.Frame(top, style='Card.TFrame', name='cuma11004_conversions')
        panel.grid(row=3, column=0, columnspan=6, sticky='ew', pady=(10, 0))
        try:
            ttk.Separator(panel, orient='horizontal').grid(row=0, column=0, columnspan=6, sticky='ew', pady=(0, 8))
        except Exception:
            pass

        self.cuma_conversion_hint = tk.StringVar(value='Adicione ou selecione um arquivo para liberar as conversões compatíveis.')
        ttk.Label(panel, text='Conversões compatíveis', style='Strong.TLabel').grid(row=1, column=0, sticky='w', padx=(0, 12), pady=(0, 4))
        ttk.Label(panel, textvariable=self.cuma_conversion_hint, style='Muted.TLabel', wraplength=850, justify='left').grid(row=1, column=1, columnspan=5, sticky='w', pady=(0, 4))

        grid = ttk.Frame(panel, style='Card.TFrame')
        grid.grid(row=2, column=0, columnspan=6, sticky='ew')
        self._cuma_11001_conversion_widgets = {}

        def changed():
            try:
                _cuma_11001_refresh_conversion_options(self)
            except Exception:
                pass
            try:
                self.save_current_config(force=True)
            except Exception:
                pass

        ordered = (
            'pdf_epub', 'pdf_xtch', 'pdf_cbz', 'pdf_images',
            'epub_xtch', 'epub_pdf',
            'archive_epub', 'archive_xtch', 'archive_pdf',
            'images_pdf', 'images_epub', 'images_xtch'
        )
        for idx, key in enumerate(ordered):
            var = _cuma_11001_var_for_key(self, key)
            cb = ttk.Checkbutton(grid, text=CUMA_11001_CONVERSION_LABELS[key], variable=var, command=changed)
            cb.grid(row=idx // 5, column=idx % 5, sticky='w', padx=(0, 18), pady=4)
            self._cuma_11001_conversion_widgets[key] = cb

        meta = ttk.Button(grid, text='Metadados EPUB', command=lambda: _cuma_11000_open_metadata_editor(self), style='Ghost.TButton')
        meta.grid(row=0, column=4, sticky='w', padx=(0, 18), pady=4)
        self._cuma_11004_metadata_btn = meta

        for key in ('pdf_epub', 'archive_epub', 'images_epub'):
            try:
                _cuma_11001_var_for_key(self, key).trace_add('write', lambda *_: _cuma_11004_update_metadata_button(self))
            except Exception:
                pass

        try:
            self.xteink_tree.bind('<<TreeviewSelect>>', lambda _e: _cuma_11001_refresh_conversion_options(self), add='+')
        except Exception:
            pass
        try:
            self.xteink_input.trace_add('write', lambda *_: _cuma_11001_refresh_conversion_options(self))
        except Exception:
            pass

        panel.columnconfigure(1, weight=1)
        top.columnconfigure(1, weight=1)
        _cuma_11001_refresh_conversion_options(self)
    except Exception as exc:
        _cuma_11004_log('Adicionar conversões integradas ao Converter', exc)


def _cuma_11004_compact_converter_layout(self) -> None:
    try:
        tab = getattr(self, 'tab_xteink', None)
        if tab is None:
            return
        if hasattr(self, 'xteink_drop'):
            try:
                self.xteink_drop.configure(padding=10, text='Arraste PDF, EPUB, CBZ/ZIP, CBR/RAR/7Z, imagens ou pastas aqui')
                self.xteink_drop.pack_configure(pady=(4, 6))
            except Exception:
                pass
        # Diminui espaços excessivos entre área de arraste, botões e tabela.
        for child in list(tab.winfo_children()):
            try:
                for w in child.winfo_children():
                    # frame dos botões contém o botão "Adicionar arquivo(s)".
                    names = []
                    try:
                        names = [str(c.cget('text') or '') for c in w.winfo_children()]
                    except Exception:
                        names = []
                    if 'Adicionar arquivo(s)' in names and 'Prévia' in names:
                        w.pack_configure(pady=(4, 6))
                    if hasattr(self, 'xteink_tree') and _cuma_11001_contains_treeview(w):
                        w.pack_configure(pady=(2, 0))
            except Exception:
                pass
        try:
            self.xteink_prog_total.pack_configure(pady=(0, 3))
            self.xteink_prog_current.pack_configure(pady=(0, 0))
        except Exception:
            pass
    except Exception as exc:
        _cuma_11004_log('Compactar layout do Converter', exc)


def _cuma_11004_apply_tree_hover_style(self) -> None:
    """Evita texto branco em fundo claro no hover/active de cabeçalhos/linhas."""
    try:
        p = getattr(self, '_theme_palette', None) or PALETTES.get(self.theme.get(), PALETTES.get('Manga Dark', {}))
        fg = p.get('fg', '#F4F7FB')
        surface2 = p.get('surface2', '#263040')
        drop = p.get('drop', '#111821')
        selection = p.get('selection', '#31465A')
        s = getattr(self, 'style', None)
        if s is None:
            return
        s.configure('Treeview.Heading', background=surface2, foreground=fg, bordercolor=p.get('border', '#3A4658'))
        s.map('Treeview.Heading',
              background=[('active', selection), ('pressed', selection)],
              foreground=[('active', fg), ('pressed', fg)])
        s.map('Treeview',
              background=[('selected', selection), ('active', drop)],
              foreground=[('selected', fg), ('active', fg)])
        for tree_name in ('tree', 'xteink_tree'):
            tree = getattr(self, tree_name, None)
            if tree is not None:
                try:
                    tree.tag_configure('hover', foreground=fg, background=drop)
                except Exception:
                    pass
    except Exception as exc:
        _cuma_11004_log('Aplicar estilo hover da tabela', exc)


def _cuma_11004_reorganize_ui(self) -> None:
    try:
        if '_cuma_11001_destroy_legacy_converter_optimization_panel' in globals():
            _cuma_11001_destroy_legacy_converter_optimization_panel(self)
    except Exception:
        pass
    try:
        if '_cuma_11001_remove_legacy_converter_checkbuttons' in globals():
            _cuma_11001_remove_legacy_converter_checkbuttons(self)
    except Exception:
        pass

    _cuma_11004_ensure_clean_vars(self)
    _cuma_11004_remove_clean_optimization_panel(self)
    _cuma_11004_replace_clean_preview_button(self)
    _cuma_11004_add_converter_dynamic_panel(self)
    _cuma_11004_compact_converter_layout(self)
    _cuma_11004_apply_tree_hover_style(self)

    try:
        if '_cuma_11001_remove_legacy_converter_checkbuttons' in globals():
            _cuma_11001_remove_legacy_converter_checkbuttons(self)
    except Exception:
        pass


_CUMA_11004_RUNTIME = {
    'build': getattr(App, 'build', None),
    'apply_theme': getattr(App, 'apply_theme', None),
    'save_current_config': getattr(App, 'save_current_config', None),
}


def _cuma_11004_build(self):
    result = _CUMA_11004_RUNTIME['build'](self)
    try:
        _cuma_11004_reorganize_ui(self)
    except Exception as exc:
        _cuma_11004_log('Reorganização UI', exc)
    return result


def _cuma_11004_apply_theme(self):
    result = _CUMA_11004_RUNTIME['apply_theme'](self)
    try:
        _cuma_11004_apply_tree_hover_style(self)
    except Exception:
        pass
    return result


def _cuma_11004_save_current_config(self, force: bool = False):
    result = _CUMA_11004_RUNTIME['save_current_config'](self, force)
    try:
        if '_cuma_11000_set_processing_from_app' in globals():
            _cuma_11000_set_processing_from_app(self)
    except Exception as exc:
        _cuma_11004_log('Salvar configurações 1.100.4', exc)
    return result


def _cuma_11004_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11004_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11004_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11004_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'Acabamento visual do Converter, metadados EPUB contextuais, opções KCC/E-ink dentro de Configurações do PDF e prévia Limpar unificada.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11004_VERSION)
    except Exception:
        pass
    try:
        state = cuma_version_load_state()
        events = state.get('events', [])
        if not isinstance(events, list):
            events = []
        if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11004_UPDATE_ID for e in events):
            events.append({
                'update_id': CUMA_11004_UPDATE_ID,
                'version': CUMA_11004_VERSION,
                'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                'scale': 'pouca',
                'description': 'Integra conversões compatíveis ao painel de dispositivos, torna Metadados EPUB contextual, move opções KCC/E-ink para Configurações do PDF e corrige hover da tabela.',
                'timestamp': datetime.now().isoformat(timespec='seconds')
            })
        state['events'] = events[-100:]
        state['current_version'] = CUMA_11004_VERSION
        state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
        cuma_version_save_state(state)
        if '_cuma_version_write_public_files' in globals():
            _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11004_log('Versionamento 1.100.4', exc)


def _cuma_install_11004_ui_finish() -> None:
    try:
        _cuma_11004_force_version()
        App.build = _cuma_11004_build
        App.apply_theme = _cuma_11004_apply_theme
        App.save_current_config = _cuma_11004_save_current_config
        App.open_pdf_settings_window = _cuma_11004_open_pdf_settings_window
        globals()['_cuma_11001_add_clean_optimization_panel'] = lambda self: None
        globals()['_cuma_11003_add_clean_optimization_panel'] = lambda self: None
        globals()['_cuma_11001_add_converter_dynamic_panel'] = _cuma_11004_add_converter_dynamic_panel
        globals()['_cuma_11003_add_converter_dynamic_panel'] = _cuma_11004_add_converter_dynamic_panel
        globals()['_cuma_11003_reorganize_ui'] = _cuma_11004_reorganize_ui
    except Exception as exc:
        _cuma_11004_log('Instalação patch 1.100.4', exc)


_cuma_install_11004_ui_finish()


# =============================================================================
# CUMA 1.100.5 - ORDEM MANUAL DE ARQUIVOS E LAYOUT COMPACTO
# =============================================================================
# Ajustes:
# - Botões "Mover pra cima ↑" e "Mover pra baixo ↓" nas filas de Limpar,
#   Ferramentas e Converter.
# - Reordenação por clicar, segurar e arrastar uma linha da lista.
# - Remoção do espaço vazio entre os botões e a lista do Converter.
CUMA_11005_VERSION = '1.100.5'
CUMA_11005_UPDATE_ID = 'ordem_manual_filas_e_converter_compacto_11005'


def _cuma_11005_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'{context}: {exc}' if exc is not None else str(context)
        write_log(msg)
    except Exception:
        pass


def _cuma_11005_widget_text(widget) -> str:
    try:
        return str(widget.cget('text') or '')
    except Exception:
        return ''


def _cuma_11005_walk(widget):
    yield widget
    try:
        children = list(widget.winfo_children())
    except Exception:
        children = []
    for child in children:
        yield from _cuma_11005_walk(child)


def _cuma_11005_contains(root, target) -> bool:
    try:
        if root == target:
            return True
        for child in root.winfo_children():
            if _cuma_11005_contains(child, target):
                return True
    except Exception:
        pass
    return False


def _cuma_11005_ancestor_chain(widget) -> list:
    chain = []
    cur = widget
    while cur is not None:
        chain.append(cur)
        try:
            cur = cur.master
        except Exception:
            break
    return chain


def _cuma_11005_common_score(a, b) -> int:
    achain = _cuma_11005_ancestor_chain(a)
    bchain = _cuma_11005_ancestor_chain(b)
    best = 10_000
    for ai, aw in enumerate(achain):
        for bi, bw in enumerate(bchain):
            if aw == bw:
                best = min(best, ai + bi)
    return best


def _cuma_11005_is_file_toolbar(widget) -> bool:
    try:
        texts = [_cuma_11005_widget_text(child).strip() for child in widget.winfo_children()]
    except Exception:
        return False
    if not texts:
        return False
    has_add = any(t.startswith('Adicionar') or t == 'Colar caminho' for t in texts)
    has_list_action = any(t in ('Remover', 'Limpar', 'Limpar lista') for t in texts)
    has_preview_or_folder = any(t in ('Prévia', 'Abrir pasta Ferramentas', 'Abrir pasta Converter', 'Funções por tipo') for t in texts)
    return has_add and has_list_action and has_preview_or_folder


def _cuma_11005_find_toolbar(root, tree):
    try:
        candidates = []
        for widget in _cuma_11005_walk(root):
            if _cuma_11005_is_file_toolbar(widget):
                candidates.append(widget)
        if not candidates:
            return None
        candidates.sort(key=lambda w: _cuma_11005_common_score(w, tree))
        return candidates[0]
    except Exception as exc:
        _cuma_11005_log('Localizar barra de botões para reordenação', exc)
        return None


def _cuma_11005_item_file_map(tree, files: list) -> dict:
    try:
        items = list(tree.get_children(''))
    except Exception:
        items = []
    return {item: files[idx] for idx, item in enumerate(items) if idx < len(files)}


def _cuma_11005_path_key(value) -> str:
    try:
        return _cuma_11008_path_key(value)
    except Exception:
        return str(value)


def _cuma_11005_apply_tree_order_to_model(self, tree, files_attr: str, item_file: dict | None = None) -> None:
    try:
        old_files = list(getattr(self, files_attr, []))
        if item_file is None:
            item_file = _cuma_11005_item_file_map(tree, old_files)
        new_files = []
        used = set()
        for item in list(tree.get_children('')):
            if item in item_file:
                value = item_file[item]
                new_files.append(value)
                used.add(_cuma_11005_path_key(value))
        for value in old_files:
            key = _cuma_11005_path_key(value)
            if key not in used:
                new_files.append(value)
        setattr(self, files_attr, new_files)
    except Exception as exc:
        _cuma_11005_log(f'Sincronizar ordem da lista {files_attr}', exc)


def _cuma_11005_update_after_reorder(self, files_attr: str, tree=None) -> None:
    try:
        if files_attr == 'files' and hasattr(self, 'update_counter'):
            self.update_counter()
        elif files_attr == 'xteink_files':
            if tree is not None and hasattr(self, 'xteink_input'):
                selected = list(tree.selection())
                children = list(tree.get_children(''))
                files = list(getattr(self, 'xteink_files', []))
                if selected and selected[0] in children:
                    idx = children.index(selected[0])
                    if 0 <= idx < len(files):
                        try:
                            self.xteink_input.set(str(files[idx]))
                        except Exception:
                            pass
            if hasattr(self, 'update_xteink_counter'):
                self.update_xteink_counter()
            if '_cuma_11001_refresh_conversion_options' in globals():
                try:
                    _cuma_11001_refresh_conversion_options(self)
                except Exception:
                    pass
        elif files_attr == 'tools_extract_files':
            if hasattr(self, 'tools_extract_counter'):
                self.tools_extract_counter.set(f'Arquivos: {len(getattr(self, files_attr, []))}')
        elif files_attr == 'tools_create_files':
            if hasattr(self, 'tools_create_counter'):
                self.tools_create_counter.set(f'Arquivos: {len(getattr(self, files_attr, []))}')
        if hasattr(self, 'refresh_dashboard'):
            try:
                self.refresh_dashboard()
            except Exception:
                pass
    except Exception as exc:
        _cuma_11005_log(f'Atualizar contadores após reordenar {files_attr}', exc)


def _cuma_11005_move_selection(self, tree, files_attr: str, direction: int) -> None:
    try:
        children = list(tree.get_children(''))
        selected = [item for item in tree.selection() if item in children]
        if not selected:
            try:
                messagebox.showinfo('Mover arquivos', 'Selecione um arquivo na lista para mover.')
            except Exception:
                pass
            return

        item_file = _cuma_11005_item_file_map(tree, list(getattr(self, files_attr, [])))
        selected_set = set(selected)
        ordered = sorted(selected, key=lambda item: children.index(item))
        if direction < 0:
            for item in ordered:
                current = list(tree.get_children(''))
                idx = current.index(item)
                if idx > 0 and current[idx - 1] not in selected_set:
                    tree.move(item, '', idx - 1)
        else:
            for item in reversed(ordered):
                current = list(tree.get_children(''))
                idx = current.index(item)
                if idx < len(current) - 1 and current[idx + 1] not in selected_set:
                    tree.move(item, '', idx + 1)

        _cuma_11005_apply_tree_order_to_model(self, tree, files_attr, item_file)
        try:
            tree.selection_set(selected)
            tree.focus(selected[0])
            tree.see(selected[0])
        except Exception:
            pass
        _cuma_11005_update_after_reorder(self, files_attr, tree)
    except Exception as exc:
        _cuma_11005_log(f'Mover seleção em {files_attr}', exc)


def _cuma_11005_bind_drag_reorder(self, tree, files_attr: str) -> None:
    try:
        if getattr(tree, '_cuma11005_drag_reorder_bound', False):
            return
        state = {'item': None, 'item_file': None}

        def on_press(event):
            try:
                region = tree.identify_region(event.x, event.y)
                if region in ('heading', 'separator'):
                    state['item'] = None
                    state['item_file'] = None
                    return
                item = tree.identify_row(event.y)
                if not item:
                    state['item'] = None
                    state['item_file'] = None
                    return
                state['item'] = item
                state['item_file'] = _cuma_11005_item_file_map(tree, list(getattr(self, files_attr, [])))
                if item not in tree.selection():
                    tree.selection_set(item)
                tree.focus(item)
            except Exception as exc:
                _cuma_11005_log(f'Iniciar arraste em {files_attr}', exc)

        def on_motion(event):
            try:
                item = state.get('item')
                if not item or not tree.exists(item):
                    return
                target = tree.identify_row(event.y)
                if not target or target == item or not tree.exists(target):
                    return
                children = list(tree.get_children(''))
                if item not in children or target not in children:
                    return
                old_idx = children.index(item)
                new_idx = children.index(target)
                if old_idx == new_idx:
                    return
                tree.move(item, '', new_idx)
                _cuma_11005_apply_tree_order_to_model(self, tree, files_attr, state.get('item_file'))
                try:
                    tree.selection_set(item)
                    tree.focus(item)
                    tree.see(item)
                except Exception:
                    pass
                _cuma_11005_update_after_reorder(self, files_attr, tree)
                return 'break'
            except Exception as exc:
                _cuma_11005_log(f'Arrastar item em {files_attr}', exc)

        def on_release(_event):
            state['item'] = None
            state['item_file'] = None

        tree.bind('<ButtonPress-1>', on_press, add='+')
        tree.bind('<B1-Motion>', on_motion, add='+')
        tree.bind('<ButtonRelease-1>', on_release, add='+')
        tree._cuma11005_drag_reorder_bound = True
    except Exception as exc:
        _cuma_11005_log(f'Vincular arraste em {files_attr}', exc)


def _cuma_11005_add_move_buttons(self, toolbar, tree, files_attr: str) -> None:
    try:
        if toolbar is None or getattr(toolbar, '_cuma11005_move_buttons_added', False):
            return
        existing = {_cuma_11005_widget_text(child).strip() for child in toolbar.winfo_children()}
        if 'Mover pra cima ↑' not in existing:
            ttk.Button(
                toolbar,
                text='Mover pra cima ↑',
                command=lambda t=tree, attr=files_attr: _cuma_11005_move_selection(self, t, attr, -1),
                style='Ghost.TButton'
            ).pack(side='left', padx=(10, 4))
        if 'Mover pra baixo ↓' not in existing:
            ttk.Button(
                toolbar,
                text='Mover pra baixo ↓',
                command=lambda t=tree, attr=files_attr: _cuma_11005_move_selection(self, t, attr, 1),
                style='Ghost.TButton'
            ).pack(side='left', padx=4)
        toolbar._cuma11005_move_buttons_added = True
    except Exception as exc:
        _cuma_11005_log(f'Adicionar botões de mover para {files_attr}', exc)


def _cuma_11005_container_is_empty(widget) -> bool:
    try:
        children = list(widget.winfo_children())
        if not children:
            return True
        # Frames que ficaram somente com checkbuttons removidos/ocultos não precisam ocupar espaço.
        visible = []
        for child in children:
            try:
                if child.winfo_ismapped():
                    visible.append(child)
            except Exception:
                pass
        return len(visible) == 0
    except Exception:
        return False


def _cuma_11005_compact_converter_gap(self) -> None:
    try:
        tree = getattr(self, 'xteink_tree', None)
        tab = getattr(self, 'tab_xteink', None)
        if tree is None or tab is None:
            return
        toolbar = _cuma_11005_find_toolbar(tab, tree)
        tree_frame = getattr(tree, 'master', None)
        if toolbar is None or tree_frame is None:
            return

        parent = getattr(tree_frame, 'master', None)
        if parent is not None:
            # Remove frames vazios que ficavam entre a barra de botões e a tabela.
            try:
                children = list(parent.winfo_children())
                if toolbar in children and tree_frame in children:
                    i_toolbar = children.index(toolbar)
                    i_tree = children.index(tree_frame)
                    if i_toolbar < i_tree:
                        for child in children[i_toolbar + 1:i_tree]:
                            if child is not tree_frame and _cuma_11005_container_is_empty(child):
                                try:
                                    child.pack_forget()
                                except Exception:
                                    pass
                    tree_frame.pack_configure(after=toolbar, pady=(0, 4))
            except Exception:
                pass

            for child in list(parent.winfo_children()):
                try:
                    if child == getattr(self, 'xteink_drop', None):
                        child.pack_configure(pady=(0, 4))
                    elif child == toolbar:
                        child.pack_configure(pady=(0, 4))
                    elif child == tree_frame:
                        child.pack_configure(pady=(0, 4))
                except Exception:
                    pass

        try:
            if hasattr(self, 'xteink_drop'):
                self.xteink_drop.configure(padding=8)
        except Exception:
            pass
    except Exception as exc:
        _cuma_11005_log('Compactar espaço entre botões e lista do Converter', exc)


def _cuma_11005_install_reorder_controls(self) -> None:
    try:
        specs = [
            (getattr(self, 'tab_files', None), getattr(self, 'tree', None), 'files'),
            (getattr(self, 'tab_xteink', None), getattr(self, 'xteink_tree', None), 'xteink_files'),
            (getattr(self, 'tab_tools', None), getattr(self, 'tools_extract_tree', None), 'tools_extract_files'),
            (getattr(self, 'tab_tools', None), getattr(self, 'tools_create_tree', None), 'tools_create_files'),
        ]
        for root, tree, files_attr in specs:
            if root is None or tree is None or not hasattr(self, files_attr):
                continue
            _cuma_11005_bind_drag_reorder(self, tree, files_attr)
            toolbar = _cuma_11005_find_toolbar(root, tree)
            _cuma_11005_add_move_buttons(self, toolbar, tree, files_attr)
        _cuma_11005_compact_converter_gap(self)
    except Exception as exc:
        _cuma_11005_log('Instalar controles de ordem manual', exc)


_CUMA_11005_RUNTIME = {
    'build': getattr(App, 'build', None),
    'apply_theme': getattr(App, 'apply_theme', None),
}


def _cuma_11005_build(self):
    result = _CUMA_11005_RUNTIME['build'](self)
    try:
        _cuma_11005_install_reorder_controls(self)
    except Exception as exc:
        _cuma_11005_log('Build 1.100.5', exc)
    return result


def _cuma_11005_apply_theme(self):
    result = _CUMA_11005_RUNTIME['apply_theme'](self)
    try:
        # Garante que os botões de mover continuem presentes após reconstruções visuais.
        _cuma_11005_install_reorder_controls(self)
    except Exception:
        pass
    return result


def _cuma_11005_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11005_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11005_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11005_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'Adiciona reordenação manual nas filas e compacta o espaço do Converter.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11005_VERSION)
    except Exception:
        pass
    try:
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            state = cuma_version_load_state()
            events = state.get('events', []) if isinstance(state, dict) else []
            if not isinstance(events, list):
                events = []
            if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11005_UPDATE_ID for e in events):
                events.append({
                    'update_id': CUMA_11005_UPDATE_ID,
                    'version': CUMA_11005_VERSION,
                    'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                    'scale': 'pouca',
                    'description': 'Botões Mover pra cima/baixo e arraste para reordenar nas filas de Limpar, Ferramentas e Converter; layout do Converter mais compacto.',
                    'timestamp': datetime.now().isoformat(timespec='seconds')
                })
            state['events'] = events[-100:]
            state['current_version'] = CUMA_11005_VERSION
            state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
            cuma_version_save_state(state)
            if '_cuma_version_write_public_files' in globals():
                _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11005_log('Versionamento 1.100.5', exc)


def _cuma_install_11005_reorder_and_compact_layout() -> None:
    try:
        _cuma_11005_force_version()
        App.build = _cuma_11005_build
        App.apply_theme = _cuma_11005_apply_theme
    except Exception as exc:
        _cuma_11005_log('Instalação patch 1.100.5', exc)


_cuma_install_11005_reorder_and_compact_layout()


# =============================================================================
# CUMA 1.100.6 - CRIAR PDF ACEITA IMAGENS, PDF, CBZ E ARQUIVOS COM IMAGENS
# =============================================================================
# Ajustes:
# - A ferramenta "Criar PDF de imagens" também aceita PDFs.
# - Também aceita CBZ/ZIP/EPUB com imagens nativamente.
# - Aceita CBR/RAR/7Z quando o 7-Zip estiver instalado e disponível no PATH.
# - A ordem da lista continua sendo respeitada, inclusive com os controles de mover.
CUMA_11006_VERSION = '1.100.6'
CUMA_11006_UPDATE_ID = 'ferramentas_criar_pdf_multiformato_11006'
CUMA_11006_ARCHIVE_EXTS = ('.cbz', '.zip', '.epub', '.cbr', '.rar', '.7z')
CUMA_11006_CREATE_PDF_EXTS = tuple(dict.fromkeys(tuple(SUPPORTED_IMAGE_EXT) + ('.pdf',) + CUMA_11006_ARCHIVE_EXTS))


def _cuma_11006_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'{context}: {type(exc).__name__}: {exc}' if exc is not None else str(context)
        write_log(msg)
    except Exception:
        pass


def _cuma_11006_accept_create_path(path: Path) -> bool:
    try:
        return Path(path).suffix.lower() in CUMA_11006_CREATE_PDF_EXTS
    except Exception:
        return False


_CUMA_11006_ORIG_TOOLS_ACCEPT_PATH = globals().get('_tools_accept_path')
def _tools_accept_path(path: Path, kind: str) -> bool:
    try:
        suffix = Path(path).suffix.lower()
        if kind == 'extract':
            return suffix == '.pdf'
        if kind == 'create':
            return suffix in CUMA_11006_CREATE_PDF_EXTS
        if _CUMA_11006_ORIG_TOOLS_ACCEPT_PATH:
            return _CUMA_11006_ORIG_TOOLS_ACCEPT_PATH(path, kind)
    except Exception:
        return False
    return False


def _cuma_11006_create_filetypes():
    return [
        ('Imagens, PDF e quadrinhos', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.pdf *.cbz *.zip *.epub *.cbr *.rar *.7z'),
        ('Imagens', '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff'),
        ('PDF', '*.pdf'),
        ('CBZ/ZIP/EPUB', '*.cbz *.zip *.epub'),
        ('CBR/RAR/7Z', '*.cbr *.rar *.7z'),
        ('Todos', '*.*'),
    ]


def _tools_add_files(self, kind: str) -> None:
    if kind == 'extract':
        files = filedialog.askopenfilenames(title='Adicionar PDFs', filetypes=[('PDF', '*.pdf'), ('Todos', '*.*')])
    else:
        files = filedialog.askopenfilenames(title='Adicionar imagens, PDFs ou arquivos com imagens', filetypes=_cuma_11006_create_filetypes())
    _tools_tree_insert(self, kind, files)


def _cuma_11006_natural_key(value) -> list:
    try:
        if '_natural_key' in globals():
            return _natural_key(str(value))
    except Exception:
        pass
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(value))]


def _cuma_11006_image_names_from_zip(zf: zipfile.ZipFile) -> list[str]:
    names = []
    for name in zf.namelist():
        try:
            if name.endswith('/'):
                continue
            if Path(name).suffix.lower() in SUPPORTED_IMAGE_EXT:
                names.append(name)
        except Exception:
            pass
    return sorted(names, key=_cuma_11006_natural_key)


def _cuma_11006_rgb_copy(img: Image.Image) -> Image.Image:
    try:
        if img.mode in ('RGBA', 'LA') or 'transparency' in getattr(img, 'info', {}):
            rgba = img.convert('RGBA')
            bg = Image.new('RGB', rgba.size, 'white')
            bg.paste(rgba, mask=rgba.getchannel('A'))
            try:
                rgba.close()
            except Exception:
                pass
            return bg
        return img.convert('RGB')
    except Exception:
        return img.copy().convert('RGB')


def _cuma_11006_iter_opened_image(opened: Image.Image):
    frames = int(getattr(opened, 'n_frames', 1) or 1)
    for idx in range(max(1, frames)):
        try:
            if frames > 1:
                opened.seek(idx)
            yield _cuma_11006_rgb_copy(opened)
        except EOFError:
            break


def _cuma_11006_iter_image_file(path: Path):
    with Image.open(path) as opened:
        for img in _cuma_11006_iter_opened_image(opened):
            yield img


def _cuma_11006_extract_archive_with_7z(archive_path: Path, tmp_dir: Path) -> list[Path]:
    if '_cuma_11000_extract_with_7z' in globals():
        return _cuma_11000_extract_with_7z(archive_path, tmp_dir)
    exe = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
    if not exe:
        raise RuntimeError('Arquivos CBR/RAR/7Z precisam do 7-Zip instalado e disponível no PATH. CBZ/ZIP/EPUB funciona nativamente.')
    cmd = [exe, 'x', '-y', f'-o{str(tmp_dir)}', str(archive_path)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'Falha ao extrair arquivo compactado com 7-Zip.').strip())
    files = [p for p in tmp_dir.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXT]
    return sorted(files, key=lambda p: _cuma_11006_natural_key(p.as_posix()))


def _cuma_11006_iter_archive_images(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix in ('.cbz', '.zip', '.epub'):
        with zipfile.ZipFile(path, 'r') as zf:
            names = _cuma_11006_image_names_from_zip(zf)
            if not names:
                raise RuntimeError(f'Não encontrei imagens dentro de {path.name}.')
            for name in names:
                try:
                    with zf.open(name) as f:
                        data = BytesIO(f.read())
                    with Image.open(data) as opened:
                        for img in _cuma_11006_iter_opened_image(opened):
                            yield img
                except Exception as exc:
                    _cuma_11006_log(f'Imagem ignorada em {path.name}: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        import tempfile
        with tempfile.TemporaryDirectory(prefix='cuma_criar_pdf_') as td:
            files = _cuma_11006_extract_archive_with_7z(path, Path(td))
            if not files:
                raise RuntimeError(f'Não encontrei imagens dentro de {path.name}.')
            for img_path in files:
                try:
                    for img in _cuma_11006_iter_image_file(img_path):
                        yield img
                except Exception as exc:
                    _cuma_11006_log(f'Imagem ignorada em {path.name}: {img_path.name}', exc)
    else:
        raise RuntimeError(f'Arquivo compactado não suportado: {path.name}')


def _cuma_11006_iter_source_images(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix in SUPPORTED_IMAGE_EXT:
        yield from _cuma_11006_iter_image_file(path)
    elif suffix in CUMA_11006_ARCHIVE_EXTS:
        yield from _cuma_11006_iter_archive_images(path)
    else:
        raise RuntimeError(f'Formato não suportado para criar PDF: {path.name}')


def _cuma_11006_add_image_page(out_doc, img: Image.Image) -> None:
    rgb = _cuma_11006_rgb_copy(img)
    try:
        width = max(1, int(rgb.width))
        height = max(1, int(rgb.height))
        page = out_doc.new_page(width=float(width), height=float(height))
        rect = fitz.Rect(0, 0, float(width), float(height))
        bio = BytesIO()
        rgb.save(bio, format='JPEG', quality=95, optimize=True)
        page.insert_image(rect, stream=bio.getvalue())
    finally:
        try:
            if rgb is not img:
                rgb.close()
        except Exception:
            pass


def _cuma_11006_append_pdf_source(out_doc, pdf_path: Path, progress_cb=None) -> int:
    src_doc = fitz.open(str(pdf_path))
    try:
        page_count = len(src_doc)
        if page_count <= 0:
            raise RuntimeError(f'PDF sem páginas: {pdf_path.name}')
        for page_index in range(page_count):
            out_doc.insert_pdf(src_doc, from_page=page_index, to_page=page_index)
            if progress_cb:
                progress_cb(page_index + 1, page_count)
        return page_count
    finally:
        src_doc.close()


def _cuma_11006_append_image_source(out_doc, source_path: Path, progress_cb=None) -> int:
    count = 0
    for img in _cuma_11006_iter_source_images(source_path):
        try:
            _cuma_11006_add_image_page(out_doc, img)
            count += 1
            if progress_cb:
                progress_cb(count, max(1, count))
        finally:
            try:
                img.close()
            except Exception:
                pass
    if count <= 0:
        raise RuntimeError(f'Nenhuma imagem válida em {source_path.name}.')
    return count


def _cuma_11006_first_preview_image(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        doc = fitz.open(str(path))
        try:
            if len(doc) <= 0:
                return None
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        finally:
            doc.close()
    if suffix in SUPPORTED_IMAGE_EXT:
        with Image.open(path) as opened:
            for img in _cuma_11006_iter_opened_image(opened):
                return img
        return None
    if suffix in CUMA_11006_ARCHIVE_EXTS:
        iterator = _cuma_11006_iter_archive_images(path)
        try:
            return next(iterator)
        except StopIteration:
            return None
    return None


def _tools_preview(self, kind: str) -> None:
    paths = _tools_selected_paths(self, kind) or list(getattr(self, 'tools_extract_files' if kind == 'extract' else 'tools_create_files', []))[:1]
    if not paths:
        messagebox.showinfo('Prévia', 'Adicione ou selecione um arquivo.')
        return
    p = Path(paths[0])
    if kind == 'extract':
        try:
            PreviewWindow(self, p)
        except Exception as exc:
            messagebox.showerror('Prévia', friendly_error(exc))
        return
    top = tk.Toplevel(self.root)
    top.title(f'Prévia - {p.name}')
    top.geometry('720x820')
    try:
        im = _cuma_11006_first_preview_image(p)
        if im is None:
            raise RuntimeError('Não consegui gerar prévia deste arquivo.')
        try:
            im.thumbnail((680, 760), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            lbl = ttk.Label(top, image=photo)
            lbl.image = photo
            lbl.pack(padx=10, pady=10)
            ttk.Label(top, text=str(p), style='Muted.TLabel', wraplength=680).pack()
        finally:
            try:
                im.close()
            except Exception:
                pass
    except Exception as exc:
        messagebox.showerror('Prévia', friendly_error(exc))
        top.destroy()


def _tools_process_create_pdf(self, selected=False) -> None:
    paths = _tools_selected_paths(self, 'create') if selected else list(getattr(self, 'tools_create_files', []))
    paths = [Path(p) for p in paths if _cuma_11006_accept_create_path(Path(p))]
    if not paths:
        messagebox.showinfo('Criar PDF', 'Adicione ou selecione imagens, PDFs, CBZ/ZIP/EPUB ou arquivos compactados com imagens.')
        return

    out_dir = _cuma_tab_output_dir('Ferramentas', True)
    name = self.tools_pdf_name.get().strip() or 'imagens_unidas.pdf'
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    output = unique_path(out_dir / name)
    total_sources = len(paths)
    total_pages = 0
    debug = {
        'acao': 'criar_pdf_a_partir_de_imagens_pdf_cbz_arquivos',
        'versao': APP_DISPLAY_VERSION,
        'arquivos': [str(p) for p in paths],
        'saida': str(output),
        'status': 'iniciado',
        'resultados': []
    }
    out_doc = fitz.open()
    try:
        for source_index, p in enumerate(paths, 1):
            suffix = p.suffix.lower()
            _tools_set_tree_status(self, 'create', p, 'Processando')

            def progress(done, max_value, src=p, index=source_index):
                _tools_update_progress(
                    self,
                    'create',
                    int(done),
                    max(1, int(max_value)),
                    index - 1,
                    total_sources,
                    f'{src.name}: {done}/{max_value}'
                )

            if suffix == '.pdf':
                pages_added = _cuma_11006_append_pdf_source(out_doc, p, progress_cb=progress)
            else:
                pages_added = _cuma_11006_append_image_source(out_doc, p, progress_cb=progress)

            total_pages += pages_added
            _tools_set_tree_status(self, 'create', p, f'OK ({pages_added} pág.)')
            _tools_update_progress(self, 'create', pages_added, max(1, pages_added), source_index, total_sources, f'Concluído: {p.name}')
            debug['resultados'].append({'arquivo': str(p), 'paginas_adicionadas': pages_added})
            self.log(f'Ferramentas / Criar PDF: {p.name} → {pages_added} página(s) adicionada(s)')

        if total_pages <= 0:
            raise RuntimeError('Nenhuma página foi adicionada ao PDF.')

        output.parent.mkdir(parents=True, exist_ok=True)
        _tools_update_progress(self, 'create', total_pages, max(1, total_pages), total_sources, total_sources, 'Salvando PDF...')
        out_doc.save(str(output), garbage=4, deflate=True)
        debug['status'] = 'ok'
        debug['total_paginas'] = total_pages
        self.log(f'Ferramentas / Criar PDF: {len(paths)} arquivo(s), {total_pages} página(s) → {output}')
        self.tools_debug_var.set(f'PDF criado com {total_pages} página(s) de {len(paths)} arquivo(s): {output}')
        _tools_update_progress(self, 'create', total_pages, max(1, total_pages), total_sources, total_sources, f'PDF criado: {output.name}')
        if self.tools_pdf_open_after.get():
            open_folder(output)
        messagebox.showinfo('Criar PDF', f'PDF criado:\n{output}')
    except Exception as exc:
        debug['status'] = 'erro'
        debug['erro'] = friendly_error(exc)
        write_error_log(type(exc), exc, exc.__traceback__, 'Erro na ferramenta Criar PDF multiformato')
        messagebox.showerror('Criar PDF', friendly_error(exc))
    finally:
        try:
            out_doc.close()
        except Exception:
            pass
        try:
            (runtime_dir() / 'debug_ferramentas_criar_pdf_multiformato.json').write_text(json.dumps(debug, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        except Exception:
            pass


_CUMA_11006_ORIG_TOOLS_MAKE_TAB = globals().get('_tools_make_clean_like_tab')
def _tools_make_clean_like_tab(self, parent, kind: str, title: str, subtitle: str) -> None:
    if kind == 'create':
        title = 'Criar PDF de imagens/PDF/CBZ'
        subtitle = 'Cria um PDF único usando imagens, PDFs, CBZ/ZIP/EPUB e arquivos compactados com imagens. A ordem da lista é respeitada.'
    return _CUMA_11006_ORIG_TOOLS_MAKE_TAB(self, parent, kind, title, subtitle)


def _cuma_11006_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11006_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11006_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11006_VERSION,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'notes': 'A ferramenta Criar PDF agora aceita imagens, PDFs, CBZ/ZIP/EPUB e arquivos compactados com imagens.'
        }
        if 'cuma_version_apply_globals' in globals():
            cuma_version_apply_globals(CUMA_11006_VERSION)
    except Exception:
        pass
    try:
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            state = cuma_version_load_state()
            events = state.get('events', []) if isinstance(state, dict) else []
            if not isinstance(events, list):
                events = []
            if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11006_UPDATE_ID for e in events):
                events.append({
                    'update_id': CUMA_11006_UPDATE_ID,
                    'version': CUMA_11006_VERSION,
                    'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                    'scale': 'pouca',
                    'description': 'Ferramentas/Criar PDF aceita imagens, PDFs, CBZ/ZIP/EPUB e compactados com imagens; preserva a ordem manual da lista.',
                    'timestamp': datetime.now().isoformat(timespec='seconds')
                })
            state['events'] = events[-100:]
            state['current_version'] = CUMA_11006_VERSION
            state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
            cuma_version_save_state(state)
            if '_cuma_version_write_public_files' in globals():
                _cuma_version_write_public_files(state)
    except Exception as exc:
        _cuma_11006_log('Versionamento 1.100.6', exc)


def _cuma_install_11006_create_pdf_multiformat() -> None:
    try:
        _cuma_11006_force_version()
        globals()['_tools_accept_path'] = _tools_accept_path
        globals()['_tools_add_files'] = _tools_add_files
        globals()['_tools_preview'] = _tools_preview
        globals()['_tools_process_create_pdf'] = _tools_process_create_pdf
        globals()['_tools_make_clean_like_tab'] = _tools_make_clean_like_tab
        try:
            BaseApp.create_pdf_from_images_dialog = lambda self: _tools_process_create_pdf(self, selected=False)
        except Exception:
            pass
    except Exception as exc:
        _cuma_11006_log('Instalação patch 1.100.6', exc)


_cuma_install_11006_create_pdf_multiformat()


# =============================================================================
# CUMA 1.100.7 - MANUAIS E HISTÓRICO CONSOLIDADOS
# =============================================================================
# Ajustes:
# - Manual TXT da raiz e manual gerado pelo botão Manual alinhados com 1.100.7.
# - README/LEIA-ME/histórico/arquivo de atualizações explicam as funções desde 1.100.2.
# - Não altera o motor de processamento; é uma atualização documental.
CUMA_11007_VERSION = '1.100.7'
CUMA_11007_UPDATE_ID = 'manuais_historico_11007'
CUMA_11007_MANUAL_TEXT = 'MANUAL COMPLETO DO CUMA - Conversor Ultimate de Mangás\nVersão: 1.100.7\nBase de versionamento: 1.080.0\n\n===============================================================================\nATUALIZAÇÃO 1.100.7 - MANUAIS E HISTÓRICO CONSOLIDADOS\n===============================================================================\n\nEsta atualização não muda o fluxo principal de processamento. Ela atualiza os\nmanuais e arquivos de apoio para explicar melhor as funções adicionadas desde a\nversão 1.100.2.\n\nO que foi alinhado:\n• Manual principal da raiz do pacote.\n• Manual completo em docs/manual_do_programa.txt.\n• README.md, LEIA-ME.txt e histórico de versões.\n• Manual TXT gerado pelo botão Manual do aplicativo.\n• Arquivo ATUALIZACOES_DESDE_1.100.2.txt com o resumo consolidado das versões.\n\nResumo rápido das funções recentes:\n• Limpar, Ferramentas e Converter permitem reordenar arquivos manualmente.\n• É possível clicar, segurar e arrastar uma linha da lista para cima ou para baixo.\n• Também existem botões "Mover pra cima ↑" e "Mover pra baixo ↓" acima das listas.\n• A aba Converter ficou mais compacta, sem o grande espaço vazio entre botões e lista.\n• Ferramentas > Criar PDF de imagens aceita imagens, PDFs, CBZ, ZIP e EPUB com imagens.\n• CBR, RAR e 7Z também podem ser usados nessa ferramenta quando o 7-Zip estiver\n  instalado e disponível no sistema.\n• A ordem visível da lista é respeitada no processamento.\n\n===============================================================================\n1. VISÃO GERAL\n===============================================================================\n\nO CUMA é um aplicativo desktop para Windows voltado a limpeza, organização e\nconversão de arquivos usados em mangás, quadrinhos, PDFs escaneados e leitura em\ne-readers.\n\nEle concentra quatro fluxos principais:\n\n1. Limpar PDFs, removendo páginas vazias ou pouco úteis.\n2. Exportar o resultado como PDF, PDF + CBZ, CBZ ou imagens.\n3. Usar ferramentas auxiliares para extrair páginas e montar PDFs a partir de\n   imagens, PDFs e arquivos compactados com imagens.\n4. Converter arquivos prontos para formatos como PDF, EPUB, CBZ, imagens e XTCH,\n   conforme o tipo de entrada detectado.\n\nA interface é dividida em áreas laterais:\n\n• Limpar: fluxo principal de limpeza, preparação visual e exportação.\n• Ferramentas: utilidades auxiliares, como extrair páginas e criar PDF de imagens.\n• Converter: conversão pura de formato, sem relimpar nem reaplicar filtros visuais.\n• Resultados: lista processos concluídos e arquivos gerados.\n• Registros: mostra mensagens internas, logs e diagnósticos.\n• Configurações: aparência, idioma, desempenho, segurança, logs e preferências.\n• Sobre: resumo do aplicativo, versão e acesso aos manuais.\n\nRegra mais importante:\n• Use Limpar para preparar ou modificar o conteúdo.\n• Use Converter para transformar o arquivo já pronto em outro formato.\n• Use Ferramentas quando precisar de ações auxiliares fora da fila principal.\n\n===============================================================================\n2. BOTÕES DO TOPO\n===============================================================================\n\nManual\nAbre o manual do CUMA. O aplicativo também grava um TXT de manual ao lado do\nprograma ou na pasta de execução, dependendo do modo de uso.\n\nLog\nAbre o arquivo de log quando ele existir. Use para investigar falhas, conferir\nmensagens internas ou enviar diagnóstico.\n\nProcurar atualizações\nVerifica o manifesto de atualização configurado no aplicativo. Quando houver\nfonte válida, compara a versão atual com a versão disponível.\n\nBotão de tema rápido\nAlterna rapidamente o tema claro/escuro quando disponível. As opções completas\nficam em Configurações.\n\n===============================================================================\n3. LISTAS DE ARQUIVOS E ORDEM MANUAL\n===============================================================================\n\nAs abas Limpar, Ferramentas e Converter usam listas de arquivos. A partir da\nversão 1.100.5, essas listas podem ser reorganizadas manualmente.\n\nComo mover com o mouse:\n1. Clique no arquivo desejado dentro da lista.\n2. Segure o clique.\n3. Arraste a linha para cima ou para baixo.\n4. Solte na posição desejada.\n\nComo mover com botões:\n• Selecione um arquivo na lista.\n• Clique em "Mover pra cima ↑" para subir uma posição.\n• Clique em "Mover pra baixo ↓" para descer uma posição.\n\nObservações:\n• A ordem visível da lista é a ordem usada no processamento.\n• Em Ferramentas > Criar PDF de imagens, essa ordem define a sequência das páginas\n  no PDF final.\n• Em lotes grandes, revise a ordem antes de clicar em Processar.\n• Use os botões de mover quando quiser um ajuste preciso de uma linha por vez.\n• Use arrastar e soltar dentro da lista quando precisar reorganizar vários itens\n  visualmente.\n\n===============================================================================\n4. ABA LIMPAR\n===============================================================================\n\nA aba Limpar é o fluxo principal do programa para PDFs.\n\nÁrea "Arraste PDFs ou pastas aqui"\nPermite soltar PDFs ou pastas diretamente na fila. Quando tkinterdnd2 não estiver\ninstalado, o aplicativo continua funcionando, mas o arrastar-e-soltar externo\npode ficar indisponível. Nesse caso, use os botões de seleção.\n\nAdicionar PDF(s)\nAdiciona um ou mais PDFs à fila.\n\nAdicionar pasta\nAdiciona PDFs encontrados dentro de uma pasta. Quando a opção de incluir\nsubpastas estiver marcada, também procura PDFs nas subpastas.\n\nColar caminho\nPermite colar manualmente caminhos de arquivos ou pastas.\n\nRemover\nRemove da fila os itens selecionados.\n\nLimpar lista\nEsvazia a fila da aba Limpar.\n\nMover pra cima ↑ / Mover pra baixo ↓\nReordena o arquivo selecionado dentro da fila.\n\nPrévia Limpar\nMostra a prévia correta das opções de limpeza e preparação visual. Essa prévia\nserve para conferir alterações antes do processamento.\n\nConfigurações do PDF\nAbre as opções que realmente modificam ou preparam o conteúdo antes da exportação.\nNessa janela ficam as opções de perfil visual e preparação, como:\n• Ordem de leitura Ocidental/Mangá.\n• Presets E-ink.\n• Remoção automática de margens.\n• Remoção de rodapé ou número de página.\n• Divisão de páginas duplas.\n• Manter a página original ao dividir.\n• Webtoon/imagens longas.\n• Prévia Limpar.\n\nPasta de saída\nDefine onde os arquivos limpos serão gravados. Essa pasta é independente da pasta\ndo Converter.\n\nSufixo\nTexto adicionado ao nome final. Exemplo: "capitulo01.pdf" com sufixo "_limpo"\nvira "capitulo01_limpo.pdf".\n\nFormato de exportação\nDefine o tipo de saída:\n• PDF: cria apenas o PDF limpo.\n• PDF + CBZ: cria o PDF limpo e um CBZ com as páginas mantidas.\n• CBZ: cria apenas o CBZ.\n• Imagens JPG: exporta as páginas mantidas como JPG.\n• Imagens PNG: exporta as páginas mantidas como PNG.\n\nIntervalo de páginas\nPermite limitar o processamento. Exemplos:\n• 1-10: processa da página 1 até a 10.\n• 1-5, 8, 12-15: processa blocos separados.\n• vazio: processa todas as páginas.\n\nAbrir resultado ao concluir\nQuando marcado, tenta abrir a pasta ou o arquivo final ao terminar.\n\nProcessar\nExecuta a limpeza conforme as opções configuradas.\n\nQuando usar Limpar:\n• Quando o PDF precisa passar por preparação visual.\n• Quando você quer remover páginas vazias ou pouco úteis.\n• Quando quer criar PDF/CBZ/imagens já limpos.\n• Quando quer aplicar corte, preset E-ink, divisão de página dupla ou webtoon.\n\n===============================================================================\n5. ABA FERRAMENTAS\n===============================================================================\n\nA aba Ferramentas reúne utilidades auxiliares que não dependem da fila principal\nda aba Limpar.\n\nEla possui duas subabas principais:\n\n-------------------------------------------------------------------------------\n5.1 EXTRAIR PÁGINAS\n-------------------------------------------------------------------------------\n\nA função Extrair páginas trabalha com PDFs.\n\nAdicionar PDF(s)\nAdiciona PDFs à lista de extração.\n\nAdicionar pasta\nAdiciona PDFs encontrados em uma pasta.\n\nColar caminho\nPermite colar caminhos manualmente.\n\nRemover / Limpar\nRemove itens selecionados ou limpa a lista inteira.\n\nMover pra cima ↑ / Mover pra baixo ↓\nReordena os PDFs da lista.\n\nArrastar dentro da lista\nTambém é possível clicar, segurar e mover um arquivo para outra posição.\n\nProcessar\nExtrai as páginas dos PDFs como imagens, conforme as opções disponíveis.\n\nQuando usar:\n• Para transformar páginas de PDF em PNG/JPG.\n• Para separar páginas antes de montar outro arquivo.\n• Para diagnóstico quando um PDF específico precisa ser conferido página por página.\n\n-------------------------------------------------------------------------------\n5.2 CRIAR PDF DE IMAGENS\n-------------------------------------------------------------------------------\n\nA função Criar PDF de imagens monta um PDF único a partir da lista exibida.\n\nTipos aceitos:\n• Imagens: JPG, JPEG, PNG, WEBP, BMP, TIF e TIFF.\n• PDF.\n• CBZ.\n• ZIP.\n• EPUB com imagens.\n• CBR, RAR e 7Z quando o 7-Zip estiver instalado e disponível no sistema.\n\nComo adicionar:\n• Use Adicionar arquivo(s) para selecionar imagens, PDFs ou arquivos com imagens.\n• Use Adicionar pasta para inserir arquivos encontrados em uma pasta.\n• Use Colar caminho para informar caminhos manualmente.\n• Também é possível arrastar arquivos/pastas para a área da ferramenta quando o\n  arrastar-e-soltar estiver disponível.\n\nOrdem:\n• A ordem da lista é a ordem do PDF final.\n• Use "Mover pra cima ↑", "Mover pra baixo ↓" ou arraste linhas na lista para\n  ajustar a sequência.\n• Em CBZ/ZIP/EPUB com imagens, as imagens internas são lidas em ordem natural.\n• Em PDFs adicionados à lista, as páginas entram na posição daquele PDF na lista.\n\nComo o PDF final é montado:\n• Imagens comuns entram como páginas.\n• PDFs entram página por página.\n• CBZ, ZIP e EPUB com imagens têm suas imagens internas extraídas temporariamente\n  e inseridas no PDF.\n• CBR, RAR e 7Z dependem do 7-Zip para extração.\n• A ferramenta respeita a ordem manual da lista antes de gerar o arquivo.\n\nLimitações:\n• EPUB textual puro não é renderizado nessa ferramenta.\n• EPUB com imagens é aceito.\n• Arquivos CBR/RAR/7Z exigem 7-Zip instalado e disponível no PATH do Windows.\n• Arquivos protegidos por senha podem falhar.\n\nQuando usar:\n• Para juntar capas, imagens soltas e capítulos em um PDF.\n• Para criar um PDF a partir de um CBZ/ZIP/EPUB de imagens.\n• Para juntar PDFs e imagens em uma sequência única.\n• Para reorganizar manualmente capítulos antes de gerar um PDF final.\n\n===============================================================================\n6. ABA CONVERTER\n===============================================================================\n\nA aba Converter transforma arquivos prontos em outros formatos. Ela foi ajustada\npara ser mais compacta visualmente e não exibir o grande espaço vazio entre os\nbotões e a lista.\n\nRegra da aba Converter:\n• Converter apenas converte formato.\n• Converter não relimpa o arquivo.\n• Converter não remove margens.\n• Converter não divide páginas duplas.\n• Converter não reaplica presets E-ink.\n• Converter não remove rodapé/número de página.\n• Converter não aplica webtoon/imagens longas.\n\nUse Limpar primeiro quando precisar modificar o conteúdo. Depois use Converter\npara gerar o formato final.\n\nÁrea "Arraste PDFs, EPUBs ou pastas aqui"\nPermite soltar arquivos ou pastas. O texto pode variar conforme a versão, mas a\nfunção é adicionar arquivos à lista de conversão.\n\nAdicionar arquivo(s)\nAdiciona arquivos compatíveis à fila do Converter.\n\nAdicionar pasta\nAdiciona arquivos compatíveis encontrados em uma pasta.\n\nColar caminho\nPermite colar caminhos manualmente.\n\nRemover\nRemove os itens selecionados.\n\nLimpar\nEsvazia a lista do Converter.\n\nPrévia\nMostra a prévia da entrada real que será enviada ao conversor, sem encaixar em\ncanvas branco de dispositivo nas conversões puras.\n\nFunções por tipo\nMostra ou atualiza as conversões disponíveis conforme o tipo de arquivo selecionado.\n\nMover pra cima ↑ / Mover pra baixo ↓\nReordena os arquivos da fila do Converter.\n\nArrastar dentro da lista\nPermite clicar, segurar e mover um arquivo para outra posição.\n\nDispositivo\nSeleciona um perfil de dispositivo. O perfil é importante principalmente para\nsaídas que exigem dimensões específicas, como XTCH.\n\nAplicar perfil\nAplica o perfil escolhido às opções de conversão compatíveis.\n\nEditor de perfis\nPermite criar ou ajustar perfis de dispositivo.\n\nPasta de saída\nDefine onde o Converter salvará seus arquivos. Essa pasta é separada da pasta da\naba Limpar.\n\nMetadados EPUB\nAparece somente quando o arquivo selecionado é EPUB ou quando alguma conversão de\nsaída para EPUB está marcada.\n\nConversões compatíveis por tipo:\n• PDF pode liberar PDF → EPUB, PDF → XTCH, PDF → CBZ e PDF → imagens.\n• EPUB pode liberar EPUB → XTCH e EPUB → PDF.\n• CBZ/ZIP/CBR/RAR/7Z podem liberar compactado → EPUB, compactado → XTCH e\n  compactado → PDF.\n• Imagens podem liberar imagem → PDF, imagem → EPUB e imagem → XTCH.\n\nDependências:\n• CBZ e ZIP funcionam nativamente.\n• CBR, RAR e 7Z dependem do 7-Zip instalado no Windows.\n• XTCH usa dimensões fixas de dispositivo por exigência do formato.\n\nQuando usar:\n• Para converter um arquivo que já está pronto.\n• Para gerar EPUB de imagens, CBZ, imagens ou XTCH.\n• Para adaptar arquivos a dispositivos Kindle, Kobo, reMarkable ou perfis\n  personalizados.\n• Para manter a preparação visual separada da conversão final.\n\n===============================================================================\n7. EDITOR DE PERFIS DE DISPOSITIVO\n===============================================================================\n\nO editor de perfis permite ajustar dimensões e parâmetros usados por conversões\nvoltadas a e-readers.\n\nUse quando:\n• O dispositivo desejado não estiver na lista.\n• O arquivo final precisa seguir uma resolução específica.\n• Você quer testar um perfil personalizado.\n\nDica:\nFaça um teste com poucos arquivos antes de converter uma coleção inteira.\n\n===============================================================================\n8. ABA RESULTADOS\n===============================================================================\n\nA aba Resultados mostra processos concluídos e arquivos gerados.\n\nUse para:\n• Confirmar quais arquivos foram criados.\n• Abrir pastas de saída.\n• Conferir se um lote terminou corretamente.\n\n===============================================================================\n9. ABA REGISTROS\n===============================================================================\n\nA aba Registros mostra mensagens internas, logs e diagnósticos.\n\nUse quando:\n• Uma conversão falhar.\n• Um arquivo não for aceito.\n• For necessário copiar informações para suporte.\n• Você quiser conferir caminhos de saída e mensagens de erro.\n\nArquivos relacionados:\n• CUMA.log.\n• erro.txt.\n• debug_completo_cuma.txt, quando gerado por --debug-env.\n\n===============================================================================\n10. ABA CONFIGURAÇÕES\n===============================================================================\n\nA aba Configurações centraliza preferências do aplicativo.\n\nItens comuns:\n• Tema e cores.\n• Idioma.\n• Desempenho.\n• Segurança.\n• Logs.\n• Preferências de abertura de resultados.\n• Opções de hardware quando disponíveis.\n\nAs configurações do usuário ficam em:\n%APPDATA%\\CUMA\\cuma_settings.json\n\nNão é necessário copiar esse arquivo para dentro da pasta do programa.\n\n===============================================================================\n11. ABA SOBRE\n===============================================================================\n\nA aba Sobre mostra:\n• Nome do aplicativo.\n• Versão.\n• Resumo do projeto.\n• Acesso aos manuais.\n• Informações gerais de suporte.\n\n===============================================================================\n12. SISTEMA DE VERSÕES\n===============================================================================\n\nBase oficial: 1.080.0.\n\nEscalas usadas pelo projeto:\n• grande: incrementa o primeiro número e zera os demais.\n  Exemplo: 1.100.0 → 2.000.0\n• média: soma 10 ao bloco central e zera correções.\n  Exemplo: 1.080.0 → 1.090.0\n• pequena: soma 1 ao bloco central e zera correções.\n  Exemplo: 1.080.0 → 1.081.0\n• pouca/hotfix: soma 1 ao terceiro número.\n  Exemplo: 1.100.6 → 1.100.7\n\n===============================================================================\n13. ARQUIVOS E DADOS DO USUÁRIO\n===============================================================================\n\nArquivos principais do pacote:\n• cuma.py: código principal.\n• cuma.spec: receita de build PyInstaller.\n• requirements.txt: dependências Python.\n• rodar_cuma.bat: abre o programa no Windows com ambiente preparado.\n• criar_exe_windows_e_zip.bat: compila e compacta o executável.\n• app_icon.ico e cuma_logo.png: ícone e logo.\n• manual_do_programa.txt: manual completo.\n• LEIA-ME.txt: resumo rápido de uso.\n• README.md: descrição para GitHub.\n• docs/manual_do_programa.txt: cópia do manual completo para documentação.\n• docs/historico_versoes.md: histórico das versões.\n• ATUALIZACOES_DESDE_1.100.2.txt: resumo consolidado das alterações recentes.\n\nArquivos que não devem ser enviados como parte limpa da release:\n• limpos/\n• CUMA.log\n• erro.txt\n• debug_completo_cuma.txt\n• arquivos convertidos\n• builds antigas\n• __pycache__/\n• *.pyc\n\nDados do usuário no Windows:\n%APPDATA%\\CUMA\\\n\nDentro dessa pasta podem ficar:\n• cuma_settings.json.\n• CUMA.log.\n• erro.txt.\n• debug_completo_cuma.txt.\n\n===============================================================================\n14. LIMITAÇÕES CONHECIDAS\n===============================================================================\n\n• EPUB textual puro não é renderizado em Ferramentas > Criar PDF de imagens.\n• EPUB com imagens é aceito nessa ferramenta.\n• CBR/RAR/7Z dependem do 7-Zip instalado e disponível no PATH.\n• tkinterdnd2 é opcional; sem ele, o arrastar-e-soltar externo pode não funcionar.\n• Arquivos protegidos por senha podem falhar.\n• Arquivos muito grandes podem demorar e consumir bastante memória.\n• A detecção de páginas vazias é visual/heurística; revise o PDF de removidas\n  antes de apagar originais.\n• XTCH exige dimensões fixas de dispositivo, então o perfil escolhido importa.\n\n===============================================================================\n15. FLUXOS RECOMENDADOS\n===============================================================================\n\nFluxo seguro para limpeza:\n1. Abra o CUMA.\n2. Vá para Limpar.\n3. Adicione um PDF de teste.\n4. Ajuste Configurações do PDF se necessário.\n5. Use Prévia Limpar.\n6. Processe.\n7. Confira o resultado antes de rodar lotes grandes.\n\nFluxo para criar PDF a partir de imagens/PDF/CBZ:\n1. Vá para Ferramentas.\n2. Abra Criar PDF de imagens.\n3. Adicione imagens, PDFs, CBZ, ZIP ou EPUB com imagens.\n4. Reordene a lista com arraste ou com "Mover pra cima ↑" e "Mover pra baixo ↓".\n5. Processe e confira o PDF final.\n\nFluxo para converter arquivo pronto:\n1. Prepare o arquivo em Limpar, se ele precisar de ajustes visuais.\n2. Vá para Converter.\n3. Adicione o arquivo pronto.\n4. Escolha dispositivo e formato de saída quando aplicável.\n5. Confira as conversões compatíveis.\n6. Processe.\n7. Teste o resultado no leitor ou dispositivo real.\n\nFluxo para diagnóstico:\n1. Abra Registros.\n2. Copie as mensagens relevantes.\n3. Verifique CUMA.log e erro.txt, se existirem.\n4. Execute python cuma.py --debug-env quando precisar gerar diagnóstico completo.\n'
CUMA_11007_README_TXT = 'CUMA - Conversor Ultimate de Mangás\nVersão: 1.100.7\n\nCOMO USAR\n1. Extraia o ZIP inteiro.\n2. Abra cuma.exe.\n3. Não apague a pasta _internal.\n4. O manual completo está em manual_do_programa.txt.\n5. O resumo das mudanças recentes está em ATUALIZACOES_DESDE_1.100.2.txt.\n\nNOVIDADES RECENTES\n- Limpar, Ferramentas e Converter permitem mover arquivos com arraste ou com os botões "Mover pra cima ↑" e "Mover pra baixo ↓".\n- A aba Converter está mais compacta, sem o grande espaço vazio entre botões e lista.\n- Ferramentas > Criar PDF de imagens aceita imagens, PDFs, CBZ, ZIP, EPUB com imagens e, com 7-Zip, CBR/RAR/7Z.\n- Os manuais foram atualizados para explicar essas funções.\n\nESTRUTURA RECOMENDADA\nCUMA/\n  cuma.exe\n  manual_do_programa.txt\n  ATUALIZACOES_DESDE_1.100.2.txt\n  LEIA-ME.txt\n  _internal/\n\nDADOS DO USUÁRIO\nAs configurações ficam em um único arquivo:\n%APPDATA%\\CUMA\\cuma_settings.json\n\nLogs e relatórios de erro também ficam em %APPDATA%\\CUMA quando forem necessários.\n\nOBSERVAÇÃO\nNão distribua a pasta limpos/, arquivos convertidos, CUMA.log, erro.txt ou arquivos de debug.\n'


def _cuma_11007_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'[CUMA 1.100.7] {context}' if exc is None else f'[CUMA 1.100.7] {context}: {exc}'
        write_log(msg)
    except Exception:
        pass


def ensure_manual() -> Path:
    try:
        manual_path().write_text(CUMA_11007_MANUAL_TEXT, encoding='utf-8')
    except Exception as exc:
        _cuma_11007_log('Falha ao gerar manual 1.100.7', exc)
    return manual_path()


def _cuma_11007_write_readme() -> None:
    try:
        target = app_dir() / 'LEIA-ME.txt'
        target.write_text(CUMA_11007_README_TXT, encoding='utf-8')
    except Exception as exc:
        _cuma_11007_log('Falha ao atualizar LEIA-ME 1.100.7', exc)


def _cuma_11007_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11007_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11007_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11007_VERSION,
            'date': '2026-06-23',
            'items': [
                'Manuais atualizados para explicar reordenação manual nas abas Limpar, Ferramentas e Converter.',
                'Documentação atualizada para Criar PDF de imagens com PDFs e arquivos compactados com imagens.',
                'Criado ATUALIZACOES_DESDE_1.100.2.txt com o resumo consolidado das versões recentes.'
            ]
        }
        if 'cuma_settings_load' in globals() and 'cuma_settings_save' in globals():
            try:
                data = cuma_settings_load()
                if isinstance(data, dict):
                    version_payload = data.get('version') if isinstance(data.get('version'), dict) else {}
                    version_payload.update({
                        'version': CUMA_11007_VERSION,
                        'updated_at': '2026-06-23',
                        'notes': 'Manuais atualizados e arquivo de atualizações desde 1.100.2 adicionado.'
                    })
                    data['version'] = version_payload
                    cuma_settings_save(data)
            except Exception as exc:
                _cuma_11007_log('Atualizar settings de versão 1.100.7', exc)
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            try:
                state = cuma_version_load_state()
                if not isinstance(state, dict):
                    state = {}
                events = state.get('events', [])
                if not isinstance(events, list):
                    events = []
                if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11007_UPDATE_ID for e in events):
                    events.append({
                        'update_id': CUMA_11007_UPDATE_ID,
                        'version': CUMA_11007_VERSION,
                        'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                        'scale': 'pouca',
                        'description': 'Manuais e histórico consolidados; arquivo ATUALIZACOES_DESDE_1.100.2.txt adicionado.',
                        'timestamp': datetime.now().isoformat(timespec='seconds')
                    })
                state['events'] = events[-100:]
                state['current_version'] = CUMA_11007_VERSION
                state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
                cuma_version_save_state(state)
                if '_cuma_version_write_public_files' in globals():
                    _cuma_version_write_public_files(state)
            except Exception as exc:
                _cuma_11007_log('Versionamento 1.100.7', exc)
    except Exception as exc:
        _cuma_11007_log('Forçar versão 1.100.7', exc)


def _cuma_install_11007_manuals_and_history() -> None:
    try:
        _cuma_11007_force_version()
        try:
            ensure_manual()
        except Exception:
            pass
        try:
            _cuma_11007_write_readme()
        except Exception:
            pass
    except Exception as exc:
        _cuma_11007_log('Instalação patch 1.100.7', exc)


_cuma_install_11007_manuals_and_history()




# =============================================================================
# CUMA 1.100.8 - CORREÇÕES DE AUDITORIA E ROBUSTEZ
# =============================================================================
# Correções principais:
# - Escrita atômica/temporária para EPUB, CBZ e PDFs gerados.
# - Correção de CBZ/ZIP no Converter em modo puro.
# - Validação de arquivos existentes nas abas Ferramentas.
# - Limite de leitura por item em compactados para reduzir risco de consumo excessivo de memória.
# - Versionamento e documentação alinhados com 1.100.8.
CUMA_11008_VERSION = '1.100.8'
CUMA_11008_UPDATE_ID = 'auditoria_robustez_codigo_11008'
CUMA_11008_MAX_ARCHIVE_ENTRY_BYTES = 512 * 1024 * 1024


def _cuma_11008_log(context: str, exc: Exception | None = None) -> None:
    try:
        msg = f'[CUMA 1.100.8] {context}' if exc is None else f'[CUMA 1.100.8] {context}: {type(exc).__name__}: {exc}'
        write_log(msg)
    except Exception:
        pass


def _cuma_11008_path_key(value) -> str:
    # Chave de identidade de caminho sem reduzir maiúsculas/minúsculas em sistemas case-sensitive.
    try:
        resolved = Path(value).expanduser().resolve()
        raw = str(resolved) if os.name == 'nt' else resolved.as_posix()
        return os.path.normcase(raw) if os.name == 'nt' else raw
    except Exception:
        raw = str(value)
        return os.path.normcase(raw) if os.name == 'nt' else raw


def _cuma_11008_tmp_path(target: Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.with_name(f'.{target.name}.{uuid.uuid4().hex}.tmp')


def _cuma_11008_replace_atomically(tmp_path: Path, final_path: Path) -> None:
    os.replace(str(tmp_path), str(final_path))


def _cuma_11008_read_zip_member_limited(zf: zipfile.ZipFile, name: str, max_bytes: int = CUMA_11008_MAX_ARCHIVE_ENTRY_BYTES) -> bytes:
    try:
        info = zf.getinfo(name)
        if int(getattr(info, 'file_size', 0) or 0) > max_bytes:
            raise RuntimeError(f'Arquivo interno muito grande: {name} ({info.file_size} bytes).')
    except KeyError:
        raise
    with zf.open(name) as f:
        data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise RuntimeError(f'Arquivo interno excede o limite de {max_bytes} bytes: {name}.')
    return data


def _cuma_11008_image_from_zip_member(zf: zipfile.ZipFile, name: str) -> Image.Image:
    data = BytesIO(_cuma_11008_read_zip_member_limited(zf, name))
    with Image.open(data) as opened:
        return opened.convert('RGB')


def _cuma_11008_create_image_epub_from_iter(image_iter, output_epub: Path, title: str, quality: int = 92) -> None:
    output_epub = Path(output_epub)
    tmp_epub = _cuma_11008_tmp_path(output_epub)
    tmp_epub.unlink(missing_ok=True)
    uid = str(uuid.uuid4())
    manifest = []
    spine = []
    nav = []
    meta = _cuma_11000_epub_metadata(title) if '_cuma_11000_epub_metadata' in globals() else {'title': title or 'CUMA', 'language': 'pt-BR'}
    count = 0
    try:
        with zipfile.ZipFile(tmp_epub, 'w') as z:
            z.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            z.writestr('META-INF/container.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>''')
            for count, im in enumerate(image_iter, 1):
                try:
                    img_name = f'images/page_{count:04d}.jpg'
                    html_name = f'page_{count:04d}.xhtml'
                    bio = BytesIO()
                    q = int(max(50, min(100, quality or 92)))
                    im.convert('RGB').save(bio, format='JPEG', quality=q, optimize=True)
                    z.writestr('OEBPS/' + img_name, bio.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
                    z.writestr('OEBPS/' + html_name, f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Página {count}</title><style>html,body{{margin:0;padding:0;background:white;}} img{{width:100%;height:100%;object-fit:contain;display:block;}}</style></head><body><img src="{img_name}" alt="Página {count}"/></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
                    manifest.append(f'<item id="p{count}" href="{html_name}" media-type="application/xhtml+xml"/>')
                    manifest.append(f'<item id="img{count}" href="{img_name}" media-type="image/jpeg"/>')
                    spine.append(f'<itemref idref="p{count}"/>')
                    nav.append(f'<li><a href="{html_name}">Página {count}</a></li>')
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
            if count <= 0:
                raise RuntimeError('Nenhuma imagem para criar EPUB.')
            z.writestr('OEBPS/nav.xhtml', f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Sumário</title></head><body><nav epub:type="toc"><ol>{''.join(nav)}</ol></nav></body></html>''', compress_type=zipfile.ZIP_DEFLATED)
            meta_writer = globals().get('_cuma_11000_epub_opf_metadata')
            meta_xml = meta_writer(meta, uid) if callable(meta_writer) else f'<dc:identifier id="uid">{uid}</dc:identifier><dc:title>{html.escape(title or "CUMA")}</dc:title><dc:language>pt-BR</dc:language>'
            z.writestr('OEBPS/content.opf', f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">{meta_xml}</metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>''', compress_type=zipfile.ZIP_DEFLATED)
        _cuma_11008_replace_atomically(tmp_epub, output_epub)
    except Exception:
        tmp_epub.unlink(missing_ok=True)
        raise


def _cuma_11008_create_image_epub(images: list[Image.Image], output_epub: Path, title: str, quality: int = 92) -> None:
    if not images:
        raise RuntimeError('Nenhuma imagem para criar EPUB.')
    return _cuma_11008_create_image_epub_from_iter(iter(images), output_epub, title, quality)


def _cuma_11008_create_image_epub_from_pdf(pdf_path: Path, output_epub: Path, title: str, target: Optional[tuple[int, int]] = None, quality: int = 92) -> None:
    return _cuma_11008_create_image_epub_from_iter(_cuma_11000_iter_pdf_pages_as_images(pdf_path, target=target), output_epub, title, quality)


def _cuma_11008_create_epub_from_archive(archive_path: Path, output_epub: Path, title: str, target: Optional[tuple[int, int]] = None, quality: int = 92) -> None:
    return _cuma_11008_create_image_epub_from_iter(_cuma_11000_iter_archive_images(archive_path, target=target), output_epub, title, quality)


def _cuma_11008_iter_archive_images(archive_path: Path, target: Optional[tuple[int, int]] = None):
    settings = _cuma_11000_processing_settings()
    suffix = Path(archive_path).suffix.lower()
    if suffix in ('.zip', '.cbz'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            for name in _cuma_11000_archive_image_names(z):
                try:
                    im = _cuma_11008_image_from_zip_member(z, name)
                    try:
                        if im.width < 80 or im.height < 80:
                            continue
                        for processed in _cuma_11000_process_source_image(im, target, settings):
                            yield processed
                    finally:
                        try:
                            im.close()
                        except Exception:
                            pass
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada no compactado: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        with tempfile.TemporaryDirectory(prefix='cuma_archive_') as td:
            files = _cuma_11000_extract_with_7z(archive_path, Path(td))
            for p in files:
                try:
                    with Image.open(p) as opened:
                        im = opened.convert('RGB')
                    try:
                        if im.width < 80 or im.height < 80:
                            continue
                        for processed in _cuma_11000_process_source_image(im, target, settings):
                            yield processed
                    finally:
                        try:
                            im.close()
                        except Exception:
                            pass
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada no compactado: {p.name}', exc)
    else:
        raise RuntimeError('Arquivo compactado não suportado. Use CBZ, ZIP, CBR, RAR ou 7Z.')


def _cuma_11008_iter_epub_images(epub_path: Path, target: tuple[int, int]):
    if not Path(epub_path).exists():
        raise RuntimeError('EPUB não encontrado.')
    settings = _cuma_11000_processing_settings()
    with zipfile.ZipFile(epub_path, 'r') as z:
        names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_cuma_11000_natural_key)
        for name in names:
            try:
                im = _cuma_11008_image_from_zip_member(z, name)
                try:
                    if im.width < 80 or im.height < 80:
                        continue
                    for processed in _cuma_11000_process_source_image(im, target, settings):
                        yield processed
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
            except Exception as exc:
                _cuma_11008_log(f'Imagem ignorada no EPUB: {name}', exc)


def _cuma_11008_iter_archive_images_raw(archive_path: Path):
    archive_path = Path(archive_path)
    suffix = archive_path.suffix.lower()
    if suffix in ('.zip', '.cbz'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            names = _cuma_11000_archive_image_names(z) if '_cuma_11000_archive_image_names' in globals() else sorted(
                [n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT],
                key=_natural_key
            )
            for name in names:
                try:
                    im = _cuma_11008_image_from_zip_member(z, name)
                    if im.width < 80 or im.height < 80:
                        try:
                            im.close()
                        except Exception:
                            pass
                        continue
                    yield im
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada no compactado: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        with tempfile.TemporaryDirectory(prefix='cuma_archive_raw_') as td:
            files = _cuma_11000_extract_with_7z(archive_path, Path(td))
            for p in files:
                try:
                    with Image.open(p) as opened:
                        rgb = opened.convert('RGB')
                    if rgb.width < 80 or rgb.height < 80:
                        try:
                            rgb.close()
                        except Exception:
                            pass
                        continue
                    yield rgb
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada no compactado: {p.name}', exc)
    else:
        raise RuntimeError('Arquivo compactado não suportado. Use CBZ, ZIP, CBR, RAR ou 7Z.')


def _cuma_11008_iter_epub_images_raw(epub_path: Path):
    with zipfile.ZipFile(epub_path, 'r') as z:
        names = sorted([n for n in z.namelist() if Path(n).suffix.lower() in SUPPORTED_IMAGE_EXT], key=_cuma_11000_natural_key)
        for name in names:
            try:
                im = _cuma_11008_image_from_zip_member(z, name)
                if im.width < 80 or im.height < 80:
                    try:
                        im.close()
                    except Exception:
                        pass
                    continue
                yield im
            except Exception as exc:
                _cuma_11008_log(f'Imagem ignorada no EPUB: {name}', exc)


def _cuma_11008_create_pdf_from_image_iter(image_iter, output_pdf: Path) -> None:
    output_pdf = Path(output_pdf)
    tmp_pdf = _cuma_11008_tmp_path(output_pdf)
    tmp_pdf.unlink(missing_ok=True)
    doc = fitz.open()
    count = 0
    try:
        for im in image_iter:
            count += 1
            rgb = None
            try:
                rgb = im.convert('RGB')
                bio = BytesIO()
                rgb.save(bio, format='JPEG', quality=92, optimize=True)
                page = doc.new_page(width=max(1, rgb.width), height=max(1, rgb.height))
                page.insert_image(page.rect, stream=bio.getvalue())
            finally:
                try:
                    if rgb is not None and rgb is not im:
                        rgb.close()
                except Exception:
                    pass
                try:
                    im.close()
                except Exception:
                    pass
        if count <= 0:
            raise RuntimeError('Nenhuma imagem para criar PDF.')
        doc.save(str(tmp_pdf), garbage=4, deflate=True)
        _cuma_11008_replace_atomically(tmp_pdf, output_pdf)
    except Exception:
        tmp_pdf.unlink(missing_ok=True)
        raise
    finally:
        doc.close()


def _cuma_11008_create_cbz_from_image_iter(image_iter, output_cbz: Path, quality: int = 92) -> None:
    output_cbz = Path(output_cbz)
    tmp_cbz = _cuma_11008_tmp_path(output_cbz)
    tmp_cbz.unlink(missing_ok=True)
    count = 0
    try:
        with zipfile.ZipFile(tmp_cbz, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for im in image_iter:
                count += 1
                try:
                    bio = BytesIO()
                    im.convert('RGB').save(bio, format='JPEG', quality=int(max(50, min(100, quality or 92))), optimize=True)
                    z.writestr(f'page_{count:04d}.jpg', bio.getvalue())
                finally:
                    try:
                        im.close()
                    except Exception:
                        pass
        if count <= 0:
            raise RuntimeError('Nenhuma imagem para criar CBZ.')
        _cuma_11008_replace_atomically(tmp_cbz, output_cbz)
    except Exception:
        tmp_cbz.unlink(missing_ok=True)
        raise


def _cuma_11008_accept_create_path(path: Path) -> bool:
    try:
        p = Path(path)
        return p.is_file() and p.suffix.lower() in CUMA_11006_CREATE_PDF_EXTS
    except Exception:
        return False


def _tools_accept_path(path: Path, kind: str) -> bool:
    try:
        p = Path(path)
        if not p.is_file():
            return False
        suffix = p.suffix.lower()
        if kind == 'extract':
            return suffix == '.pdf'
        if kind == 'create':
            return suffix in CUMA_11006_CREATE_PDF_EXTS
        if _CUMA_11006_ORIG_TOOLS_ACCEPT_PATH:
            return _CUMA_11006_ORIG_TOOLS_ACCEPT_PATH(p, kind)
    except Exception:
        return False
    return False


def _cuma_11008_iter_archive_images_for_create(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix in ('.cbz', '.zip', '.epub'):
        with zipfile.ZipFile(path, 'r') as zf:
            names = _cuma_11006_image_names_from_zip(zf)
            if not names:
                raise RuntimeError(f'Não encontrei imagens dentro de {Path(path).name}.')
            for name in names:
                try:
                    with Image.open(BytesIO(_cuma_11008_read_zip_member_limited(zf, name))) as opened:
                        for img in _cuma_11006_iter_opened_image(opened):
                            yield img
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada em {Path(path).name}: {name}', exc)
    elif suffix in ('.cbr', '.rar', '.7z'):
        with tempfile.TemporaryDirectory(prefix='cuma_criar_pdf_') as td:
            files = _cuma_11006_extract_archive_with_7z(path, Path(td))
            if not files:
                raise RuntimeError(f'Não encontrei imagens dentro de {Path(path).name}.')
            for img_path in files:
                try:
                    for img in _cuma_11006_iter_image_file(img_path):
                        yield img
                except Exception as exc:
                    _cuma_11008_log(f'Imagem ignorada em {Path(path).name}: {img_path.name}', exc)
    else:
        raise RuntimeError(f'Arquivo compactado não suportado: {Path(path).name}')


def _cuma_11008_iter_source_images_for_create(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix in SUPPORTED_IMAGE_EXT:
        yield from _cuma_11006_iter_image_file(path)
    elif suffix in CUMA_11006_ARCHIVE_EXTS:
        yield from _cuma_11008_iter_archive_images_for_create(path)
    else:
        raise RuntimeError(f'Formato não suportado para criar PDF: {Path(path).name}')


def _cuma_11008_append_image_source(out_doc, source_path: Path, progress_cb=None) -> int:
    count = 0
    for img in _cuma_11008_iter_source_images_for_create(source_path):
        try:
            _cuma_11006_add_image_page(out_doc, img)
            count += 1
            if progress_cb:
                progress_cb(count, max(1, count))
        finally:
            try:
                img.close()
            except Exception:
                pass
    if count <= 0:
        raise RuntimeError(f'Nenhuma imagem válida em {Path(source_path).name}.')
    return count


def _tools_process_create_pdf(self, selected=False) -> None:
    paths = _tools_selected_paths(self, 'create') if selected else list(getattr(self, 'tools_create_files', []))
    paths = [Path(p) for p in paths if _cuma_11008_accept_create_path(Path(p))]
    if not paths:
        messagebox.showinfo('Criar PDF', 'Adicione ou selecione imagens, PDFs, CBZ/ZIP/EPUB ou arquivos compactados com imagens.')
        return

    out_dir = _cuma_tab_output_dir('Ferramentas', True)
    name = self.tools_pdf_name.get().strip() or 'imagens_unidas.pdf'
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    output = unique_path(out_dir / name)
    tmp_output = _cuma_11008_tmp_path(output)
    total_sources = len(paths)
    total_pages = 0
    debug = {
        'acao': 'criar_pdf_a_partir_de_imagens_pdf_cbz_arquivos',
        'versao': APP_DISPLAY_VERSION,
        'arquivos': [str(p) for p in paths],
        'saida': str(output),
        'status': 'iniciado',
        'resultados': []
    }
    out_doc = fitz.open()
    try:
        for source_index, p in enumerate(paths, 1):
            suffix = p.suffix.lower()
            _tools_set_tree_status(self, 'create', p, 'Processando')

            def progress(done, max_value, src=p, index=source_index):
                _tools_update_progress(
                    self,
                    'create',
                    int(done),
                    max(1, int(max_value)),
                    index - 1,
                    total_sources,
                    f'{src.name}: {done}/{max_value}'
                )

            if suffix == '.pdf':
                pages_added = _cuma_11006_append_pdf_source(out_doc, p, progress_cb=progress)
            else:
                pages_added = _cuma_11008_append_image_source(out_doc, p, progress_cb=progress)

            total_pages += pages_added
            _tools_set_tree_status(self, 'create', p, f'OK ({pages_added} pág.)')
            _tools_update_progress(self, 'create', pages_added, max(1, pages_added), source_index, total_sources, f'Concluído: {p.name}')
            debug['resultados'].append({'arquivo': str(p), 'paginas_adicionadas': pages_added})
            self.log(f'Ferramentas / Criar PDF: {p.name} → {pages_added} página(s) adicionada(s)')

        if total_pages <= 0:
            raise RuntimeError('Nenhuma página foi adicionada ao PDF.')

        output.parent.mkdir(parents=True, exist_ok=True)
        tmp_output.unlink(missing_ok=True)
        _tools_update_progress(self, 'create', total_pages, max(1, total_pages), total_sources, total_sources, 'Salvando PDF...')
        out_doc.save(str(tmp_output), garbage=4, deflate=True)
        _cuma_11008_replace_atomically(tmp_output, output)
        debug['status'] = 'ok'
        debug['total_paginas'] = total_pages
        self.log(f'Ferramentas / Criar PDF: {len(paths)} arquivo(s), {total_pages} página(s) → {output}')
        self.tools_debug_var.set(f'PDF criado com {total_pages} página(s) de {len(paths)} arquivo(s): {output}')
        _tools_update_progress(self, 'create', total_pages, max(1, total_pages), total_sources, total_sources, f'PDF criado: {output.name}')
        if self.tools_pdf_open_after.get():
            open_folder(output)
        messagebox.showinfo('Criar PDF', f'PDF criado:\n{output}')
    except Exception as exc:
        tmp_output.unlink(missing_ok=True)
        debug['status'] = 'erro'
        debug['erro'] = friendly_error(exc)
        write_error_log(type(exc), exc, exc.__traceback__, 'Erro na ferramenta Criar PDF multiformato')
        messagebox.showerror('Criar PDF', friendly_error(exc))
    finally:
        try:
            out_doc.close()
        except Exception:
            pass
        try:
            (runtime_dir() / 'debug_ferramentas_criar_pdf_multiformato.json').write_text(json.dumps(debug, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        except Exception:
            pass


def _cuma_11008_first_preview_image(path: Path):
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        doc = fitz.open(str(path))
        try:
            if len(doc) <= 0:
                return None
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            return Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
        finally:
            doc.close()
    if suffix in SUPPORTED_IMAGE_EXT:
        with Image.open(path) as opened:
            for img in _cuma_11006_iter_opened_image(opened):
                return img
        return None
    if suffix in CUMA_11006_ARCHIVE_EXTS:
        iterator = _cuma_11008_iter_archive_images_for_create(path)
        try:
            return next(iterator)
        except StopIteration:
            return None
    return None


def _cuma_11008_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11008_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11008_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11008_VERSION,
            'date': '2026-06-23',
            'items': [
                'Correções da auditoria: CBZ/ZIP, CBR/RAR/7Z, escrita atômica e validação de arquivos.',
                'Ferramentas e Converter ficaram mais robustos contra arquivos parciais e entradas inválidas.',
                'Pacote de release ajustado para não incluir dados locais do usuário.'
            ]
        }
        if 'cuma_version_apply_globals' in globals():
            try:
                cuma_version_apply_globals(CUMA_11008_VERSION)
            except Exception:
                pass
        if 'cuma_settings_load' in globals() and 'cuma_settings_save' in globals():
            try:
                data = cuma_settings_load()
                if isinstance(data, dict):
                    version_payload = data.get('version') if isinstance(data.get('version'), dict) else {}
                    version_payload.update({
                        'version': CUMA_11008_VERSION,
                        'updated_at': '2026-06-23',
                        'notes': 'Correções de auditoria, robustez de escrita e empacotamento.'
                    })
                    data['version'] = version_payload
                    cuma_settings_save(data)
            except Exception as exc:
                _cuma_11008_log('Atualizar settings de versão 1.100.8', exc)
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            try:
                state = cuma_version_load_state()
                if not isinstance(state, dict):
                    state = {}
                events = state.get('events', [])
                if not isinstance(events, list):
                    events = []
                if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11008_UPDATE_ID for e in events):
                    events.append({
                        'update_id': CUMA_11008_UPDATE_ID,
                        'version': CUMA_11008_VERSION,
                        'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                        'scale': 'pouca',
                        'description': 'Correções de auditoria: escrita atômica, validações, compactados e limpeza do pacote.',
                        'timestamp': datetime.now().isoformat(timespec='seconds')
                    })
                state['events'] = events[-100:]
                state['current_version'] = CUMA_11008_VERSION
                state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
                cuma_version_save_state(state)
                if '_cuma_version_write_public_files' in globals():
                    _cuma_version_write_public_files(state)
            except Exception as exc:
                _cuma_11008_log('Versionamento 1.100.8', exc)
    except Exception as exc:
        _cuma_11008_log('Forçar versão 1.100.8', exc)


def _cuma_install_11008_audit_fixes() -> None:
    try:
        globals()['_cuma_11000_create_image_epub_from_iter'] = _cuma_11008_create_image_epub_from_iter
        globals()['_cuma_11000_create_image_epub'] = _cuma_11008_create_image_epub
        globals()['_cuma_11000_create_image_epub_from_pdf'] = _cuma_11008_create_image_epub_from_pdf
        globals()['_cuma_11000_create_epub_from_archive'] = _cuma_11008_create_epub_from_archive
        globals()['_cuma_11000_iter_archive_images'] = _cuma_11008_iter_archive_images
        globals()['_cuma_11000_iter_epub_images'] = _cuma_11008_iter_epub_images
        globals()['_cuma_11002_iter_archive_images_raw'] = _cuma_11008_iter_archive_images_raw
        globals()['_cuma_11002_iter_epub_images_raw'] = _cuma_11008_iter_epub_images_raw
        globals()['_cuma_11001_create_pdf_from_image_iter'] = _cuma_11008_create_pdf_from_image_iter
        globals()['_cuma_11001_create_cbz_from_image_iter'] = _cuma_11008_create_cbz_from_image_iter
        globals()['_cuma_11006_accept_create_path'] = _cuma_11008_accept_create_path
        globals()['_tools_accept_path'] = _tools_accept_path
        globals()['_tools_process_create_pdf'] = _tools_process_create_pdf
        globals()['_cuma_11006_iter_archive_images'] = _cuma_11008_iter_archive_images_for_create
        globals()['_cuma_11006_iter_source_images'] = _cuma_11008_iter_source_images_for_create
        globals()['_cuma_11006_append_image_source'] = _cuma_11008_append_image_source
        globals()['_cuma_11006_first_preview_image'] = _cuma_11008_first_preview_image
        try:
            BaseApp.create_pdf_from_images_dialog = lambda self: _tools_process_create_pdf(self, selected=False)
        except Exception:
            pass
        _cuma_11008_force_version()
    except Exception as exc:
        _cuma_11008_log('Instalação patch 1.100.8', exc)


_cuma_install_11008_audit_fixes()


CUMA_11008_MANUAL_TEXT = (
    globals().get('CUMA_11007_MANUAL_TEXT', '')
    .replace('1.100.7', '1.100.8')
    + '''

===============================================================================
16. CORREÇÕES DE AUDITORIA - 1.100.8
===============================================================================

Esta versão corrigiu problemas internos encontrados na auditoria de código:

• CBZ/ZIP no Converter: corrigida a leitura das imagens internas.
• CBR/RAR/7Z no Converter: corrigido o uso de diretório temporário.
• Saídas EPUB, CBZ e PDF: agora usam arquivo temporário e substituição atômica.
• Ferramentas: validação reforçada para aceitar apenas arquivos existentes.
• Limpar PDF: "Sempre manter primeira página" agora força a preservação da página.
• Release: dados locais do usuário não são incluídos no ZIP.
• Build: o BAT copia os arquivos de documentação e chama o script de manifesto.
• Dependências: requirements.txt usa faixas de versão.
'''
)

CUMA_11008_README_TXT = '''CUMA - Conversor Ultimate de Mangás
Versão: 1.100.8

COMO USAR
1. Extraia o ZIP inteiro.
2. Abra cuma.exe.
3. Não apague a pasta _internal.
4. O manual completo está em manual_do_programa.txt.
5. O resumo das mudanças recentes está em ATUALIZACOES_DESDE_1.100.2.txt.
6. O relatório das correções está em AUDITORIA_CORRECOES_1.100.8.txt.

CORREÇÕES DA 1.100.8
- Corrigido CBZ/ZIP no Converter.
- Corrigido CBR/RAR/7Z no Converter quando 7-Zip estiver instalado.
- EPUB, CBZ e PDFs gerados agora usam escrita temporária/atômica.
- Ferramentas validam arquivos existentes antes de processar.
- O pacote não inclui .cuma_user_data/cuma_settings.json.
- O build prepara o manifesto de atualização com SHA256/tamanho do ZIP final.

DADOS DO USUÁRIO
As configurações ficam em:
%APPDATA%\\CUMA\\cuma_settings.json

Não distribua a pasta limpos/, arquivos convertidos, CUMA.log, erro.txt, debug_completo_cuma.txt ou .cuma_user_data.
'''


def ensure_manual() -> Path:
    try:
        manual_path().write_text(CUMA_11008_MANUAL_TEXT, encoding='utf-8')
    except Exception as exc:
        _cuma_11008_log('Falha ao gerar manual 1.100.8', exc)
    return manual_path()


def _cuma_11008_write_readme() -> None:
    try:
        (app_dir() / 'LEIA-ME.txt').write_text(CUMA_11008_README_TXT, encoding='utf-8')
    except Exception as exc:
        _cuma_11008_log('Falha ao atualizar LEIA-ME 1.100.8', exc)


def _cuma_11008_write_runtime_docs() -> None:
    try:
        ensure_manual()
    except Exception:
        pass
    try:
        _cuma_11008_write_readme()
    except Exception:
        pass


_cuma_11008_write_runtime_docs()



# =============================================================================
# CUMA 1.100.9 - AJUSTE FINAL DA JANELA DE ATUALIZAÇÃO
# =============================================================================
# Mantém o rodapé com botões sempre visível, mesmo com notas de release longas.
# A área de detalhes usa rolagem vertical fixa; quando há update, o botão Baixar
# aparece habilitado. Quando não há pacote para baixar, permanece apenas Cancelar.

CUMA_11009_UPDATE_ID = 'update_dialog_fixed_footer_11009'
CUMA_11009_VERSION = '1.100.9'


def _cuma_show_themed_update_dialog(app, state='none', title='Procurar atualizações',
                                    heading=None, message=None, details=None,
                                    download_url='', sha256='', size_bytes=0,
                                    release_notes='') -> None:
    try:
        pal = _cuma_update_dialog_palette(app)
        root = app.root
        top = tk.Toplevel(root)
        top.title(title or 'Procurar atualizações')
        top.configure(bg=pal['bg'])
        top.resizable(True, True)
        try:
            top.minsize(580, 360)
        except Exception:
            pass
        try:
            top.transient(root)
            top.grab_set()
        except Exception:
            pass

        width, height = 640, 500
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            x = rx + max(0, (rw - width) // 2)
            y = ry + max(0, (rh - height) // 2)
            top.geometry(f'{width}x{height}+{x}+{y}')
        except Exception:
            top.geometry(f'{width}x{height}')

        container = tk.Frame(top, bg=pal['surface'], bd=0,
                             highlightthickness=1, highlightbackground=pal['border'])
        container.pack(fill='both', expand=True, padx=1, pady=1)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)

        accent_color = pal['accent']
        icon_text = 'i'
        if state == 'available':
            accent_color = pal['accent']
            icon_text = '↓'
            heading = heading or 'Atualização disponível'
        elif state == 'error':
            accent_color = pal['danger']
            icon_text = '!'
            heading = heading or 'Não foi possível verificar atualizações'
        else:
            accent_color = pal['success']
            icon_text = '✓'
            heading = heading or 'Não há atualizações. Aguarde...'

        top_bar = tk.Frame(container, bg=accent_color, height=4)
        top_bar.grid(row=0, column=0, sticky='ew')
        try:
            top_bar.grid_propagate(False)
        except Exception:
            pass

        header = tk.Frame(container, bg=pal['surface'], padx=24, pady=20)
        header.grid(row=1, column=0, sticky='ew')
        header.grid_columnconfigure(1, weight=1)

        icon = tk.Canvas(header, width=54, height=54, bg=pal['surface'], highlightthickness=0)
        icon.grid(row=0, column=0, sticky='nw', padx=(0, 16))
        icon.create_oval(4, 4, 50, 50, fill=accent_color, outline=accent_color)
        icon.create_text(27, 27, text=icon_text, fill=pal['button_fg'], font=('Segoe UI', 22, 'bold'))

        title_box = tk.Frame(header, bg=pal['surface'])
        title_box.grid(row=0, column=1, sticky='ew')
        tk.Label(title_box, text=_cuma_update_safe_text(heading, 'Procurar atualizações'),
                 bg=pal['surface'], fg=pal['fg'], font=('Segoe UI', 14, 'bold'),
                 anchor='w', justify='left').pack(fill='x', anchor='w')

        sub = 'Verificação concluída pelo GitHub Releases.'
        if state == 'available':
            sub = 'Existe um pacote novo publicado para baixar.'
        elif state == 'error':
            sub = 'Confira sua conexão ou o manifesto de atualização.'
        tk.Label(title_box, text=sub, bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 9), anchor='w', justify='left').pack(fill='x', anchor='w', pady=(4, 0))

        body = tk.Frame(container, bg=pal['surface'], padx=24, pady=0)
        body.grid(row=2, column=0, sticky='nsew')
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        msg = _cuma_update_safe_text(message, 'Nenhuma informação adicional foi recebida.')
        msg_label = tk.Label(body, text=msg, bg=pal['surface'], fg=pal['fg'],
                             font=('Segoe UI', 10), anchor='nw', justify='left',
                             wraplength=570)
        msg_label.grid(row=0, column=0, sticky='ew', pady=(0, 12))

        info_box = tk.Frame(body, bg=pal['surface2'], highlightthickness=1,
                            highlightbackground=pal['border'])
        info_box.grid(row=1, column=0, sticky='nsew')
        info_box.grid_columnconfigure(0, weight=1)
        info_box.grid_rowconfigure(0, weight=1)

        text_box = tk.Text(info_box, wrap='word', bg=pal['surface2'], fg=pal['fg'],
                           insertbackground=pal['fg'], relief='flat', bd=0,
                           font=('Segoe UI', 9), padx=12, pady=10)
        text_box.grid(row=0, column=0, sticky='nsew')

        scroll = tk.Scrollbar(info_box, orient='vertical', command=text_box.yview,
                              bg=pal['surface2'], activebackground=pal['drop'],
                              troughcolor=pal['bg'], relief='flat', bd=0)
        scroll.grid(row=0, column=1, sticky='ns')
        text_box.configure(yscrollcommand=scroll.set)

        lines = []
        if details:
            lines.append(_cuma_update_safe_text(details, ''))
        if download_url:
            lines.append('')
            lines.append('Link de download:')
            lines.append(str(download_url))
        if sha256:
            lines.append('')
            lines.append('SHA256:')
            lines.append(str(sha256))
        if size_bytes:
            lines.append('')
            lines.append('Tamanho:')
            lines.append(_cuma_update_human_size(size_bytes))
        if release_notes:
            lines.append('')
            lines.append('Novidades:')
            lines.append(_cuma_update_safe_text(release_notes, ''))

        text_box.insert('1.0', '\n'.join(lines).strip() or 'Sem detalhes extras.')
        text_box.configure(state='disabled')

        actions = tk.Frame(container, bg=pal['surface'], padx=24, pady=(14, 18))
        actions.grid(row=3, column=0, sticky='ew')
        actions.grid_columnconfigure(0, weight=1)

        def make_button(text_label, command, primary=False, enabled=True):
            bg = accent_color if primary else pal['surface2']
            fg = pal['button_fg'] if primary else pal['fg']
            active = pal['drop'] if not primary else pal['accent']
            btn = tk.Button(actions, text=text_label, command=command, bg=bg, fg=fg,
                            activebackground=active, activeforeground=fg,
                            disabledforeground=pal['muted'], relief='flat', bd=0,
                            padx=18, pady=9,
                            font=('Segoe UI', 9, 'bold' if primary else 'normal'),
                            cursor='hand2' if enabled else 'arrow',
                            state='normal' if enabled else 'disabled')
            btn.pack(side='right', padx=(8, 0))
            return btn

        def open_download():
            try:
                import webbrowser
                webbrowser.open(str(download_url))
            except Exception as exc:
                try:
                    write_log(f'Falha ao abrir download: {exc}')
                except Exception:
                    pass

        # O botão Cancelar/Fechar é sempre criado no rodapé fixo.
        make_button('Cancelar', top.destroy, primary=False, enabled=True)

        # O botão Baixar só aparece habilitado quando realmente há link de update.
        if state == 'available' and str(download_url or '').strip():
            make_button('Baixar', open_download, primary=True, enabled=True)

        try:
            top.bind('<Escape>', lambda _e: top.destroy())
            top.focus_force()
            text_box.yview_moveto(0)
        except Exception:
            pass
    except Exception as exc:
        fallback = _cuma_update_safe_text(message or exc, 'Não foi possível verificar atualizações.')
        try:
            messagebox.showinfo(title or 'Procurar atualizações', fallback)
        except Exception:
            pass


def _cuma_11009_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11009_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11009_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11009_VERSION,
            'date': '2026-06-23',
            'items': [
                'Janela de atualização com rodapé fixo.',
                'Botão Baixar sempre visível quando há atualização disponível.',
                'Botão Cancelar sempre visível e área de detalhes com rolagem vertical.',
                'Build Windows passa a usar a pasta dist\\CUMA_windows e script de informações SHA256/tamanho.'
            ],
        }
        if 'cuma_version_apply_globals' in globals():
            try:
                cuma_version_apply_globals(CUMA_11009_VERSION)
            except Exception:
                pass
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            try:
                state = cuma_version_load_state()
                events = state.get('events', [])
                if not isinstance(events, list):
                    events = []
                if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11009_UPDATE_ID for e in events):
                    events.append({
                        'update_id': CUMA_11009_UPDATE_ID,
                        'version': CUMA_11009_VERSION,
                        'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                        'scale': 'pouca',
                        'applied_at': datetime.now().isoformat(timespec='seconds'),
                        'description': 'Correção do layout da janela de atualizações e ajustes no build Windows.',
                    })
                state['events'] = events[-100:]
                state['current_version'] = CUMA_11009_VERSION
                state['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
                cuma_version_save_state(state)
                if '_cuma_version_write_public_files' in globals():
                    _cuma_version_write_public_files(state)
            except Exception:
                pass
    except Exception:
        pass


_cuma_11009_force_version()


CUMA_11009_MANUAL_TEXT = (
    globals().get('CUMA_11008_MANUAL_TEXT', '')
    .replace('1.100.8', '1.100.9')
    + """

===============================================================================
17. AJUSTE DO ATUALIZADOR - 1.100.9
===============================================================================

Esta atualização corrige somente o layout da janela "Procurar atualizações".

- O rodapé da janela agora fica fixo.
- O botão Cancelar aparece sempre.
- Quando há atualização disponível e há link de download, o botão Baixar aparece habilitado.
- A caixa de detalhes possui rolagem vertical para notas grandes, SHA256, tamanho e link.
- O build Windows passa a gerar a pasta dist\\CUMA_windows.
- O arquivo gerar_info_release.bat calcula SHA256 e tamanho do CUMA_windows.zip.
"""
)

CUMA_11009_README_TXT = """CUMA - Conversor Ultimate de Mangás
Versão: 1.100.9

COMO USAR
1. Extraia o ZIP inteiro.
2. Abra cuma.exe.
3. Não apague a pasta _internal.
4. O manual completo está em manual_do_programa.txt.

CORREÇÃO DA 1.100.9
- Janela de atualização com rodapé fixo.
- Botão Cancelar sempre visível.
- Botão Baixar aparece quando há atualização disponível.
- Área de detalhes com rolagem vertical.
- Build Windows ajustado para pasta dist\\CUMA_windows.
- gerar_info_release.bat calcula SHA256 e tamanho do CUMA_windows.zip.
"""


def ensure_manual() -> Path:
    try:
        manual_path().write_text(CUMA_11009_MANUAL_TEXT, encoding='utf-8')
    except Exception:
        pass
    return manual_path()


def _cuma_11009_write_runtime_docs() -> None:
    try:
        ensure_manual()
    except Exception:
        pass
    try:
        (app_dir() / 'LEIA-ME.txt').write_text(CUMA_11009_README_TXT, encoding='utf-8')
    except Exception:
        pass


_cuma_11009_write_runtime_docs()



# =============================================================================
# CUMA 1.100.10 - CORREÇÃO DEFINITIVA DO RODAPÉ DO ATUALIZADOR
# =============================================================================
# Corrige o caso em que a caixa de detalhes crescia e escondia os botões.
# O rodapé agora é reservado antes da área expansível: Cancelar sempre aparece;
# Baixar aparece apenas quando há atualização disponível com link de download.

CUMA_11010_UPDATE_ID = 'update_dialog_footer_visible_11010'
CUMA_11010_VERSION = '1.100.10'


def _cuma_show_themed_update_dialog(app, state='none', title='Procurar atualizações',
                                    heading=None, message=None, details=None,
                                    download_url='', sha256='', size_bytes=0,
                                    release_notes='') -> None:
    try:
        pal = _cuma_update_dialog_palette(app)
        root = app.root
        top = tk.Toplevel(root)
        top.title(title or 'Procurar atualizações')
        top.configure(bg=pal['bg'])
        top.resizable(True, True)
        try:
            top.minsize(600, 420)
        except Exception:
            pass
        try:
            top.transient(root)
            top.grab_set()
        except Exception:
            pass

        width, height = 660, 520
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            x = rx + max(0, (rw - width) // 2)
            y = ry + max(0, (rh - height) // 2)
            top.geometry(f'{width}x{height}+{x}+{y}')
        except Exception:
            top.geometry(f'{width}x{height}')

        container = tk.Frame(top, bg=pal['surface'], bd=0,
                             highlightthickness=1, highlightbackground=pal['border'])
        container.pack(fill='both', expand=True, padx=1, pady=1)

        accent_color = pal['accent']
        icon_text = 'i'
        if state == 'available':
            accent_color = pal['accent']
            icon_text = '↓'
            heading = heading or 'Atualização disponível'
        elif state == 'error':
            accent_color = pal['danger']
            icon_text = '!'
            heading = heading or 'Não foi possível verificar atualizações'
        else:
            accent_color = pal['success']
            icon_text = '✓'
            heading = heading or 'Não há atualizações. Aguarde...'

        top_bar = tk.Frame(container, bg=accent_color, height=4)
        top_bar.pack(side='top', fill='x')
        try:
            top_bar.pack_propagate(False)
        except Exception:
            pass

        header = tk.Frame(container, bg=pal['surface'], padx=24, pady=(20, 14))
        header.pack(side='top', fill='x')

        icon = tk.Canvas(header, width=54, height=54, bg=pal['surface'], highlightthickness=0)
        icon.pack(side='left', padx=(0, 16), anchor='n')
        icon.create_oval(4, 4, 50, 50, fill=accent_color, outline=accent_color)
        icon.create_text(27, 27, text=icon_text, fill=pal['button_fg'], font=('Segoe UI', 22, 'bold'))

        title_box = tk.Frame(header, bg=pal['surface'])
        title_box.pack(side='left', fill='x', expand=True)
        tk.Label(title_box, text=_cuma_update_safe_text(heading, 'Procurar atualizações'),
                 bg=pal['surface'], fg=pal['fg'], font=('Segoe UI', 14, 'bold'),
                 anchor='w', justify='left').pack(fill='x', anchor='w')

        sub = 'Verificação concluída pelo GitHub Releases.'
        if state == 'available':
            sub = 'Existe um pacote novo publicado para baixar.'
        elif state == 'error':
            sub = 'Confira sua conexão ou o manifesto de atualização.'
        tk.Label(title_box, text=sub, bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 9), anchor='w', justify='left').pack(fill='x', anchor='w', pady=(4, 0))

        # O rodapé é empacotado ANTES do corpo expansível para reservar espaço.
        actions = tk.Frame(container, bg=pal['surface'], padx=24, pady=(10, 16))
        actions.pack(side='bottom', fill='x')

        def make_button(text_label, command, primary=False, enabled=True):
            bg = accent_color if primary else pal['surface2']
            fg = pal['button_fg'] if primary else pal['fg']
            active = pal['drop'] if not primary else pal['accent']
            btn = tk.Button(actions, text=text_label, command=command, bg=bg, fg=fg,
                            activebackground=active, activeforeground=fg,
                            disabledforeground=pal['muted'], relief='flat', bd=0,
                            padx=20, pady=9,
                            font=('Segoe UI', 9, 'bold' if primary else 'normal'),
                            cursor='hand2' if enabled else 'arrow',
                            state='normal' if enabled else 'disabled')
            btn.pack(side='right', padx=(8, 0))
            return btn

        def open_download():
            try:
                import webbrowser
                webbrowser.open(str(download_url))
            except Exception as exc:
                try:
                    write_log(f'Falha ao abrir download: {exc}')
                except Exception:
                    pass

        # Cancelar sempre visível.
        make_button('Cancelar', top.destroy, primary=False, enabled=True)

        # Baixar aparece só quando existe atualização e existe link.
        if state == 'available' and str(download_url or '').strip():
            make_button('Baixar', open_download, primary=True, enabled=True)

        body = tk.Frame(container, bg=pal['surface'], padx=24, pady=(0, 0))
        body.pack(side='top', fill='both', expand=True)

        msg = _cuma_update_safe_text(message, 'Nenhuma informação adicional foi recebida.')
        msg_label = tk.Label(body, text=msg, bg=pal['surface'], fg=pal['fg'],
                             font=('Segoe UI', 10), anchor='nw', justify='left',
                             wraplength=590)
        msg_label.pack(side='top', fill='x', anchor='w', pady=(0, 12))

        info_box = tk.Frame(body, bg=pal['surface2'], highlightthickness=1,
                            highlightbackground=pal['border'])
        info_box.pack(side='top', fill='both', expand=True)

        text_box = tk.Text(info_box, height=8, wrap='word', bg=pal['surface2'], fg=pal['fg'],
                           insertbackground=pal['fg'], relief='flat', bd=0,
                           font=('Segoe UI', 9), padx=12, pady=10)
        text_box.pack(side='left', fill='both', expand=True)

        scroll = tk.Scrollbar(info_box, orient='vertical', command=text_box.yview,
                              bg=pal['surface2'], activebackground=pal['drop'],
                              troughcolor=pal['bg'], relief='flat', bd=0)
        scroll.pack(side='right', fill='y')
        text_box.configure(yscrollcommand=scroll.set)

        lines = []
        if details:
            lines.append(_cuma_update_safe_text(details, ''))
        if download_url:
            lines.append('')
            lines.append('Link de download:')
            lines.append(str(download_url))
        if sha256:
            lines.append('')
            lines.append('SHA256:')
            lines.append(str(sha256))
        if size_bytes:
            lines.append('')
            lines.append('Tamanho:')
            lines.append(_cuma_update_human_size(size_bytes))
        if release_notes:
            lines.append('')
            lines.append('Novidades:')
            lines.append(_cuma_update_safe_text(release_notes, ''))

        text_box.insert('1.0', '\n'.join(lines).strip() or 'Sem detalhes extras.')
        text_box.configure(state='disabled')

        try:
            top.bind('<Escape>', lambda _e: top.destroy())
            top.focus_force()
            text_box.yview_moveto(0)
            actions.lift()
        except Exception:
            pass
    except Exception as exc:
        fallback = _cuma_update_safe_text(message or exc, 'Não foi possível verificar atualizações.')
        try:
            messagebox.showinfo(title or 'Procurar atualizações', fallback)
        except Exception:
            pass


def _cuma_11010_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11010_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11010_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11010_VERSION,
            'date': '2026-06-23',
            'items': [
                'Corrige o rodapé da janela de atualizações para nunca ficar escondido.',
                'Botão Cancelar fica sempre visível.',
                'Botão Baixar aparece quando há atualização disponível com link.',
                'Caixa de detalhes mantém barra de rolagem vertical.'
            ],
        }
        if 'cuma_version_apply_globals' in globals():
            try:
                cuma_version_apply_globals(CUMA_11010_VERSION)
            except Exception:
                pass
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            try:
                state_data = cuma_version_load_state()
                events = state_data.get('events', [])
                if not isinstance(events, list):
                    events = []
                if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11010_UPDATE_ID for e in events):
                    events.append({
                        'update_id': CUMA_11010_UPDATE_ID,
                        'version': CUMA_11010_VERSION,
                        'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                        'scale': 'pouca',
                        'applied_at': datetime.now().isoformat(timespec='seconds'),
                        'description': 'Correção definitiva do rodapé da janela de atualizações.',
                    })
                state_data['events'] = events[-100:]
                state_data['current_version'] = CUMA_11010_VERSION
                state_data['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
                cuma_version_save_state(state_data)
                if '_cuma_version_write_public_files' in globals():
                    _cuma_version_write_public_files(state_data)
            except Exception:
                pass
    except Exception:
        pass


_cuma_11010_force_version()


CUMA_11010_MANUAL_TEXT = (
    globals().get('CUMA_11009_MANUAL_TEXT', globals().get('CUMA_11008_MANUAL_TEXT', ''))
    .replace('1.100.9', '1.100.10')
    + """

===============================================================================
18. CORREÇÃO DEFINITIVA DO ATUALIZADOR - 1.100.10
===============================================================================

Esta atualização corrige a janela "Procurar atualizações" para que o rodapé nunca
fique escondido pela caixa de detalhes.

- O botão Cancelar aparece sempre no rodapé.
- Quando há atualização disponível e link de download, o botão Baixar aparece habilitado.
- Quando não há atualização, fica apenas Cancelar.
- A caixa de detalhes possui barra de rolagem vertical.
"""
)

CUMA_11010_README_TXT = """CUMA - Conversor Ultimate de Mangás
Versão: 1.100.10

COMO USAR
1. Extraia o ZIP inteiro.
2. Abra cuma.exe.
3. Não apague a pasta _internal.
4. O manual completo está em manual_do_programa.txt.

CORREÇÃO DA 1.100.10
- Rodapé da janela de atualização corrigido para ficar sempre visível.
- Botão Cancelar sempre visível.
- Botão Baixar aparece quando há atualização disponível.
- Caixa de detalhes com barra de rolagem vertical.
"""


def ensure_manual() -> Path:
    try:
        manual_path().write_text(CUMA_11010_MANUAL_TEXT, encoding='utf-8')
    except Exception:
        pass
    return manual_path()


def _cuma_11010_write_runtime_docs() -> None:
    try:
        ensure_manual()
    except Exception:
        pass
    try:
        (app_dir() / 'LEIA-ME.txt').write_text(CUMA_11010_README_TXT, encoding='utf-8')
    except Exception:
        pass


_cuma_11010_write_runtime_docs()




# =============================================================================
# CUMA 1.100.12 - ATUALIZADOR AUTOMÁTICO VIA GITHUB RELEASES
# =============================================================================
# Mantém a opção manual e adiciona a opção automática:
# - Atualizar agora: baixa o ZIP, valida SHA256, inicia cuma_updater.exe temporário,
#   fecha o CUMA e deixa o atualizador substituir os arquivos.
# - Baixar manualmente: abre o link da release para o usuário instalar quando quiser.

CUMA_11012_UPDATE_ID = 'github_auto_updater_external_11012'
CUMA_11012_VERSION = '1.100.12'


def _cuma_auto_update_install_dir() -> Path:
    try:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
    except Exception:
        pass
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return app_dir()


def _cuma_auto_update_valid_sha256(value: str) -> str:
    try:
        text = str(value or '').strip().upper()
    except Exception:
        return ''
    if not text or 'COLOQUE' in text or 'PLACEHOLDER' in text:
        return ''
    text = ''.join(ch for ch in text if ch in '0123456789ABCDEF')
    return text if len(text) == 64 else ''


def _cuma_auto_update_verify_sha_enabled() -> bool:
    try:
        settings = cuma_settings_load()
        updates = settings.get('updates', {}) if isinstance(settings, dict) else {}
        if isinstance(updates, dict):
            return bool(updates.get('verify_sha256', True))
    except Exception:
        pass
    return True


def _cuma_auto_update_sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def _cuma_auto_update_download_file(url: str, dest: Path, expected_size: int = 0,
                                    progress_cb: Optional[Callable[[str], None]] = None) -> None:
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        str(url),
        headers={'User-Agent': 'CUMA-Auto-Updater/1.100.12'}
    )
    downloaded = 0
    last_report = 0.0
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = expected_size
        try:
            header_size = int(resp.headers.get('Content-Length') or 0)
            if not total and header_size:
                total = header_size
        except Exception:
            pass

        with dest.open('wb') as f:
            while True:
                chunk = resp.read(1024 * 512)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if progress_cb and (now - last_report > 0.35):
                    last_report = now
                    if total:
                        pct = min(100, int(downloaded * 100 / max(1, total)))
                        progress_cb(f'Baixando pacote... {pct}% ({_cuma_update_human_size(downloaded)} de {_cuma_update_human_size(total)})')
                    else:
                        progress_cb(f'Baixando pacote... {_cuma_update_human_size(downloaded)}')

    if expected_size and dest.stat().st_size != int(expected_size):
        raise RuntimeError(
            f'Tamanho do ZIP diferente do manifesto. Esperado: {expected_size}; recebido: {dest.stat().st_size}.'
        )


def _cuma_auto_update_prepare_updater_command(install_dir: Path, work_dir: Path, request_file: Path) -> list[str]:
    # O updater é copiado para uma pasta temporária antes de rodar.
    # Assim ele consegue substituir também o cuma_updater.exe da pasta instalada.
    updater_exe = install_dir / 'cuma_updater.exe'
    if updater_exe.exists():
        temp_updater = work_dir / 'cuma_updater.exe'
        shutil.copy2(updater_exe, temp_updater)
        return [str(temp_updater), '--request', str(request_file)]

    # Caminho útil para testes executando pelo Python, antes de compilar.
    try:
        updater_py = Path(__file__).resolve().with_name('cuma_updater.py')
        if updater_py.exists():
            return [sys.executable, str(updater_py), '--request', str(request_file)]
    except Exception:
        pass

    raise RuntimeError(
        'cuma_updater.exe não foi encontrado na pasta do programa. '
        'Compile novamente usando criar_exe_windows_e_zip.bat para incluir o atualizador externo.'
    )


def _cuma_auto_update_launch(payload: dict, progress_cb: Optional[Callable[[str], None]] = None) -> None:
    download_url = str(payload.get('download_url') or '').strip()
    if not download_url:
        raise RuntimeError('O manifesto não informou um link de download para a atualização.')

    if os.name != 'nt':
        raise RuntimeError('A atualização automática foi preparada para o pacote Windows do CUMA.')

    install_dir = _cuma_auto_update_install_dir()
    if not (install_dir / 'cuma.exe').exists() and getattr(sys, 'frozen', False):
        raise RuntimeError(f'Não encontrei cuma.exe na pasta de instalação: {install_dir}')

    expected_size = 0
    try:
        expected_size = int(payload.get('size_bytes', 0) or 0)
    except Exception:
        expected_size = 0

    expected_sha = _cuma_auto_update_valid_sha256(payload.get('sha256', ''))
    if _cuma_auto_update_verify_sha_enabled() and not expected_sha:
        raise RuntimeError(
            'O manifesto não contém um SHA256 válido. '
            'Por segurança, a atualização automática foi bloqueada. '
            'Use "Baixar manualmente" ou publique a release gerando o stable.json pelo script.'
        )

    temp_base = Path(tempfile.gettempdir()) / 'CUMA_updates'
    temp_base.mkdir(parents=True, exist_ok=True)
    work_dir = temp_base / f'update_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:8]}'
    work_dir.mkdir(parents=True, exist_ok=True)

    archive_path = work_dir / 'CUMA_windows.zip'
    if progress_cb:
        progress_cb('Baixando pacote de atualização...')
    _cuma_auto_update_download_file(download_url, archive_path, expected_size, progress_cb)

    if expected_sha:
        if progress_cb:
            progress_cb('Verificando SHA256 do pacote...')
        got_sha = _cuma_auto_update_sha256_file(archive_path)
        if got_sha != expected_sha:
            raise RuntimeError(f'SHA256 inválido. Esperado {expected_sha}, recebido {got_sha}.')

    main_exe_name = 'cuma.exe'
    try:
        if getattr(sys, 'frozen', False):
            main_exe_name = Path(sys.executable).name
    except Exception:
        pass

    request = {
        'schema': 'CUMA_UPDATE_REQUEST',
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'install_dir': str(install_dir),
        'archive_path': str(archive_path),
        'main_exe_name': main_exe_name,
        'main_pid': os.getpid(),
        'latest_version': str(payload.get('latest_version') or '').strip(),
        'current_version': str(payload.get('current_version') or '').strip(),
        'expected_sha256': expected_sha,
        'expected_size_bytes': expected_size,
        'download_url': download_url,
        'manifest_url': str(payload.get('manifest_url') or '').strip(),
        'keep_backup': True,
    }
    request_file = work_dir / 'update_request.json'
    request_file.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')

    cmd = _cuma_auto_update_prepare_updater_command(install_dir, work_dir, request_file)
    flags = 0
    if os.name == 'nt':
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    if progress_cb:
        progress_cb('Atualizador iniciado. O CUMA será fechado para instalar a nova versão...')
    subprocess.Popen(cmd, cwd=str(work_dir), close_fds=True, creationflags=flags)


def _cuma_force_close_for_auto_update(app) -> None:
    try:
        root = app.root
    except Exception:
        root = None

    def hard_exit():
        try:
            os._exit(0)
        except Exception:
            pass

    try:
        if root is not None:
            root.destroy()
    except Exception:
        pass

    try:
        if root is not None:
            root.after(1200, hard_exit)
    except Exception:
        # Se o loop Tk já terminou, garante encerramento mesmo assim.
        try:
            threading.Timer(1.2, hard_exit).start()
        except Exception:
            pass


def _cuma_show_themed_update_dialog(app, state='none', title='Procurar atualizações',
                                    heading=None, message=None, details=None,
                                    download_url='', sha256='', size_bytes=0,
                                    release_notes='', latest_version='',
                                    current_version='', manifest_url='', channel='',
                                    mandatory=False, **_extra) -> None:
    try:
        pal = _cuma_update_dialog_palette(app)
        root = app.root
        top = tk.Toplevel(root)
        top.title(title or 'Procurar atualizações')
        top.configure(bg=pal['bg'])
        top.resizable(True, True)
        try:
            top.minsize(620, 450)
        except Exception:
            pass
        try:
            top.transient(root)
            top.grab_set()
        except Exception:
            pass

        width, height = 700, 560
        try:
            root.update_idletasks()
            rx = root.winfo_rootx()
            ry = root.winfo_rooty()
            rw = root.winfo_width()
            rh = root.winfo_height()
            x = rx + max(0, (rw - width) // 2)
            y = ry + max(0, (rh - height) // 2)
            top.geometry(f'{width}x{height}+{x}+{y}')
        except Exception:
            top.geometry(f'{width}x{height}')

        container = tk.Frame(top, bg=pal['surface'], bd=0,
                             highlightthickness=1, highlightbackground=pal['border'])
        container.pack(fill='both', expand=True, padx=1, pady=1)

        accent_color = pal['accent']
        icon_text = 'i'
        if state == 'available':
            accent_color = pal['accent']
            icon_text = '↓'
            heading = heading or 'Atualização disponível'
        elif state == 'error':
            accent_color = pal['danger']
            icon_text = '!'
            heading = heading or 'Não foi possível verificar atualizações'
        else:
            accent_color = pal['success']
            icon_text = '✓'
            heading = heading or 'Não há atualizações. Aguarde...'

        top_bar = tk.Frame(container, bg=accent_color, height=4)
        top_bar.pack(side='top', fill='x')
        try:
            top_bar.pack_propagate(False)
        except Exception:
            pass

        header = tk.Frame(container, bg=pal['surface'], padx=24, pady=(20, 14))
        header.pack(side='top', fill='x')

        icon = tk.Canvas(header, width=54, height=54, bg=pal['surface'], highlightthickness=0)
        icon.pack(side='left', padx=(0, 16), anchor='n')
        icon.create_oval(4, 4, 50, 50, fill=accent_color, outline=accent_color)
        icon.create_text(27, 27, text=icon_text, fill=pal['button_fg'], font=('Segoe UI', 22, 'bold'))

        title_box = tk.Frame(header, bg=pal['surface'])
        title_box.pack(side='left', fill='x', expand=True)
        tk.Label(title_box, text=_cuma_update_safe_text(heading, 'Procurar atualizações'),
                 bg=pal['surface'], fg=pal['fg'], font=('Segoe UI', 14, 'bold'),
                 anchor='w', justify='left').pack(fill='x', anchor='w')

        sub = 'Verificação concluída pelo GitHub Releases.'
        if state == 'available':
            sub = 'Você pode atualizar automaticamente ou baixar o pacote manualmente.'
        elif state == 'error':
            sub = 'Confira sua conexão ou o manifesto de atualização.'
        tk.Label(title_box, text=sub, bg=pal['surface'], fg=pal['muted'],
                 font=('Segoe UI', 9), anchor='w', justify='left').pack(fill='x', anchor='w', pady=(4, 0))

        actions = tk.Frame(container, bg=pal['surface'], padx=24, pady=(10, 16))
        actions.pack(side='bottom', fill='x')

        status_var = tk.StringVar(value='')
        status_label = tk.Label(container, textvariable=status_var, bg=pal['surface'], fg=pal['muted'],
                                font=('Segoe UI', 9), anchor='w', justify='left')
        status_label.pack(side='bottom', fill='x', padx=24, pady=(0, 2))

        buttons = []

        def make_button(text_label, command, primary=False, enabled=True):
            bg = accent_color if primary else pal['surface2']
            fg = pal['button_fg'] if primary else pal['fg']
            active = pal['drop'] if not primary else pal['accent']
            btn = tk.Button(actions, text=text_label, command=command, bg=bg, fg=fg,
                            activebackground=active, activeforeground=fg,
                            disabledforeground=pal['muted'], relief='flat', bd=0,
                            padx=18, pady=9,
                            font=('Segoe UI', 9, 'bold' if primary else 'normal'),
                            cursor='hand2' if enabled else 'arrow',
                            state='normal' if enabled else 'disabled')
            btn.pack(side='right', padx=(8, 0))
            buttons.append(btn)
            return btn

        def open_download():
            try:
                import webbrowser
                webbrowser.open(str(download_url))
                status_var.set('Download manual aberto no navegador. Você decide quando instalar.')
            except Exception as exc:
                try:
                    write_log(f'Falha ao abrir download manual: {exc}')
                except Exception:
                    pass
                try:
                    messagebox.showerror('Baixar manualmente', _cuma_update_safe_text(exc, 'Falha ao abrir o link.'))
                except Exception:
                    pass

        def set_status(text_value: str) -> None:
            try:
                root.after(0, lambda value=str(text_value): status_var.set(value))
            except Exception:
                try:
                    status_var.set(str(text_value))
                except Exception:
                    pass

        def start_auto_update():
            payload = {
                'download_url': str(download_url or '').strip(),
                'sha256': str(sha256 or '').strip(),
                'size_bytes': int(size_bytes or 0) if str(size_bytes or '').strip() else 0,
                'latest_version': str(latest_version or '').strip(),
                'current_version': str(current_version or '').strip(),
                'manifest_url': str(manifest_url or '').strip(),
                'channel': str(channel or '').strip(),
            }
            try:
                for b in buttons:
                    b.configure(state='disabled', cursor='arrow')
                status_var.set('Preparando atualização automática...')
            except Exception:
                pass

            def worker():
                try:
                    _cuma_auto_update_launch(payload, set_status)
                    try:
                        root.after(350, lambda: _cuma_force_close_for_auto_update(app))
                    except Exception:
                        _cuma_force_close_for_auto_update(app)
                except Exception as exc:
                    try:
                        _cuma_patch_log_exception('Atualização automática GitHub', exc)
                    except Exception:
                        try:
                            write_log(f'Atualização automática GitHub: {exc}')
                        except Exception:
                            pass

                    def fail():
                        try:
                            for b in buttons:
                                b.configure(state='normal', cursor='hand2')
                            status_var.set('Atualização automática não concluída. Use o download manual se preferir.')
                            messagebox.showerror(
                                'Atualização automática',
                                _cuma_update_safe_text(exc, 'Não foi possível atualizar automaticamente.')
                            )
                        except Exception:
                            pass
                    try:
                        root.after(0, fail)
                    except Exception:
                        pass

            threading.Thread(target=worker, daemon=True, name='CUMA-Auto-Updater-Launcher').start()

        cancel_btn = make_button('Cancelar', top.destroy, primary=False, enabled=True)

        if state == 'available' and str(download_url or '').strip():
            manual_btn = make_button('Baixar manualmente', open_download, primary=False, enabled=True)
            auto_enabled = True
            if _cuma_auto_update_verify_sha_enabled() and not _cuma_auto_update_valid_sha256(sha256):
                auto_enabled = False
                status_var.set('Atualização automática bloqueada: o SHA256 do stable.json ainda não é válido.')
            auto_btn = make_button('Atualizar agora', start_auto_update, primary=True, enabled=auto_enabled)
        elif sha256:
            make_button('Copiar SHA256', lambda: _cuma_copy_to_clipboard(root, sha256), primary=False, enabled=True)

        body = tk.Frame(container, bg=pal['surface'], padx=24, pady=(0, 0))
        body.pack(side='top', fill='both', expand=True)

        msg = _cuma_update_safe_text(message, 'Nenhuma informação adicional foi recebida.')
        msg_label = tk.Label(body, text=msg, bg=pal['surface'], fg=pal['fg'],
                             font=('Segoe UI', 10), anchor='nw', justify='left',
                             wraplength=640)
        msg_label.pack(side='top', fill='x', anchor='w', pady=(0, 12))

        info_box = tk.Frame(body, bg=pal['surface2'], highlightthickness=1,
                            highlightbackground=pal['border'])
        info_box.pack(side='top', fill='both', expand=True)

        text_box = tk.Text(info_box, height=8, wrap='word', bg=pal['surface2'], fg=pal['fg'],
                           insertbackground=pal['fg'], relief='flat', bd=0,
                           font=('Segoe UI', 9), padx=12, pady=10)
        text_box.pack(side='left', fill='both', expand=True)

        scroll = tk.Scrollbar(info_box, orient='vertical', command=text_box.yview,
                              bg=pal['surface2'], activebackground=pal['drop'],
                              troughcolor=pal['bg'], relief='flat', bd=0)
        scroll.pack(side='right', fill='y')
        text_box.configure(yscrollcommand=scroll.set)

        lines = []
        if details:
            lines.append(_cuma_update_safe_text(details, ''))
        if download_url:
            lines.append('')
            lines.append('Link de download:')
            lines.append(str(download_url))
        if sha256:
            lines.append('')
            lines.append('SHA256:')
            lines.append(str(sha256))
        if size_bytes:
            lines.append('')
            lines.append('Tamanho:')
            lines.append(_cuma_update_human_size(size_bytes))
        if release_notes:
            lines.append('')
            lines.append('Novidades:')
            lines.append(_cuma_update_safe_text(release_notes, ''))

        text_box.insert('1.0', '\n'.join(lines).strip() or 'Sem detalhes extras.')
        text_box.configure(state='disabled')

        try:
            top.bind('<Escape>', lambda _e: top.destroy())
            top.focus_force()
            text_box.yview_moveto(0)
            actions.lift()
        except Exception:
            pass
    except Exception as exc:
        fallback = _cuma_update_safe_text(message or exc, 'Não foi possível verificar atualizações.')
        try:
            messagebox.showinfo(title or 'Procurar atualizações', fallback)
        except Exception:
            pass


def _cuma_check_updates_button_async_11012(self):
    if getattr(self, '_update_manifest_check_running', False):
        return
    self._update_manifest_check_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None:
            btn.configure(state='disabled', text='Verificando...')
    except Exception:
        pass

    def finish(payload: dict) -> None:
        self._update_manifest_check_running = False
        try:
            if btn is not None:
                btn.configure(state='normal', text='Procurar atualizações')
        except Exception:
            pass
        try:
            _cuma_show_themed_update_dialog(self, **payload)
        except Exception as exc:
            safe_message = _cuma_update_safe_text(payload.get('message') or exc, 'Não foi possível verificar atualizações.')
            try:
                messagebox.showinfo(payload.get('title', 'Procurar atualizações'), safe_message)
            except Exception:
                pass

    def worker():
        try:
            _cuma_ensure_update_settings_defaults()
            manifest_url = _cuma_update_manifest_url_from_settings()
            import urllib.request
            req = urllib.request.Request(
                manifest_url,
                headers={'User-Agent': 'CUMA-Update-Checker/1.100.12'}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                remote = json.loads(resp.read().decode('utf-8'))

            if str(remote.get('app_id', 'cuma')).lower() != 'cuma':
                raise ValueError('O manifesto remoto não parece ser do CUMA.')

            latest = str(remote.get('version', '') or '').strip()
            current = str(globals().get('APP_DISPLAY_VERSION', '1.100.12') or '1.100.12').strip()
            download_url = str(remote.get('download_url', '') or '').strip()
            remote_sha = str(remote.get('sha256', '') or '').strip()
            try:
                remote_size = int(remote.get('size_bytes', 0) or 0)
            except Exception:
                remote_size = 0
            notes = remote.get('release_notes', [])
            if isinstance(notes, list):
                notes_text = '\n'.join(f'• {str(item)}' for item in notes[:12])
            else:
                notes_text = str(notes or '')

            try:
                settings = cuma_settings_load()
                settings.setdefault('updates', {})
                if isinstance(settings.get('updates'), dict):
                    settings['updates']['last_checked_at'] = datetime.now().isoformat(timespec='seconds')
                    settings['updates']['last_available_version'] = latest
                    settings['updates']['last_manifest_url'] = manifest_url
                cuma_settings_save(settings)
            except Exception:
                pass

            latest_tuple = _cuma_update_version_tuple(latest)
            current_tuple = _cuma_update_version_tuple(current)
            channel = str(remote.get('channel', 'stable') or 'stable')
            mandatory = bool(remote.get('mandatory', False))

            if latest and latest_tuple > current_tuple:
                payload = {
                    'state': 'available',
                    'title': 'Atualização disponível',
                    'heading': f'CUMA {latest} está disponível',
                    'message': (
                        f'Você está usando a versão {current}. '
                        f'Escolha "Atualizar agora" para baixar, fechar o CUMA e instalar automaticamente, '
                        f'ou "Baixar manualmente" para instalar depois.'
                    ),
                    'details': f'Versão instalada: {current}\nVersão no GitHub: {latest}\nCanal: {channel}\nManifesto: {manifest_url}',
                    'download_url': download_url or CUMA_DEFAULT_UPDATE_DOWNLOAD_URL,
                    'sha256': remote_sha,
                    'size_bytes': remote_size,
                    'release_notes': notes_text,
                    'latest_version': latest,
                    'current_version': current,
                    'manifest_url': manifest_url,
                    'channel': channel,
                    'mandatory': mandatory,
                }
            else:
                payload = {
                    'state': 'none',
                    'title': 'Procurar atualizações',
                    'heading': 'Não há atualizações. Aguarde...',
                    'message': 'Você já está usando a versão mais recente disponível para este canal.',
                    'details': f'Versão instalada: {current}\nVersão no GitHub: {latest or "não informada"}\nCanal: {channel}\nManifesto: {manifest_url}',
                    'download_url': '',
                    'sha256': remote_sha,
                    'size_bytes': remote_size,
                    'release_notes': notes_text,
                    'latest_version': latest,
                    'current_version': current,
                    'manifest_url': manifest_url,
                    'channel': channel,
                    'mandatory': mandatory,
                }

            self.root.after(0, lambda payload=payload: finish(payload))
        except Exception as exc:
            try:
                _cuma_patch_log_exception('Verificação de atualizações GitHub', exc)
            except Exception:
                try:
                    write_log(f'Verificação de atualizações GitHub: {exc}')
                except Exception:
                    pass
            payload = {
                'state': 'error',
                'title': 'Procurar atualizações',
                'heading': 'Não foi possível verificar atualizações',
                'message': _cuma_update_safe_text(friendly_error(exc), 'Não foi possível verificar atualizações.'),
                'details': f'Erro técnico: {type(exc).__name__}: {exc}',
            }
            self.root.after(0, lambda payload=payload: finish(payload))

    threading.Thread(target=worker, daemon=True, name='CUMA-Update-Checker').start()


def _cuma_11012_force_version() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11012_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11012_VERSION} CUMA'
        globals()['CHANGELOG_LATEST'] = {
            'version': CUMA_11012_VERSION,
            'date': '2026-06-24',
            'items': [
                'Adiciona atualização automática via GitHub Releases.',
                'Mantém a opção de download manual para instalação pelo usuário.',
                'Usa cuma_updater.exe externo para fechar o CUMA e substituir arquivos com segurança.',
                'Valida SHA256 antes de instalar automaticamente.'
            ],
        }
        if 'cuma_version_apply_globals' in globals():
            try:
                cuma_version_apply_globals(CUMA_11012_VERSION)
            except Exception:
                pass
        if 'cuma_version_load_state' in globals() and 'cuma_version_save_state' in globals():
            try:
                state_data = cuma_version_load_state()
                events = state_data.get('events', [])
                if not isinstance(events, list):
                    events = []
                if not any(isinstance(e, dict) and e.get('update_id') == CUMA_11012_UPDATE_ID for e in events):
                    events.append({
                        'update_id': CUMA_11012_UPDATE_ID,
                        'version': CUMA_11012_VERSION,
                        'base_version': globals().get('CUMA_VERSION_BASE', '1.080.0'),
                        'scale': 'pouca',
                        'applied_at': datetime.now().isoformat(timespec='seconds'),
                        'description': 'Atualizador automático externo via GitHub Releases.',
                    })
                state_data['events'] = events[-100:]
                state_data['current_version'] = CUMA_11012_VERSION
                state_data['base_version'] = globals().get('CUMA_VERSION_BASE', '1.080.0')
                cuma_version_save_state(state_data)
                if '_cuma_version_write_public_files' in globals():
                    _cuma_version_write_public_files(state_data)
            except Exception:
                pass
    except Exception:
        pass


def _cuma_install_auto_updater_11012() -> None:
    try:
        _cuma_ensure_update_settings_defaults()
        globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_async_11012
    except Exception as exc:
        try:
            write_log(f'Instalação do atualizador automático 1.100.12: {exc}')
        except Exception:
            pass


_cuma_11012_force_version()
_cuma_install_auto_updater_11012()


CUMA_11012_MANUAL_APPEND = """

===============================================================================
19. ATUALIZADOR AUTOMÁTICO VIA GITHUB - 1.100.12
===============================================================================

A janela "Procurar atualizações" agora possui duas opções quando há uma versão
nova no GitHub Releases:

- Atualizar agora: baixa CUMA_windows.zip, confere o SHA256 do stable.json,
  inicia o cuma_updater.exe, fecha o CUMA e instala a nova versão.
- Baixar manualmente: abre o link do pacote para o usuário baixar e atualizar
  quando preferir.

Por segurança, a atualização automática exige SHA256 válido no stable.json.
O script criar_exe_windows_e_zip.bat gera esse valor automaticamente depois de
compactar a release.
"""

try:
    CUMA_11012_PREVIOUS_MANUAL = globals().get('CUMA_11010_MANUAL_TEXT', '')
    CUMA_11012_MANUAL_TEXT = (CUMA_11012_PREVIOUS_MANUAL or '') + CUMA_11012_MANUAL_APPEND
except Exception:
    CUMA_11012_MANUAL_TEXT = CUMA_11012_MANUAL_APPEND


def ensure_manual() -> Path:
    try:
        manual_manual_text = CUMA_11012_MANUAL_TEXT or CUMA_11012_MANUAL_APPEND
        manual_path().write_text(manual_manual_text, encoding='utf-8')
    except Exception:
        pass
    return manual_path()


def _cuma_11012_write_runtime_docs() -> None:
    try:
        ensure_manual()
    except Exception:
        pass
    try:
        readme = globals().get('CUMA_11010_README_TXT', '')
        readme = readme.replace('Versão: 1.100.10', 'Versão: 1.100.12')
        readme += """

ATUALIZADOR AUTOMÁTICO DA 1.100.12
- Botão Atualizar agora baixa, valida e instala a atualização automaticamente.
- Botão Baixar manualmente continua disponível.
- O CUMA é fechado para que os arquivos possam ser substituídos com segurança.
"""
        (app_dir() / 'LEIA-ME.txt').write_text(readme, encoding='utf-8')
    except Exception:
        pass


_cuma_11012_write_runtime_docs()


# =============================================================================
# CUMA 1.100.12 - BOTÃO DE ATUALIZAÇÃO VINCULADO AO APLICATIVO ATUALIZADOR
# =============================================================================
# O CUMA principal não baixa nem instala pacotes neste fluxo.
# O botão "Procurar atualizações" apenas abre o cuma_updater.exe em modo
# verificação. O atualizador externo consulta o stable.json, mostra as opções
# "Atualizar agora" e "Baixar manualmente", baixa, valida, fecha o CUMA e instala.

CUMA_11012_EXTERNAL_UPDATE_ID = 'external_updater_button_link_11012'
CUMA_11012_VERSION = '1.100.12'


def _cuma_11012_install_dir() -> Path:
    try:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
    except Exception:
        pass
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return app_dir()


def _cuma_11012_main_exe_name() -> str:
    try:
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).name
    except Exception:
        pass
    return 'cuma.exe'


def _cuma_11012_updater_command(manifest_url: str) -> list[str]:
    install_dir = _cuma_11012_install_dir()
    current_version = str(globals().get('APP_DISPLAY_VERSION', CUMA_11012_VERSION) or CUMA_11012_VERSION).strip()

    updater_exe = install_dir / 'cuma_updater.exe'
    updater_py = install_dir / 'cuma_updater.py'

    if updater_exe.exists():
        cmd = [str(updater_exe)]
    elif updater_py.exists():
        cmd = [sys.executable, str(updater_py)]
    else:
        raise RuntimeError(
            'Não encontrei o aplicativo de atualização.\n\n'
            f'Esperado:\n{updater_exe}\n\n'
            'Compile novamente usando "criar_exe_windows_e_zip.bat" para incluir o cuma_updater.exe.'
        )

    cmd.extend([
        '--check',
        '--manifest-url', str(manifest_url or CUMA_DEFAULT_UPDATE_MANIFEST_URL),
        '--current-version', current_version,
        '--install-dir', str(install_dir),
        '--main-pid', str(os.getpid()),
        '--main-exe-name', _cuma_11012_main_exe_name(),
    ])
    return cmd


def _cuma_check_updates_button_external_11012(self):
    """Abre o atualizador externo. A lógica de update fica fora do CUMA."""
    if getattr(self, '_external_update_launcher_running', False):
        return

    self._external_update_launcher_running = True
    btn = getattr(self, 'update_btn', None)
    try:
        if btn is not None:
            btn.configure(state='disabled', text='Abrindo atualizador...')
    except Exception:
        pass

    def restore_button():
        self._external_update_launcher_running = False
        try:
            if btn is not None:
                btn.configure(state='normal', text='Procurar atualizações')
        except Exception:
            pass

    try:
        try:
            _cuma_ensure_update_settings_defaults()
        except Exception:
            pass

        try:
            manifest_url = _cuma_update_manifest_url_from_settings()
        except Exception:
            manifest_url = CUMA_DEFAULT_UPDATE_MANIFEST_URL

        cmd = _cuma_11012_updater_command(manifest_url)

        flags = 0
        if os.name == 'nt':
            flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

        subprocess.Popen(
            cmd,
            cwd=str(_cuma_11012_install_dir()),
            close_fds=True,
            creationflags=flags,
        )

        try:
            self.root.after(1200, restore_button)
        except Exception:
            restore_button()
    except Exception as exc:
        restore_button()
        try:
            write_log(f'Falha ao abrir o atualizador externo 1.100.12: {exc}')
        except Exception:
            pass
        try:
            messagebox.showerror(
                'Procurar atualizações',
                _cuma_update_safe_text(exc, 'Não foi possível abrir o aplicativo de atualização.')
            )
        except Exception:
            pass


def _cuma_11012_force_version_and_external_updater() -> None:
    try:
        globals()['APP_DISPLAY_VERSION'] = CUMA_11012_VERSION
        globals()['APP_VERSION'] = f'{CUMA_11012_VERSION} CUMA'
        globals()['_cuma_check_updates_button'] = _cuma_check_updates_button_external_11012
        if 'cuma_version_apply_globals' in globals():
            try:
                cuma_version_apply_globals(CUMA_11012_VERSION)
            except Exception:
                pass
    except Exception:
        pass


_cuma_11012_force_version_and_external_updater()


if __name__ == '__main__':
    main()
