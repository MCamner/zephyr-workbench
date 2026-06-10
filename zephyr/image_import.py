"""Image OCR import: extract text from architecture diagrams embedded in raster images."""

from __future__ import annotations

import shutil
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from zephyr.diagram_import import parse_diagram

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif"}


def is_image_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTENSIONS


def _ocr_with_pytesseract(path: Path) -> str:
    try:
        image_module = cast(Any, import_module("PIL.Image"))
    except ImportError as exc:
        raise RuntimeError("Pillow is not installed") from exc

    try:
        pytesseract = cast(Any, import_module("pytesseract"))
    except ImportError as exc:
        raise RuntimeError("pytesseract is not installed") from exc

    with image_module.open(path) as img:
        return pytesseract.image_to_string(img)


def _ocr_with_tesseract_cli(path: Path) -> str:
    if not shutil.which("tesseract"):
        raise RuntimeError("Tesseract CLI is not installed or not found on PATH")

    result = subprocess.run(
        ["tesseract", str(path), "stdout"], capture_output=True, text=True
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown tesseract error"
        raise RuntimeError(f"tesseract failed: {stderr}")

    return result.stdout


def extract_text_from_image(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        return _ocr_with_pytesseract(path)
    except RuntimeError:
        return _ocr_with_tesseract_cli(path)


def _infer_format_from_text(text: str) -> str:
    lower = text.lower()
    if "<mxgraphmodel" in lower or "<mxcell" in lower or "<diagram" in lower:
        return "drawio"
    return "mermaid"


def parse_image(path: str | Path, format: str | None = None):
    """Parse an image file into a DiagramImportResult using OCR + diagram parsing."""
    text = extract_text_from_image(path)
    if format == "auto":
        format = None
    fmt = format or _infer_format_from_text(text)
    if fmt not in ("mermaid", "drawio"):
        raise ValueError(
            "Unsupported OCR diagram format. Use format='mermaid', format='drawio', or format='auto'."
        )
    return parse_diagram(text, fmt)
