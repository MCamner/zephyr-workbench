"""Image OCR import: extract text from architecture diagrams embedded in raster images."""

from __future__ import annotations

import re
import tempfile
import shutil
import subprocess
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from zephyr.diagram_import import DiagramImportResult, parse_diagram

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
        ["tesseract", str(path), "stdout"], capture_output=True, text=True, check=False
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
    if format not in (None, "mermaid", "drawio"):
        raise ValueError(
            "Unsupported OCR diagram format. Use mermaid, drawio, or auto."
        )
    if (
        format
        or re.search(r"(?im)^\s*(graph|flowchart)\s+", text)
        or "<mx" in text.lower()
    ):
        result = parse_diagram(text, format or _infer_format_from_text(text))
        if not result.components:
            raise ValueError(
                "OCR did not recover any diagram components. Check the source or use a raster diagram."
            )
        result.warnings.append(
            "OCR import: verify all labels and connections against the source image."
        )
        return result
    return _parse_raster(path)


def _rectangles(image) -> list[tuple[int, int, int, int]]:
    """Detect dark, axis-aligned rectangular outlines on a light background."""
    pixels = image.load()
    width, height = image.size
    lines = []
    for y in range(height):
        start = None
        for x in range(width + 1):
            dark = x < width and pixels[x, y] < 100
            if dark and start is None:
                start = x
            elif not dark and start is not None:
                if x - start >= 45:
                    lines.append((start, x - 1, y))
                start = None
    if len(lines) > 2000:
        raise ValueError(
            "Image is too complex for rectangular diagram recognition; use Mermaid/draw.io."
        )
    boxes = []
    for i, (left, right, top) in enumerate(lines):
        for l2, r2, bottom in lines[i + 1 :]:
            if bottom - top < 25 or abs(l2 - left) > 2 or abs(r2 - right) > 2:
                continue
            if all(
                sum(pixels[x, y] < 100 for y in range(top, bottom + 1))
                / (bottom - top + 1)
                > 0.95
                for x in (left, right)
            ):
                candidate = (left, top, right, bottom)
                if not any(
                    all(abs(a - b) <= 3 for a, b in zip(candidate, box))
                    for box in boxes
                ):
                    boxes.append(candidate)
                break
    # Nested containers are ambiguous: import leaf boxes only.
    return [
        box
        for box in boxes
        if not any(
            box != other
            and box[0] <= other[0]
            and box[1] <= other[1]
            and box[2] >= other[2]
            and box[3] >= other[3]
            for other in boxes
        )
    ]


def _arrow(image, start: int, end: int, cross: int, vertical=False):
    """Accept a continuous straight line with an arrowhead near one/both ends."""
    pixels = image.load()
    if end - start < 16:
        return None
    width, height = image.size
    limit = width if vertical else height
    counts = []
    center_hits = []
    for along in range(start, end + 1):
        points = [
            (offset, along) if vertical else (along, offset)
            for offset in range(max(0, cross - 10), min(limit, cross + 11))
        ]
        counts.append(sum(pixels[x, y] < 100 for x, y in points))
        center_hits.append(
            any(
                pixels[x, y] < 100
                for x, y in (
                    [
                        (offset, along) if vertical else (along, offset)
                        for offset in range(max(0, cross - 2), min(limit, cross + 3))
                    ]
                )
            )
        )
    if sum(center_hits) / len(center_hits) < 0.85:
        return None
    third = max(1, len(counts) // 3)
    at_start = max(counts[:third]) >= 7
    at_end = max(counts[-third:]) >= 7
    if at_start and at_end:
        return "bidirectional"
    if at_start:
        return "reverse"
    if at_end:
        return "forward"
    return "unknown"


def _parse_raster(path: Path) -> DiagramImportResult:
    try:
        image_module = import_module("PIL.Image")
    except ImportError as exc:
        raise RuntimeError(
            "Raster import requires Pillow: install zephyr-workbench[image]"
        ) from exc
    with image_module.open(path) as source:
        if max(source.size) > 2500:
            raise ValueError(
                "Raster import supports images up to 2500 pixels per side; crop or resize first."
            )
        image = source.convert("L")
    boxes = _rectangles(image)
    if not boxes:
        raise ValueError(
            "No rectangular components detected. Use a light-background box diagram or Mermaid/draw.io."
        )
    result = DiagramImportResult(name=path.stem, source_format="raster")
    result.warnings.append(
        "Experimental raster import: types default to application. Verify labels, arrow directions and missing connections; supports dark rectangular boxes and straight centered arrows only."
    )
    names = []
    with tempfile.TemporaryDirectory(prefix="zephyr-ocr-") as directory:
        for i, (left, top, right, bottom) in enumerate(boxes):
            crop = Path(directory) / f"node-{i}.png"
            image.crop((left + 4, top + 4, right - 3, bottom - 3)).save(crop)
            label = (
                " ".join(extract_text_from_image(crop).split()) or f"component-{i + 1}"
            )
            name = label
            suffix = 2
            while name in names:
                name = f"{label}-{suffix}"
                suffix += 1
            if name != label:
                result.warnings.append(
                    f"Duplicate OCR label {label!r}; renamed to {name!r}."
                )
            names.append(name)
            result.components.append({"name": name, "type": "application"})
    for i, a in enumerate(boxes):
        for j, b in enumerate(boxes):
            if i >= j:
                continue
            ax, ay = (a[0] + a[2]) // 2, (a[1] + a[3]) // 2
            bx, by = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
            if abs(ay - by) <= 3 and (a[2] < b[0] or b[2] < a[0]):
                first, second = (i, j) if ax < bx else (j, i)
                left, right = boxes[first], boxes[second]
                direction = _arrow(image, left[2] + 2, right[0] - 2, (ay + by) // 2)
            elif abs(ax - bx) <= 3 and (a[3] < b[1] or b[3] < a[1]):
                first, second = (i, j) if ay < by else (j, i)
                top, bottom = boxes[first], boxes[second]
                direction = _arrow(
                    image, top[3] + 2, bottom[1] - 2, (ax + bx) // 2, True
                )
            else:
                continue
            # Never bridge across another detected box.
            if direction is None:
                continue
            if direction == "unknown":
                result.warnings.append(
                    f"Line between {names[first]!r} and {names[second]!r} omitted: direction unclear."
                )
                continue
            if direction == "reverse":
                first, second = second, first
            flow = {"source": names[first], "target": names[second]}
            if direction == "bidirectional":
                flow["direction"] = "bidirectional"
            result.flows.append(flow)
    return result
